// Copyright (c) 2023, Kishan Panchal and contributors
// For license information, please see license.txt

frappe.ui.form.on("Expenses Entry", {
    refresh: function (frm) {
        field_control(frm);
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
        field_control(frm);
        const get_account_filters = () => {
            const filters = [["Account", "is_group", "=", 0]];
            if (frm.doc.company) {
                filters.push(["Account", "company", "=", frm.doc.company]);
            }
            return { filters };
        };

        frm.set_query("account_paid_from", function () {
            return get_account_filters();
        });
        frm.set_query("account_paid_to", "expenses", function () {
            return get_account_filters();
        });
    },
    before_save: function (frm) {
        update_total_debit(frm);
    },

    // validate event: Perform all validation checks
    validate: function (frm) {
        // Round paid amount and total debit for comparison
        let rounded_paid_amount = parseFloat(frm.doc.paid_amount.toFixed(2));
        let rounded_total_debit = parseFloat(frm.doc.total_debit.toFixed(2));

        if (rounded_paid_amount <= 0) {
            frappe.throw("Paid Amount cannot be zero");
        }

        if (rounded_total_debit <= 0) {
            frappe.throw("Total Debit cannot be zero");
        }

        if (rounded_paid_amount !== rounded_total_debit) {
            frappe.throw(
                "Total Debit amount must be equal to or less than the Paid Amount"
            );
        }

        // Validation 2: Check each row in the Expenses child table
        let invalid_rows = [];

        frm.doc.expenses.forEach((expense) => {
            let calculated_total;
            if (expense.vat_amount > 0) {
                calculated_total = parseFloat(
                    (expense.amount_without_vat + expense.vat_amount).toFixed(2)
                );
            } else {
                calculated_total = parseFloat(
                    expense.amount_without_vat.toFixed(2)
                );
            }
            let rounded_amount = parseFloat(expense.amount.toFixed(2));

            if (rounded_amount !== calculated_total) {
                console.log("Rounded Amount : " + rounded_amount);
                console.log("Calculated Total : ", calculated_total);
                invalid_rows.push(
                    `Row #${expense.idx}: Amount (${rounded_amount}) does not equal Amount Without VAT (${expense.amount_without_vat}) + VAT Amount (${expense.vat_amount})`
                );
            }
        });

        if (invalid_rows.length > 0) {
            frappe.throw(
                `The following rows have miscalculated amounts:<br><br>${invalid_rows.join(
                    "<br>"
                )}`
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
            frm.set_df_property("paid_amount", "read_only", 1);
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
            frm.set_df_property("paid_amount", "read_only", 0);
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
        const get_account_filters = () => {
            const filters = [["Account", "is_group", "=", 0]];
            if (frm.doc.company) {
                filters.push(["Account", "company", "=", frm.doc.company]);
            }
            return { filters };
        };

        frm.set_query("account_paid_to", "expenses", function () {
            return get_account_filters();
        });
    },
    amount: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        // sum all the amounts from the expenses table and set it to the total_debit field
        // let totalAmountPromise = new Promise(function (resolve, reject) {
        //     let totalAmount = 0;
        //     frm.doc.expenses.forEach(function (d) {
        //         totalAmount += d.amount;
        //     });

        //     resolve(totalAmount);
        // });

        // totalAmountPromise.then(function (totalAmount) {
        //     frm.set_value("total_debit", totalAmount);
        //     frm.set_value("paid_amount", totalAmount);
        //     if (frm.doc.multi_currency) {
        //         frm.set_value(
        //             "paid_amount_in_account_currency",
        //             totalAmount / frm.doc.exchange_rate
        //         );
        //     }
        // });

        update_total_debit(frm);
        console.log("row.vat_amount: ", d.vat_amount);
        console.log("row.amount_without_vat: ", d.amount_without_vat);
        if (d.vat_amount === 0 || d.vat_amount === undefined) {
            console.log("vat_amount passedd");
            if (
                d.amount_without_vat === undefined ||
                d.amount_without_vat === 0
            ) {
                console.log("copy amountt to amount_without_vat: ");
                d.amount_without_vat = d.amount;
                frm.refresh_field("items");
                frm.fields_dict.expenses.grid.grid_rows_by_docname[
                    d.name
                ].refresh();
            }
        }
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
        update_total_debit(frm);
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
    vat_template: function (frm, cdt, cdn) {
        // Get the current child row data
        let row = locals[cdt][cdn];

        if (row.vat_template) {
            calculate_vat(row, cdt, cdn);
        }
    },

    // To handle changes in amount_without_vat as well
    amount_without_vat: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        console.log("row.amount_without_vat: ", row.amount_without_vat);
        console.log("row.amount", row.amount);
        update_total_debit(frm);
        if (row.vat_template !== undefined) {
            calculate_vat(row, cdt, cdn);
        } else {
            if (!row.amount) {
                row.amount = row.amount_without_vat;
                frm.refresh_field("items");
                frm.fields_dict.expenses.grid.grid_rows_by_docname[
                    row.name
                ].refresh();
                console.log("Updated amount with vat");
            }
        }
    },
});

function calculate_vat(row, cdt, cdn) {
    if (row.vat_template) {
        // Call the server-side method to fetch the tax rate from the selected template
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Purchase Taxes and Charges Template",
                name: row.vat_template,
            },
            callback: function (r) {
                if (r.message) {
                    // Assuming the rate is in the first row of the taxes child table
                    let tax_rate = r.message.taxes[0].rate;

                    // Update VAT Amount based on Amount Without VAT
                    let vat_amount = (row.amount_without_vat * tax_rate) / 100;

                    // Update the child table fields
                    frappe.model.set_value(cdt, cdn, "vat_amount", vat_amount);
                    frappe.model.set_value(
                        cdt,
                        cdn,
                        "amount",
                        row.amount_without_vat + vat_amount
                    );
                    update_total_debit(frm);
                }
            },
        });
    }
}

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

function update_total_debit(frm) {
    console.log("Total Debit Amount called");

    // Initialize total_debit_amount to 0
    let total_debit_amount = 0;

    frm.doc.expenses.forEach((expense, index) => {
        if (expense.vat_amount) {
            total_debit_amount +=
                expense.amount_without_vat + expense.vat_amount;
        } else {
            total_debit_amount += expense.amount_without_vat;
        }
    });

    frm.set_value("total_debit", total_debit_amount);

    if (frm.doc.multi_currency) {
        frm.set_value(
            "paid_amount_in_account_currency",
            total_debit_amount / frm.doc.exchange_rate
        );
    }

    frm.refresh_field("total_debit");
    console.log("Total debit amount updated");
}

function field_control(frm) {
    if (frm.doc.docstatus === 1) {
        // Check if the document is submitted
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Expense Entry Settings",
            },
            callback: function (r) {
                if (r.message) {
                    const settings = r.message;
                    const user_roles = frappe.user_roles;

                    // Check if user has allowed roles and the setting to allow editing after submit is true
                    const is_allowed = settings.allowed_roles.some((role) =>
                        user_roles.includes(role.role)
                    );

                    if (settings.allow_after_submit_entries && is_allowed) {
                        // Allow editing
                        frm.set_df_property("paid_amount", "read_only", 0);
                        frm.set_df_property("exchange_rate", "read_only", 0);
                        frm.set_df_property("total_debit", "read_only", 0);
                        frm.fields_dict.expenses.grid.update_docfield_property(
                            "vat_template",
                            "read_only",
                            0
                        );
                        frm.fields_dict.expenses.grid.update_docfield_property(
                            "vat_amount",
                            "read_only",
                            0
                        );
                        frm.fields_dict.expenses.grid.update_docfield_property(
                            "amount",
                            "read_only",
                            0
                        );
                        frm.fields_dict.expenses.grid.update_docfield_property(
                            "amount_without_vat",
                            "read_only",
                            0
                        );
                    } else {
                        // Make fields read-only
                        frm.set_df_property("paid_amount", "read_only", 1);
                        frm.set_df_property("exchange_rate", "read_only", 1);
                        frm.set_df_property("total_debit", "read_only", 1);
                        frm.fields_dict.expenses.grid.update_docfield_property(
                            "vat_template",
                            "read_only",
                            1
                        );
                        frm.fields_dict.expenses.grid.update_docfield_property(
                            "vat_amount",
                            "read_only",
                            1
                        );
                        frm.fields_dict.expenses.grid.update_docfield_property(
                            "amount",
                            "read_only",
                            1
                        );
                        frm.fields_dict.expenses.grid.update_docfield_property(
                            "amount_without_vat",
                            "read_only",
                            1
                        );
                    }
                }
            },
        });
    }
}
