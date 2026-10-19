import frappe


def daily():
    print("GulfCare daily scheduled job executed")
    frappe.logger("gulfcare_custom").info(
        "GulfCare daily scheduled job executed"
    )