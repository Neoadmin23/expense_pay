// Copyright (c) 2023, Kishan Panchal and contributors
// For license information, please see license.txt

frappe.ui.form.on("Expenses Entry", {
    refresh: function (frm) {
        frm.events.show_general_ledger(frm);
        // add_custom_column(frm);
        // Call the function to modify existing rows
        // modify_existing_rows(frm);

        // // Event handler for grid row load
        // frm.fields_dict["expenses"].grid.get_field("amount").grid_row_onload =
        //     function (row) {
        //         // Check if multi_currency is enabled
        //         if (frm.doc.multi_currency) {
        //             modify_row(row);
        //         }
        //     };
        if (frm.doc.multi_currency) {
            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount_in_account_currency",
                "read_only",
                0
            );
        } else {
            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount_in_account_currency",
                "read_only",
                1
            );
        }
    },
    show_general_ledger: function (frm) {
        if (frm.doc.docstatus > 0) {
            frm.add_custom_button(
                __("Ledger"),
                function () {
                    frappe.route_options = {
                        voucher_no: frm.doc.name,
                        from_date: frm.doc.posting_date,
                        to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
                        company: frm.doc.company,
                        group_by: "",
                        show_cancelled_entries: frm.doc.docstatus === 2,
                    };
                    frappe.set_route("query-report", "General Ledger");
                },
                "fa fa-table"
            );
        }
    },
    onload: function (frm) {
        frm.set_query("account_paid_from", function () {
            return {
                filters: [["Account", "is_group", "=", 0]],
            };
        });
        frm.set_query("account_paid_to", "expenses", function (doc, cdt, cdn) {
            return {
                filters: [["Account", "is_group", "=", 0]],
            };
        });
    },
    before_save: function (frm) {
        console.log("paid amount", frm.doc.paid_amount);
        console.log("total debit", frm.doc.total_debit);

        let rounded_paid_amount = parseFloat(frm.doc.paid_amount.toFixed(2));
        let rounded_total_debit = parseFloat(frm.doc.total_debit.toFixed(2));

        if (rounded_paid_amount !== rounded_total_debit) {
            frappe.throw(
                "Total Debit amount must be equal to or less than the Paid Amount"
            );
        }
    },
    multi_currency: function (frm) {
        if (frm.doc.multi_currency) {
            frm.toggle_reqd("exchange_rate", frm.doc.multi_currency);
            frm.toggle_reqd(
                "paid_amount_in_account_currency",
                frm.doc.multi_currency
            );
            update_exchange_rate(frm);
            // add_custom_column(frm);
            // modify_existing_rows(frm);

            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount",
                "read_only",
                1
            );

            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount_in_account_currency",
                "read_only",
                0
            );

            frm.fields_dict.expenses.grid.update_docfield_property(
                "account_currency",
                "reqd",
                1
            );

            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount",
                "reqd",
                1
            );

            frm.fields_dict.expenses.grid.update_docfield_property(
                "exchange_rate",
                "reqd",
                1
            );

            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount_in_account_currency",
                "reqd",
                1
            );
        } else {
            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount",
                "read_only",
                0
            );
            frm.fields_dict.expenses.grid.update_docfield_property(
                "account_currency",
                "reqd",
                0
            );

            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount",
                "reqd",
                1
            );

            frm.fields_dict.expenses.grid.update_docfield_property(
                "exchange_rate",
                "reqd",
                0
            );

            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount_in_account_currency",
                "reqd",
                0
            );
            frm.fields_dict.expenses.grid.update_docfield_property(
                "amount_in_account_currency",
                "read_only",
                1
            );

            frm.toggle_reqd("exchange_rate", frm.doc.multi_currency);
            frm.toggle_reqd(
                "paid_amount_in_account_currency",
                frm.doc.multi_currency
            );
        }
    },
    paid_amount_in_account_currency: function (frm) {
        if (frm.doc.paid_amount_in_account_currency) {
            //    set paid_amount valur to the paid_amount_in_account_currency field * exchange_rate
            frm.set_value(
                "paid_amount",
                frm.doc.paid_amount_in_account_currency * frm.doc.exchange_rate
            );
            // frm.refresh_field("expenses");
        }
    },
    account_currency_from: function (frm) {
        update_exchange_rate(frm);
    },
    currency_exchange_link: function (frm) {
        if (frm.doc.currency_exchange_link && frm.doc.multi_currency) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Currency Exchange",
                    name: frm.doc.currency_exchange_link,
                },
                callback: function (r) {
                    if (r.message) {
                        var exchange = r.message;
                        // Update fields in your doctype
                        frappe.model.set_value(
                            frm.doctype,
                            frm.docname,
                            "exchange_rate",
                            exchange.exchange_rate
                        );
                        frappe.model.set_value(
                            frm.doctype,
                            frm.docname,
                            "exchange_rate_date",
                            exchange.date
                        );
                        frappe.model.set_value(
                            frm.doctype,
                            frm.docname,
                            "account_currency_from",
                            exchange.from_currency
                        );
                    }
                },
            });
        }
    },
});

frappe.ui.form.on("Expenses", {
    onload: function (frm) {
        frm.set_query("account_paid_to", "expenses", function (doc, cdt, cdn) {
            return {
                filters: [["Account", "is_group", "=", 0]],
            };
        });
    },
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
            frm.set_value("total_debit", totalAmount);
            frm.set_value("paid_amount", totalAmount);
            if (frm.doc.multi_currency) {
                frm.set_value(
                    "paid_amount_in_account_currency",
                    totalAmount / frm.doc.exchange_rate
                );
            }
        });
    },
    account_paid_to: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        if (d.account_paid_to) {
            frappe.model.set_value(
                cdt,
                cdn,
                "cost_center",
                frm.doc.default_cost_center
            );
        }
    },
    amount_in_account_currency: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        frappe.model.set_value(
            cdt,
            cdn,
            "amount",
            d.amount_in_account_currency * d.exchange_rate
        );
    },
    expenses_add: function (frm, cdt, cdn) {
        console.log("expenses_add");
        frappe.model.set_value(
            cdt,
            cdn,
            "account_currency",
            frm.doc.account_currency_from
        );
        frappe.model.set_value(
            cdt,
            cdn,
            "exchange_rate",
            frm.doc.exchange_rate
        );

        frappe.model.set_value(
            cdt,
            cdn,
            "exchange_rate_date",
            frm.doc.exchange_rate_date
        );

        frappe.model.set_value(
            cdt,
            cdn,
            "currency_exchange_link",
            frm.doc.currency_exchange_link
        );
    },
    form_render: function (frm, cdt, cdn) {
        // set the exchange_rate value to the exchange_rate field
        var row = locals[cdt][cdn];
        console.log("exchange_rate_on_form_rendered");
        if (
            !row.account_currency ||
            (row.account_currency !== frm.doc.account_currency_from &&
                frm.doc.multi_currency &&
                !row.exchange_rate)
        ) {
            frappe.model.set_value(
                cdt,
                cdn,
                "account_currency",
                frm.doc.account_currency_from
            );
        }

        if (!row.exchange_rate && frm.doc.multi_currency) {
            frappe.model.set_value(
                cdt,
                cdn,
                "exchange_rate",
                frm.doc.exchange_rate
            );
        }
        if (!row.exchange_rate_date && frm.doc.multi_currency) {
            frappe.model.set_value(
                cdt,
                cdn,
                "exchange_rate_date",
                frm.doc.exchange_rate_date
            );
        }
        if (!row.currency_exchange_link && frm.doc.multi_currency) {
            frappe.model.set_value(
                cdt,
                cdn,
                "currency_exchange_link",
                frm.doc.currency_exchange_link
            );
        }

        frm.fields_dict.expenses.grid.update_docfield_property(
            "amount",
            "reqd",
            1
        );
    },
    account_currency: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (frm.doc.multi_currency) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Currency Exchange",
                    filters: {
                        from_currency: row.account_currency,
                    },
                    fields: ["name", "exchange_rate", "date"],
                    order_by: "date desc",
                    limit_page_length: 1,
                },
                callback: function (r) {
                    if (r.message && r.message.length > 0) {
                        var latest_exchange = r.message[0];
                        // Update fields in your doctype
                        frappe.model.set_value(
                            cdt,
                            cdn,
                            "exchange_rate",
                            latest_exchange.exchange_rate
                        );
                        frappe.model.set_value(
                            cdt,
                            cdn,
                            "exchange_rate_date",
                            latest_exchange.date
                        );
                        frappe.model.set_value(
                            cdt,
                            cdn,
                            "currency_exchange_link",
                            latest_exchange.name
                        );
                    }
                },
            });
        }
    },
    currency_exchange_link: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.currency_exchange_link) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Currency Exchange",
                    name: row.currency_exchange_link,
                },
                callback: function (r) {
                    if (r.message) {
                        var exchange = r.message;
                        // Update fields in your doctype
                        frappe.model.set_value(
                            cdt,
                            cdn,
                            "exchange_rate",
                            exchange.exchange_rate
                        );
                        frappe.model.set_value(
                            cdt,
                            cdn,
                            "exchange_rate_date",
                            exchange.date
                        );
                        frappe.model.set_value(
                            cdt,
                            cdn,
                            "account_currency",
                            exchange.from_currency
                        );
                    }
                },
            });
        }
    },
});

function add_custom_column(frm) {
    let intervalId;

    function modify_column() {
        let grid = frm.fields_dict["expenses"].grid;
        let header_row = grid.wrapper.find(".grid-heading-row .data-row");

        // Identify the "Amount" column
        let amount_column = header_row.find('[data-fieldname="amount"]');

        if (frm.doc.multi_currency) {
            // Update column title and fieldname to "Amount In Account Currency"
            amount_column.attr("title", "Amount In Account Currency");
            amount_column.attr("data-fieldname", "amount_in_account_currency");
            amount_column
                .find(".static-area")
                .text("Amount In Account Currency");
        } else {
            // Revert to original "Amount" settings
            amount_column.attr("title", "Amount");
            amount_column.attr("data-fieldname", "amount");
            amount_column.find(".static-area").text("Amount");
        }
    }

    frappe.after_ajax(() => {
        modify_column();
        clearInterval(intervalId);
        intervalId = setInterval(modify_column, 500); // Reapply every 500ms
    });

    frm.on("before_refresh", function () {
        clearInterval(intervalId); // Clear interval on form refresh
    });
}

function modify_existing_rows(frm) {
    let grid_rows = frm.fields_dict["expenses"].grid.grid_rows;

    // Iterate through each row and apply modifications
    grid_rows.forEach(function (row) {
        if (frm.doc.multi_currency) {
            modify_row(row);
        }
    });
}

function modify_row(row) {
    // Replace "Amount" with "Amount In Account Currency"
    let amount_field = row.wrapper.find('[data-fieldname="amount"]');
    // amount_field.attr("title", "Amount In Account Currency");
    amount_field.attr("data-fieldname", "amount_in_account_currency");
    amount_field.find(".static-area").text("Amount In Account Currency");

    // You can also update the input placeholder if needed
    let amount_input = amount_field.find('input[data-fieldname="amount"]');
    if (amount_input.length) {
        amount_input.attr("placeholder", "Amount In Account Currency");
        amount_input.attr("data-fieldname", "amount_in_account_currency");
    }
}

function update_exchange_rate(frm) {
    if (frm.doc.account_currency_from && frm.doc.multi_currency) {
        // Fetch the latest exchange rate
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Currency Exchange",
                filters: {
                    from_currency: frm.doc.account_currency_from,
                },
                fields: ["name", "exchange_rate", "date"],
                order_by: "date desc",
                limit_page_length: 1,
            },
            callback: function (r) {
                if (r.message && r.message.length > 0) {
                    var latest_exchange = r.message[0];
                    // Update fields in your doctype
                    frappe.model.set_value(
                        frm.doctype,
                        frm.docname,
                        "exchange_rate",
                        latest_exchange.exchange_rate
                    );
                    frappe.model.set_value(
                        frm.doctype,
                        frm.docname,
                        "exchange_rate_date",
                        latest_exchange.date
                    );
                    frappe.model.set_value(
                        frm.doctype,
                        frm.docname,
                        "currency_exchange_link",
                        latest_exchange.name
                    );
                }
            },
        });
    }
}
