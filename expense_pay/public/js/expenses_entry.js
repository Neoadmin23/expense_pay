// Copyright (c) 2023, Kishan Panchal and contributors
// For license information, please see license.txt

frappe.ui.form.on('Expenses Entry', {
    refresh: function (frm) {
        frm.events.show_general_ledger(frm);
    },
    show_general_ledger: function (frm) {
        if (frm.doc.docstatus > 0) {
            frm.add_custom_button(__('Ledger'), function () {
                frappe.route_options = {
                    "voucher_no": frm.doc.name,
                    "from_date": frm.doc.posting_date,
                    "to_date": moment(frm.doc.modified).format('YYYY-MM-DD'),
                    "company": frm.doc.company,
                    "group_by": "",
                    "show_cancelled_entries": frm.doc.docstatus === 2
                };
                frappe.set_route("query-report", "General Ledger");
            }, "fa fa-table");
        }
    },
    before_save: function (frm) {
        if (frm.doc.paid_amount < frm.doc.total_debit) {
            frappe.throw("Total Debit amount must be equal to or less than the Paid Amount");
        }
    },
});

frappe.ui.form.on('Expenses', {
    amount: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        // sum all the amounts from the expenses table and set it to the total_debit field
        let totalAmountPromise = new Promise(function (resolve, reject) {
            let totalAmount = 0;
            frm.doc.expenses.forEach(function (d) {
                totalAmount += d.amount;
            });

            resolve(totalAmount);
        });

        totalAmountPromise.then(function (totalAmount) {
            frm.set_value('total_debit', totalAmount);
        });
    }
});
