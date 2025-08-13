frappe.ui.form.on("Expenses Entry Cost Center Update", {
  refresh: function(frm) {
    // Add custom button to trigger cost center update
    frm.add_custom_button(__("Update Cost Centers"), function() {
      // Validate date range
      if (!frm.doc.from_date || !frm.doc.to_date) {
        frappe.msgprint(__("Please select both From Date and To Date"));
        return;
      }
      if (frm.doc.from_date > frm.doc.to_date) {
        frappe.msgprint(__("From Date cannot be later than To Date"));
        return;
      }

      // Save the document if unsaved
      if (frm.doc.__islocal) {
        frm.save("Save", function() {
          // Proceed with update after saving
          run_cost_center_update(frm);
        });
      } else {
        // Document is already saved, proceed directly
        run_cost_center_update(frm);
      }
    });
  },

  from_date: function(frm) {
    // Clear update_status when date changes
    frm.set_value("update_status", "");
  },

  to_date: function(frm) {
    // Clear update_status when date changes
    frm.set_value("update_status", "");
  }
});

// Helper function to run cost center update
function run_cost_center_update(frm) {
  // Fetch count of eligible Expenses Entry documents
  frappe.call({
    method: "frappe.client.get_count",
    args: {
      doctype: "Expenses Entry",
      filters: {
          docstatus: 1,
          posting_date: ["between", [frm.doc.from_date, frm.doc.to_date]]
      }

    },
    callback: function(r) {
      let count = r.message || 0;
      // Show confirmation dialog with document count
      frappe.confirm(
        __(`Found ${count} submitted Expenses Entry documents in the date range. Proceed with updating their VAT GL entry cost centers?`),
        function() {
          // Trigger background job with document name
          frappe.call({
            method: "expense_pay.update_cost_centers.update_cost_centers",
            args: {
              docname: frm.doc.name
            },
            callback: function(r) {
              if (r.message && r.message.job_id) {
                frappe.msgprint(__("Cost center update job enqueued. Check the Update Status field for progress."));
              }
            }
          });
        },
        function() {
          frappe.msgprint(__("Update cancelled."));
        }
      );
    }
  });
}