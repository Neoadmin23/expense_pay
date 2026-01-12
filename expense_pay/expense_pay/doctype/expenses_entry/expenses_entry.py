# Copyright (c) 2023, Kishan Panchal and contributors
# For license information, please see license.txt

import frappe
from frappe import _

class ExpensesEntry(Document):
	def validate(self):
		"""Validate accounts before saving/submitting"""
		# Validate that all accounts are ledger accounts (not group accounts)
		# This prevents the error from happening deep in GL Entry creation
		self._validate_account_is_ledger(self.account_paid_from, "Account Paid From")
		
		for expense in self.expenses:
			self._validate_account_is_ledger(
				expense.account_paid_to, 
				f"Account Paid To (Row #{expense.idx})"
			)
			
			# Validate VAT account if template is specified
			if expense.vat_template:
				try:
					vat_template = frappe.get_doc("Purchase Taxes and Charges Template", expense.vat_template)
					if vat_template and vat_template.taxes:
						vat_account = vat_template.taxes[0].account_head
						self._validate_account_is_ledger(
							vat_account,
							f"VAT Account from template '{expense.vat_template}' (Row #{expense.idx})"
						)
				except frappe.DoesNotExistError:
					# Template doesn't exist, skip validation
					pass
	
	def _validate_account_is_ledger(self, account, field_label="Account"):
		"""Validate that the given account is a ledger account (not a group account)"""
		if not account:
			return
		
		is_group = frappe.db.get_value("Account", account, "is_group")
		if is_group:
			frappe.throw(
				_("{0} '{1}' is a Group Account. Group accounts cannot be used in transactions. "
				  "Please select a Ledger account.").format(field_label, account),
				title=_("Invalid Account")
			)
