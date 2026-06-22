from frappe import _
from erpnext.accounts.doctype.sales_invoice.sales_invoice_dashboard import get_data as get_sales_invoice_dashboard


def get_data(data=None):
    data = get_sales_invoice_dashboard()

    data.setdefault("transactions", [])

    data["transactions"].append({
        "label": _("Reference"),
        "items": [
            "Automated BOM Manufacturing",
            "Stock Entry"
        ],
    })

    data.setdefault("non_standard_fieldnames", {})
    data["non_standard_fieldnames"].update({
        "Automated BOM Manufacturing": "reference_name",
        "Stock Entry": "sales_invoice"
    })

    return data