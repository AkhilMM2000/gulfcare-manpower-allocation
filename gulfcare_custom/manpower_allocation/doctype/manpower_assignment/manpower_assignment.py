
import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class ManpowerAssignment(Document):

    def validate(self):
        self.validate_dates()
        self.validate_status_transition()
        self.validate_overstaffing_approval()
        self.validate_employee_conflicts()
        self.validate_overstaffing()

    def validate_dates(self):
        """Ensure assignment dates are valid and inside the request period."""

        if not self.manpower_request:
            frappe.throw("Manpower Request is required.")

        if not self.employee:
            frappe.throw("Employee is required.")

        if not self.start_date or not self.end_date:
            frappe.throw("Start Date and End Date are required.")

        start_date = getdate(self.start_date)
        end_date = getdate(self.end_date)

        if end_date < start_date:
            frappe.throw("End Date cannot be before Start Date.")

        request = frappe.get_doc(
            "Manpower Request",
            self.manpower_request,
        )

        request_start = getdate(request.start_date)
        request_end = getdate(request.end_date)

        if start_date < request_start or end_date > request_end:
            frappe.throw(
                "Assignment dates must fall within the linked "
                "Manpower Request dates: "
                f"{request.start_date} to {request.end_date}."
            )

    def validate_status_transition(self):
        """Allow only explicitly permitted status transitions."""

        allowed_transitions = {
            "Draft": ["Active", "Cancelled"],
            "Active": ["Cancelled", "Completed"],
            "Cancelled": [],
            "Completed": [],
        }

        old_doc = self.get_doc_before_save()

        # Every new assignment must start as Draft.
        if not old_doc:
            if self.status != "Draft":
                frappe.throw(
                    "New Manpower Assignments must start as Draft."
                )
            return

        old_status = old_doc.status
        new_status = self.status

        if old_status == new_status:
            return

        allowed = allowed_transitions.get(old_status, [])

        if new_status not in allowed:
            frappe.throw(
                f"Status transition from {old_status} to {new_status} "
                "is not allowed."
            )

    def validate_overstaffing_approval(self):
        """Restrict overstaffing approval to authorized managers."""

        if self.overstaffing_approved:
            if "System Manager" not in frappe.get_roles(frappe.session.user):
                frappe.throw(
                    "Only a System Manager can approve overstaffing."
                )

            if not self.approval_reason or not self.approval_reason.strip():
                frappe.throw(
                    "Approval Reason is required when overstaffing "
                    "is approved."
                )

    def validate_employee_conflicts(self):
        """Prevent an employee from having overlapping active assignments."""

        if self.status != "Active":
            return

        start_date = getdate(self.start_date)
        end_date = getdate(self.end_date)

        assignments = frappe.get_all(
            "Manpower Assignment",
            filters={
                "employee": self.employee,
                "status": "Active",
                "start_date": ["<=", end_date],
                "end_date": [">=", start_date],
            },
            fields=[
                "name",
                "manpower_request",
                "start_date",
                "end_date",
            ],
        )

        for assignment in assignments:
            # Ignore this document when updating an existing assignment.
            if assignment.name == self.name:
                continue

            frappe.throw(
                f"Employee {self.employee} already has an overlapping "
                f"active assignment ({assignment.name}) from "
                f"{assignment.start_date} to {assignment.end_date}. "
                "Resolve the conflict before activating this assignment."
            )

    def validate_overstaffing(self):
        """Prevent daily staffing coverage from exceeding the request."""

        if self.status != "Active":
            return

        request = frappe.get_doc(
            "Manpower Request",
            self.manpower_request,
        )

        workers_required = request.workers_required

        if workers_required is None or workers_required <= 0:
            frappe.throw(
                "Workers Required must be greater than zero "
                "on the Manpower Request."
            )

        start_date = getdate(self.start_date)
        end_date = getdate(self.end_date)

        existing_assignments = frappe.get_all(
            "Manpower Assignment",
            filters={
                "manpower_request": self.manpower_request,
                "status": "Active",
                "start_date": ["<=", end_date],
                "end_date": [">=", start_date],
            },
            fields=["name", "start_date", "end_date"],
        )

        # Do not count the current document twice during an update.
        existing_assignments = [
            assignment
            for assignment in existing_assignments
            if assignment.name != self.name
        ]

        current_date = start_date

        while current_date <= end_date:
            existing_count = sum(
                1
                for assignment in existing_assignments
                if getdate(assignment.start_date) <= current_date
                and getdate(assignment.end_date) >= current_date
            )

            # Include the assignment currently being saved.
            total_count = existing_count + 1

            if total_count > workers_required:
                if not self.overstaffing_approved:
                    frappe.throw(
                        f"Overstaffing detected on {current_date}. "
                        f"Required workers: {workers_required}; "
                        f"resulting active assignments: {total_count}. "
                        "An authorized manager must approve the exception "
                        "and provide an approval reason."
                    )

            current_date = frappe.utils.add_days(current_date, 1)
