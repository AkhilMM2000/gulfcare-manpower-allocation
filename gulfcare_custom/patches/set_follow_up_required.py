
import frappe


def execute():
    frappe.db.sql("""
        UPDATE `tabGulfCare Site Visit`
        SET follow_up_required = 1
        WHERE status = 'Planned'
          AND follow_up_required = 0
    """)
