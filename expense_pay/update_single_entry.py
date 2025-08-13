import frappe
from frappe import _
from frappe.utils import now
from frappe.utils.background_jobs import enqueue

@frappe.whitelist()
def update_single_expense_entry_cost_centers(expense_entry_name):
    """
    Enqueue a background job to update VAT GL entry cost centers for a single Expenses Entry document.
    """
    if not expense_entry_name:
        frappe.throw(_("Expenses Entry name is required."))

    # Fetch the Expenses Entry document to get posting_date
    expense_entry = frappe.get_doc("Expenses Entry", expense_entry_name)
    if expense_entry.docstatus != 1:
        frappe.throw(_("Expenses Entry must be submitted to update cost centers."))

    # Create a new Expenses Entry Cost Center Update document
    try:
        cost_center_update_doc = frappe.new_doc("Expenses Entry Cost Center Update")
        cost_center_update_doc.from_date = expense_entry.posting_date
        cost_center_update_doc.to_date = expense_entry.posting_date
        cost_center_update_doc.expense_entry = expense_entry_name
        cost_center_update_doc.save()
        frappe.db.commit()  # Ensure document is saved to database
    except Exception as e:
        frappe.log_error(f"Failed to create Expenses Entry Cost Center Update document for {expense_entry_name}: {str(e)}", "Cost Center Update Error")
        frappe.throw(_("Failed to create update document: {0}. Please check permissions or contact the administrator.").format(str(e)))

    # Enqueue background job
    job = enqueue(
        process_single_expense_entry_cost_centers,
        queue="long",
        timeout=600,
        job_name=f"Update Cost Centers for Expenses Entry {expense_entry_name}",
        expense_entry_name=expense_entry_name,
        cost_center_update_docname=cost_center_update_doc.name
    )
    return {"job_id": job.id if hasattr(job, "id") else str(job)}


def process_single_expense_entry_cost_centers(expense_entry_name, cost_center_update_docname):
    """
    Process a single Expenses Entry document and update VAT GL entry cost centers.
    """
    logger = frappe.logger("expensepay", file_count=1, allow_site=True)
    
    # Fetch the Expenses Entry and Cost Center Update documents
    doc = frappe.get_doc("Expenses Entry", expense_entry_name)
    cost_center_update_doc = frappe.get_doc("Expenses Entry Cost Center Update", cost_center_update_docname)
    logger.info(f"Starting cost center update for Expenses Entry: {doc.name}")

    total_documents = 1
    updated_count = 0
    skipped_count = 0

    # Clear existing log details
    cost_center_update_doc.log_details = []

    try:
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

                # Check if VAT template cost center matches target cost center
                if template_cost_center == target_cost_center:
                    logger.info(f"Skipping row #{expense.idx} in {doc.name}: VAT template cost center {template_cost_center} matches target cost center")
                    skipped_count += 1
                    log_entry = frappe.new_doc("Update Log Detail")
                    log_entry.entry_name = doc.name
                    log_entry.row_idx = expense.idx
                    log_entry.log_message = f"Skipped (VAT template cost center {template_cost_center} matches target cost center)"
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

    # Update the doctype with summary
    cost_center_update_doc.update_status = (
        f"Processed 1 Expenses Entry document.\n"
        f"Updated {updated_count} GL entries.\n"
        f"Skipped {skipped_count} entries."
    )
    cost_center_update_doc.save()
    frappe.db.commit()
    logger.info(f"Completed cost center update for {doc.name}. {updated_count} entries updated, {skipped_count} skipped.")