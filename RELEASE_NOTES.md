# Expense Pay - Release Notes

## v0.2.1 (2025-02-11)

### Summary

This release fixes issues with cancelling and deleting Expenses Entry documents that have missing account details in the expenses child table (legacy data created before validation was enforced).

### Changes

#### Cancel & Delete for Invalid/Legacy Documents

- **Cancel flow**: Documents with blank `Account Paid From` or blank `Account Paid To` in any expense row can now be cancelled successfully. The system detects invalid account data, deletes existing GL entries (if any), and allows the cancel to complete without attempting to create reversal entries.

- **Delete flow**: 
  - Fixed `ignore_linked_doctypes` to correctly ignore GL Entry links during deletion.
  - Wrapped GL entry cleanup in try/except so deletion proceeds even if GL cleanup fails.
  - Users can now delete Expenses Entry documents that have invalid or missing account details.

#### Exception Handling Improvements

- Extended cancel exception handler to catch mandatory/required field errors (e.g. when creating reversal entries fails due to blank account). In such cases, existing GL entries are deleted and the cancel succeeds instead of failing.

### Technical Details

- Added `_doc_has_invalid_account_data(doc)` helper to detect documents with missing account fields.
- Cancel: Early exit path when invalid account data is detected → delete GL entries and return.
- Delete: Set `doc.ignore_linked_doctypes = ("GL Entry",)` at start; wrap `_delete_gl_entries` in try/except.

---

## v0.2.0 (Previous Release)

### Summary

Mandatory account validations to prevent submitting Expenses Entry with blank account details.

### Changes

- **Account Paid To** made required in the Expenses child table (schema + server validation).
- **Credit account** (Account Paid From) and **debit accounts** (Account Paid To per row) validated as mandatory before save.
- Prevents creating and submitting expenses with missing account paid to.
