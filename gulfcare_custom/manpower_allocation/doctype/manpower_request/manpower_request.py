# Copyright (c) 2026, akhil mm and contributors
# For license information, please see license.txt

# import frappe

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class ManpowerRequest(Document):
    def before_insert(self):
        if not self.status:
            self.status = "Draft"

    def validate(self):
        self.validate_dates()
        self.validate_workers_required()
        self.validate_opportunity()
        self.validate_status_transition()

    def validate_dates(self):
        if not self.start_date or not self.end_date:
            frappe.throw("Start Date and End Date are required.")

        if getdate(self.end_date) < getdate(self.start_date):
            frappe.throw("End Date cannot be before Start Date.")

    def validate_workers_required(self):
        if self.workers_required is None or self.workers_required <= 0:
            frappe.throw("Workers Required must be greater than zero.")

    def validate_opportunity(self):
        if not self.opportunity:
            return

        opportunity = frappe.db.get_value(
            "Opportunity",
            self.opportunity,
            ["opportunity_from", "party_name"],
            as_dict=True,
        )

        if not opportunity:
            frappe.throw("The selected Opportunity does not exist.")

        if opportunity.opportunity_from == "Customer":
            if opportunity.party_name != self.customer:
                frappe.throw(
                    "The selected Opportunity does not belong to this Customer."
                )

        elif opportunity.opportunity_from == "Lead":
            customer_lead = frappe.db.get_value(
                "Customer",
                self.customer,
                "lead_name",
            )

            if opportunity.party_name != customer_lead:
                frappe.throw(
                    "The selected Opportunity is not associated with this Customer."
                )

        else:
            frappe.throw(
                "Select an Opportunity linked to this Customer or its originating Lead."
            )

    def validate_status_transition(self):
        old_doc = self.get_doc_before_save()

        # New documents must start as Draft.
        if not old_doc:
            if self.status != "Draft":
                frappe.throw("New requests must start as Draft.")
            return

        old_status = old_doc.status
        new_status = self.status

        # No transition if the status has not changed.
        if old_status == new_status:
            return

        allowed_transitions = {
            "Draft": ["Open", "Cancelled"],
            "Open": ["Cancelled"],
        }

        if new_status not in allowed_transitions.get(old_status, []):
            frappe.throw(
                f"Status transition from {old_status} to {new_status} "
                "is not allowed."
            )

        # Cancellation requires System Manager permission.
        if new_status == "Cancelled" and not frappe.has_role("System Manager"):
            frappe.throw(
                "Only an authorized manager can cancel a Manpower Request."
            )
