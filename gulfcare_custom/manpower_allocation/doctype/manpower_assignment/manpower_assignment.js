
frappe.ui.form.on("Manpower Assignment", {
    refresh(frm) {
        if (
            !frm.is_new() &&
            frm.doc.status === "Active" &&
            !frm.doc.replaced_by
        ) {
            frm.add_custom_button("Replace Employee", () => {
                frappe.prompt(
                    [
                        {
                            fieldname: "replacement_employee",
                            label: "Replacement Employee",
                            fieldtype: "Link",
                            options: "Employee",
                            reqd: 1,
                        },
                        {
                            fieldname: "replacement_reason",
                            label: "Replacement Reason",
                            fieldtype: "Small Text",
                            reqd: 1,
                        },
                    ],
                    (values) => {
                        frm.call("replace_assignment", {
                            replacement_employee:
                                values.replacement_employee,
                            replacement_reason:
                                values.replacement_reason,
                        }).then((r) => {
                            if (r.message) {
                                frappe.show_alert({
                                    message:
                                        `Replacement created: ${r.message}`,
                                    indicator: "green",
                                });

                                frappe.set_route(
                                    "Form",
                                    "Manpower Assignment",
                                    r.message
                                );
                            }
                        });
                    },
                    "Replace Employee",
                    "Replace"
                );
            });
        }
    },
});
