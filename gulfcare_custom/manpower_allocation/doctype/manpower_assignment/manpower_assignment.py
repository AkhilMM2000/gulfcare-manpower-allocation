
import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class ManpowerAssignment(Document):

    def validate(self):
        self.validate_dates()
        self.validate_employee_eligibility()
        self.validate_employee_leave()
        self.validate_status_transition()
        self.validate_overstaffing_approval()

        self.lock_assignment_resources()

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


    def validate_employee_eligibility(self):
        """Ensure the employee is eligible for the assignment period."""

        employee = frappe.get_doc("Employee", self.employee)

        if employee.status != "Active":
            frappe.throw(
                f"Employee {self.employee} is {employee.status}. "
                "Only Active employees can be assigned."
            )

        start_date = getdate(self.start_date)
        end_date = getdate(self.end_date)

        if employee.date_of_joining:
            joining_date = getdate(employee.date_of_joining)

            if start_date < joining_date:
                frappe.throw(
                    f"Employee {self.employee} joined on "
                    f"{joining_date} and cannot be assigned before "
                    "their joining date."
                )

        if employee.relieving_date:
            relieving_date = getdate(employee.relieving_date)

            if end_date > relieving_date:
                frappe.throw(
                    f"Employee {self.employee} has a relieving date of "
                    f"{relieving_date}. The assignment cannot extend "
                    "beyond that date."
                )

        if employee.contract_end_date:
            contract_end_date = getdate(employee.contract_end_date)

            if end_date > contract_end_date:
                frappe.throw(
                    f"Employee {self.employee} has a contract ending on "
                    f"{contract_end_date}. The assignment cannot extend "
                    "beyond that date."
                )


    def validate_employee_leave(self):
        """Prevent assignments that overlap approved employee leave."""

        if self.status != "Active":
            return

        start_date = getdate(self.start_date)
        end_date = getdate(self.end_date)

        leave_applications = frappe.get_all(
            "Leave Application",
            filters={
                "employee": self.employee,
                "status": "Approved",
                "from_date": ["<=", end_date],
                "to_date": [">=", start_date],
            },
            fields=[
                "name",
                "from_date",
                "to_date",
                "leave_type",
            ],
        )

        if leave_applications:
            leave = leave_applications[0]

            frappe.throw(
                f"Employee {self.employee} has approved leave "
                f"({leave.leave_type}) from {leave.from_date} "
                f"to {leave.to_date}. The assignment overlaps "
                "this leave and cannot be activated."
            )

    def validate_status_transition(self):
        """Allow only explicitly permitted assignment status transitions."""

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

        allowed_transitions = {
            "Draft": ["Active", "Cancelled"],
            "Active": ["Cancelled", "Completed"],
            "Cancelled": [],
            "Completed": [],
        }

        if new_status not in allowed_transitions.get(old_status, []):
            frappe.throw(
                f"Assignment status transition from {old_status} "
                f"to {new_status} is not allowed."
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

        assignments = frappe.db.sql(
            """
            SELECT name, manpower_request, start_date, end_date
            FROM `tabManpower Assignment`
            WHERE employee = %s
              AND status = 'Active'
              AND start_date <= %s
              AND end_date >= %s
            FOR UPDATE
            """,
            (self.employee, end_date, start_date),
            as_dict=True,
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

        existing_assignments = frappe.db.sql(
            """
            SELECT name, start_date, end_date
            FROM `tabManpower Assignment`
            WHERE manpower_request = %s
              AND status = 'Active'
              AND start_date <= %s
              AND end_date >= %s
            FOR UPDATE
            """,
            (self.manpower_request, end_date, start_date),
            as_dict=True,
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

    def on_update(self):
        """Recalculate the linked request after an assignment is saved."""

        request = frappe.get_doc(
            "Manpower Request",
            self.manpower_request,
        )

        request.update_staffing_status()

    def lock_assignment_resources(self):
        """Lock the employee and request rows during assignment validation."""

        if self.status != "Active":
            return

        # Always lock Employee first.
        frappe.db.sql(
            """
            SELECT name
            FROM `tabEmployee`
            WHERE name = %s
            FOR UPDATE
            """,
            self.employee,
        )

        # Then lock the Manpower Request.
        frappe.db.sql(
            """
            SELECT name
            FROM `tabManpower Request`
            WHERE name = %s
            FOR UPDATE
            """,
            self.manpower_request,
        )

    @frappe.whitelist()
    def replace_assignment(self, replacement_employee, replacement_reason):
        """Replace an active assignment with another employee."""

        self.check_permission("write")

        if self.status != "Active":
            frappe.throw("Only Active assignments can be replaced.")

        if self.replaced_by:
            frappe.throw("This assignment has already been replaced.")

        if not replacement_employee:
            frappe.throw("Replacement Employee is required.")

        if replacement_employee == self.employee:
            frappe.throw(
                "The replacement employee must be different "
                "from the original employee."
            )

        if not replacement_reason or not replacement_reason.strip():
            frappe.throw("Replacement Reason is required.")

        savepoint = "manpower_assignment_replacement"
        frappe.db.savepoint(savepoint)

        try:
            # Create the replacement first as a Draft.
            replacement = frappe.get_doc({
                "doctype": "Manpower Assignment",
                "manpower_request": self.manpower_request,
                "employee": replacement_employee,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "status": "Draft",
                "replaces_assignment": self.name,
                "replacement_reason": replacement_reason.strip(),
            })

            replacement.insert()

            # Preserve the original record and link the replacement.
            self.reload()
            self.status = "Cancelled"
            self.replaced_by = replacement.name
            self.replacement_reason = replacement_reason.strip()
            self.save()

            # Activate the replacement only after the old assignment
            # has been cancelled, so capacity checks see the right count.
            replacement.status = "Active"
            replacement.save()

            return replacement.name

        except Exception:
            frappe.db.rollback(save_point=savepoint)
            raise
