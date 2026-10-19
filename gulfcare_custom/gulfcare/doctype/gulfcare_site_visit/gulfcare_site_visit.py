
# Copyright (c) 2026, akhil mm and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class GulfCareSiteVisit(Document):
    def before_insert(self):
        if not self.status:
            self.status = "Planned"

    def validate(self):
        if self.visit_date and getdate(self.visit_date) < getdate(today()):
            frappe.throw("Visit Date cannot be in the past.")

    def on_trash(self):
        if self.status == "Completed":
            frappe.throw("Completed site visits cannot be deleted.")
