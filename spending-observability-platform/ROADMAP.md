# Roadmap

## Near-term priorities

1. Keep exclusion quality high using explicit rules and verification checks.
2. Add category assignment rules with a manual-review fallback.
3. Improve reporting outputs for monthly spending review.

## Planned analysis outputs

- Imported flow totals
- Excluded totals and counts by reason
- True spending totals
- Category-level spend summary
- Fixed vs variable spending view
- Manual review queue for unresolved rows

## Category model (initial)

- Housing
- Groceries
- Dining
- Transport
- Subscriptions
- Shopping
- Travel
- Healthcare
- Children / Family
- Giving
- Fees / Finance Charges
- Other
- Manual Review

## Exclusion reasons (initial)

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

## Not in v1

- Web app
- Cloud sync
- Plaid integration
- Envelope budgeting
- Forecasting engine
- Double-entry accounting
- Investment performance tracking
- Tax reporting

## Possible later extensions

- Merchant normalization dictionary
- Multi-currency FX normalization
- Recurring subscription detection
- Monthly trend reports
- Beancount or Ledger export
- Reconciliation against statement balances
