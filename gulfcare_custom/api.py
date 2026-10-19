
import frappe


@frappe.whitelist()
def hello():
    return {
        "message": "Hello from GulfCare Custom API!"
    }
