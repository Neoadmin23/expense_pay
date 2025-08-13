# Copyright (c) 2023, Kishan Panchal and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ExpensesEntry(Document):
    pass
    def validate(self):
        # Validate parent cost center
        if self.default_cost_center:
            is_group = frappe.db.get_value("Cost Center", self.default_cost_center, "is_group")
            if is_group:
                frappe.throw("Default Cost Center cannot be a group.")

        # Validate child cost centers
        for row in self.expenses:
            if row.cost_center:
                is_group = frappe.db.get_value("Cost Center", row.cost_center, "is_group")
                if is_group:
                    frappe.throw(f"Cost Center in row {row.idx} cannot be a group.")
