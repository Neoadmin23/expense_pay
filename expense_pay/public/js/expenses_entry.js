frappe.ui.form.on("Expenses Entry", {
  refresh: function (frm) {
    frm.events.show_general_ledger(frm);
    // Add custom button to update cost centers for this Expenses Entry
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
    frm.fields_dict["account_paid_from"].get_query = function (doc) {
      return {
        filters: {
          is_group: 0,
        },
      };
    };
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
});

frappe.ui.form.on("Expenses", {
  expenses_remove: function (frm, cdt, cdn) {
    let totalAmountPromise = new Promise(function (resolve, reject) {
      let totalAmount = 0;
      frm.doc.expenses.forEach(function (d) {
        totalAmount += d.amount;
      });
      resolve(totalAmount);
    });

    totalAmountPromise.then(function (totalAmount) {
      frm.set_value("total_debit", totalAmount);
    });
  },

  onload: function (frm) {
    frm.fields_dict["expenses"].grid.get_field("account_paid_to").get_query =
      function (doc, cdt, cdn) {
        return {
          filters: {
            is_group: 0,
          },
        };
      };
  },

  amount: function (frm, cdt, cdn) {
    let d = locals[cdt][cdn];
    let totalAmountPromise = new Promise(function (resolve, reject) {
      let totalAmount = 0;
      frm.doc.expenses.forEach(function (d) {
        totalAmount += d.amount;
      });
      resolve(totalAmount);
    });

    totalAmountPromise.then(function (totalAmount) {
      frm.set_value("total_debit", totalAmount);
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
});