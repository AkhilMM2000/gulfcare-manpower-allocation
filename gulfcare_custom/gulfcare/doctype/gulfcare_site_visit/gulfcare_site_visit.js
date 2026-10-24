// Copyright (c) 2026, akhil mm and contributors
// For license information, please see license.txt

// frappe.ui.form.on("GulfCare Site Visit", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on("GulfCare Site Visit", {
	validate(frm) {
		if (frm.doc.visit_date && frm.doc.visit_date < frappe.datetime.get_today()) {
			frappe.msgprint({
				title: __("Invalid Visit Date"),
				message: __("Visit Date cannot be in the past."),
				indicator: "red",
			});
			frappe.validated = false;
		}
	},
});
