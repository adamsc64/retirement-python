# Roadmap

## Completed

- ✅ CSV importers: Citi, Amex, HSBC, Wise
- ✅ Three-layer ingestion: `ImportBatch` / `RawTransaction` / `Transaction`
- ✅ File-hash deduplication (idempotent re-import)
- ✅ Row-level cross-batch overlap detection (date-range boundary handling)
- ✅ Rule-based exclusion engine (`apply_exclusions`, `rules/rules.yml`)
- ✅ Rule-based categorization engine (`apply_categories`, `Manual Review` fallback)
- ✅ `uncategorized_top_spend` CLI command (sort by spend or count, filter, limit)
- ✅ Web UI: index page with categorization stats and progress
- ✅ Web UI: keyboard-driven categorization queue (`/categorize/`)
- ✅ Django admin with inline category editing

## Near-term priorities

1. **Monthly spending summary** — category-level totals for a given date range (the last missing v1 output).
2. **Improve categorization coverage** — continue working through the Manual Review queue to get rule-based coverage as high as possible before relying on the web UI for edge cases.
3. **Exclusion quality** — review and tighten exclusion rules as new sources are added.

## Target reports

See [VISION.md](VISION.md) for the authoritative list. The immediate next step is the category-level monthly summary command that produces all three views.

- ✅ Imported flow totals
- ✅ Excluded totals and counts by reason
- ✅ Manual review queue for unresolved rows
- ⬜ **Category-level monthly summary** (next priority)

## Category model

- Housing
- Groceries
- Dining
- Transport
- Subscriptions
- Shopping
- Entertainment
- Laundry
- Travel
- Healthcare
- Giving
- Fees / Finance Charges
- Other
- Manual Review (sentinel — not a real category)

## Exclusion reasons

- `internal_transfer`
- `credit_card_payment`
- `wise_transfer`
- `investment_transfer`
- `savings_transfer`
- `refund`
- `reimbursement`
- `duplicate`
- `opening_balance`
- `unknown_non_spend`

## Not in scope

- Cloud sync
- Plaid integration
- Envelope budgeting
- Forecasting engine
- Double-entry accounting
- Investment performance tracking
- Tax reporting

## Possible later extensions

- Merchant normalization dictionary
- Multi-currency FX normalization (convert all to one currency for summary)
- Recurring subscription detection
- Monthly trend reports (month-over-month comparison)
- Beancount or Ledger export
- Reconciliation against statement balances
- Promote web UI manual decisions back to `rules.yml` automatically
