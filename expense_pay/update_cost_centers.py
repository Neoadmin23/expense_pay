import frappe
from frappe import _
from frappe.utils import now, getdate
from frappe.utils.background_jobs import enqueue

@frappe.whitelist()
def update_cost_centers(docname):
    """
    Enqueue a background job to update VAT GL entry cost centers for Expenses Entry documents.
    """
    # Fetch the Expenses Entry Cost Center Update document
    if not docname:
        frappe.throw(_("Document name is required."))
    
    # Check if the document is unsaved (temporary name)
    if docname.startswith("new-"):
        frappe.throw(_("Please save the Expenses Entry Cost Center Update document before running the update. This ensures the document is properly named and saved for tracking purposes."))

    cost_center_update_doc = frappe.get_doc("Expenses Entry Cost Center Update", docname)
    from_date = cost_center_update_doc.from_date
    to_date = cost_center_update_doc.to_date

    # Validate date range
    if not from_date or not to_date:
        frappe.throw(_("From Date and To Date are required in the document."))
    if getdate(from_date) > getdate(to_date):
        frappe.throw(_("From Date cannot be later than To Date."))

    # Enqueue background job
    job_id = enqueue(
        process_cost_center_updates,
        queue="long",
        timeout=3600,  # 1 hour timeout
        job_name="Update Expenses Entry Cost Centers",
        docname=docname
    )
    return {"job_id": job_id}

def process_cost_center_updates(docname):
    """
    Process Expenses Entry documents and update VAT GL entry cost centers.
    """
    logger = frappe.logger("expensepay", file_count=1, allow_site=True)
    
    # Fetch the Expenses Entry Cost Center Update document
    cost_center_update_doc = frappe.get_doc("Expenses Entry Cost Center Update", docname)
    from_date = cost_center_update_doc.from_date
    to_date = cost_center_update_doc.to_date
    logger.info(f"Starting cost center update for Expenses Entry from {from_date} to {to_date}")

    # Fetch submitted Expenses Entry documents
    expenses_entries = frappe.get_all(
        "Expenses Entry",
        filters={
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]]
        },
        fields=["name", "default_cost_center"]
    )

    total_documents = len(expenses_entries)
    updated_count = 0
    skipped_count = 0

    # Clear existing log details if reprocessing
    cost_center_update_doc.log_details = []

    for entry in expenses_entries:
        try:
            doc = frappe.get_doc("Expenses Entry", entry.name)
            logger.info(f"Processing Expenses Entry: {doc.name}")

            for expense in doc.expenses:
                if not (expense.vat_template and expense.vat_amount > 0):
                    logger.info(f"Skipping row #{expense.idx} in {doc.name}: No VAT template or amount")
                    skipped_count += 1
                    log_entry = frappe.new_doc("Update Log Detail")
                    log_entry.entry_name = doc.name
                    log_entry.row_idx = expense.idx
                    log_entry.log_message = "Skipped (No VAT template or amount)"
                    cost_center_update_doc.append("log_details", log_entry)
                    continue

                # Get VAT account and template cost center
                vat_template = frappe.get_doc("Purchase Taxes and Charges Template", expense.vat_template)
                if not (vat_template and vat_template.taxes):
                    logger.info(f"Skipping row #{expense.idx} in {doc.name}: Invalid VAT template")
                    skipped_count += 1
                    log_entry = frappe.new_doc("Update Log Detail")
                    log_entry.entry_name = doc.name
                    log_entry.row_idx = expense.idx
                    log_entry.log_message = "Skipped (Invalid VAT template)"
                    cost_center_update_doc.append("log_details", log_entry)
                    continue

                vat_account = vat_template.taxes[0].account_head
                template_cost_center = vat_template.taxes[0].cost_center
                target_cost_center = expense.cost_center or doc.default_cost_center

                if not target_cost_center:
                    logger.info(f"Skipping row #{expense.idx} in {doc.name}: No cost center set")
                    skipped_count += 1
                    log_entry = frappe.new_doc("Update Log Detail")
                    log_entry.entry_name = doc.name
                    log_entry.row_idx = expense.idx
                    log_entry.log_message = "Skipped (No cost center set)"
                    cost_center_update_doc.append("log_details", log_entry)
                    continue

                # Validate cost center
                if frappe.db.get_value("Cost Center", target_cost_center, "is_group"):
                    logger.error(f"Skipping row #{expense.idx} in {doc.name}: Cost center {target_cost_center} is a group")
                    skipped_count += 1
                    log_entry = frappe.new_doc("Update Log Detail")
                    log_entry.entry_name = doc.name
                    log_entry.row_idx = expense.idx
                    log_entry.log_message = f"Skipped (Cost center {target_cost_center} is a group)"
                    cost_center_update_doc.append("log_details", log_entry)
                    continue

                # Find VAT GL entry
                gl_entries = frappe.get_all(
                    "GL Entry",
                    filters={
                        "voucher_type": "Expenses Entry",
                        "voucher_no": doc.name,
                        "account": vat_account,
                        "is_cancelled": 0
                    },
                    fields=["name", "cost_center"]
                )

                if not gl_entries:
                    logger.info(f"Skipping row #{expense.idx} in {doc.name}: No VAT GL entry found")
                    skipped_count += 1
                    log_entry = frappe.new_doc("Update Log Detail")
                    log_entry.entry_name = doc.name
                    log_entry.row_idx = expense.idx
                    log_entry.log_message = "Skipped (No VAT GL entry found)"
                    cost_center_update_doc.append("log_details", log_entry)
                    continue

                for gl_entry in gl_entries:
                    if gl_entry.cost_center == target_cost_center:
                        logger.info(f"Skipping row #{expense.idx} in {doc.name}: GL entry {gl_entry.name} already has correct cost center {target_cost_center}")
                        skipped_count += 1
                        log_entry = frappe.new_doc("Update Log Detail")
                        log_entry.entry_name = doc.name
                        log_entry.row_idx = expense.idx
                        log_entry.log_message = f"Skipped (GL entry {gl_entry.name} already has cost center {target_cost_center})"
                        cost_center_update_doc.append("log_details", log_entry)
                        continue

                    # Update GL entry
                    frappe.db.set_value(
                        "GL Entry",
                        gl_entry.name,
                        {
                            "cost_center": target_cost_center,
                            "remarks": f"Cost center updated to {target_cost_center} on {now()} (Original: {gl_entry.cost_center})"
                        }
                    )
                    logger.info(f"Updated GL entry {gl_entry.name} for row #{expense.idx} in {doc.name}: Cost center changed to {target_cost_center}")
                    log_entry = frappe.new_doc("Update Log Detail")
                    log_entry.entry_name = doc.name
                    log_entry.row_idx = expense.idx
                    log_entry.log_message = f"Updated GL entry {gl_entry.name} to cost center {target_cost_center}"
                    cost_center_update_doc.append("log_details", log_entry)
                    updated_count += 1

            frappe.db.commit()
        except Exception as e:
            logger.error(f"Error processing {doc.name}: {str(e)}")
            log_entry = frappe.new_doc("Update Log Detail")
            log_entry.entry_name = doc.name
            log_entry.row_idx = 0
            log_entry.log_message = f"Error processing: {str(e)}"
            cost_center_update_doc.append("log_details", log_entry)
            frappe.db.rollback()
            continue

    # Update the doctype with summary
    cost_center_update_doc.update_status = (
        f"Processed {total_documents} Expenses Entry documents.\n"
        f"Updated {updated_count} GL entries.\n"
        f"Skipped {skipped_count} entries."
    )
    cost_center_update_doc.save()
    frappe.db.commit()
    logger.info(f"Completed cost center update. {updated_count} entries updated, {skipped_count} skipped.")