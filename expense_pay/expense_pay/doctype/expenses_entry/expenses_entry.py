# Copyright (c) 2023, Kishan Panchal and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class ExpensesEntry(Document):
	def validate(self):
		"""Validate entries and collect all errors before throwing once."""
		errors = []
		paid_amount_precision = self.precision("paid_amount") or 2
		rounded_paid_amount = flt(self.paid_amount or 0, paid_amount_precision)
		total_debit = 0.0

		# Header checks
		if not self.account_paid_from:
			errors.append(_("Account Paid From (Credit account) is mandatory."))
		else:
			self._validate_account_is_ledger(
				self.account_paid_from,
				"Account Paid From",
				errors
			)

		if rounded_paid_amount <= 0:
			errors.append(_("Paid Amount must be greater than zero."))

		# Row checks
		for expense in self.expenses:
			row_no = expense.idx
			amount_precision = expense.precision("amount") or 2
			amount_without_vat_precision = expense.precision("amount_without_vat") or amount_precision
			vat_precision = expense.precision("vat_amount") or amount_precision
			row_precision = max(amount_precision, amount_without_vat_precision, vat_precision)

			amount_without_vat = flt(expense.amount_without_vat or 0, row_precision)
			vat_amount = flt(expense.vat_amount or 0, row_precision)
			amount = flt(expense.amount or 0, row_precision)
			expected_amount = flt(amount_without_vat + vat_amount, row_precision)
			total_debit += expected_amount

			if not expense.account_paid_to:
				errors.append(
					_("Row #{0}: Account Paid To (Debit account) is mandatory.").format(row_no)
				)
			else:
				self._validate_account_is_ledger(
					expense.account_paid_to,
					f"Account Paid To (Row #{row_no})",
					errors
				)

			if amount != expected_amount:
				errors.append(
					_("Row #{0}: Amount ({1}) must equal Amount Without VAT ({2}) + VAT Amount ({3}).").format(
						row_no, amount, amount_without_vat, vat_amount
					)
				)

			if expense.vat_template:
				try:
					vat_template = frappe.get_doc("Purchase Taxes and Charges Template", expense.vat_template)
					if vat_template and vat_template.taxes:
						vat_account = vat_template.taxes[0].account_head
						if not vat_account:
							errors.append(
								_("Row #{0}: VAT template '{1}' has no account head in the first tax row.").format(
									row_no, expense.vat_template
								)
							)
						else:
							self._validate_account_is_ledger(
								vat_account,
								f"VAT Account from template '{expense.vat_template}' (Row #{row_no})",
								errors
							)
				except frappe.DoesNotExistError:
					errors.append(
						_("Row #{0}: VAT template '{1}' does not exist.").format(row_no, expense.vat_template)
					)

		rounded_total_debit = flt(total_debit, paid_amount_precision)
		if rounded_total_debit <= 0:
			errors.append(_("Total Debit must be greater than zero."))

		if rounded_paid_amount != rounded_total_debit:
			errors.append(
				_("Paid Amount ({0}) must equal Total Debit ({1}).").format(
					rounded_paid_amount, rounded_total_debit
				)
			)

		if errors:
			message = "<br>".join(f"- {frappe.utils.escape_html(error)}" for error in errors)
			frappe.throw(
				_("Please correct the following validation errors:<br><br>{0}").format(message),
				title=_("Validation Errors Found")
			)
	
	def _validate_account_is_ledger(self, account, field_label="Account", errors=None):
		"""Validate that the given account is a ledger account (not a group account)."""
		if not account:
			return
		
		is_group = frappe.db.get_value("Account", account, "is_group")
		if is_group:
			message = _(
				"{0} '{1}' is a Group Account. Group accounts cannot be used in transactions. "
				"Please select a Ledger account."
			).format(field_label, account)
			if errors is not None:
				errors.append(message)
			else:
				frappe.throw(
					message,
					title=_("Invalid Account")
				)
