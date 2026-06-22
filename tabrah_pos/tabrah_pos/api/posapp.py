from __future__ import unicode_literals
import json
import frappe
import datetime
from frappe.utils import nowdate, flt, cstr, getdate
from frappe import _
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.stock.get_item_details import get_item_details
from erpnext.accounts.doctype.pos_profile.pos_profile import get_item_groups
from frappe.utils.background_jobs import enqueue
from erpnext.accounts.doctype.bank_account.bank_account import get_party_bank_account
from erpnext.stock.doctype.batch.batch import (
    get_batch_no,
    get_batch_qty,
    make_batch,

)
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
from erpnext.stock.get_item_details import get_item_price

from erpnext.accounts.doctype.payment_request.payment_request import (
    get_dummy_message,
    get_existing_payment_request_amount,
)

from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
    get_loyalty_program_details_with_points,
)
from tabrah_pos.tabrah_pos.doctype.pos_coupon.pos_coupon import check_coupon_code
from tabrah_pos.tabrah_pos.doctype.delivery_charges.delivery_charges import (
    get_applicable_delivery_charges as _get_applicable_delivery_charges,
)
from frappe.utils.caching import redis_cache
from frappe.utils import cint, flt


@frappe.whitelist()
def get_opening_dialog_data():
    data = {}
    data["companies"] = frappe.get_list("Company", limit_page_length=0, order_by="name")
    data["pos_profiles_data"] = frappe.get_list(
        "POS Profile",
        filters={"disabled": 0},
        fields=["name", "company", "currency","branch_cash_account","cost_center","pos_theme"],
        limit_page_length=0,
        order_by="name",
    )

    pos_profiles_list = []
    for i in data["pos_profiles_data"]:
        pos_profiles_list.append(i.name)

    payment_method_table = (
        "POS Payment Method" if get_version() == 13 else "Sales Invoice Payment"
    )
    data["payments_method"] = frappe.get_list(
        payment_method_table,
        filters={"parent": ["in", pos_profiles_list]},
        fields=["*"],
        limit_page_length=0,
        order_by="parent",
        ignore_permissions=True,
    )
    # set currency from pos profile
    for mode in data["payments_method"]:
        mode["currency"] = frappe.get_cached_value(
            "POS Profile", mode["parent"], "currency" 
        )
        mode["type"] = frappe.get_cached_value(
            "Mode of Payment", mode["mode_of_payment"], "type"
        )
    data["branch_account_balances"] = []

    for pos_profile in data["pos_profiles_data"]:
        branch_account = pos_profile.get("branch_cash_account")
        cost_center = pos_profile.get("cost_center")
        if branch_account and cost_center:
            current_date = datetime.datetime.now()
            result = frappe.db.sql(
                """
                SELECT 
                    SUM(debit) AS total_debit, 
                    SUM(credit) AS total_credit 
                FROM 
                    `tabGL Entry`
                WHERE 
                    account = %(account)s 
                    AND cost_center = %(cost_center)s 
                    AND posting_date <= %(posting_date)s
                """, 
                {"account": branch_account, "cost_center": cost_center, "posting_date": current_date},
                as_dict=True
            )

            total_debit = result[0].get("total_debit") or 0
            total_credit = result[0].get("total_credit") or 0
            balance = total_debit - total_credit
                        
            data["branch_account_balances"].append({
                "pos_profile": pos_profile.name,
                "branch_account": branch_account,
                "cost_center": cost_center,
                "total_debit": total_debit,
                "total_credit": total_credit,
                "balance": balance
            })


    return data


@frappe.whitelist()
def create_opening_voucher(pos_profile, company, balance_details):
    balance_details = json.loads(balance_details)

    new_pos_opening = frappe.get_doc(
        {
            "doctype": "POS Opening Shift",
            "period_start_date": frappe.utils.get_datetime(),
            "posting_date": frappe.utils.getdate(),
            "user": frappe.session.user,
            "pos_profile": pos_profile,
            "company": company,
            "docstatus": 1,
        }
    )
    new_pos_opening.set("balance_details", balance_details)
    new_pos_opening.insert(ignore_permissions=True)

    data = {}
    data["pos_opening_shift"] = new_pos_opening.as_dict()
    update_opening_shift_data(data, new_pos_opening.pos_profile)
    return data


@frappe.whitelist()
def check_opening_shift(user):
    open_vouchers = frappe.db.get_all(
        "POS Opening Shift",
        filters={
            "user": user,
            "pos_closing_shift": ["in", ["", None]],
            "docstatus": 1,
            "status": "Open",
        },
        fields=["name", "pos_profile"],
        order_by="period_start_date desc",
    )
    data = ""
    if len(open_vouchers) > 0:
        data = {}
        data["pos_opening_shift"] = frappe.get_doc(
            "POS Opening Shift", open_vouchers[0]["name"]
        )
        update_opening_shift_data(data, open_vouchers[0]["pos_profile"])
    return data


def update_opening_shift_data(data, pos_profile):
    data["pos_profile"] = frappe.get_doc("POS Profile", pos_profile)
    data["company"] = frappe.get_doc("Company", data["pos_profile"].company)
    allow_negative_stock = frappe.get_value(
        "Stock Settings", None, "allow_negative_stock"
    )
    data["stock_settings"] = {}
    data["stock_settings"].update({"allow_negative_stock": allow_negative_stock})


@frappe.whitelist()
def get_items(
    pos_profile, price_list=None, item_group="", search_value="", customer=None, order_type=None
):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 30

    @redis_cache(ttl=ttl or 1800)
    def __get_items(pos_profile, price_list, item_group, search_value, customer=None):
        return _get_items(pos_profile, price_list, item_group, search_value, customer)

    def _get_items(pos_profile, price_list, item_group, search_value, customer=None):
        pos_profile = json.loads(pos_profile)
        today = nowdate()
        data = dict()
        posa_display_items_in_stock = pos_profile.get("posa_display_items_in_stock")
        search_serial_no = pos_profile.get("posa_search_serial_no")
        search_batch_no = pos_profile.get("posa_search_batch_no")
        posa_show_template_items = pos_profile.get("posa_show_template_items")
        posa_hide_variants_items = pos_profile.get("posa_hide_variants_items")
        warehouse = pos_profile.get("warehouse")
        use_limit_search = pos_profile.get("pose_use_limit_search")
        search_limit = 0

            
        if not price_list:
            price_list = get_price_list(order_type) or _pos_profile.get("selling_price_list")

        limit = ""
        condition = "WHERE disabled = 0 AND is_sales_item = 1 AND is_fixed_asset = 0"
        condition += get_item_group_condition(pos_profile.get("name"))

        if posa_show_template_items:
            condition += " AND (has_variants = 0 OR variant_of IS NULL)"

        if use_limit_search:
            search_limit = pos_profile.get("posa_search_limit") or 500
            if search_value:
                data = search_serial_or_batch_or_barcode_number(
                    search_value, search_serial_no
                )

            item_code = data.get("item_code") if data.get("item_code") else search_value
            serial_no = data.get("serial_no") if data.get("serial_no") else ""
            batch_no = data.get("batch_no") if data.get("batch_no") else ""
            barcode = data.get("barcode") if data.get("barcode") else ""

            condition += get_seearch_items_conditions(
                item_code, serial_no, batch_no, barcode
            )
            if item_group:
                condition += " AND item_group like '%{item_group}%'".format(
                    item_group=item_group
                )
            limit = " LIMIT {search_limit}".format(search_limit=search_limit)

        if item_group:
            condition += " AND item_group = '{item_group}'".format(item_group=item_group)
        result = []
        if order_type:
            condition += """
                AND EXISTS (
                    SELECT 1
                    FROM `tabItem Order Type` child
                    WHERE child.parent = `tabItem`.name
                    AND child.order_type = '{order_type}'
                )
            """.format(order_type=order_type)

        items_data = frappe.db.sql(
            """
            SELECT
                name AS item_code,
                item_name,
                description,
                stock_uom,
                image,
                is_stock_item,
                has_variants,
                variant_of,
                item_group,
                idx as idx,
                has_batch_no,
                has_serial_no,
                max_discount,
                brand
            FROM
                `tabItem`
            {condition}
            ORDER BY
                item_name asc
            {limit}
            """.format(
                condition=condition, limit=limit
            ),
            as_dict=1,
        )

        if items_data:
            items = [d.item_code for d in items_data]
            item_prices_data = frappe.get_all(
                "Item Price",
                fields=["item_code", "price_list_rate", "currency", "uom","custom_discount_percentage","custom_discounted_rate"],
                filters={
                    "price_list": price_list,
                    "item_code": ["in", items],
                    "currency": pos_profile.get("currency"),
                    "selling": 1,
                    "valid_from": ["<=", today],
                    "customer": ["in", ["", None, customer]],
                },
                or_filters=[
                    ["valid_upto", ">=", today],
                    ["valid_upto", "in", ["", None]],
                ],
                order_by="valid_from ASC, valid_upto DESC",
            )

            item_prices = {}
            for d in item_prices_data:
                item_prices.setdefault(d.item_code, {})
                item_prices[d.item_code][d.get("uom") or "None"] = d

            for item in items_data:
                item_code = item.item_code
                item_price = {}
                if item_prices.get(item_code):
                    item_price = (
                        item_prices.get(item_code).get(item.stock_uom)
                        or item_prices.get(item_code).get("None")
                        or {}
                    )
                item_barcode = frappe.get_all(
                    "Item Barcode",
                    filters={"parent": item_code},
                    fields=["barcode", "posa_uom"],
                )
                batch_no_data = []
                if search_batch_no:
                    batch_list = get_batch_qty(warehouse=warehouse, item_code=item_code)
                    if batch_list:
                        for batch in batch_list:
                            if batch.qty > 0 and batch.batch_no:
                                batch_doc = frappe.get_cached_doc(
                                    "Batch", batch.batch_no
                                )
                                if (
                                    str(batch_doc.expiry_date) > str(today)
                                    or batch_doc.expiry_date in ["", None]
                                ) and batch_doc.disabled == 0:
                                    batch_no_data.append(
                                        {
                                            "batch_no": batch.batch_no,
                                            "batch_qty": batch.qty,
                                            "expiry_date": batch_doc.expiry_date,
                                            "batch_price": batch_doc.posa_batch_price,
                                            "manufacturing_date": batch_doc.manufacturing_date,
                                        }
                                    )
                serial_no_data = []
                if search_serial_no:
                    serial_no_data = frappe.get_all(
                        "Serial No",
                        filters={
                            "item_code": item_code,
                            "status": "Active",
                            "warehouse": warehouse,
                        },
                        fields=["name as serial_no"],
                    )
                item_stock_qty = 0
                # if pos_profile.get("posa_display_items_in_stock") or use_limit_search:
                #     item_stock_qty = get_stock_availability(
                #         item_code, pos_profile.get("warehouse")
                #     )
                item_stock_qty = get_stock_availability(
                        item_code, pos_profile.get("warehouse")
                    )
                attributes = ""
                if pos_profile.get("posa_show_template_items") and item.has_variants:
                    attributes = get_item_attributes(item.item_code)
                item_attributes = ""
                if pos_profile.get("posa_show_template_items") and item.variant_of:
                    item_attributes = frappe.get_all(
                        "Item Variant Attribute",
                        fields=["attribute", "attribute_value"],
                        filters={"parent": item.item_code, "parentfield": "attributes"},
                    )

                # Add tax rate and tax template from item tax template
                tax_rate_data = frappe.db.sql(
                    """
                    SELECT 
                        i.item_code AS item_code,
                        it.item_tax_template AS tax_template_name,
                        itt.tax_rate AS tax_rate
                    FROM 
                        `tabItem` i
                    LEFT JOIN 
                        `tabItem Tax` it ON i.name = it.parent
                    LEFT JOIN 
                        `tabItem Tax Template Detail` itt ON it.item_tax_template = itt.parent
                    WHERE 
                        i.item_code = '{item_code}'
                    """.format(item_code=item_code),
                    as_dict=1,
                )

                tax_template_name = tax_rate_data[0]["tax_template_name"] if tax_rate_data else None
                tax_rate = tax_rate_data[0]["tax_rate"] if tax_rate_data else None

                if posa_display_items_in_stock and (
                    not item_stock_qty or item_stock_qty < 0
                ):
                    pass
                else:
                    row = {}
                    row.update(item)
                    row.update(
                        {
                            "rate": item_price.get("price_list_rate") or 0,
                            "currency": item_price.get("currency")
                            or pos_profile.get("currency"),
                            "uom": item_price.get("uom") or "None",
                            "custom_discount_percentage": item_price.get("custom_discount_percentage") or 0,
                            "custom_discounted_rate": item_price.get("custom_discounted_rate") or 0,
                            "item_barcode": item_barcode or [],
                            "actual_qty": item_stock_qty or 0,
                            "serial_no_data": serial_no_data or [],
                            "batch_no_data": batch_no_data or [],
                            "attributes": attributes or "",
                            "item_attributes": item_attributes or "",
                            "tax_template": tax_template_name or "",  
                            "tax_rate": tax_rate or 0,  
                        }
                    )
                    result.append(row)
        
        return result

    if _pos_profile.get("posa_use_server_cache"):
        return __get_items(pos_profile, price_list, item_group, search_value, customer)
    else:
        return _get_items(pos_profile, price_list, item_group, search_value, customer)

def get_item_group_condition(pos_profile):
    cond = " and 1=1"
    item_groups = get_item_groups(pos_profile)
    if item_groups:
        cond = " and item_group in (%s)" % (", ".join(["%s"] * len(item_groups)))

    return cond % tuple(item_groups)


def get_root_of(doctype):
    """Get root element of a DocType with a tree structure"""
    result = frappe.db.sql(
        """select t1.name from `tab{0}` t1 where
		(select count(*) from `tab{1}` t2 where
			t2.lft < t1.lft and t2.rgt > t1.rgt) = 0
		and t1.rgt > t1.lft""".format(
            doctype, doctype
        )
    )
    return result[0][0] if result else None
@frappe.whitelist()
def get_variant_with_rate(item_code, order_type):
    # Fetch the item document
    try:
        variant_doc = frappe.get_doc("Item", item_code, fields=["name", "stock_uom"]) 
    except frappe.DoesNotExistError:
        return {"error": "Item not found"}

   
    price_list = get_price_list(order_type)
    if not price_list:
        return {"error": "Price list not found for the given order type"}

    # Arguments for fetching the item price
    args_for_get_price_list = {
        "price_list": price_list,
        "item_code": variant_doc.name,
        "uom": variant_doc.stock_uom
    }

    # Fetch the price rate
    try:
        price_rate = get_item_price(args_for_get_price_list, variant_doc.name)
        rate = price_rate[0][1] if price_rate else 0
    except Exception as e:
        return {"error": str(e)}

    # Convert the document to a dictionary and add the rate
    variant_doc_dict = variant_doc.as_dict()
    variant_doc_dict["rate"] = rate

    return variant_doc_dict

def get_price_list(order_type):
        price_list_data = frappe.db.sql(
            """
            SELECT name
            FROM `tabPrice List`
            WHERE order_type = %s
            LIMIT 1
            """, (order_type), as_dict=True
        )
        if price_list_data:
            return price_list_data[0].name
        else:
            return None


@frappe.whitelist()
def get_variants_addons(item_code, order_type=None, pos_profile=None):
    # _pos_profile = json.loads(pos_profile or '{}')
    # ttl = _pos_profile.get("posa_server_cache_duration")
    # if ttl:
    #     ttl = int(ttl) * 30
    # Fetch variants for the item
    Attributes = []
    variants = []
    item_add_on_doc = []
    
    price_list = get_price_list(order_type) or "Standard Selling"
    try:
        # Fetch the main item document
        item_doc = frappe.get_doc("Item", item_code)
        attributes = get_item_attributes(item_doc.item_code)
        Attributes.append(attributes)
        if item_doc.has_variants == 1:
            try:
                # Fetch all item variants
                item_variants = frappe.get_all("Item", filters={"variant_of": item_doc.name})

                for variant_item in item_variants:
                    try:
                        # Fetch the variant document
                        variant_doc = frappe.get_doc("Item", variant_item.name)

                        # Prepare arguments to get the price list
                        args_for_get_price_list = {
                            "price_list": price_list,
                            "item_code": variant_doc.name,
                            "uom": variant_doc.stock_uom
                        }

                        # Fetch the price rate
                        price_rate = get_item_price(args_for_get_price_list, variant_doc.name)
                        variant_doc_dict = variant_doc.as_dict()
                        variant_doc_dict["rate"] = price_rate[0][1] if price_rate else 0

                        # Append the variant document to the list of variants
                        variants.append(variant_doc_dict)

                    except Exception as e:
                        print(f"Error fetching variant document or price: {e}")

            except Exception as e:
                print(f"Error fetching item variants: {e}")

    except Exception as e:
        print(f"Error fetching item document: {e}")

    # Fetch add-ons for the item with enhanced security and error handling
    try:
        # Fetch the list of item add-ons
        item_add_ons_list = frappe.get_list("Item Add-Ons", filters={"item": item_code}, fields=["*"], order_by="creation asc")

        for item_add_on in item_add_ons_list:
            try:
                # Fetch the document for each item add-on
                doc_add_on = frappe.get_doc("Item Add-Ons", item_add_on.name)
                add_on_details = doc_add_on.as_dict()

                # Process each add-on within the item add-on document
                for add_on in add_on_details.get('item_add_ons', []):
                    try:
                        add_on_item_doc = frappe.get_doc("Item", add_on['item'])

                        if add_on_item_doc.has_variants == 1:
                            add_on['variants'] = []
                            add_on_variants = frappe.get_all("Item", filters={"variant_of": add_on_item_doc.name})

                            for variant in add_on_variants:
                                try:
                                    variant_doc = frappe.get_doc("Item", variant.name)
                                    add_on['variants'].append(variant_doc.as_dict())
                                except Exception as e:
                                    print(f"Error fetching variant document: {e}")
                    except Exception as e:
                        print(f"Error fetching item document: {e}")

                item_add_on_doc.append(add_on_details)
            except Exception as e:
                print(f"Error fetching item add-on document: {e}")

    except Exception as e:
        print(f"Error fetching item add-ons list: {e}")

    # Prepare the final result
    result = []
    result.append({
        "Attributes":Attributes,
        "variants": variants,
        "add_ons": item_add_on_doc,
    })

    return result


@frappe.whitelist()
def get_items_groups():
    return frappe.db.sql(
        """
        select name 
        from `tabItem Group`
        where is_group = 0
        order by name
        LIMIT 0, 200 """,
        as_dict=1,
    )


def get_customer_groups(pos_profile):
    customer_groups = []
    if pos_profile.get("customer_groups"):
        # Get items based on the item groups defined in the POS profile
        for data in pos_profile.get("customer_groups"):
            customer_groups.extend(
                [
                    "%s" % frappe.db.escape(d.get("name"))
                    for d in get_child_nodes(
                        "Customer Group", data.get("customer_group")
                    )
                ]
            )

    return list(set(customer_groups))


def get_child_nodes(group_type, root):
    lft, rgt = frappe.db.get_value(group_type, root, ["lft", "rgt"])
    return frappe.db.sql(
        """ Select name, lft, rgt from `tab{tab}` where
			lft >= {lft} and rgt <= {rgt} order by lft""".format(
            tab=group_type, lft=lft, rgt=rgt
        ),
        as_dict=1,
    )


def get_customer_group_condition(pos_profile):
    cond = "disabled = 0"
    customer_groups = get_customer_groups(pos_profile)
    if customer_groups:
        cond = " customer_group in (%s)" % (", ".join(["%s"] * len(customer_groups)))

    return cond % tuple(customer_groups)


@frappe.whitelist()
def get_customer_names(pos_profile):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 60

    @redis_cache(ttl=ttl or 1800)
    def __get_customer_names(pos_profile):
        return _get_customer_names(pos_profile)

    def _get_customer_names(pos_profile):
        pos_profile = json.loads(pos_profile)
        condition = get_customer_group_condition(pos_profile)

        customers = frappe.db.sql(
            """
            SELECT 
                c.name, c.mobile_no, c.email_id, c.tax_id, 
                c.customer_name, c.primary_address, 
                a.address_line1, a.address_line2, a.city, a.phone
            FROM `tabCustomer` c
            LEFT JOIN `tabDynamic Link` dl ON dl.link_doctype = 'Customer' 
                AND dl.link_name = c.name AND dl.parenttype = 'Address'
            LEFT JOIN `tabAddress` a ON a.name = dl.parent
            WHERE {0}
            ORDER BY c.name
            """.format(condition),
            as_dict=1,
        )
        return customers

    if _pos_profile.get("posa_use_server_cache"):
        return __get_customer_names(pos_profile)
    else:
        return _get_customer_names(pos_profile)



@frappe.whitelist()
def get_customer_by_mobile(pos_profile, mobile_no):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 60

    @redis_cache(ttl=ttl or 1800)
    def __get_customer_details(pos_profile, mobile_no):
        return _get_customer_details(pos_profile, mobile_no)

    def _get_customer_details(pos_profile, mobile_no):
        pos_profile = json.loads(pos_profile)
        condition = get_customer_group_condition(pos_profile)
        customer_query = """
            SELECT name, mobile_no, email_id, tax_id, customer_name, gender, customer_primary_address, customer_primary_contact
            FROM `tabCustomer`
            WHERE {0} AND mobile_no = %s
            ORDER BY name
        """.format(condition)
        customers = frappe.db.sql(customer_query, (mobile_no,), as_dict=1)
        
        if not customers:
            return None
        
        customer = customers[0]
        
        if customer.get('customer_primary_address'):
            address_query = """
                SELECT address_line1, address_line2, city, state, country, pincode
                FROM `tabAddress`
                WHERE name = %s
            """
            addresses = frappe.db.sql(address_query, (customer['customer_primary_address'],), as_dict=1)
            customer['customer_primary_address'] = addresses[0] if addresses else None
        else:
            customer['customer_primary_address'] = None
        
        if customer.get('customer_primary_contact'):
            contact_query = """
                SELECT name, phone, mobile_no, email_id
                FROM `tabContact`
                WHERE name = %s
            """
            contacts = frappe.db.sql(contact_query, (customer['customer_primary_contact'],), as_dict=1)
            customer['customer_primary_contact'] = contacts[0] if contacts else None
        else:
            customer['customer_primary_contact'] = None
        sales_invoices_query = """
            SELECT *
            FROM `tabSales Invoice`
            WHERE customer = %s AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
            ORDER BY posting_date DESC
        """
        sales_invoices = frappe.db.sql(sales_invoices_query, (customer['name'],), as_dict=1)
        customer['sales_invoices'] = sales_invoices

        return customer

    if _pos_profile.get("posa_use_server_cache"):
        return __get_customer_details(pos_profile, mobile_no)
    else:
        return _get_customer_details(pos_profile, mobile_no)


@frappe.whitelist()
def get_Table_names(pos_profile):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 60

    @redis_cache(ttl=ttl or 1800)
    def __get_Table_names(pos_profile):
        return _get_Table_names(pos_profile)

    def _get_Table_names(pos_profile):
        pos_profile = json.loads(pos_profile)
        tables= frappe.get_all("Table Management", fields=["name","status","floor_no","table_no","no_of_seats"],filters={"status":"Available"},
        order_by="name")
        return tables

    if _pos_profile.get("posa_use_server_cache"):
        return __get_Table_names(pos_profile)
    else:
        return _get_Table_names(pos_profile)
    
@frappe.whitelist()
def update_table_status(table_name, status):
    if not table_name or not status:
        frappe.throw(_("Table name and status are required"))

    table = frappe.get_doc("Table Management", table_name)
    table.status = status
    table.save(ignore_permissions=True)
    
    frappe.db.commit()
    
    return {"message": f"Table {table_name} status updated to {status}"}

@frappe.whitelist()
def get_all_Table_names(pos_profile):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 60

    @redis_cache(ttl=ttl or 1800)
    def __get_Table_names(pos_profile):
        return _get_Table_names(pos_profile)

    def _get_Table_names(pos_profile):
        pos_profile = json.loads(pos_profile)
        tables = frappe.get_all("Table Management", fields=["name", "status", "floor_no", "table_no", "no_of_seats"], order_by="name")

        for table in tables:
            if table["status"] == "Reserved":
                invoices = frappe.get_all("Sales Invoice", filters={"docstatus": 0, "table_no": table["table_no"]}, fields=["name", "cover", "table_no"])
                if invoices:
                    latest_invoice = invoices[0]  # Assuming the first one is the latest
                    table["cover"] = latest_invoice.get("cover")
        return tables

    if _pos_profile.get("posa_use_server_cache"):
        return __get_Table_names(pos_profile)
    else:
        return _get_Table_names(pos_profile)
    
@frappe.whitelist()
def get_Order_type(pos_profile):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 60

    @redis_cache(ttl=ttl or 1800)
    def get_Order_type(pos_profile):
        return get_Order_type(pos_profile)

    def get_Order_type(pos_profile):
        pos_profile = json.loads(pos_profile)
        types= frappe.get_all("Order Type", fields=["*"],
        order_by="name")
        return types

    if _pos_profile.get("posa_use_server_cache"):
        return get_Order_type(pos_profile)
    else:
        return get_Order_type(pos_profile)

@frappe.whitelist()
def get_sales_person_names():
    sales_persons = frappe.get_list(
        "Sales Person",
        filters={"enabled": 1},
        fields=["name", "sales_person_name"],
        limit_page_length=100000,
    )
    return sales_persons


def add_taxes_from_tax_template(item, parent_doc):
    accounts_settings = frappe.get_cached_doc("Accounts Settings")
    add_taxes_from_item_tax_template = (
        accounts_settings.add_taxes_from_item_tax_template
    )
    if item.get("item_tax_template") and add_taxes_from_item_tax_template:
        item_tax_template = item.get("item_tax_template")
        taxes_template_details = frappe.get_all(
            "Item Tax Template Detail",
            filters={"parent": item_tax_template},
            fields=["tax_type"],
        )

        for tax_detail in taxes_template_details:
            tax_type = tax_detail.get("tax_type")

            found = any(tax.account_head == tax_type for tax in parent_doc.taxes)
            if not found:
                tax_row = parent_doc.append("taxes", {})
                tax_row.update(
                    {
                        "description": str(tax_type).split(" - ")[0],
                        "charge_type": "On Net Total",
                        "account_head": tax_type,
                    }
                )

                if parent_doc.doctype == "Purchase Order":
                    tax_row.update({"category": "Total", "add_deduct_tax": "Add"})
                tax_row.db_insert()


@frappe.whitelist()
def update_invoice_from_order(data):
    data = json.loads(data)
    invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
    invoice_doc.update(data)
    invoice_doc.save()
    return invoice_doc


@frappe.whitelist()
def update_invoice(data):
    data = json.loads(data)
    if data.get("name"):
        invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
        invoice_doc.update(data)
    else:
        invoice_doc = frappe.get_doc(data)

    invoice_doc.set_missing_values()
    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True

    if invoice_doc.is_return and invoice_doc.return_against:
        ref_doc = frappe.get_cached_doc(invoice_doc.doctype, invoice_doc.return_against)
        if not ref_doc.update_stock:
            invoice_doc.update_stock = 0
        if len(invoice_doc.payments) == 0:
            invoice_doc.payments = ref_doc.payments
        invoice_doc.paid_amount = (
            invoice_doc.rounded_total or invoice_doc.grand_total or invoice_doc.total
        )
        for payment in invoice_doc.payments:
            if payment.default:
                payment.amount = invoice_doc.paid_amount
    allow_zero_rated_items = frappe.get_cached_value(
        "POS Profile", invoice_doc.pos_profile, "posa_allow_zero_rated_items"
    )
    for item in invoice_doc.items:
        if not item.rate or item.rate == 0:
            if allow_zero_rated_items:
                item.price_list_rate = 0.00
                item.is_free_item = 1
            else:
                frappe.throw(
                    _("Rate cannot be zero for item {0}").format(item.item_code)
                )
        else:
            item.is_free_item = 0
        add_taxes_from_tax_template(item, invoice_doc)

    if frappe.get_cached_value(
        "POS Profile", invoice_doc.pos_profile, "posa_tax_inclusive"
    ):
        if invoice_doc.get("taxes"):
            for tax in invoice_doc.taxes:
                tax.included_in_print_rate = 1

    today_date = getdate()
    if (
        invoice_doc.get("posting_date")
        and getdate(invoice_doc.posting_date) != today_date
    ):
        invoice_doc.set_posting_time = 1
    invoice_doc.order_summery_for_pos = json.dumps(invoice_doc.order_summery_for_pos)
    invoice_doc.save()

    return invoice_doc

@frappe.whitelist()
def get_invoice_by_table(table):
    draft_invoice = frappe.get_all('Sales Invoice',
                                       filters={'docstatus': 0,  
                                                'table_no': table},
                                        fields={"*"},
                                       order_by='creation desc',
                                       limit=1)
    return draft_invoice


@frappe.whitelist()
def submit_invoice(invoice, data,taxvalue):
    data = json.loads(data)
    invoice = json.loads(invoice)
    invoice_doc = frappe.get_doc("Sales Invoice", invoice.get("name"))
    invoice_doc.update(invoice)
    if invoice.get("posa_delivery_date"):
        invoice_doc.update_stock = 0
    mop_cash_list = [
        i.mode_of_payment
        for i in invoice_doc.payments
        if "cash" in i.mode_of_payment.lower() and i.type == "Cash"
    ]
    if len(mop_cash_list) > 0:
        cash_account = get_bank_cash_account(mop_cash_list[0], invoice_doc.company)
    else:
        cash_account = {
            "account": frappe.get_value(
                "Company", invoice_doc.company, "default_cash_account"
            )
        }

    # creating advance payment
    if data.get("credit_change"):
        advance_payment_entry = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "mode_of_payment": "Cash",
                "paid_to": cash_account["account"],
                "payment_type": "Receive",
                "party_type": "Customer",
                "party": invoice_doc.get("customer"),
                "paid_amount": invoice_doc.get("credit_change"),
                "received_amount": invoice_doc.get("credit_change"),
                "company": invoice_doc.get("company"),
            }
        )

        advance_payment_entry.flags.ignore_permissions = True
        frappe.flags.ignore_account_permission = True
        advance_payment_entry.save()
        advance_payment_entry.submit()

    # calculating cash
    total_cash = 0
    if data.get("redeemed_customer_credit"):
        total_cash = invoice_doc.total - float(data.get("redeemed_customer_credit"))

    is_payment_entry = 0
    if data.get("redeemed_customer_credit"):
        for row in data.get("customer_credit_dict"):
            if row["type"] == "Advance" and row["credit_to_redeem"]:
                advance = frappe.get_doc("Payment Entry", row["credit_origin"])

                advance_payment = {
                    "reference_type": "Payment Entry",
                    "reference_name": advance.name,
                    "remarks": advance.remarks,
                    "advance_amount": advance.unallocated_amount,
                    "allocated_amount": row["credit_to_redeem"],
                }

                invoice_doc.append("advances", advance_payment)
                invoice_doc.is_pos = 0
                is_payment_entry = 1

    payments = invoice_doc.payments

    if frappe.get_value("POS Profile", invoice_doc.pos_profile, "posa_auto_set_batch"):
        make_batch(invoice_doc, "warehouse", throw=True)
    set_batch_nos_for_bundels(invoice_doc, "warehouse", throw=True)

    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    invoice_doc.posa_is_printed = 1
    if taxvalue:
        invoice_doc.taxes_and_charges = taxvalue
        taxes_template_details = frappe.get_all(
            "Sales Taxes and Charges",
            filters={"parent": taxvalue},
            fields=["*"],
        )
        invoice_doc.taxes = []
        if taxes_template_details:
            for tax_detail in taxes_template_details:
                tax_row = invoice_doc.append("taxes", {})
                tax_row.update(
                    {
                        "description": tax_detail.get("description").split(" - ")[0],
                        "charge_type": tax_detail.get("charge_type"),
                        "account_head": tax_detail.get("account_head"),
                        "rate":tax_detail.get("rate")
                    }
                )

                if invoice_doc.doctype == "Purchase Order":
                    tax_row.update({"category": "Total", "add_deduct_tax": "Add"})
                tax_row.db_insert()

    invoice_doc.save()


    if data.get("due_date"):
        frappe.db.set_value(
            "Sales Invoice",
            invoice_doc.name,
            "due_date",
            data.get("due_date"),
            update_modified=False,
        )
    if frappe.get_value(
        "POS Profile",
        invoice_doc.pos_profile,
        "posa_allow_submissions_in_background_job",
    ):
        invoices_list = frappe.get_all(
            "Sales Invoice",
            filters={
                "posa_pos_opening_shift": invoice_doc.posa_pos_opening_shift,
                "docstatus": 0,
                "posa_is_printed": 1,
            },
        )
        for invoice in invoices_list:
            enqueue(
                method=submit_in_background_job,
                queue="short",
                timeout=1000,
                is_async=True,
                kwargs={
                    "invoice": invoice.name,
                    "data": data,
                    "is_payment_entry": is_payment_entry,
                    "total_cash": total_cash,
                    "cash_account": cash_account,
                    "payments": payments,
                },
            )
    else:
        invoice_doc.submit()
        redeeming_customer_credit(
            invoice_doc, data, is_payment_entry, total_cash, cash_account, payments
        )

    return {"name": invoice_doc.name, "status": invoice_doc.docstatus}

@frappe.whitelist()
def sales_invoice(data, invoice=None, taxvalue=None):
    data = json.loads(invoice)
    invoice_doc = None

    # Update or create the invoice
    if data.get("name"):
        invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
        invoice_doc.update(data)
    else:
        if data.get("pos_referrence"):
            existing_invoice = frappe.db.exists("Sales Invoice", {"pos_referrence": data.get("pos_referrence")})
            if existing_invoice:
                invoice_doc = frappe.get_doc("Sales Invoice", existing_invoice)
                
                if invoice_doc.docstatus == 1:  # If the invoice is submitted/paid
                    return {"name": invoice_doc.name, "status": invoice_doc.docstatus}
                
                invoice_doc.update(data)
            else:
                invoice_doc = frappe.get_doc(data)
        else:
            invoice_doc = frappe.get_doc(data)

    invoice_doc.set_missing_values()
    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True

    # Handle returns
    if invoice_doc.is_return and invoice_doc.return_against:
        ref_doc = frappe.get_cached_doc(invoice_doc.doctype, invoice_doc.return_against)
        if not ref_doc.update_stock:
            invoice_doc.update_stock = 0
        if len(invoice_doc.payments) == 0:
            invoice_doc.payments = ref_doc.payments
        invoice_doc.paid_amount = (
            invoice_doc.rounded_total or invoice_doc.grand_total or invoice_doc.total
        )
        for payment in invoice_doc.payments:
            if payment.default:
                payment.amount = invoice_doc.paid_amount

    allow_zero_rated_items = frappe.get_cached_value(
        "POS Profile", invoice_doc.pos_profile, "posa_allow_zero_rated_items"
    )

    for item in invoice_doc.items:
        if not item.rate or item.rate == 0:
            if allow_zero_rated_items:
                item.price_list_rate = 0.00
                item.is_free_item = 1
            else:
                frappe.throw(
                    _(f"Rate cannot be zero for item {item.item_code}")
                )
        else:
            item.is_free_item = 0
        add_taxes_from_tax_template(item, invoice_doc)

    if frappe.get_cached_value(
        "POS Profile", invoice_doc.pos_profile, "posa_tax_inclusive"
    ):
        if invoice_doc.get("taxes"):
            for tax in invoice_doc.taxes:
                tax.included_in_print_rate = 1

    today_date = getdate()
    if (
        invoice_doc.get("posting_date")
        and getdate(invoice_doc.posting_date) != today_date
    ):
        invoice_doc.set_posting_time = 1
    invoice_doc.order_summery_for_pos = json.dumps(invoice_doc.order_summery_for_pos)
    
    # Handle tips ledger posting
    # if invoice_doc.get("tip"):
    #     create_tip_ledger_entry(invoice_doc)
    # Process submission if invoice data exists
    if invoice:
        invoice = json.loads(invoice)
        invoice_doc.update(invoice)

        
        invoice_doc.update_stock = 1

        mop_cash_list = [
            i.mode_of_payment
            for i in invoice_doc.payments
            if "cash" in i.mode_of_payment.lower() and i.type == "Cash"
        ]

        cash_account = (
            get_bank_cash_account(mop_cash_list[0], invoice_doc.company)
            if mop_cash_list
            else {
                "account": frappe.get_value(
                    "Company", invoice_doc.company, "default_cash_account"
                )
            }
        )

        if data.get("credit_change"):
            advance_payment_entry = frappe.get_doc(
                {
                    "doctype": "Payment Entry",
                    "mode_of_payment": "Cash",
                    "paid_to": cash_account["account"],
                    "payment_type": "Receive",
                    "party_type": "Customer",
                    "party": invoice_doc.get("customer"),
                    "paid_amount": invoice_doc.get("credit_change"),
                    "received_amount": invoice_doc.get("credit_change"),
                    "company": invoice_doc.get("company"),
                }
            )
            advance_payment_entry.flags.ignore_permissions = True
            frappe.flags.ignore_account_permission = True
            advance_payment_entry.save()
            advance_payment_entry.submit()

        total_cash = (
            invoice_doc.total - float(data.get("redeemed_customer_credit"))
            if data.get("redeemed_customer_credit")
            else 0
        )

        is_payment_entry = 0
        if data.get("redeemed_customer_credit"):
            for row in data.get("customer_credit_dict"):
                if row["type"] == "Advance" and row["credit_to_redeem"]:
                    advance = frappe.get_doc("Payment Entry", row["credit_origin"])

                    advance_payment = {
                        "reference_type": "Payment Entry",
                        "reference_name": advance.name,
                        "remarks": advance.remarks,
                        "advance_amount": advance.unallocated_amount,
                        "allocated_amount": row["credit_to_redeem"],
                    }

                    invoice_doc.append("advances", advance_payment)
                    invoice_doc.is_pos = 0
                    is_payment_entry = 1

        payments = invoice_doc.payments

        if frappe.get_value("POS Profile", invoice_doc.pos_profile, "posa_auto_set_batch"):
            make_batch(invoice_doc, "warehouse", throw=True)
        set_batch_nos_for_bundels(invoice_doc, "warehouse", throw=True)

        invoice_doc.posa_is_printed = 1

        if taxvalue:
            invoice_doc.taxes_and_charges = taxvalue
            taxes_template_details = frappe.get_all(
                "Sales Taxes and Charges",
                filters={"parent": taxvalue},
                fields=["*"],
            )
            invoice_doc.taxes = []
            if taxes_template_details:
                for tax_detail in taxes_template_details:
                    tax_row = invoice_doc.append("taxes", {})
                    tax_row.update(
                        {
                            "description": tax_detail.get("description").split(" - ")[0],
                            "charge_type": tax_detail.get("charge_type"),
                            "account_head": tax_detail.get("account_head"),
                            "rate": tax_detail.get("rate"),
                        }
                    )

                    if invoice_doc.doctype == "Purchase Order":
                        tax_row.update({"category": "Total", "add_deduct_tax": "Add"})
                    tax_row.db_insert()
        clean_invoice_for_v15(invoice_doc)
        invoice_doc.save()

        if data.get("due_date"):
            frappe.db.set_value(
                "Sales Invoice",
                invoice_doc.name,
                "due_date",
                data.get("due_date"),
                update_modified=False,
            )

        if frappe.get_value(
            "POS Profile",
            invoice_doc.pos_profile,
            "posa_allow_submissions_in_background_job",
        ):
            invoices_list = frappe.get_all(
                "Sales Invoice",
                filters={
                    "posa_pos_opening_shift": invoice_doc.posa_pos_opening_shift,
                    "docstatus": 0,
                    "posa_is_printed": 1,
                },
            )
            for invoice in invoices_list:
                enqueue(
                    method=submit_in_background_job,
                    queue="short",
                    timeout=1000,
                    is_async=True,
                    kwargs={
                        "invoice": invoice.name,
                        "data": data,
                        "is_payment_entry": is_payment_entry,
                        "total_cash": total_cash,
                        "cash_account": cash_account,
                        "payments": payments,
                    },
                )
        else:
            invoice_doc.submit()
            redeeming_customer_credit(
                invoice_doc, data, is_payment_entry, total_cash, cash_account, payments
            )

            if invoice_doc.get("pos_profile"):
                pp = frappe.get_doc("POS Profile", invoice_doc.get("pos_profile"))
                if pp.get("enable_sunmi_print") and pp.get("sunmi_printer") and pp.get("sunmi_print_format"):
                    # sp = frappe.get_doc("SUNMI Printer", pp.get("sunmi_printer"))
                    from tabrah_pos.tabrah_pos.doctype.sunmi_printer.sunmi_printer import print_receipt_to_sunmi
                    print_receipt_to_sunmi(invoice_doc.doctype, invoice_doc.name, pp.get("sunmi_printer"), pp.get("sunmi_print_format"))


    return {"name": invoice_doc.name, "status": invoice_doc.docstatus}



from typing import Optional, Union



def _row_key(item: dict) -> str:
    # Prefer a stable key from POS row (send it from client).
    # Fallback: build signature so same item w/ same rate & modifiers match.
    parts = [
        item.get("row_key") or "",
        item.get("item_code") or item.get("item_name") or "",
        str(item.get("rate") or ""),
        str(item.get("variant") or ""),
        str(item.get("modifiers_key") or ""),
    ]
    return "|".join(parts)

@frappe.whitelist()
def upsert_held_order(payload: Optional[Union[str, dict]] = None):
   # --- Parse payload safely ---
    if payload is None:
        payload = frappe.request.get_json(silent=True)
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, dict):
        frappe.throw("Invalid payload; expected a JSON object.")

    held_id = payload.get("held_id")
    if not held_id:
        frappe.throw("held_id is required.")

    # Normalize header values
    table = payload.get("table")
    order_type = payload.get("orderType")
    cover = flt(payload.get("cover") or 0)
    customer_label = payload.get("customer") or "Retail Customer"
    token_number = payload.get("custom_token_number")

    # Normalize items to a list
    incoming_items = payload.get("items") or []
    if not isinstance(incoming_items, list):
        incoming_items = []

    # Resolve company & currency
    company = frappe.db.get_default("company")
    if not company:
        frappe.throw("Default Company not set.")
    currency = frappe.db.get_value("Company", company, "default_currency") or frappe.db.get_default("currency")

    # Load or create Sales Order (by custom_hold_order_id)
    so_name = frappe.db.get_value("Sales Order", {"custom_hold_order_id": held_id}, "name")
    if so_name:
        so = frappe.get_doc("Sales Order", so_name)
        is_new = False
    else:
        # Ensure a valid Customer exists (returns a Customer *name*)
        customer_name = customer_label

        # Build the new SO with header + items BEFORE insert
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "company": company,
            "currency": currency,
            "customer": customer_name,
            "delivery_date": nowdate(),
            "transaction_date": nowdate(),
            "custom_hold_order_id": held_id,
            "custom_hold_status": "Active",
            # Avoid payment terms template interference on insert
            "payment_terms_template": None,
        })
        is_new = True

    # --- Sync header custom fields ---
    so.custom_table = table
    so.custom_order_type = order_type
    so.custom_cover = int(cover) if cover else 0
    so.custom_customer = customer_label
    so.custom_token_number = token_number

    # Ensure company/currency are set (in case existing SO missed them)
    so.company = so.company or company
    so.currency = so.currency or currency
    so.transaction_date = so.transaction_date or nowdate()

    # --- Index existing lines by custom_row_key ---
    existing_by_key = {}
    for line in (so.items or []):
        existing_by_key[(line.get("custom_row_key") or "")] = line

    # --- Process incoming lines ---
    incoming_keys = set()
    for pos_item in incoming_items:
        key = _row_key(pos_item)
        incoming_keys.add(key)

        item_code = pos_item.get("item_code") or pos_item.get("item_name")
        item_name = pos_item.get("item_name") or item_code
        qty = flt(pos_item.get("qty") or 0)
        rate = flt(pos_item.get("rate") or 0)
        uom = pos_item.get("uom") or "Nos"
        cf = flt(pos_item.get("conversion_factor") or 1)

        if key in existing_by_key:
            # Update existing line (never delete)
            row = existing_by_key[key]
            row.item_code = item_code
            row.item_name = item_name
            row.qty = qty
            row.rate = rate
            row.uom = uom
            row.conversion_factor = cf
            row.custom_hold_status = "Active"
        else:
            # Append new line
            so.append("items", {
                "item_code": item_code,
                "item_name": item_name,
                "qty": qty,
                "rate": rate,
                "uom": uom,
                "conversion_factor": cf,
                "custom_row_key": key,
                "custom_hold_status": "Active",
            })

    # --- Soft-delete lines that disappeared from the payload ---
    for line in (so.items or []):
        k = line.get("custom_row_key") or ""
        if k and k not in incoming_keys:
            line.custom_hold_status = "Deleted"

        # Totals-safety: guarantee numeric fields exist
        line.qty = flt(line.qty or 0)
        line.rate = flt(line.rate or 0)
        line.uom = line.uom or "Nos"
        line.conversion_factor = flt(line.conversion_factor or 1)

    # --- PRECOMPUTE totals BEFORE insert/save to avoid None math in hooks ---
    so.flags.ignore_permissions = True
    so.set_missing_values()
    if hasattr(so, "calculate_taxes_and_totals"):
        so.calculate_taxes_and_totals()

    # Final guards so validate math never sees None
    so.grand_total = flt(getattr(so, "grand_total", 0))
    so.base_grand_total = flt(getattr(so, "base_grand_total", so.grand_total))

    # Some environments auto-attach a Payment Terms Template in validate().
    # Keeping payment_terms_template = None on first insert avoids grand_total None usage.
    # You can set a template later when the order is finalized.
    # --- Persist ---
    if is_new:
        so.insert(ignore_permissions=True)
    else:
        so.save(ignore_permissions=True)

    row_key_map = []
    for line in (so.items or []):
        row_key_map.append({
            "so_item_name": line.name,                             # Sales Order Item rowname
            "server_row_key": line.get("custom_row_key") or "",    # what server stored
            "item_code": line.item_code,
            "item_name": line.item_name,
        })

    return {
        "status": "success",
        "sales_order": so.name,
        "held_id": held_id,
        "totals": {
            "grand_total": so.grand_total,
            "base_grand_total": so.base_grand_total,
            "total_qty": sum(flt(x.qty) for x in so.items or []),
        },
        "row_kep_map": row_key_map, 
    }

@frappe.whitelist()
def mark_held_order_deleted(held_id: str):
    """
    Called when a held order is removed from localStorage.
    Soft-cancel the Sales Order.
    """
    so_name = frappe.db.get_value("Sales Order", {"custom_hold_order_id": held_id}, "name")
    if not so_name:
        return {"status": "success", "message": "No SO found for held order."}

    so = frappe.get_doc("Sales Order", so_name)
    so.custom_hold_status = "Cancelled"
    for it in so.items:
        if it.custom_hold_status != "Deleted":
            it.custom_hold_status = "Deleted"
    so.save(ignore_permissions=True)

    return {"status":"success","sales_order": so.name}



import frappe
from frappe.utils import flt, getdate

def create_tip_ledger_entry(invoice_doc):
    try:
        print(f"Processing invoice: {invoice_doc.name}")  # Debugging

        # Fetch POS Profile
        pos_profile = frappe.get_doc("POS Profile", invoice_doc.pos_profile)
        print(f"POS Profile: {pos_profile.name}")

        # Ensure tip amount is a float
        tip_amount = flt(invoice_doc.get("tip"))
        print(f"Tip Amount: {tip_amount}")

        if not tip_amount or tip_amount <= 0:
            print("No valid tip amount found. Skipping journal entry.")
            return

        # Check if required accounts exist
        if not pos_profile.custom_tip_account:
            frappe.throw("Custom Tip Account is not set in POS Profile.")
        if not pos_profile.cost_center:
            frappe.throw("Cost Center is not set in POS Profile.")

        cash_account = frappe.get_value("Company", pos_profile.company, "default_cash_account")
        if not cash_account:
            frappe.throw("Default Cash Account is not set in Company settings.")

        print(f"Tip Account: {pos_profile.custom_tip_account}, Cash Account: {cash_account}")

        # Create Journal Entry
        journal_entry = frappe.get_doc({
            "doctype": "Journal Entry",
            "posting_date": getdate(),
            "company": pos_profile.company,
            "voucher_type": "Journal Entry",
            "accounts": [
                {
                    "account": pos_profile.custom_tip_account,
                    "debit_in_account_currency": tip_amount,
                    "cost_center": pos_profile.cost_center,
                },
                {
                    "account": cash_account,
                    "credit_in_account_currency": tip_amount,
                    "cost_center": pos_profile.cost_center,
                }
            ],
            "remark": f"Tip collected from invoice {invoice_doc.name}",
        })

        journal_entry.flags.ignore_permissions = True
        journal_entry.save()
        print(f"Journal Entry {journal_entry.name} saved successfully.")

        journal_entry.submit()
        print(f"Journal Entry {journal_entry.name} submitted successfully.")

    except Exception as e:
        frappe.throw(f"Error in create_tip_ledger_entry: {str(e)}")




def set_batch_nos_for_bundels(doc, warehouse_field, throw=False):
    """Automatically select `batch_no` for outgoing items in item table"""
    for d in doc.packed_items:
        qty = d.get("stock_qty") or d.get("transfer_qty") or d.get("qty") or 0
        has_batch_no = frappe.db.get_value("Item", d.item_code, "has_batch_no")
        warehouse = d.get(warehouse_field, None)
        if has_batch_no and warehouse and qty > 0:
            if not d.batch_no:
                d.batch_no = get_batch_no(
                    d.item_code, warehouse, qty, throw, d.serial_no
                )
            else:
                batch_qty = get_batch_qty(batch_no=d.batch_no, warehouse=warehouse)
                if flt(batch_qty, d.precision("qty")) < flt(qty, d.precision("qty")):
                    frappe.throw(
                        _(
                            "Row #{0}: The batch {1} has only {2} qty. Please select another batch which has {3} qty available or split the row into multiple rows, to deliver/issue from multiple batches"
                        ).format(d.idx, d.batch_no, batch_qty, qty)
                    )


def redeeming_customer_credit(
    invoice_doc, data, is_payment_entry, total_cash, cash_account, payments
):
    # redeeming customer credit with journal voucher
    today = nowdate()
    if data.get("redeemed_customer_credit"):
        cost_center = frappe.get_value(
            "POS Profile", invoice_doc.pos_profile, "cost_center"
        )
        if not cost_center:
            cost_center = frappe.get_value(
                "Company", invoice_doc.company, "cost_center"
            )
        if not cost_center:
            frappe.throw(
                _("Cost Center is not set in pos profile {}").format(
                    invoice_doc.pos_profile
                )
            )
        for row in data.get("customer_credit_dict"):
            if row["type"] == "Invoice" and row["credit_to_redeem"]:
                outstanding_invoice = frappe.get_doc(
                    "Sales Invoice", row["credit_origin"]
                )

                jv_doc = frappe.get_doc(
                    {
                        "doctype": "Journal Entry",
                        "voucher_type": "Journal Entry",
                        "posting_date": today,
                        "company": invoice_doc.company,
                    }
                )

                jv_debit_entry = {
                    "account": outstanding_invoice.debit_to,
                    "party_type": "Customer",
                    "party": invoice_doc.customer,
                    "reference_type": "Sales Invoice",
                    "reference_name": outstanding_invoice.name,
                    "debit_in_account_currency": row["credit_to_redeem"],
                    "cost_center": cost_center,
                }

                jv_credit_entry = {
                    "account": invoice_doc.debit_to,
                    "party_type": "Customer",
                    "party": invoice_doc.customer,
                    "reference_type": "Sales Invoice",
                    "reference_name": invoice_doc.name,
                    "credit_in_account_currency": row["credit_to_redeem"],
                    "cost_center": cost_center,
                }

                jv_doc.append("accounts", jv_debit_entry)
                jv_doc.append("accounts", jv_credit_entry)

                jv_doc.flags.ignore_permissions = True
                frappe.flags.ignore_account_permission = True
                jv_doc.set_missing_values()
                jv_doc.save()
                jv_doc.submit()

    if is_payment_entry and total_cash > 0:
        for payment in payments:
            if not payment.amount:
                continue
            payment_entry_doc = frappe.get_doc(
                {
                    "doctype": "Payment Entry",
                    "posting_date": today,
                    "payment_type": "Receive",
                    "party_type": "Customer",
                    "party": invoice_doc.customer,
                    "paid_amount": payment.amount,
                    "received_amount": payment.amount,
                    "paid_from": invoice_doc.debit_to,
                    "paid_to": payment.account,
                    "company": invoice_doc.company,
                    "mode_of_payment": payment.mode_of_payment,
                    "reference_no": invoice_doc.posa_pos_opening_shift,
                    "reference_date": today,
                }
            )

            payment_reference = {
                "allocated_amount": payment.amount,
                "due_date": data.get("due_date"),
                "reference_doctype": "Sales Invoice",
                "reference_name": invoice_doc.name,
            }

            payment_entry_doc.append("references", payment_reference)
            payment_entry_doc.flags.ignore_permissions = True
            frappe.flags.ignore_account_permission = True
            payment_entry_doc.save()
            payment_entry_doc.submit()


def submit_in_background_job(kwargs):
    invoice = kwargs.get("invoice")
    invoice_doc = kwargs.get("invoice_doc")
    data = kwargs.get("data")
    is_payment_entry = kwargs.get("is_payment_entry")
    total_cash = kwargs.get("total_cash")
    cash_account = kwargs.get("cash_account")
    payments = kwargs.get("payments")

    invoice_doc = frappe.get_doc("Sales Invoice", invoice)
    invoice_doc.submit()
    redeeming_customer_credit(
        invoice_doc, data, is_payment_entry, total_cash, cash_account, payments
    )

# def sync_pra_tax(invoice_doc,branch):
#     return 


@frappe.whitelist()
def get_available_credit(customer, company):
    total_credit = []

    outstanding_invoices = frappe.get_all(
        "Sales Invoice",
        {
            "outstanding_amount": ["<", 0],
            "docstatus": 1,
            "is_return": 0,
            "customer": customer,
            "company": company,
        },
        ["name", "outstanding_amount"],
    )

    for row in outstanding_invoices:
        outstanding_amount = -(row.outstanding_amount)
        row = {
            "type": "Invoice",
            "credit_origin": row.name,
            "total_credit": outstanding_amount,
            "credit_to_redeem": 0,
        }

        total_credit.append(row)

    advances = frappe.get_all(
        "Payment Entry",
        {
            "unallocated_amount": [">", 0],
            "party_type": "Customer",
            "party": customer,
            "company": company,
            "docstatus": 1,
        },
        ["name", "unallocated_amount"],
    )

    for row in advances:
        row = {
            "type": "Advance",
            "credit_origin": row.name,
            "total_credit": row.unallocated_amount,
            "credit_to_redeem": 0,
        }

        total_credit.append(row)

    return total_credit
@frappe.whitelist()
def get_draft_invoices_by_ordertype(pos_opening_shift, hold_invoices=None):
    # Define basic filters for Sales Invoice
    filters = {
        "posa_pos_opening_shift": pos_opening_shift,
        "docstatus": 0,
        "posa_is_printed": 0,
    }

    # If hold_invoices is provided, fetch order types from the OrderType doctype
    if hold_invoices:
        ordertypes = frappe.get_list(
            "Order Type",
            filters={"hold_invoices": hold_invoices},
            fields=["name"],
            limit_page_length=0,
        )

        # Extract the ordertype names into a list
        ordertype_names = [ordertype["name"] for ordertype in ordertypes]
        
        # Add the ordertypes list to the filters for Sales Invoice
        if ordertype_names:
            filters["resturent_type"] = ["in", ordertype_names]

    # Fetch the filtered Sales Invoices
    invoices_list = frappe.get_list(
        "Sales Invoice",
        filters=filters,
        fields=["name"],
        limit_page_length=0,
        order_by="modified desc",
    )
    
    data = []
    for invoice in invoices_list:
        data.append(frappe.get_cached_doc("Sales Invoice", invoice["name"]))
        
    return data


@frappe.whitelist()
def get_draft_invoices(pos_opening_shift):
    invoices_list = frappe.get_list(
        "Sales Invoice",
        filters={
            "posa_pos_opening_shift": pos_opening_shift,
            "docstatus": 0,
            "posa_is_printed": 0,
        },
        fields=["name"],
        limit_page_length=0,
        order_by="modified desc",
    )
    data = []
    for invoice in invoices_list:
        data.append(frappe.get_cached_doc("Sales Invoice", invoice["name"]))
    return data


@frappe.whitelist()
def delete_invoice(invoice):
    if frappe.get_value("Sales Invoice", invoice, "posa_is_printed"):
        frappe.throw(_("This invoice {0} cannot be deleted").format(invoice))
    frappe.delete_doc("Sales Invoice", invoice, force=1)
    return _("Invoice {0} Deleted").format(invoice)

@frappe.whitelist()
def create_bundle_from_item(json_data):
    try:
        data = frappe.parse_json(json_data)
        bundles_data = data.get("items", [])
        
        if not bundles_data:
            frappe.response["http_status_code"] = 400
            return {"error": "Missing required field: items"}
        
        created_bundles = []
        
        for bundle_data in bundles_data:
            items_list = bundle_data.get("items", [])
            item_specifics = bundle_data.get("item_specifics", [])
            
            if not items_list:
                frappe.response["http_status_code"] = 400
                return {"error": "Missing required field: items in one of the bundles"}
            
            # Case: If there is only one item and no item specifics, add it directly as a variant
            if len(items_list) == 1 and not item_specifics:
                variant_item = items_list[0]
                created_bundles.append({
                    "item_code": variant_item["item_code"],
                    "qty": variant_item["qty"],
                    "rate": variant_item["rate"]
                })
                continue  # Skip to the next bundle_data
                
            # Process the normal bundle creation flow
            items_to_add = []
            existing_bundle_found = False
            matched_bundle = None

            # Check for existing bundles that match the items list and item specifics
            bundle_list = frappe.get_all("Product Bundle", pluck="name")

            for bundle_name in bundle_list:
                bundle_doc = frappe.get_doc("Product Bundle", bundle_name)
                
                if len(bundle_doc.items) == len(items_list):
                    all_items_matched = True
                    
                    for bundle_item in bundle_doc.items:
                        if not any(bundle_item.item_code == item_data["item_code"] for item_data in items_list):
                            all_items_matched = False
                            break
                    
                    if all_items_matched:
                        # Check if item specifics match exactly
                        bundle_specifics = bundle_doc.get("item_specifics") or []
                        if len(bundle_specifics) == len(item_specifics):
                            all_specifics_matched = True
                            
                            for i in range(len(bundle_specifics)):
                                if bundle_specifics[i].name != item_specifics[i]["name"]:
                                    all_specifics_matched = False
                                    break
                            
                            if all_specifics_matched:
                                existing_bundle_found = True
                                matched_bundle = bundle_doc
                                break
            
            if existing_bundle_found:
                # Add the existing bundle to created_bundles
                total_rate = sum(item_data["rate"] for item_data in items_list)
                item_doc = frappe.get_doc("Item", matched_bundle.new_item_code)

                created_bundles.append({
                    "item_code": matched_bundle.name,
                    "item_name": item_doc.item_name,
                    "qty": items_list[0]["qty"],
                    "rate": total_rate,
                    "product_bundle": matched_bundle.as_dict()
                })
            else:
                # Create a new service item for the bundle
                first_item_code = items_list[0]["item_code"]
                
                if not first_item_code:
                    frappe.response["http_status_code"] = 400
                    return {"error": "Missing item_code in one of the bundles"}
                
                service_item_doc = frappe.new_doc("Item")
                service_item_doc.item_code = first_item_code
                service_item_doc.item_name = first_item_code
                service_item_doc.item_group = "Service Item"
                service_item_doc.is_stock_item = 0
                service_item_doc.save()
                frappe.db.commit()  # Optional: commit changes to the database

                # Create a new product bundle using the service item
                new_bundle = frappe.new_doc("Product Bundle")
                new_bundle.new_item_code = service_item_doc.name
                
                for item_data in items_list:
                    new_item = new_bundle.append("items", {})
                    new_item.item_code = item_data["item_code"]
                    new_item.item_name = item_data.get("item_name", "")
                    new_item.description = item_data["item_code"]
                    new_item.qty = 1
                
                # Add item specifics to the new product bundle if available
                for specific in item_specifics:
                    new_specific = new_bundle.append("item_specifics", {})
                    new_specific.item_specifics_name = specific["name"]
                
                new_bundle.save()
                frappe.db.commit()

                # Add the newly created bundle to created_bundles
                total_rate = sum(item_data["rate"] for item_data in items_list)
                created_bundles.append({
                    "item_code": new_bundle.name,
                    "item_name": service_item_doc.item_name,
                    "qty": items_list[0]["qty"],
                    "rate": total_rate,
                    "product_bundle": new_bundle.as_dict()
                })

        # Return the flat list of created bundles
        return created_bundles

    except Exception as e:
        frappe.response["http_status_code"] = 500
        return {"error": str(e)}


    except ValueError:
        # Return a 400 error if JSON data is invalid
        frappe.response["http_status_code"] = 400
        return {"error": "Invalid JSON data"}




@frappe.whitelist()
def get_items_details(pos_profile, items_data):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 60

    @redis_cache(ttl=ttl or 1800)
    def __get_items_details(pos_profile, items_data):
        return _get_items_details(pos_profile, items_data)

    def _get_items_details(pos_profile, items_data):
        today = nowdate()
        pos_profile = json.loads(pos_profile)
        items_data = json.loads(items_data)
        warehouse = pos_profile.get("warehouse")
        result = []

        if len(items_data) > 0:
            for item in items_data:
                item_code = item.get("item_code")
                item_stock_qty = get_stock_availability(item_code, warehouse)
                has_batch_no, has_serial_no = frappe.get_value(
                    "Item", item_code, ["has_batch_no", "has_serial_no"]
                )

                uoms = frappe.get_all(
                    "UOM Conversion Detail",
                    filters={"parent": item_code},
                    fields=["uom", "conversion_factor"],
                )

                serial_no_data = frappe.get_all(
                    "Serial No",
                    filters={
                        "item_code": item_code,
                        "status": "Active",
                        "warehouse": warehouse,
                    },
                    fields=["name as serial_no"],
                )

                batch_no_data = []

                batch_list = get_batch_qty(warehouse=warehouse, item_code=item_code)

                if batch_list:
                    for batch in batch_list:
                        if batch.qty > 0 and batch.batch_no:
                            batch_doc = frappe.get_cached_doc("Batch", batch.batch_no)
                            if (
                                str(batch_doc.expiry_date) > str(today)
                                or batch_doc.expiry_date in ["", None]
                            ) and batch_doc.disabled == 0:
                                batch_no_data.append(
                                    {
                                        "batch_no": batch.batch_no,
                                        "batch_qty": batch.qty,
                                        "expiry_date": batch_doc.expiry_date,
                                        "batch_price": batch_doc.posa_batch_price,
                                        "manufacturing_date": batch_doc.manufacturing_date,
                                    }
                                )
                
                row = {}
                row.update(item)
                row.update(
                    {
                        "item_uoms": uoms or [],
                        "serial_no_data": serial_no_data or [],
                        "batch_no_data": batch_no_data or [],
                        "actual_qty": item_stock_qty or 0,
                        "has_batch_no": has_batch_no,
                        "has_serial_no": has_serial_no,
                    }
                )

                result.append(row)

        return result

    if _pos_profile.get("posa_use_server_cache"):
        return __get_items_details(pos_profile, items_data)
    else:
        return _get_items_details(pos_profile, items_data)


@frappe.whitelist()
def get_item_with_rate(item, order_type):
    # Fetch the item document
    item_doc = frappe.get_doc("Item", item)

    # Determine the price list
    price_list = get_price_list(order_type) or "Standard Selling"

    # Fetch the item price based on the price list
    item_price_data = frappe.db.sql(
        """
        SELECT price_list_rate
        FROM `tabItem Price`
        WHERE item_code = %s AND price_list = %s
        LIMIT 1
        """, (item, price_list), as_dict=True
    )

    if item_price_data:
        item_price = item_price_data[0].price_list_rate
    else:
        item_price = None

    # Create a dictionary with item document and price details
    item_details = {
        "item_doc": item_doc,
        "price_list": price_list,
        "item_price": item_price
    }

    return item_details



@frappe.whitelist()
def get_item_detail(item, doc=None, warehouse=None, price_list=None ,order_type=None, pos_profile=None):
    
    item = json.loads(item)
    today = nowdate()
    item_code = item.get("item_code")
    batch_no_data = []
    if warehouse and item.get("has_batch_no"):
        batch_list = get_batch_qty(warehouse=warehouse, item_code=item_code)
        if batch_list:
            for batch in batch_list:
                if batch.qty > 0 and batch.batch_no:
                    batch_doc = frappe.get_cached_doc("Batch", batch.batch_no)
                    if (
                        str(batch_doc.expiry_date) > str(today)
                        or batch_doc.expiry_date in ["", None]
                    ) and batch_doc.disabled == 0:
                        batch_no_data.append(
                            {
                                "batch_no": batch.batch_no,
                                "batch_qty": batch.qty,
                                "expiry_date": batch_doc.expiry_date,
                                "batch_price": batch_doc.posa_batch_price,
                                "manufacturing_date": batch_doc.manufacturing_date,
                            }
                        )
        
    if not price_list:
        price_list = get_price_list(order_type) or "Standard Selling"
    item["selling_price_list"] = price_list
    item["price_list"] = price_list

    max_discount = frappe.get_value("Item", item_code, "max_discount")
    res = get_item_details(
        item,
        doc,
        overwrite_warehouse=False,
    )
    if item.get("is_stock_item") and warehouse:
        res["actual_qty"] = get_stock_availability(item_code, warehouse)
    res["max_discount"] = max_discount
    res["batch_no_data"] = batch_no_data
    return res


def get_stock_availability(item_code, warehouse):
    actual_qty = (
        frappe.db.get_value(
            "Stock Ledger Entry",
            filters={
                "item_code": item_code,
                "warehouse": warehouse,
                "is_cancelled": 0,
            },
            fieldname="qty_after_transaction",
            order_by="posting_date desc, posting_time desc, creation desc",
        )
        or 0.0
    )
    return actual_qty
@frappe.whitelist()
def create_customer_with_address(
    customer_id,
    customer_name,
    company,
    pos_profile_doc,
    tax_id=None,
    mobile_no=None,
    email_id=None,
    referral_code=None,
    birthday=None,
    customer_group=None,
    territory=None,
    customer_type=None,
    gender=None,
    address_line1=None,
    address_line2=None,
    city=None,
    state=None,
    country=None,
    pincode=None,
    phone=None,
    method="create",
):
    pos_profile = json.loads(pos_profile_doc)
    
    if method == "create":
        is_exist = frappe.db.exists("Customer", {"customer_name": customer_name})
        if pos_profile.get("posa_allow_duplicate_customer_names") or not is_exist:
            # Create Customer
            customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": customer_name,
                    "posa_referral_company": company,
                    "tax_id": tax_id,
                    "mobile_no": mobile_no,
                    "email_id": email_id,
                    "posa_referral_code": referral_code,
                    "posa_birthday": birthday,
                    "customer_type": customer_type,
                    "gender": gender,
                }
            )
            if customer_group:
                customer.customer_group = customer_group
            else:
                customer.customer_group = "All Customer Groups"
            if territory:
                customer.territory = territory
            else:
                customer.territory = "All Territories"
            customer.save()
            
            # Create Address and Dynamic Link
            if address_line1:
                address = frappe.get_doc(
                    {
                        "doctype": "Address",
                        "address_title": customer_name,
                        "address_type": "Billing",
                        "address_line1": address_line1,
                        "address_line2": address_line2,
                        "city": city,
                        "state": state,
                        "country": country,
                        "pincode": pincode,
                        "phone": phone,
                    }
                )
                address.append("links", {
                    "link_doctype": "Customer",
                    "link_name": customer.name
                })
                address.save()

                # Update Customer's primary address
                customer.customer_primary_address = address.name
            customer.save()

            return {"customer": customer, "address": address if address_line1 else None}
        else:
            frappe.throw(_("Customer already exists"))

    elif method == "update":
        customer_doc = frappe.get_doc("Customer", customer_id)
        customer_doc.customer_name = customer_name
        customer_doc.posa_referral_company = company
        customer_doc.tax_id = tax_id
        customer_doc.posa_referral_code = referral_code
        customer_doc.posa_birthday = birthday
        customer_doc.customer_type = customer_type
        customer_doc.territory = territory
        customer_doc.customer_group = customer_group
        customer_doc.gender = gender
        customer_doc.save()
        
        if mobile_no != customer_doc.mobile_no:
            set_customer_info(customer_doc.name, "mobile_no", mobile_no)
        if email_id != customer_doc.email_id:
            set_customer_info(customer_doc.name, "email_id", email_id)
        
        # Update Address
        if address_line1:
            address_doc = frappe.db.exists("Address", {"link_name": customer_doc.name})
            if address_doc:
                address = frappe.get_doc("Address", address_doc[0][0])
                address.address_line1 = address_line1
                address.address_line2 = address_line2
                address.city = city
                address.state = state
                address.country = country
                address.pincode = pincode
                address.phone = phone
                address.save()
            else:
                address = frappe.get_doc(
                    {
                        "doctype": "Address",
                        "address_title": customer_name,
                        "address_type": "Billing",
                        "address_line1": address_line1,
                        "address_line2": address_line2,
                        "city": city,
                        "state": state,
                        "country": country,
                        "pincode": pincode,
                        "phone": phone,
                    }
                )
                address.append("links", {
                    "link_doctype": "Customer",
                    "link_name": customer_doc.name
                })
                address.save()
            
            # Update Customer's primary address
            customer_doc.customer_primary_address = address.name
        customer_doc.save()

        return {"customer": customer_doc, "address": address if address_line1 else None}

def set_customer_info(customer_name, field, value):
    frappe.db.set_value("Customer", customer_name, field, value)


@frappe.whitelist()
def create_customer(
    customer_id,
    customer_name,
    company,
    pos_profile_doc,
    tax_id=None,
    mobile_no=None,
    email_id=None,
    referral_code=None,
    birthday=None,
    customer_group=None,
    territory=None,
    customer_type=None,
    gender=None,
    method="create",
):
    pos_profile = json.loads(pos_profile_doc)
    if method == "create":
        is_exist = frappe.db.exists("Customer", {"customer_name": customer_name})
        if pos_profile.get("posa_allow_duplicate_customer_names") or not is_exist:
            customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": customer_name,
                    "posa_referral_company": company,
                    "tax_id": tax_id,
                    "mobile_no": mobile_no,
                    "email_id": email_id,
                    "posa_referral_code": referral_code,
                    "posa_birthday": birthday,
                    "customer_type": customer_type,
                    "gender": gender,
                }
            )
            if customer_group:
                customer.customer_group = customer_group
            else:
                customer.customer_group = "All Customer Groups"
            if territory:
                customer.territory = territory
            else:
                customer.territory = "All Territories"
            customer.save()
            return customer
        else:
            frappe.throw(_("Customer already exists"))

    elif method == "update":
        customer_doc = frappe.get_doc("Customer", customer_id)
        customer_doc.customer_name = customer_name
        customer_doc.posa_referral_company = company
        customer_doc.tax_id = tax_id
        customer_doc.posa_referral_code = referral_code
        customer_doc.posa_birthday = birthday
        customer_doc.customer_type = customer_type
        customer_doc.territory = territory
        customer_doc.customer_group = customer_group
        customer_doc.gender = gender
        customer_doc.save()
        if mobile_no != customer_doc.mobile_no:
            set_customer_info(customer_doc.name, "mobile_no", mobile_no)
        if email_id != customer_doc.email_id:
            set_customer_info(customer_doc.name, "email_id", email_id)
        return customer_doc


@frappe.whitelist()
def get_items_from_barcode(selling_price_list, currency, barcode):
    search_item = frappe.get_all(
        "Item Barcode",
        filters={"barcode": barcode},
        fields=["parent", "barcode", "posa_uom"],
    )
    if len(search_item) == 0:
        return ""
    item_code = search_item[0].parent
    item_list = frappe.get_all(
        "Item",
        filters={"name": item_code},
        fields=[
            "name",
            "item_name",
            "description",
            "stock_uom",
            "image",
            "is_stock_item",
            "has_variants",
            "variant_of",
            "item_group",
            "has_batch_no",
            "has_serial_no",
        ],
    )

    if item_list[0]:
        item = item_list[0]
        filters = {"price_list": selling_price_list, "item_code": item_code}
        prices_with_uom = frappe.db.count(
            "Item Price",
            filters={
                "price_list": selling_price_list,
                "item_code": item_code,
                "uom": item.stock_uom,
            },
        )

        if prices_with_uom > 0:
            filters["uom"] = item.stock_uom
        else:
            filters["uom"] = ["in", ["", None, item.stock_uom]]

        item_prices_data = frappe.get_all(
            "Item Price",
            fields=["item_code", "price_list_rate", "currency"],
            filters=filters,
        )

        item_price = 0
        if len(item_prices_data):
            item_price = item_prices_data[0].get("price_list_rate")
            currency = item_prices_data[0].get("currency")

        item.update(
            {
                "rate": item_price,
                "currency": currency,
                "item_code": item_code,
                "barcode": barcode,
                "actual_qty": 0,
                "item_barcode": search_item,
            }
        )
        return item


@frappe.whitelist()
def set_customer_info(customer, fieldname, value=""):
    if fieldname == "loyalty_program":
        frappe.db.set_value("Customer", customer, "loyalty_program", value)

    contact = (
        frappe.get_cached_value("Customer", customer, "customer_primary_contact") or ""
    )

    if contact:
        contact_doc = frappe.get_doc("Contact", contact)
        if fieldname == "email_id":
            contact_doc.set("email_ids", [{"email_id": value, "is_primary": 1}])
            frappe.db.set_value("Customer", customer, "email_id", value)
        elif fieldname == "mobile_no":
            contact_doc.set("phone_nos", [{"phone": value, "is_primary_mobile_no": 1}])
            frappe.db.set_value("Customer", customer, "mobile_no", value)
        contact_doc.save()

    else:
        contact_doc = frappe.new_doc("Contact")
        contact_doc.first_name = customer
        contact_doc.is_primary_contact = 1
        contact_doc.is_billing_contact = 1
        if fieldname == "mobile_no":
            contact_doc.add_phone(value, is_primary_mobile_no=1, is_primary_phone=1)

        if fieldname == "email_id":
            contact_doc.add_email(value, is_primary=1)

        contact_doc.append("links", {"link_doctype": "Customer", "link_name": customer})

        contact_doc.flags.ignore_mandatory = True
        contact_doc.save()
        frappe.set_value(
            "Customer", customer, "customer_primary_contact", contact_doc.name
        )


@frappe.whitelist()
def search_invoices_for_return(invoice_name, company):
    invoices_list = frappe.get_list(
        "Sales Invoice",
        filters={
            "name": ["like", f"%{invoice_name}%"],
            "company": company,
            "docstatus": 1,
            "is_return": 0,
        },
        fields=["name"],
        limit_page_length=0,
        order_by="customer",
    )
    data = []
    is_returned = frappe.get_all(
        "Sales Invoice",
        filters={"return_against": invoice_name, "docstatus": 1},
        fields=["name"],
        order_by="customer",
    )
    if len(is_returned):
        return data
    for invoice in invoices_list:
        data.append(frappe.get_doc("Sales Invoice", invoice["name"]))
    return data


@frappe.whitelist()
def search_orders(company, currency, branch=None, order_name=None):
    filters = {
        "billing_status": ["in", ["Not Billed", "Partly Billed"]],
        "docstatus": 1,
        "company": company,
        "currency": currency,
    }
    if branch:
        filters["sender"] = branch
    if order_name:
        filters["name"] = ["like", f"%{order_name}%"]
    orders_list = frappe.get_list(
        "Sales Order",
        filters=filters,
        fields=["name"],
        limit_page_length=0,
        order_by="transaction_date desc, order_time desc, creation desc",
    )
    data = []
    for order in orders_list:
        data.append(frappe.get_doc("Sales Order", order["name"]))
    return data


def get_version():
    branch_name = get_app_branch("erpnext")
    if "12" in branch_name:
        return 12
    elif "13" in branch_name:
        return 13
    else:
        return 13


def get_app_branch(app):
    """Returns branch of an app"""
    import subprocess

    try:
        branch = subprocess.check_output(
            "cd ../apps/{0} && git rev-parse --abbrev-ref HEAD".format(app), shell=True
        )
        branch = branch.decode("utf-8")
        branch = branch.strip()
        return branch
    except Exception:
        return ""


@frappe.whitelist()
def get_offers(profile):
    pos_profile = frappe.get_doc("POS Profile", profile)
    pos_profile_filter = ""
    values = {
        "company": pos_profile.company,
        "pos_profile": None,
        "warehouse": pos_profile.warehouse,
        "valid_from": nowdate(),
        "valid_upto": nowdate(),
    }
    
    if profile:  # Only apply pos_profile filter if profile is provided
        values["pos_profile"] = profile
        
        pos_profile_filter = "AND (pos_profile = %(pos_profile)s)"
    else:
        # If profile is empty, retrieve offers without pos_profile filter
        values["company"] = "default_company"  # Or some fallback if needed
        
    query = f"""
        SELECT *
        FROM `tabPOS Offer`
        WHERE 
        disable = 0 AND
        company = %(company)s
        {pos_profile_filter} AND
        (warehouse is NULL OR warehouse = '' OR warehouse = %(warehouse)s) AND
        (valid_from is NULL OR valid_from = '' OR valid_from <= %(valid_from)s) AND
        (valid_upto is NULL OR valid_from = '' OR valid_upto >= %(valid_upto)s)
    """
    
    data = frappe.db.sql(query, values=values, as_dict=1)
    return data



@frappe.whitelist()
def get_customer_addresses(customer):
    return frappe.db.sql(
        """
        SELECT 
            address.name,
            address.address_line1,
            address.address_line2,
            address.address_title,
            address.city,
            address.state,
            address.country,
            address.address_type
        FROM `tabAddress` as address
        INNER JOIN `tabDynamic Link` AS link
				ON address.name = link.parent
        WHERE link.link_doctype = 'Customer'
            AND link.link_name = '{0}'
            AND address.disabled = 0
        ORDER BY address.name
        """.format(
            customer
        ),
        as_dict=1,
    )


@frappe.whitelist()
def make_address(args):
    args = json.loads(args)
    address = frappe.get_doc(
        {
            "doctype": "Address",
            "address_title": args.get("name"),
            "address_line1": args.get("address_line1"),
            "address_line2": args.get("address_line2"),
            "city": args.get("city"),
            "state": args.get("state"),
            "pincode": args.get("pincode"),
            "country": args.get("country"),
            "address_type": "Shipping",
            "links": [
                {"link_doctype": args.get("doctype"), "link_name": args.get("customer")}
            ],
        }
    ).insert()

    return address


def build_item_cache(item_code):
    parent_item_code = item_code

    attributes = [
        a.attribute
        for a in frappe.db.get_all(
            "Item Variant Attribute",
            {"parent": parent_item_code},
            ["attribute"],
            order_by="idx asc",
        )
    ]

    item_variants_data = frappe.db.get_all(
        "Item Variant Attribute",
        {"variant_of": parent_item_code},
        ["parent", "attribute", "attribute_value"],
        order_by="name",
        as_list=1,
    )

    disabled_items = set([i.name for i in frappe.db.get_all("Item", {"disabled": 1})])

    attribute_value_item_map = frappe._dict({})
    item_attribute_value_map = frappe._dict({})

    item_variants_data = [r for r in item_variants_data if r[0] not in disabled_items]
    for row in item_variants_data:
        item_code, attribute, attribute_value = row
        # (attr, value) => [item1, item2]
        attribute_value_item_map.setdefault((attribute, attribute_value), []).append(
            item_code
        )
        # item => {attr1: value1, attr2: value2}
        item_attribute_value_map.setdefault(item_code, {})[attribute] = attribute_value

    optional_attributes = set()
    for item_code, attr_dict in item_attribute_value_map.items():
        for attribute in attributes:
            if attribute not in attr_dict:
                optional_attributes.add(attribute)

    frappe.cache().hset(
        "attribute_value_item_map", parent_item_code, attribute_value_item_map
    )
    frappe.cache().hset(
        "item_attribute_value_map", parent_item_code, item_attribute_value_map
    )
    frappe.cache().hset("item_variants_data", parent_item_code, item_variants_data)
    frappe.cache().hset("optional_attributes", parent_item_code, optional_attributes)


def get_item_optional_attributes(item_code):
    val = frappe.cache().hget("optional_attributes", item_code)

    if not val:
        build_item_cache(item_code)

    return frappe.cache().hget("optional_attributes", item_code)

def get_sales_invoices(pos_shift, pos_profile):
    # Assuming you're using Frappe ORM or SQL queries

    # Example using Frappe ORM (recommended)
    invoices = frappe.get_list(
        "Sales Invoice",
        filters={"pos_shift": pos_shift, "pos_profile": pos_profile, "docstatus": 1},
        fields=["name", "customer", "grand_total", "posting_date"],
    )

    return invoices




@frappe.whitelist()
def create_sales_return(invoice):
    # Fetch the original sales invoice
    try:
        invoice = frappe._dict(frappe.parse_json(invoice))
    except Exception as e:
        frappe.throw(f"Failed to parse the invoice. Error: {str(e)}")
    if not invoice:
        frappe.throw(f"Sales Invoice {invoice.name} not found.")
    if invoice.is_return:
        frappe.throw("You cannot create a return for a return invoice.")
    if invoice.docstatus != 1:
        frappe.throw("Only submitted invoices can be returned.")
    if not invoice.pos_profile:
        frappe.throw("The original Sales Invoice does not have a POS Profile.")

    try:
        # Create the Sales Return document
        sales_return = frappe.new_doc("Sales Invoice")
        sales_return.update({
            "naming_series": invoice.naming_series,
            "customer": invoice.customer,
            "customer_name": invoice.customer_name,
            "company": invoice.company,
            "company_tax_id": invoice.company_tax_id,
            "pos_profile": invoice.pos_profile,
            "custom_branch": invoice.custom_branch,
            "posting_date": frappe.utils.today(),
            "posting_time": frappe.utils.nowtime(),
            "is_return": 1,
            "posa_pos_opening_shift": invoice.posa_pos_opening_shift,
            "return_against": invoice.name,
            "items": [],
            "taxes_and_charges": invoice.taxes_and_charges,
            "taxes": [],
            "payments": [],
            "is_pos": 1,
            "docstatus": 0,
            "update_stock" : 1
        })

        # Copy items and adjust quantities
        for item in invoice.get("items", []):
            sales_return.append("items", {
                "item_code": item["item_code"],
                "item_name": item["item_name"],
                "description": item["description"],
                "uom": item["uom"],
                "qty": -1 * item["qty"],
                "rate": item["rate"],
                "amount": -1 * item["amount"],
                "warehouse": item["warehouse"],
                "income_account": item["income_account"],
                "cost_center": item["cost_center"],
            })

        # # Copy taxes
        # for tax in invoice.get("taxes", []):
        #     sales_return.append("taxes", {
        #         "charge_type": tax["charge_type"],
        #         "account_head": tax["account_head"],
        #         "description": tax["description"],
        #         "rate": tax["rate"],
        #         "tax_amount": -1 * tax["tax_amount"],
        #         "cost_center": tax["cost_center"],
        #     })

        # Copy payments if applicable
        for payment in invoice.get("payments", []):
            sales_return.append("payments", {
                "mode_of_payment": payment["mode_of_payment"],
                "amount": -1 * invoice.rounded_total,
                "account": payment["account"],
                "type": payment["type"],
            })

        # Save and submit the Sales Return
        sales_return.insert(ignore_permissions=True)
        sales_return.submit()
          # Step 2: Prepare Credit Note Data
        credit_amount = invoice.outstanding_amount or invoice.grand_total
        default_income_account = frappe.get_value("Company", invoice.company, "default_income_account")

        credit_note = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Credit Note",
            "posting_date": frappe.utils.nowdate(),
            "company": invoice.company,
            "accounts": [
                {
                    "account": invoice.debit_to,
                    "party_type": "Customer",
                    "party": invoice.customer,
                    "credit_in_account_currency": credit_amount,
                    "reference_type": "Sales Invoice",
                    "reference_name": invoice.name,
                },
                {
                    "account": default_income_account,
                    "debit_in_account_currency": credit_amount,
                }
            ],
            "remarks": f"Credit Note for Sales Invoice {invoice.name}",
        }).insert(ignore_permissions=True)
        credit_note.submit()
        return {
        "status": "success",
        "message": f"Return invoice {sales_return.name} and credit note {credit_note.name} created successfully.",
        "return_invoice": sales_return.name,
        "credit_note": credit_note.name
    }

    except Exception as e:
        frappe.throw(f"An error occurred while creating the Sales Return: {str(e)}")


        

@frappe.whitelist()
def get_item_attributes(item_code):
    # Get all attributes for the given item
    attributes = frappe.db.get_all(
        "Item Variant Attribute",
        fields=["attribute","attribute_value",""],
        filters={"parenttype": "Item", "variant_of": item_code},
        order_by="idx asc",
    )
    organized_attributes = {}

    # Iterate through each attribute dictionary
    for attr in attributes:
        attribute_name = attr['attribute']
        attribute_value = attr['attribute_value']

        # Check if attribute name already exists in organized_attributes
        if attribute_name in organized_attributes:
            # Check if attribute_value already exists in values list
            if not any(v['attribute_value'] == attribute_value for v in organized_attributes[attribute_name]['values']):
                organized_attributes[attribute_name]['values'].append({'attribute_value': attribute_value, 'abbr': attribute_value})
        else:
            organized_attributes[attribute_name] = {
                'attribute': attribute_name,
                'values': [{'attribute_value': attribute_value, 'abbr': attribute_value}]
            }

    # Convert the dictionary to a list of dictionaries (desired format)
    desired_format = list(organized_attributes.values())

    # Print the result
    return desired_format

    # # Get optional attributes for the item
    # optional_attributes = get_item_optional_attributes(item_code)

    # # List to store attributes with variants
    # attributes_with_variants = []

    # for a in attributes:
    #     # Check if the attribute has any variant values
    #     values = frappe.db.get_all(
    #         "Item Attribute Value",
    #         fields=["attribute_value", "abbr"],
    #         filters={"parenttype": "Item Attribute", "parent": a['attribute']},
    #         order_by="idx asc",
    #     )

    #     # Only include the attribute if it has variant values
    #     if values:
    #         a['values'] = values
    #         if a['attribute'] in optional_attributes:
    #             a['optional'] = True
    #         attributes_with_variants.append(a)

    # print(attributes_with_variants) 



@frappe.whitelist()
def create_payment_request(doc):
    doc = json.loads(doc)
    for pay in doc.get("payments"):
        if pay.get("type") == "Phone":
            if pay.get("amount") <= 0:
                frappe.throw(_("Payment amount cannot be less than or equal to 0"))

            if not doc.get("contact_mobile"):
                frappe.throw(_("Please enter the phone number first"))

            pay_req = get_existing_payment_request(doc, pay)
            if not pay_req:
                pay_req = get_new_payment_request(doc, pay)
                pay_req.submit()
            else:
                pay_req.request_phone_payment()

            return pay_req


def get_new_payment_request(doc, mop):
    payment_gateway_account = frappe.db.get_value(
        "Payment Gateway Account",
        {
            "payment_account": mop.get("account"),
        },
        ["name"],
    )

    args = {
        "dt": "Sales Invoice",
        "dn": doc.get("name"),
        "recipient_id": doc.get("contact_mobile"),
        "mode_of_payment": mop.get("mode_of_payment"),
        "payment_gateway_account": payment_gateway_account,
        "payment_request_type": "Inward",
        "party_type": "Customer",
        "party": doc.get("customer"),
        "return_doc": True,
    }
    return make_payment_request(**args)


def get_payment_gateway_account(args):
    return frappe.db.get_value(
        "Payment Gateway Account",
        args,
        ["name", "payment_gateway", "payment_account", "message"],
        as_dict=1,
    )


def get_existing_payment_request(doc, pay):
    payment_gateway_account = frappe.db.get_value(
        "Payment Gateway Account",
        {
            "payment_account": pay.get("account"),
        },
        ["name"],
    )

    args = {
        "doctype": "Payment Request",
        "reference_doctype": "Sales Invoice",
        "reference_name": doc.get("name"),
        "payment_gateway_account": payment_gateway_account,
        "email_to": doc.get("contact_mobile"),
    }
    pr = frappe.db.exists(args)
    if pr:
        return frappe.get_doc("Payment Request", pr)


def make_payment_request(**args):
    """Make payment request"""

    args = frappe._dict(args)

    ref_doc = frappe.get_doc(args.dt, args.dn)
    gateway_account = get_payment_gateway_account(args.get("payment_gateway_account"))
    if not gateway_account:
        frappe.throw(_("Payment Gateway Account not found"))

    grand_total = get_amount(ref_doc, gateway_account.get("payment_account"))
    if args.loyalty_points and args.dt == "Sales Order":
        from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
            validate_loyalty_points,
        )

        loyalty_amount = validate_loyalty_points(ref_doc, int(args.loyalty_points))
        frappe.db.set_value(
            "Sales Order",
            args.dn,
            "loyalty_points",
            int(args.loyalty_points),
            update_modified=False,
        )
        frappe.db.set_value(
            "Sales Order",
            args.dn,
            "loyalty_amount",
            loyalty_amount,
            update_modified=False,
        )
        grand_total = grand_total - loyalty_amount

    bank_account = (
        get_party_bank_account(args.get("party_type"), args.get("party"))
        if args.get("party_type")
        else ""
    )

    existing_payment_request = None
    if args.order_type == "Shopping Cart":
        existing_payment_request = frappe.db.get_value(
            "Payment Request",
            {
                "reference_doctype": args.dt,
                "reference_name": args.dn,
                "docstatus": ("!=", 2),
            },
        )

    if existing_payment_request:
        frappe.db.set_value(
            "Payment Request",
            existing_payment_request,
            "grand_total",
            grand_total,
            update_modified=False,
        )
        pr = frappe.get_doc("Payment Request", existing_payment_request)
    else:
        if args.order_type != "Shopping Cart":
            existing_payment_request_amount = get_existing_payment_request_amount(
                args.dt, args.dn
            )

            if existing_payment_request_amount:
                grand_total -= existing_payment_request_amount

        pr = frappe.new_doc("Payment Request")
        pr.update(
            {
                "payment_gateway_account": gateway_account.get("name"),
                "payment_gateway": gateway_account.get("payment_gateway"),
                "payment_account": gateway_account.get("payment_account"),
                "payment_channel": gateway_account.get("payment_channel"),
                "payment_request_type": args.get("payment_request_type"),
                "currency": ref_doc.currency,
                "grand_total": grand_total,
                "mode_of_payment": args.mode_of_payment,
                "email_to": args.recipient_id or ref_doc.owner,
                "subject": _("Payment Request for {0}").format(args.dn),
                "message": gateway_account.get("message") or get_dummy_message(ref_doc),
                "reference_doctype": args.dt,
                "reference_name": args.dn,
                "party_type": args.get("party_type") or "Customer",
                "party": args.get("party") or ref_doc.get("customer"),
                "bank_account": bank_account,
            }
        )

        if args.order_type == "Shopping Cart" or args.mute_email:
            pr.flags.mute_email = True

        pr.insert(ignore_permissions=True)
        if args.submit_doc:
            pr.submit()

    if args.order_type == "Shopping Cart":
        frappe.db.commit()
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = pr.get_payment_url()

    if args.return_doc:
        return pr

    return pr.as_dict()


def get_amount(ref_doc, payment_account=None):
    """get amount based on doctype"""
    grand_total = 0
    for pay in ref_doc.payments:
        if pay.type == "Phone" and pay.account == payment_account:
            grand_total = pay.amount
            break

    if grand_total > 0:
        return grand_total

    else:
        frappe.throw(
            _("Payment Entry is already created or payment account is not matched")
        )


@frappe.whitelist()
def get_pos_coupon(coupon, customer, company):
    res = check_coupon_code(coupon, customer, company)
    return res


@frappe.whitelist()
def get_active_gift_coupons(customer, company):
    coupons = []
    coupons_data = frappe.get_all(
        "POS Coupon",
        filters={
            "company": company,
            "coupon_type": "Gift Card",
            "customer": customer,
            "used": 0,
        },
        fields=["coupon_code"],
    )
    if len(coupons_data):
        coupons = [i.coupon_code for i in coupons_data]
    return coupons


@frappe.whitelist()
def get_customer_info(customer):
    customer = frappe.get_doc("Customer", customer)

    res = {"loyalty_points": None, "conversion_factor": None}

    res["email_id"] = customer.email_id
    res["mobile_no"] = customer.mobile_no
    res["image"] = customer.image
    res["loyalty_program"] = customer.loyalty_program
    res["customer_price_list"] = customer.default_price_list
    res["customer_group"] = customer.customer_group
    res["customer_type"] = customer.customer_type
    res["territory"] = customer.territory
    res["birthday"] = customer.posa_birthday
    res["gender"] = customer.gender
    res["tax_id"] = customer.tax_id
    res["posa_discount"] = customer.posa_discount
    res["name"] = customer.name
    res["customer_name"] = customer.customer_name
    res["customer_group_price_list"] = frappe.get_value(
        "Customer Group", customer.customer_group, "default_price_list"
    )

    if customer.loyalty_program:
        lp_details = get_loyalty_program_details_with_points(
            customer.name,
            customer.loyalty_program,
            silent=True,
            include_expired_entry=False,
        )
        res["loyalty_points"] = lp_details.get("loyalty_points")
        res["conversion_factor"] = lp_details.get("conversion_factor")

    return res


def get_company_domain(company):
    return frappe.get_cached_value("Company", cstr(company), "domain")


@frappe.whitelist()
def get_applicable_delivery_charges(
    company, pos_profile, customer, shipping_address_name=None
):
    return _get_applicable_delivery_charges(
        company, pos_profile, customer, shipping_address_name
    )


def auto_create_items():
    # create 20000 items
    for i in range(20000):
        item_code = "AUTO-ITEM-{}".format(i)
        item = frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "description": item_code,
                "item_group": "Auto Items",
                "is_stock_item": 0,
                "stock_uom": "Nos",
                "is_sales_item": 1,
                "is_purchase_item": 0,
                "is_fixed_asset": 0,
                "is_sub_contracted_item": 0,
                "is_pro_applicable": 0,
                "is_manufactured_item": 0,
                "is_service_item": 0,
                "is_non_stock_item": 0,
                "is_batch_item": 0,
                "is_table_item": 0,
                "is_variant_item": 0,
                "is_stock_item": 1,
                "opening_stock": 1000,
                "valuation_rate": 50 + i,
                "standard_rate": 100 + i,
            }
        )
        item.insert(ignore_permissions=True)
        frappe.db.commit()


@frappe.whitelist()
def search_serial_or_batch_or_barcode_number(search_value, search_serial_no):
    # search barcode no
    barcode_data = frappe.db.get_value(
        "Item Barcode",
        {"barcode": search_value},
        ["barcode", "parent as item_code"],
        as_dict=True,
    )
    if barcode_data:
        return barcode_data
    # search serial no
    if search_serial_no:
        serial_no_data = frappe.db.get_value(
            "Serial No", search_value, ["name as serial_no", "item_code"], as_dict=True
        )
        if serial_no_data:
            return serial_no_data
    # search batch no
    batch_no_data = frappe.db.get_value(
        "Batch", search_value, ["name as batch_no", "item as item_code"], as_dict=True
    )
    if batch_no_data:
        return batch_no_data
    return {}


def get_seearch_items_conditions(item_code, serial_no, batch_no, barcode):
    if serial_no or batch_no or barcode:
        return " and name = {0}".format(frappe.db.escape(item_code))
    return """ and (name like {item_code} or item_name like {item_code})""".format(
        item_code=frappe.db.escape("%" + item_code + "%")
    )


@frappe.whitelist()
def create_sales_invoice_from_order(sales_order):
    sales_invoice = make_sales_invoice(sales_order, ignore_permissions=True)
    sales_invoice.save()
    return sales_invoice


@frappe.whitelist()
def delete_sales_invoice(sales_invoice):
    frappe.delete_doc("Sales Invoice", sales_invoice)


@frappe.whitelist()
def get_sales_invoice_child_table(sales_invoice, sales_invoice_item):
    parent_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    child_doc = frappe.get_doc(
        "Sales Invoice Item", {"parent": parent_doc.name, "name": sales_invoice_item}
    )
    return child_doc

from frappe.utils import cint
@frappe.whitelist()
def get_next_token_number(company, pos_profile, pos_opening_shift):
    """
    Get the next token number from POS Opening Shift.
    If token is empty or zero → start from 1.
    Otherwise → return current token and increment in POS Opening Shift.
    """
    try:
        # Only generate token numbers for Run of the Mill
        if company != "Run of the Mill":
            return None

        # Get the POS Opening Shift doc
        shift_doc = frappe.get_doc("POS Opening Shift", pos_opening_shift)

        # Read current token
        current_token = cint(shift_doc.custom_current_token)

        if not current_token or current_token <= 0:
            # If empty or zero → set to 1
            next_token = 1
        else:
            # If more than 0 → return current and increment
            next_token = current_token

        # Update shift token for next time
        shift_doc.custom_current_token = next_token + 1
        shift_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return str(next_token)

    except Exception as e:
        frappe.log_error(f"Error getting next token number: {str(e)}", "Token Number Error")
        return "1"  # Default to 1 if there's an error


# for Digital KOT
@frappe.whitelist()
def create_kot(order=None, items=None, table_no=None, company=None, warehouse=None, notes=None, pos_opening_shift=None, sales_invoice=None):
    """
    Create a KOT from POS cart (without requiring Sales Invoice).
    items is expected as list of dicts: [{item_code, item_name, qty, uom, remarks}]
    """
    if isinstance(items, str):
        items = json.loads(items)

    if not items:
        frappe.throw(_("No items provided for KOT"))


    doc = frappe.new_doc("Kitchen Order Ticket")
    doc.company = company
    doc.warehouse = warehouse
    doc.table_no = table_no
    doc.notes = notes
    doc.pos_opening_shift = pos_opening_shift
    doc.sales_invoice = sales_invoice
    for it in items:
        child = doc.append("items", {})
        child.item_code = it.get("item_code")
        child.item_name = it.get("item_name")
        child.qty = it.get("qty", 1)
        child.uom = it.get("uom")
        child.remarks = it.get("remarks")
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "kot_no": doc.kot_no, "status": doc.status}

@frappe.whitelist()
def get_pending_kots(company, pos_profile, statuses=None, limit=200):
    filters = {}
    # try:
    statuses = ["todo", "inprogress", "completed"]
    if isinstance(statuses, str):
        statuses = statuses.split(',')
    filters = {"status": ["in", statuses]}
    if company:
        filters = {"pos_profile":company}
    if pos_profile:
        filters = {"pos_profile":pos_profile}
    kots = frappe.get_all("Kitchen Order Ticket",
        fields=["name", "kot_no", "status", "token_no", "company", "pos_profile", "sales_invoice"],
        filters=filters,
        order_by="token_no desc",
        limit=limit
    )
    # fetch items
    # for k in kots:
    #     k["items"] = frappe.get_all("Kitchen Order Ticket Item", fields=["item_name as name","qty as quantity","item_group"], filters={"parent": k.name})
    # return kots
    if not kots:
        return []

    # Step 2: Build result
    result = []

    for kot in kots:
        # Fetch items for each KOT
        kot_items = frappe.get_all(
            "Kitchen Order Ticket Item",
            fields=["name", "item_name", "qty as quantity", "item_group", "remarks", "item_status"],
            filters={"parent": kot.name, "item_status": ["in", statuses]}
        )

        if not kot_items:
            continue
        # Group items by item_group
        grouped = {}
        for item in kot_items:
            grouped.setdefault(item["item_group"], []).append(item)


        merged_groups = {}
        for item_group, items in grouped.items():
            key = item_group

            # Combine Smoothies + Add-ons
            if item_group in ["Smoothies-RM", "AddOns-RM"]:
                key = "Smoothies-RM"

            if key not in merged_groups:
                merged_groups[key] = []

            merged_groups[key].extend(items)

        # For each item_group, make a separate payload block
        for item_group, items in merged_groups.items():
            # Extract child statuses
            statuses_in_group = {i.get("item_status", "todo").lower() for i in items}

            # Derive group status logic
            if all(s == "completed" for s in statuses_in_group):
                group_status = "completed"
            elif any(s == "inprogress" for s in statuses_in_group):
                group_status = "inprogress"
            else:
                group_status = "todo"

            result.append({
                "name": kot.name,
                "kot_no": kot.kot_no,
                "status": group_status,
                "sales_invoice": kot.sales_invoice,
                "token_no": kot.token_no,
                "item_group": item_group,
                "items": items,
            })

    return result
    
    # except Exception as e:
    #     frappe.log_error(f"Error getting KOTs: {str(e)}", "KOT Error")
    #     return "1"  # Default to 1 if there's an error

@frappe.whitelist()
def update_kot_status(item_id=None, item_ids=None, new_status=None):
    # allowed = ["todo", "inprogress", "completed", "delivered"]
    # if status not in allowed:
    #     frappe.throw(_("Invalid status"))
    # doc = frappe.get_doc("Kitchen Order Ticket", kot_name)
    # doc.status = status
    # doc.save(ignore_permissions=True)
    # frappe.db.commit()
    """
    Update item(s) in Kitchen Order Ticket Item.
    - If one item_id is sent: updates that row only.
    - If multiple item_ids are sent: updates all of them together.
    """
    if not new_status:
        frappe.throw("New status is required.")

    # Normalize input into a list
    item_list = []

    if item_ids:
        # If frontend sends JSON array → parse it
        if isinstance(item_ids, str):
            import json
            item_list = json.loads(item_ids)
        else:
            item_list = item_ids
    elif item_id:
        item_list = [item_id]
    else:
        frappe.throw("Item ID(s) required.")

    parent_kot_set = set()

    # Update each item
    for iid in item_list:
        frappe.db.set_value("Kitchen Order Ticket Item", iid, "item_status", new_status)
        parent_kot = frappe.db.get_value("Kitchen Order Ticket Item", iid, "parent")
        if parent_kot:
            parent_kot_set.add(parent_kot)

    # For each affected KOT parent, update if all done
    for kot in parent_kot_set:
        remaining = frappe.db.count(
            "Kitchen Order Ticket Item",
            {"parent": kot, "item_status": ["!=", "delivered"]}
        )

        # auto-update parent only when everything done
        if remaining == 0:
            frappe.db.set_value("Kitchen Order Ticket", kot, "status", "delivered")
        elif remaining > 0 and new_status == "inprogress":
            frappe.db.set_value("Kitchen Order Ticket", kot, "status", "inprogress")

    frappe.db.commit()

    frappe.publish_realtime(
        "kot_created",
        {"kot": 'success'},
        after_commit=True
    )

    return {"name": kot, "status": new_status}


# Optional: auto‑KOT from Sales Invoice (if you want that flow)
@frappe.whitelist()
def create_kot_from_sales_invoice(doc, method=None):
    """Hook for Sales Invoice on_submit. Extracts kitchen items and creates a KOT."""
    # doc is a Sales Invoice document
    items = []
    for it in doc.items:
        if getattr(it, "is_kitchen_item", 1): 
            # Todo: add flag in Item if needed
            items.append({
            "item_code": it.item_code,
            "item_name": it.item_name,
            "qty": it.qty,
            "uom": it.uom,
            "remarks": getattr(it, "kot_remarks", None)
            })
    if not items:
        return
    
    return create_kot(items=items, table_no=getattr(doc, "table_no", None), company=doc.company, warehouse=doc.set_warehouse, notes=None, pos_opening_shift=getattr(doc, "pos_opening_shift", None), sales_invoice=doc.name)



def clean_invoice_for_v15(invoice_doc):
    # Parent check fields
    invoice_doc.is_return = cint(invoice_doc.get("is_return") or 0)
    invoice_doc.update_stock = cint(invoice_doc.get("update_stock") or 0)
    invoice_doc.is_pos = cint(invoice_doc.get("is_pos") or 0)
    invoice_doc.set_posting_time = cint(invoice_doc.get("set_posting_time") or 0)

    # Empty link fields should be None, not ""
    if not invoice_doc.get("return_against"):
        invoice_doc.return_against = None

    # Item rows cleanup
    for d in invoice_doc.items:
        d.allow_zero_valuation_rate = cint(d.get("allow_zero_valuation_rate") or 0)
        d.is_free_item = cint(d.get("is_free_item") or 0)

        if d.get("qty") in ("", None):
            d.qty = 0
        else:
            d.qty = flt(d.qty)

        if d.get("rate") in ("", None):
            d.rate = 0
        else:
            d.rate = flt(d.rate)

        if d.get("amount") in ("", None):
            d.amount = 0
        else:
            d.amount = flt(d.amount)

        if d.get("price_list_rate") in ("", None):
            d.price_list_rate = 0
        else:
            d.price_list_rate = flt(d.price_list_rate)

        if d.get("conversion_factor") in ("", None, 0):
            d.conversion_factor = 1
        else:
            d.conversion_factor = flt(d.conversion_factor)
