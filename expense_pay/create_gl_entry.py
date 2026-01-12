import frappe
from frappe import _
from frappe.utils import  now, logger
from erpnext.accounts.utils import _delete_gl_entries

logger.set_log_level("DEBUG")
logger = frappe.logger("expensepay", file_count=1, allow_site=True)


def validate_account_is_ledger(account, doc_name, field_label="Account"):
    """
    Validate that the given account is a ledger account (not a group account).
    Group accounts cannot be used in GL Entry transactions.
    """
    if not account:
        return
    
    is_group = frappe.db.get_value("Account", account, "is_group")
    if is_group:
        frappe.throw(
            _("{0} '{1}' is a Group Account. Group accounts cannot be used in transactions. "
              "Please select a Ledger account for {2}.").format(field_label, account, doc_name),
            title=_("Invalid Account")
        )


def validate_all_accounts(doc):
    """
    Validate all accounts used in the Expenses Entry to ensure they are ledger accounts.
    """
    # Validate the main account paid from
    validate_account_is_ledger(doc.account_paid_from, doc.name, "Account Paid From")
    
    # Validate expense accounts
    for expense in doc.expenses:
        validate_account_is_ledger(
            expense.account_paid_to, 
            doc.name, 
            f"Account Paid To (Row #{expense.idx})"
        )
        
        # Validate VAT account if template is specified
        if expense.vat_template:
            vat_template = frappe.get_doc("Purchase Taxes and Charges Template", expense.vat_template)
            if vat_template and vat_template.taxes:
                vat_account = vat_template.taxes[0].account_head
                validate_account_is_ledger(
                    vat_account,
                    doc.name,
                    f"VAT Account from template '{expense.vat_template}' (Row #{expense.idx})"
                )


@frappe.whitelist()
def create_gl_entries(doc, method):
    gl_entries = []
    
    # Validate all accounts before creating GL entries
    validate_all_accounts(doc)

    # Create GL entry for Account Paid From
    paid_to_accounts = ", ".join([d.account_paid_to for d in doc.expenses])
    
    # Update the remarks with VAT details
    vat_remarks = ""
    for expense in doc.expenses:
        vat_remarks += f"Expense: {expense.account_paid_to}, VAT: {expense.vat_amount} ({expense.vat_template})\n"

    main_remarks = f"{doc.remarks}\nVAT Info:\n{vat_remarks}"
    
    # GL entry for the account paid from
    gl_entry = {
        "doctype": "GL Entry",
        "posting_date": doc.posting_date,
        "account": doc.account_paid_from,
        "cost_center": doc.default_cost_center or "",
        "debit": 0,
        "credit": doc.paid_amount,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": doc.paid_amount,
        "against": paid_to_accounts,
        "voucher_type": _("Expenses Entry"),
        "voucher_no": doc.name,
        "is_opening": "No",
        "is_advance": "No",
        "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
        "company": doc.company,
        "remarks": main_remarks
    }
    gl_entries.append(gl_entry)

    # Create GL entries for each expense and VAT
    for expense in doc.expenses:
        expense_remarks = f"{expense.remarks or ''} | Amount without VAT: {expense.amount_without_vat} | VAT Amount: {expense.vat_amount} ({expense.vat_template})"
        logger.info(f"Amount without vat : {expense.amount_without_vat}\n")
        # GL entry for the amount without VAT
        gl_entry = {
            "doctype": "GL Entry",
            "posting_date": doc.posting_date,
            "account": expense.account_paid_to,
            "cost_center": expense.cost_center or doc.default_cost_center,
            "project": expense.project or "",
            "debit": expense.amount_without_vat,
            "credit": 0,
            "debit_in_account_currency": expense.amount_without_vat,
            "credit_in_account_currency": 0,
            "against": doc.account_paid_from,
            "voucher_type": _("Expenses Entry"),
            "voucher_no": doc.name,
            "is_opening": "No",
            "is_advance": "No",
            "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
            "company": doc.company,
            "remarks": expense_remarks
        }
        gl_entries.append(gl_entry)

        # GL entry for VAT amount
        if expense.vat_template and (expense.vat_amount > 0):
            vat_template = frappe.get_doc("Purchase Taxes and Charges Template", expense.vat_template)
            if vat_template and vat_template.taxes:
                vat_account = vat_template.taxes[0].account_head
                vat_cost_center = vat_template.taxes[0].cost_center

                vat_gl_entry = {
                    "doctype": "GL Entry",
                    "posting_date": doc.posting_date,
                    "account": vat_account,
                    "cost_center": vat_cost_center,
                    "debit": expense.vat_amount,
                    "credit": 0,
                    "debit_in_account_currency": expense.vat_amount,
                    "credit_in_account_currency": 0,
                    "against": expense.account_paid_to,
                    "voucher_type": _("Expenses Entry"),
                    "voucher_no": doc.name,
                    "is_opening": "No",
                    "is_advance": "No",
                    "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
                    "company": doc.company,
                    "remarks": f"VAT Amount: {expense.vat_amount} | VAT Account: {vat_account} | Cost Center: {vat_cost_center}"
                }
                gl_entries.append(vat_gl_entry)

    # Save and submit all GL Entries
    for gl_entry in gl_entries:
        try:
            gle = frappe.new_doc("GL Entry")
            gle.update(gl_entry)
            gle.flags.ignore_permissions = 1
            gle.flags.notify_update = False
            gle.submit()
            logger.info(f"GL Entry successfully submitted for Doc: {doc.name}")
        except Exception as e:
            logger.error(f"Error submitting GL Entry for Doc {doc.name}: {e}")
            frappe.msgprint(f"Error submitting GL Entry for {doc.name}: {str(e)}", alert=True, indicator="red")
            return  # Stop the function if an error occurs

    logger.info(f"GL Entry created for Doc: {doc.name} using create_gl_entries")
    frappe.msgprint(f"GL Entry Created for {doc.name}", alert=True, indicator="green")



def cancel_gl_entries(doc, method):
    doc.ignore_linked_doctypes = ("GL Entry",)
    
    gl_entries = []

    # Check if GL Entries exist for the current document
    existing_gl_entries = frappe.get_all(
        "GL Entry",
        filters={"voucher_type": _("Expenses Entry"), "voucher_no": doc.name, "is_cancelled": 0},
        fields=["name"]
    )

    # If no GL entries exist, skip the cancellation process
    if not existing_gl_entries:
        logger.info(f"No GL entries found for {doc.name}. Skipping cancellation process.")
        return
    
    # Try to validate accounts, but don't block cancellation if validation fails
    # This allows cancelling documents that were created with group accounts (legacy data)
    try:
        validate_all_accounts(doc)
        accounts_valid = True
    except frappe.ValidationError as e:
        logger.warning(f"Account validation failed for {doc.name} during cancellation: {e}. "
                      f"Proceeding with cancellation by deleting invalid GL entries (group accounts detected).")
        accounts_valid = False
        # If accounts are invalid (group accounts), delete the GL entries to keep ledger clean
        # These entries shouldn't exist in the first place since group accounts can't be used in transactions
        try:
            _delete_gl_entries(_("Expenses Entry"), doc.name)
            logger.info(f"Successfully deleted invalid GL entries for {doc.name} (group accounts detected)")
            frappe.msgprint(
                _("Cancelled Expenses Entry {0}. Invalid GL entries (with group accounts) have been deleted to keep the ledger clean.").format(doc.name),
                alert=True,
                indicator="orange"
            )
        except Exception as delete_error:
            logger.error(f"Error deleting GL entries for {doc.name}: {delete_error}")
            # Fallback: mark as cancelled if deletion fails
            voucher_type = _("Expenses Entry")
            voucher_no = doc.name
            frappe.db.sql(
                """UPDATE `tabGL Entry` SET is_cancelled = 1,
                modified=%s, modified_by=%s
                where voucher_type=%s and voucher_no=%s and is_cancelled = 0""",
                (now(), frappe.session.user, voucher_type, voucher_no),
            )
            frappe.db.commit()
            frappe.msgprint(
                _("Cancelled Expenses Entry {0}. GL entries marked as cancelled (could not delete due to error).").format(doc.name),
                alert=True,
                indicator="orange"
            )
        return  # Exit early - we've handled the invalid entries

    # Check if the necessary fields exist to identify if it's a newer version
    is_new_version = all(
        hasattr(expense, "vat_amount") and hasattr(expense, "amount_without_vat") and hasattr(expense, "vat_template") and expense.amount_without_vat > 0
        for expense in doc.expenses
    )

    if not is_new_version:
        logger.info(f"Old version of the expenses entry")
        # If it's an older document, execute the older function logic

        paid_to_accounts = ", ".join([d.account_paid_to for d in doc.expenses])

        # Create GL entry for Account Paid From
        gl_entry = {
            "doctype": "GL Entry",
            "posting_date": doc.posting_date,
            "account": doc.account_paid_from,
            "cost_center": doc.default_cost_center,
            "debit": doc.paid_amount,
            "credit": 0,
            "debit_in_account_currency": doc.paid_amount,
            "credit_in_account_currency": 0,
            "against": paid_to_accounts,
            "voucher_type": _("Expenses Entry"),
            "voucher_no": doc.name,
            "is_opening": "No",
            "is_advance": "No",
            "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
            "company": doc.company,
            "is_cancelled": 1,
            "to_rename": 1,
            "remarks": "On Cancelled " + (doc.remarks if doc.remarks else "")
        }
        gl_entries.append(gl_entry)

        # Create GL entries for Expenses child table
        for expense in doc.expenses:
            gl_entry = {
                "doctype": "GL Entry",
                "posting_date": doc.posting_date,
                "account": expense.account_paid_to,
                "debit": 0,
                "credit": expense.amount,
                "cost_center": (expense.cost_center if expense.cost_center else doc.default_cost_center),
                "project": (expense.project if expense.project else ""),
                "debit_in_account_currency": 0,
                "credit_in_account_currency": expense.amount,
                "against": doc.account_paid_from,
                "voucher_type": _("Expenses Entry"),
                "voucher_no": doc.name,
                "is_opening": "No",
                "is_advance": "No",
                "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
                "company": doc.company,
                "is_cancelled": 1,
                "to_rename": 1,
                "remarks": "On Cancelled " + (expense.remarks if expense.remarks else "")
            }
            gl_entries.append(gl_entry)

    else:
        logger.info(f"New expense entry version selected")
        # New version logic - Proceed with the updated logic

        paid_to_accounts = ", ".join([d.account_paid_to for d in doc.expenses])

        # Update the remarks for cancellation with VAT details
        vat_remarks = ""
        for expense in doc.expenses:
            vat_remarks += f"Cancelled Expense: {expense.account_paid_to}, VAT: {expense.vat_amount} ({expense.vat_template})\n"

        cancel_remarks = f"On Cancelled {doc.remarks if doc.remarks else ''}\nVAT Info:\n{vat_remarks}"

        # Create GL entry for Account Paid From
        gl_entry = {
            "doctype": "GL Entry",
            "posting_date": doc.posting_date,
            "account": doc.account_paid_from,
            "cost_center": doc.default_cost_center,
            "debit": doc.paid_amount,
            "credit": 0,
            "debit_in_account_currency": doc.paid_amount,
            "credit_in_account_currency": 0,
            "against": paid_to_accounts,
            "voucher_type": _("Expenses Entry"),
            "voucher_no": doc.name,
            "is_opening": "No",
            "is_advance": "No",
            "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
            "company": doc.company,
            "is_cancelled": 1,
            "to_rename": 1,
            "remarks": cancel_remarks  # Use updated remarks with VAT info
        }
        gl_entries.append(gl_entry)

        # Create GL entries for Expenses child table and VAT
        for expense in doc.expenses:
            # Update the remarks for cancellation with VAT information
            expense_cancel_remarks = f"On Cancelled {expense.remarks if expense.remarks else ''} | \n Amount without VAT: {expense.amount_without_vat} \n VAT Amount: {expense.vat_amount} ({expense.vat_template})"
            
            # 1. GL entry for the amount without VAT (Expense Cancellation)
            gl_entry = {
                "doctype": "GL Entry",
                "posting_date": doc.posting_date,
                "account": expense.account_paid_to,
                "debit": 0,
                "credit": expense.amount_without_vat,
                "cost_center": (expense.cost_center if expense.cost_center else doc.default_cost_center),
                "project": (expense.project if expense.project else ""),
                "debit_in_account_currency": 0,
                "credit_in_account_currency": expense.amount_without_vat,
                "against": doc.account_paid_from,
                "voucher_type": _("Expenses Entry"),
                "voucher_no": doc.name,
                "is_opening": "No",
                "is_advance": "No",
                "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
                "company": doc.company,
                "is_cancelled": 1,
                "to_rename": 1,
                "remarks": expense_cancel_remarks  # Include VAT info in each expense's remark for cancellation
            }
            gl_entries.append(gl_entry)

            # 2. Fetch VAT account and cost center from the VAT template
            if expense.vat_template:
                vat_template = frappe.get_doc("Purchase Taxes and Charges Template", expense.vat_template)
                if vat_template and vat_template.taxes:
                    vat_account = vat_template.taxes[0].account_head
                    vat_cost_center = vat_template.taxes[0].cost_center

                    # 3. GL entry for the VAT amount (Cancellation)
                    vat_cancel_remarks = f"On Cancelled VAT Amount: {expense.vat_amount} | VAT Account: {vat_account} | Cost Center: {vat_cost_center}"
                    vat_gl_entry = {
                        "doctype": "GL Entry",
                        "posting_date": doc.posting_date,
                        "account": vat_account,  # Use VAT account from the template
                        "cost_center": vat_cost_center,  # Use VAT cost center from the template
                        "debit": 0,
                        "credit": expense.vat_amount,  # Credit for VAT
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": expense.vat_amount,
                        "against": expense.account_paid_to,  # VAT is against the expense's account_paid_to
                        "voucher_type": _("Expenses Entry"),
                        "voucher_no": doc.name,
                        "is_opening": "No",
                        "is_advance": "No",
                        "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
                        "company": doc.company,
                        "is_cancelled": 1,
                        "remarks": vat_cancel_remarks  # VAT cancellation remarks
                    }
                    gl_entries.append(vat_gl_entry)

    # Save and submit all GL Entries with cancellation flag
    try:
        for gl_entry in gl_entries:
            gle = frappe.new_doc("GL Entry")
            gle.update(gl_entry)
            gle.flags.ignore_permissions = 1
            gle.flags.notify_update = False
            gle.submit()

        # Set all original GL Entries as cancelled
        voucher_type = gle.voucher_type
        voucher_no = gle.voucher_no
        frappe.db.sql(
            """UPDATE `tabGL Entry` SET is_cancelled = 1,
            modified=%s, modified_by=%s
            where voucher_type=%s and voucher_no=%s and is_cancelled = 0""",
            (now(), frappe.session.user, voucher_type, voucher_no),
        )
        frappe.db.commit()
    except Exception as e:
        # If creating reversal entries fails (e.g., due to group accounts),
        # check if it's a validation error about group accounts and delete entries if so
        error_message = str(e)
        is_group_account_error = "Group Account" in error_message or "group accounts cannot be used" in error_message.lower()
        
        if is_group_account_error:
            # Delete invalid GL entries (group accounts) to keep ledger clean
            logger.warning(f"Failed to create reversal GL entries for {doc.name} due to group accounts: {e}. "
                          f"Deleting invalid GL entries to keep ledger clean.")
            try:
                _delete_gl_entries(_("Expenses Entry"), doc.name)
                logger.info(f"Successfully deleted invalid GL entries for {doc.name} (group accounts detected)")
                frappe.msgprint(
                    _("Cancelled Expenses Entry {0}. Invalid GL entries (with group accounts) have been deleted to keep the ledger clean.").format(doc.name),
                    alert=True,
                    indicator="orange"
                )
            except Exception as delete_error:
                logger.error(f"Error deleting GL entries for {doc.name}: {delete_error}")
                # Fallback: mark as cancelled if deletion fails
                voucher_type = _("Expenses Entry")
                voucher_no = doc.name
                frappe.db.sql(
                    """UPDATE `tabGL Entry` SET is_cancelled = 1,
                    modified=%s, modified_by=%s
                    where voucher_type=%s and voucher_no=%s and is_cancelled = 0""",
                    (now(), frappe.session.user, voucher_type, voucher_no),
                )
                frappe.db.commit()
                frappe.msgprint(
                    _("Cancelled Expenses Entry {0}. GL entries marked as cancelled (could not delete due to error).").format(doc.name),
                    alert=True,
                    indicator="orange"
                )
        else:
            # For other errors, mark as cancelled (standard behavior)
            logger.warning(f"Failed to create reversal GL entries for {doc.name}: {e}. "
                          f"Marking existing GL entries as cancelled only.")
            voucher_type = _("Expenses Entry")
            voucher_no = doc.name
            frappe.db.sql(
                """UPDATE `tabGL Entry` SET is_cancelled = 1,
                modified=%s, modified_by=%s
                where voucher_type=%s and voucher_no=%s and is_cancelled = 0""",
                (now(), frappe.session.user, voucher_type, voucher_no),
            )
            frappe.db.commit()


def delete_gl_entries(doc, method):
    """
    Cancels and deletes GL Entries linked to the Expenses Entry before deleting the doc.
    """
    logger.info(f"Deleting GL Entries related to Expenses Entry {doc.name}")
    # Find all related GL Entries for this voucher type and number
    _delete_gl_entries("Expenses Entry", doc.name)
    
    doc.ignore_linked_doctypes = ("Gl Entry")
    
    logger.info("Ignoring the gl entries")
    # Optionally log or notify about the deletion
    frappe.msgprint(_("Cancelled and deleted GL Entries related to Expenses Entry {0}.").format(doc.name), alert=True)


@frappe.whitelist()
def sync_missing_gl_entries():
    missing_entries = []
    validation_errors = []

    # Log the start of the function
    logger.info("Starting sync_missing_gl_entries function")

    # Fetch submitted Expenses Entries
    expenses_entries = frappe.get_all("Expenses Entry", filters={"docstatus": 1}, fields=["name"])
    logger.info(f"Fetched {len(expenses_entries)} submitted Expenses Entries")

    for entry in expenses_entries:
        # Fetch the Expenses Entry document
        doc = frappe.get_doc("Expenses Entry", entry.name)
        logger.info(f"Processing Expenses Entry: {doc.name}")

        # Update amounts if amount_without_vat and vat_amount are zero
        for expense in doc.expenses:
            if expense.amount_without_vat == 0 and expense.vat_amount == 0 and expense.amount > 0:
                logger.info(f"Updating amount_without_vat for row #{expense.idx} in doc {doc.name}")
                expense.amount_without_vat = expense.amount

        # Save the updated document before creating GL Entries
        try:
            doc.save()
            frappe.db.commit()
            logger.info(f"Saved updated document {doc.name}")
        except Exception as e:
            logger.error(f"Error saving document {doc.name}: {e}")
            validation_errors.append(f"Error saving document {doc.name}: {str(e)}")
            continue


        # Step 1: Validate all rows in the expenses child table
        doc_validation_errors = []
        for expense in doc.expenses:
            logger.info(f"Validating row #{expense.idx} in doc {doc.name}")
            if expense.amount != expense.amount_without_vat + expense.vat_amount:
                error_message = _(
                    "Doc {0}, Row #{1}: Amount ({2}) does not equal Amount Without VAT ({3}) + VAT Amount ({4}) <br><br>"
                ).format(
                    doc.name,
                    expense.idx,
                    expense.amount,
                    expense.amount_without_vat,
                    expense.vat_amount
                )
                logger.info(f"Validation error found: {error_message}")
                doc_validation_errors.append(error_message)

        # If there are validation errors for this document, collect them and skip GL Entry creation
        if doc_validation_errors:
            logger.info(f"Validation errors found in doc {doc.name}, skipping GL Entry creation")
            validation_errors.extend(doc_validation_errors)
            continue  # Skip to the next document

        # Check if GL Entries exist for this Expenses Entry
        gl_entries = frappe.get_all("GL Entry", filters={"voucher_type": "Expenses Entry", "voucher_no": entry.name})
        logger.info(f"GL Entries found for {doc.name}: {len(gl_entries)}")

        if not gl_entries:
            logger.info(f"No GL Entries found for {doc.name}, creating GL Entries")

            # Call the existing function to create GL Entries
            try:
                create_gl_entries(doc, "on_submit")
                logger.info(f"GL Entries successfully created for {doc.name}")
                missing_entries.append(doc.name)
            except Exception as e:
                logger.error(f"Error creating GL Entries for document {doc.name}: {e}")
                validation_errors.append(f"Error creating GL Entries for document {doc.name}: {str(e)}")

    # After processing all documents, throw an error if any validation errors were collected
    if validation_errors:
        logger.info("Validation errors encountered during the process")
        frappe.throw(
            _("The following validation errors were found:\n\n{0}").format("\n".join(validation_errors)),
            title=_("Validation Errors Found")
        )

    logger.info(f"GL Entries created for the following documents: {missing_entries}")

    # Return the list of entries where GL Entries were created
    return missing_entries


@frappe.whitelist()
def find_miscalculated_amounts():
    miscalculated_entries = []

    # Fetch submitted Expenses Entries
    expenses_entries = frappe.get_all("Expenses Entry", filters={"docstatus": 1}, fields=["name"])

    for entry in expenses_entries:
        doc = frappe.get_doc("Expenses Entry", entry.name)
        for expense in doc.expenses:
            if expense.amount != expense.amount_without_vat + expense.vat_amount:
                miscalculated_entries.append(entry.name)
                break  # No need to check further rows if one is already miscalculated

    return miscalculated_entries
