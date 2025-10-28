# import frappe

# def sales_invoice_set_draft_series(doc, method):
#     # When new invoice is created (draft)
#     if doc.docstatus == 0:
#         doc.naming_series = "DRAFT-SINV-.YYYY.-"

# def sales_invoice_set_final_series(doc, method):
#     # When invoice is being submitted
#     if doc.docstatus == 1:
#         # Change the naming series
#         doc.naming_series = "ACC-SINV-.YYYY.-"

#         # Force rename to final series
#         new_name = frappe.model.naming.make_autoname(doc.naming_series)
#         if doc.name != new_name:
#             frappe.rename_doc("Sales Invoice", doc.name, new_name, force=True)
#             doc.name = new_name
