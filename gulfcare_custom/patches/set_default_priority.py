
import frappe


def execute():
    frappe.db.sql("""
        UPDATE `tabGulfCare Site Visit`
        SET priority = 'Medium'
        WHERE priority IS NULL OR priority = ''
    """)
