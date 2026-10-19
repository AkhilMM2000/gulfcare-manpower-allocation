import frappe


def site_visit_after_insert(doc, method=None):
    print(f"Site Visit {doc.name} was created")
    frappe.logger("gulfcare_custom").info(
        f"Site Visit {doc.name} was created"
    )
