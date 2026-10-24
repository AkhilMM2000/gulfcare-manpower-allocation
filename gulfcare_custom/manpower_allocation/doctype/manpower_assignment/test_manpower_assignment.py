
import frappe
from frappe.tests import IntegrationTestCase


class TestManpowerAssignment(IntegrationTestCase):

    def test_rejects_overlapping_active_assignment_for_same_employee(self):
        # Reuse existing records to avoid unnecessary test fixtures.
        customers = frappe.get_all("Customer", pluck="name", limit=1)
        employees = frappe.get_all("Employee", pluck="name", limit=1)

        if not customers:
            self.skipTest("Create a Customer before running this test.")

        if not employees:
            self.skipTest("Create an Employee before running this test.")

        customer = customers[0]
        employee = employees[0]

        # Create an isolated request in the future.
        request = frappe.get_doc({
            "doctype": "Manpower Request",
            "customer": customer,
            "job_role": "Automated Test Guard",
            "location": "Automated Test Location",
            "start_date": "2099-01-01",
            "end_date": "2099-01-31",
            "workers_required": 2,
            "status": "Draft",
        })
        request.insert()

        # First assignment: activate successfully.
        first = frappe.get_doc({
            "doctype": "Manpower Assignment",
            "manpower_request": request.name,
            "employee": employee,
            "start_date": "2099-01-05",
            "end_date": "2099-01-15",
            "status": "Draft",
        })
        first.insert()

        first.status = "Active"
        first.save()

        # Second assignment: same employee, overlapping dates.
        second = frappe.get_doc({
            "doctype": "Manpower Assignment",
            "manpower_request": request.name,
            "employee": employee,
            "start_date": "2099-01-10",
            "end_date": "2099-01-20",
            "status": "Draft",
        })
        second.insert()

        second.status = "Active"

        # The second activation must fail because the dates overlap.
        with self.assertRaisesRegex(
            frappe.ValidationError,
            "overlapping active assignment",
        ):
            second.save()
