
import frappe
from unittest.mock import patch
from frappe.tests import IntegrationTestCase

IGNORE_TEST_RECORD_DEPENDENCIES = ["Customer", "Opportunity"]


class IntegrationTestManpowerRequest(IntegrationTestCase):

    def make_request(self):
        doc = frappe.new_doc("Manpower Request")
        doc.customer = "Test Customer"
        doc.job_role = "Security Guard"
        doc.location = "Kozhikode"
        doc.start_date = "2026-11-01"
        doc.end_date = "2026-11-10"
        doc.workers_required = 5
        return doc

    def test_new_request_defaults_to_draft(self):
        doc = self.make_request()

        doc.before_insert()

        self.assertEqual(doc.status, "Draft")

    def test_valid_request_passes_validation(self):
        doc = self.make_request()
        doc.status = "Draft"

        doc.validate()

        self.assertEqual(doc.status, "Draft")

    def test_end_date_before_start_date_is_rejected(self):
        doc = self.make_request()
        doc.end_date = "2026-10-31"

        with self.assertRaises(frappe.ValidationError):
            doc.validate_dates()

    def test_zero_workers_is_rejected(self):
        doc = self.make_request()
        doc.workers_required = 0

        with self.assertRaises(frappe.ValidationError):
            doc.validate_workers_required()

    def test_negative_workers_is_rejected(self):
        doc = self.make_request()
        doc.workers_required = -1

        with self.assertRaises(frappe.ValidationError):
            doc.validate_workers_required()

    def test_positive_workers_is_allowed(self):
        doc = self.make_request()
        doc.workers_required = 5

        doc.validate_workers_required()

    def test_nonexistent_opportunity_is_rejected(self):
        doc = self.make_request()
        doc.opportunity = "NONEXISTENT-OPPORTUNITY"

        with patch("frappe.db.get_value", return_value=None):
            with self.assertRaises(frappe.ValidationError):
                doc.validate_opportunity()

    def test_opportunity_for_different_customer_is_rejected(self):
        doc = self.make_request()
        doc.customer = "CUSTOMER-A"
        doc.opportunity = "OPP-1"

        opportunity = frappe._dict(
            opportunity_from="Customer",
            party_name="CUSTOMER-B",
        )

        with patch("frappe.db.get_value", return_value=opportunity):
            with self.assertRaises(frappe.ValidationError):
                doc.validate_opportunity()

    def test_draft_can_transition_to_open(self):
        doc = self.make_request()
        doc.status = "Open"

        with patch.object(
            doc, "get_doc_before_save",
            return_value=frappe._dict(status="Draft")
        ):
            doc.validate_status_transition()

    def test_draft_cannot_transition_to_fully_assigned(self):
        doc = self.make_request()
        doc.status = "Fully Assigned"

        with patch.object(
            doc, "get_doc_before_save",
            return_value=frappe._dict(status="Draft")
        ):
            with self.assertRaises(frappe.ValidationError):
                doc.validate_status_transition()

    def test_cancel_requires_system_manager_role(self):
        doc = self.make_request()
        doc.status = "Cancelled"

        with patch.object(
            doc, "get_doc_before_save",
            return_value=frappe._dict(status="Draft")
        ), patch("frappe.has_role", return_value=False):
            with self.assertRaises(frappe.ValidationError):
                doc.validate_status_transition()

    def test_system_manager_can_cancel_draft(self):
        doc = self.make_request()
        doc.status = "Cancelled"

        with patch.object(
            doc, "get_doc_before_save",
            return_value=frappe._dict(status="Draft")
        ), patch("frappe.has_role", return_value=True):
            doc.validate_status_transition()

    def test_cancelled_request_cannot_be_reopened(self):
        doc = self.make_request()
        doc.status = "Open"

        with patch.object(
            doc, "get_doc_before_save",
            return_value=frappe._dict(status="Cancelled")
        ):
            with self.assertRaises(frappe.ValidationError):
                doc.validate_status_transition()
