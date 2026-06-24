# Expense Pay — Introduction

[README](../README.md) · [Changelog](CHANGELOG.md)

Expense Pay adds **Expenses Entry**, a submittable voucher that splits one payment across multiple expense lines (with optional VAT) and posts balanced **GL Entry** rows on submit.

## Table of contents

- [Architecture overview](#architecture-overview)
- [DocType model](#doctype-model)
- [VAT amount normalization](#vat-amount-normalization)
- [Submit and GL posting flow](#submit-and-gl-posting-flow)

## Architecture overview

```mermaid
flowchart TB
    subgraph client [Desk client]
        Form[Expenses Entry form]
        CalcVat[calculate_vat JS]
        TotalDebit[update_total_debit JS]
    end
    subgraph server [Expense Pay server]
        BeforeSave[before_save normalize amounts]
        Validate[validate]
        CreateGL[create_gl_entries]
    end
    subgraph erpnext [ERPNext]
        GLEntry[GL Entry]
        GLReport[General Ledger report]
    end
    Form --> CalcVat
    Form --> TotalDebit
    Form -->|save| BeforeSave
    BeforeSave --> Validate
    Form -->|submit| CreateGL
    CreateGL --> GLEntry
    GLEntry --> GLReport
```

## DocType model

```mermaid
erDiagram
    ExpensesEntry ||--o{ Expenses : expenses
    ExpensesEntry }o--|| Account : account_paid_from
    Expenses }o--|| Account : account_paid_to
    Expenses }o--o| PurchaseTaxesAndChargesTemplate : vat_template
    ExpenseEntryType ||--o| Account : account
    Expenses }o--o| ExpenseEntryType : expense_entry_type
    ExpensesEntry ||--o{ GLEntry : "voucher_no"
```

## VAT amount normalization

Child-table fields `amount_without_vat` and `vat_amount` are **Float** fields. Without rounding, VAT computed as `(amount_without_vat × rate) / 100` can produce values such as `48.91305`, while `paid_amount` (Currency) is stored at two decimal places. GL debits then sum to a different total than the credit line.

**Fix (v0.2.3):** amounts are rounded to currency precision on the client, normalized again in `before_save`, and rounded when building GL entries.

```mermaid
flowchart LR
    A[User enters amount_without_vat] --> B[calculate_vat rounds VAT]
    B --> C[before_save normalizes rows]
    C --> D[validate checks totals]
    D --> E[create_gl_entries uses flt]
    E --> F["debit sum = credit (paid_amount)"]
```

| Step | Location | Behavior |
|------|----------|----------|
| Client VAT | `expenses_entry.js` | `flt()` on `amount_without_vat`, `vat_amount`, `amount` |
| Save | `expenses_entry.py` | `_normalize_expense_amounts()` recomputes VAT from template |
| Submit | `create_gl_entry.py` | `flt()` on all debit/credit GL amounts |

## Submit and GL posting flow

```mermaid
sequenceDiagram
    participant User
    participant Form as Expenses Entry
    participant Hook as create_gl_entries
    participant GL as GL Entry
    User->>Form: Save draft
    Form->>Form: before_save normalize amounts
    User->>Form: Submit
    Form->>Hook: on_submit
    Hook->>Hook: flt paid_amount and row amounts
    Hook->>GL: Credit account_paid_from
    loop Each expense row
        Hook->>GL: Debit account_paid_to
        Hook->>GL: Debit VAT account if template set
    end
    User->>GL: General Ledger report
```

**Result:** one credit on **Account Paid From** for `paid_amount`, plus debits per row on expense and VAT accounts, with debits and credit balancing at currency precision.
