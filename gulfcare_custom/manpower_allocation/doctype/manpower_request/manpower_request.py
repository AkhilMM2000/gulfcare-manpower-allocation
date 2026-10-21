# Copyright (c) 2026, akhil mm and contributors
# For license information, please see license.txt

# import frappe

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from datetime import timedelta

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
        """Validate manual and automatic request status transitions."""

        old_doc = self.get_doc_before_save()

        if not old_doc:
            if self.status != "Draft":
                frappe.throw("New requests must start as Draft.")
            return

        old_status = old_doc.status
        new_status = self.status

        if old_status == new_status:
            return

        # Permit calculated staffing statuses only through
        # the trusted server-side update method.
        if self.flags.ignore_staffing_status_validation:
            if new_status in (
                "Open",
                "Partially Assigned",
                "Fully Assigned",
            ):
                return

        # Cancellation requires System Manager permission.
        if new_status == "Cancelled":
            if old_status == "Completed":
                frappe.throw(
                    "A completed Manpower Request cannot be cancelled."
                )

            if "System Manager" not in frappe.get_roles(
                frappe.session.user
            ):
                frappe.throw(
                    "Only a System Manager can cancel a Manpower Request."
                )
            return

        # Manual transitions.
        allowed_transitions = {
            "Draft": ["Open"],
            "Open": [],
            "Partially Assigned": [],
            "Fully Assigned": [],
            "Completed": [],
            "Cancelled": [],
        }

        if new_status not in allowed_transitions.get(old_status, []):
            frappe.throw(
                f"Status transition from {old_status} to {new_status} "
                "is not allowed."
            )


    def get_daily_staffing_coverage(self):
        """Return active employee coverage for each day of this request."""

        request_start = getdate(self.start_date)
        request_end = getdate(self.end_date)

        # Initialize every requested date with zero workers.
        daily_coverage = {}
        current_date = request_start

        while current_date <= request_end:
            daily_coverage[str(current_date)] = 0
            current_date += timedelta(days=1)

        # Fetch active assignments overlapping this request's period.
        assignments = frappe.get_all(
            "Manpower Assignment",
            filters={
                "manpower_request": self.name,
                "status": "Active",
                "start_date": ["<=", request_end],
                "end_date": [">=", request_start],
            },
            fields=["start_date", "end_date"],
        )

        # Count each assignment only on the dates it covers.
        for assignment in assignments:
            assignment_start = max(
                getdate(assignment.start_date),
                request_start,
            )
            assignment_end = min(
                getdate(assignment.end_date),
                request_end,
            )

            current_date = assignment_start

            while current_date <= assignment_end:
                daily_coverage[str(current_date)] += 1
                current_date += timedelta(days=1)

        return daily_coverage


    def get_daily_staffing_shortage(self):
        """Calculate the remaining workers needed for each day."""

        daily_coverage = self.get_daily_staffing_coverage()
        workers_required = self.workers_required

        daily_shortage = {}

        for date, assigned_workers in daily_coverage.items():
            shortage = max(0, workers_required - assigned_workers)
            daily_shortage[date] = shortage

        return daily_shortage


    def get_calculated_staffing_status(self):
        """Determine staffing status from daily coverage."""

        # Preserve special statuses.
        if self.status in ("Cancelled", "Completed"):
            return self.status

        # A Draft request stays Draft until staffing is opened.
        if self.status == "Draft":
            return "Draft"

        daily_coverage = self.get_daily_staffing_coverage()
        daily_shortage = self.get_daily_staffing_shortage()

        # No active workers on any requested day.
        if not any(daily_coverage.values()):
            return "Open"

        # Every requested day has enough active workers.
        if all(shortage == 0 for shortage in daily_shortage.values()):
            return "Fully Assigned"

        # Coverage exists, but at least one day has a shortage.
        return "Partially Assigned"


    def update_staffing_status(self):
        """Update status using the calculated staffing coverage."""

        calculated_status = self.get_calculated_staffing_status()

        if self.status == calculated_status:
            return

        self.flags.ignore_staffing_status_validation = True
        self.status = calculated_status
        self.save(ignore_permissions=True)
