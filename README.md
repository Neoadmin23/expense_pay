## Expense Pay

Custom Frappe / ERPNext app that introduces an **`Expenses Entry`** document to record a single “payment” that is split across **multiple expense lines**, and automatically generates the corresponding **`GL Entry`** rows on submit (including optional **VAT split**).

This README documents:
- **What features the app provides**
- **Which DocTypes it adds**
- **How the document creation + accounting flow works end-to-end**
- **How to configure and use it**

### What this app adds (features)

- **New DocType: `Expenses Entry` (submittable)**:
  - A header with “Paid From” account + posting date + paid amount + default cost center.
  - A child table where you can add **multiple expense rows**.
  - Client-side validation that **Paid Amount == Total Debit** (sum of rows).
  - On submit, creates **multiple `GL Entry` records** (one credit + many debits).
  - Adds a “Ledger” button to open ERPNext’s **General Ledger** report filtered to this voucher.

- **New child table DocType: `Expenses`**:
  - One row per expense line.
  - Supports:
    - Selecting an **expense type** which can auto-fill the expense account.
    - Optional **VAT** via “Purchase Taxes and Charges Template”.
    - Optional **multi-currency** helpers (amount in account currency + exchange rate).

- **New DocType: `Expense Entry Type`**:
  - Simple master: `type` + `account`.
  - Used by `Expenses` rows to auto-fetch the “Account Paid To”.

- **New Single DocType: `Expense Entry Settings`**:
  - Allows enabling **editing after submit** for specific roles.
  - Client-side logic makes selected fields editable on submitted documents.

- **Accounting automation (server-side)**:
  - On `Expenses Entry` **submit**: creates `GL Entry` rows (`expense_pay/create_gl_entry.py:create_gl_entries`).
  - On `Expenses Entry` **cancel**: creates reversal entries (new or old logic), then marks original GLs cancelled (`cancel_gl_entries`).
  - On `Expenses Entry` **delete**: cancels/deletes linked GL entries (`delete_gl_entries`).

- **Maintenance utilities (server-side, whitelisted)**:
  - `sync_missing_gl_entries`: creates missing GL entries for already-submitted `Expenses Entry` docs.
  - `find_miscalculated_amounts`: finds submitted entries whose row totals don’t match (amount vs VAT split).

- **Patch**:
  - `expense_pay.expense_pay.doctype.expenses_entry.patches.fiscal_year` updates `GL Entry.fiscal_year` for vouchers created by this DocType to match the `posting_date` year (runs as a post-model-sync patch).

### DocTypes introduced by this app

- **`Expenses Entry`** (submittable, main transaction)
- **`Expenses`** (child table for expense lines)
- **`Expense Entry Type`** (master for categorizing rows + picking default accounts)
- **`Expense Entry Settings`** (Single)
- **`Allowed Roles`** (child table used by `Expense Entry Settings`)

### Installation

Install like any other Frappe app:

- Get the app:
  - `bench get-app <this_repo_or_app_url>`
- Install on a site:
  - `bench --site <site_name> install-app expense_pay`
- Apply migrations:
  - `bench --site <site_name> migrate`

### Configuration (required / recommended)

#### 1) Accounts & Cost Centers

On `Expenses Entry` you must choose:
- **Account Paid From**: a ledger `Account` (group accounts are rejected).
- **Default Cost Center**: used as fallback for expense rows.

Each `Expenses` row uses:
- **Account Paid To**: an expense/ledger account (can be auto-filled from `Expense Entry Type`).
- Optional **Cost Center** override per row.

#### 2) Expense Entry Types (optional)

Create `Expense Entry Type` records if you want a controlled list of row “types”:
- `type`: a unique label
- `account`: the default account used for that type

When you select `expense_entry_type` on a row, the row’s **Account Paid To** is fetched from that type’s `account`.

#### 3) VAT Templates (optional)

VAT is driven by ERPNext’s **`Purchase Taxes and Charges Template`**:
- On each expense row you may set **VAT Template**
- The client script reads the **first tax row** and uses its `rate` as the VAT rate
- On submit, the server script uses the **first tax row**’s `account_head` as the VAT account and its `cost_center` as the VAT cost center

Practical requirement:
- Ensure your VAT template’s first tax row has:
  - **Rate**
  - **Account Head**
  - (Optionally) **Cost Center**

#### 4) Multi-currency (optional)

If you enable **Multi Currency** on `Expenses Entry`:
- The form pulls the latest `Currency Exchange` for a given `from_currency`
- It calculates:
  - `paid_amount_in_account_currency` = `total_debit` / `exchange_rate`
  - row `amount` = row `amount_in_account_currency` * row `exchange_rate`

To use it cleanly:
- Maintain recent `Currency Exchange` records for your currencies.

#### 5) Editing after submit (optional, role-gated)

In `Expense Entry Settings`:
- Enable **Allow After Submit Entries**
- Add allowed roles in the **Allowed Roles** table

On submitted `Expenses Entry` documents, if the current user has any allowed role, the client script will allow editing:
- Header: `paid_amount`, `exchange_rate`, `total_debit`
- Row fields: `vat_template`, `vat_amount`, `amount`, `amount_without_vat`

Important note:
- The app’s GL automation is triggered only by **submit/cancel/delete** hooks. Editing after submit does **not** automatically re-create or adjust existing GL Entries. For accounting correctness, prefer **Cancel + Amend + Submit** when changes must affect the ledger.

### How the document flow works (end-to-end)

This section describes what happens from the time you create an `Expenses Entry` to the time it posts to the ledger.

#### A) Draft → Save (client-side behavior)

On the form (`expense_pay/expense_pay/doctype/expenses_entry/expenses_entry.js`):
- **Account selection guards**:
  - `account_paid_from` and row `account_paid_to` are filtered to `Account.is_group = 0` (ledger accounts only).
- **Totals**:
  - `total_debit` is computed as the sum of each row’s:
    - `amount_without_vat + vat_amount` (if VAT exists)
    - otherwise `amount_without_vat`
- **Validation before submit**:
  - `paid_amount` must be > 0
  - `total_debit` must be > 0
  - `paid_amount` must equal `total_debit` (rounded to 2 decimals)
  - For each row: `amount` must equal `amount_without_vat + vat_amount` (rounded to 2 decimals)

#### B) Submit → GL Entry creation (server-side)

Hook:
- `Expenses Entry.on_submit` → `expense_pay.create_gl_entry.create_gl_entries`

Server flow (`expense_pay/create_gl_entry.py:create_gl_entries`):
- **1) Validate accounts are ledger accounts**
  - Validates `account_paid_from`
  - Validates each row’s `account_paid_to`
  - If VAT template exists, validates the VAT account from the template’s first tax row
- **2) Build GL Entries**
  - **Credit**: one GL Entry on `account_paid_from` for `paid_amount`
  - For each expense row:
    - **Debit**: one GL Entry on `account_paid_to` for `amount_without_vat`
    - If VAT is set and `vat_amount > 0`:
      - **Debit**: one GL Entry on the VAT account (from template) for `vat_amount`
- **3) Submit all GL Entry docs**
  - Creates each `GL Entry` with `ignore_permissions = 1`
  - Submits each entry individually

Result:
- Your `Expenses Entry` becomes a voucher that appears in General Ledger via the created `GL Entry` rows, using:
  - `voucher_type = "Expenses Entry"`
  - `voucher_no = <Expenses Entry name>`

#### C) Viewing ledger for an Expenses Entry (UI)

On refresh, if the document is submitted/cancelled (`docstatus > 0`), the form adds:
- **Ledger** button → opens “General Ledger” report with route options:
  - `voucher_no = <doc.name>`
  - `from_date = posting_date`
  - `to_date = modified (YYYY-MM-DD)`
  - `company = company`
  - `show_cancelled_entries = true` when doc is cancelled

#### D) Cancel → reversal logic + mark existing GL cancelled

Hook:
- `Expenses Entry.on_cancel` → `expense_pay.create_gl_entry.cancel_gl_entries`

Server flow (high-level):
- **1) If no (active) GL Entries exist, do nothing**
- **2) Try validating accounts**
  - If validation fails (e.g. legacy group accounts), it **does not block cancellation**:
    - It directly updates existing linked `GL Entry` rows and sets `is_cancelled = 1`
- **3) If validation succeeds, create reversal GL entries**
  - There are two branches:
    - **Old version**: uses row `amount` directly
    - **New version**: uses `amount_without_vat` + `vat_amount` split
  - In both branches, the code creates new `GL Entry` rows with `is_cancelled = 1` and submits them (these act as reversal entries).
- **4) Mark original GL Entries cancelled**
  - Executes an SQL update to set all original linked GL entries to `is_cancelled = 1`

#### E) Delete (trash) → delete linked GL entries

Hook:
- `Expenses Entry.on_trash` → `expense_pay.create_gl_entry.delete_gl_entries`

Server flow:
- Calls ERPNext `_delete_gl_entries("Expenses Entry", <doc.name>)` to cancel/delete linked `GL Entry` rows for this voucher.

### Operational / maintenance utilities

These are whitelisted Python functions in `expense_pay/create_gl_entry.py` that you can run from:
- Bench console, background jobs, or via Frappe RPC (if permitted)

#### `sync_missing_gl_entries`

Purpose:
- For already-submitted `Expenses Entry` documents, find ones that have **no GL Entries** and create them.

Important behaviors:
- Before creating missing GLs, it:
  - Backfills `amount_without_vat` from `amount` when both VAT fields are zero (for older records)
  - Validates each row that `amount == amount_without_vat + vat_amount`; if not, it collects errors and throws at the end.

#### `find_miscalculated_amounts`

Purpose:
- Returns a list of submitted `Expenses Entry` names where any row violates:
  - `amount != amount_without_vat + vat_amount`

### Notes / constraints (as implemented)

- **Ledger accounts only**:
  - Both client and server enforce that `Account Paid From` and `Account Paid To` are not group accounts.
- **VAT template handling assumes first tax row**:
  - Both client VAT calculation and server VAT posting use only the template’s first tax row.
- **Fiscal year**:
  - `GL Entry.fiscal_year` is initially set from the user default fiscal year during creation.
  - The included patch attempts to correct fiscal year for GL entries created by this voucher type to match posting year.

#### License

MIT