# Copyright (c) 2023, Hussain and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.model.document import Document
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import get_default_bom
from erpnext.stock.doctype.stock_entry.stock_entry import get_uom_details

class AutomatedBOMManufacturing(Document):
	def validate(self):
		self.validate_item()
		self.get_default_bom_for_finished()
		self.validate_bom()
		self.validate_item_qty()

	def validate_item_qty(self):
		if not self.qty or self.qty <= 0:
			frappe.throw(_("QTY must be greater then 0."))

	def get_default_bom_for_finished(self):
		if not self.bom:
			self.bom = get_default_bom(self.item_code)

	def validate_item(self):
		self.item_doc = frappe.get_doc("Item", self.item_code)
		if not self.item_doc.include_item_in_manufacturing:
			frappe.throw(_("Include Item in Manufacturing is not checked for Finished Item"))

	def validate_bom(self):
		bom = frappe.get_doc("BOM", self.bom)
		if self.item_code != bom.item:
			frappe.throw(_("Finished Item in BOM doesn't match with the Item Selected"))

		if not bom.is_active:
			frappe.throw(_("BOM is not Active"))

	def on_submit(self):
		if not self.bom:
			frappe.throw(_(""))
		self.submit_stock_entry()

	def submit_stock_entry(self):
		# Fetch the Sales Invoice using reference_name
		sales_invoice = frappe.get_doc("Sales Invoice", self.reference_name)
		order_type = sales_invoice.resturent_type

		# Fetch the BOM and filter BOM items based on order_type
		bom = frappe.get_doc("BOM", self.bom)
		bom_items = {}

		# Filter BOM items to only include those with no order_type or matching order_type
		for item in bom.items:
			if not item.order_type or item.order_type == order_type:
				if item.item_code in bom_items:
					# If the item_code already exists, merge the quantities
					bom_items[item.item_code].qty += item.qty
				else:
					# If the item_code does not exist, add it to bom_items
					bom_items[item.item_code] = item


		# Create a new Stock Entry document
		se = frappe.new_doc("Stock Entry")
		se.set_posting_time = 1
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time
		se.company = self.company
		se.stock_entry_type = "Manufacture"
		se.purpose = "Manufacture"
		se.from_bom = 1
		se.use_multi_level_bom = 0
		se.bom_no = self.bom
		se.fg_completed_qty = self.qty
		se.get_items()
		se.automated_bom_manufacturing = self.name
		se.cost_center = self.cost_center

		# Update se.items based on bom_items and retain finished_good items
		updated_items = []
		for d in se.items:
			if d.item_code in bom_items:
				# Update the quantity in Stock Entry items based on BOM items
				bom_item = bom_items[d.item_code]
				d.qty = bom_item.qty * self.qty  # Adjust quantity based on Stock Entry quantity

				d.uom = bom_item.uom
				conver = get_uom_details(d.item_code, d.uom, d.qty)
				d.conversion_factor = conver['conversion_factor']
				d.transfer_qty = conver['transfer_qty']

				updated_items.append(d)
			elif d.is_finished_item:
				# Retain finished goods items even if they are not in bom_items
				updated_items.append(d)
		
		# Assign the updated items back to se.items
		se.items = updated_items

		# Update warehouses and cost centers
		for d in se.items:
			d.cost_center = self.cost_center
			item_default = get_item_defaults(d.item_code, self.company)
			if not item_default.get("default_warehouse"):
				frappe.throw(_("Set Default Warehouse for Item {0}: {1}".format(d.item_code, d.item_name)))

			if d.is_finished_item or d.is_scrap_item:
				d.t_warehouse = item_default.get("default_warehouse")
			else:
				d.s_warehouse = item_default.get("default_warehouse")

		se.save()
		se.submit()


def create_automated_bom_manufacturing(data):
	data = json.loads(data)
	pos_settings = frappe.get_single("POS Settings")
	if pos_settings.post_auto_consumption_on_sales:
		for d in data["items"]:
			bom = get_default_bom(d["item_code"])
			if bom:
				doc = frappe.new_doc("Automated BOM Manufacturing")
				doc.item_code = d["item_code"]
				doc.bom = bom
				doc.posting_date = data["posting_date"]
				doc.posting_time = data["posting_time"]
				doc.reference_doctype = data["doctype"]
				doc.reference_name = data["name"]
				doc.cost_center = data["cost_center"]
				doc.qty = d["qty"]
				doc.save()
				doc.submit()