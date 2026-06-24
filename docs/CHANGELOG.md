# Changelog

All notable changes to **Expense Pay** are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.3] — 2026-06-24

Fix VAT and expense amount rounding so GL debits match paid amount credit.

### Fixed

- VAT amounts no longer store extra decimal places (e.g. `48.91305`) when calculated from `amount_without_vat` and a tax template rate.
- `before_save` normalizes child-row `amount_without_vat`, `vat_amount`, and `amount` to currency precision and recomputes VAT from the template.
- GL posting rounds debit and credit amounts with `flt()` so General Ledger totals balance (no spurious 0.01 difference).
- Client-side `calculate_vat` and `update_total_debit` now round to currency precision before save.

---

## [0.2.2] — prior release

Harden Expenses Entry submit and precision validation.

See git history for earlier releases.
