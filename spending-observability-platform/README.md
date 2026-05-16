# Personal Finance Observability Platform

A Python-based, local-first pipeline for turning messy bank, credit card, and transfer CSVs into a clean, queryable view of personal spending.

The immediate goal is modest: analyse one month of real spending from 9 April to 9 May.

The longer-term goal is a durable personal finance observability system: raw imports preserved, transactions normalised, transfers excluded, categories applied, and spending made visible through reproducible analysis.

## Why this exists

> What am I actually spending?

Before setting a budget, the first task is to audit reality.

This repository is not initially trying to replace YNAB, Quicken, Actual Budget, Ledger, hledger, or Beancount. It is a small, transparent data pipeline for understanding personal cash flow across multiple accounts and currencies.

## Design principles

### Local first

All data should remain local by default.

No Plaid, no cloud sync, no vendor lock-in, no opaque categorisation engine.

### Raw data is immutable

Source CSVs are never edited in place.

Every imported file should remain available for re-processing.

### Exclusions are first-class

Budget analysis is useless if internal transfers are treated as spending.

The system must explicitly identify and exclude:

- credit card balance payments
- internal account transfers
- Wise currency movements
- investment contributions
- savings movements
- duplicate imports

Each excluded transaction should retain an exclusion reason.

### Categorisation should be explainable

Categories should come from visible rules, not hidden app logic.

A transaction should preserve both:

- the raw bank description
- the normalised merchant/category assigned by the pipeline

## Initial scope

Initial data sources may include:

- US checking accounts
- US credit cards
- UK current accounts
- UK credit cards
- Wise
- HSBC
- Citi
- Amex

Sources: https://docs.google.com/spreadsheets/d/1o2eYO7TNud3fYdDiUWjNSNmFNXc1qBOuD9AeYTJrDYQ/edit?gid=1376229671#gid=1376229671

The first successful output should answer:

1. What was the total imported transaction flow?
2. What was excluded as non-spending?
3. What was true spending?
4. What were the top spending categories?
5. What spending was fixed vs variable?
6. Which transactions still need manual review?

## Proposed architecture

```text
raw CSV files
    ↓
source-specific loaders
    ↓
validated normalized transaction objects
    ↓
SQLite / Django ORM storage
    ↓
later enrichment:
    - exclusions
    - categorization
    ↓
webapp
```

## Next enrichment plan

Near-term enrichment will happen in two steps:

1. Exclusion engine
  - Rule-based marking on canonical `Transaction` rows.
  - Transactions are never deleted; they are flagged with exclusion metadata.
2. Categorization engine
  - Rule-based category assignment using normalized descriptions/merchant mappings.
  - Manual review queue for unresolved rows.

## Canonical transaction model

Every source file should be transformed into this shared schema.

| Field | Description |
|---|---|
| `id` | Database primary key |
| `account` | Linked account/card record |
| `source_institution` | Bank or provider name |
| `source_row_key` | Unique key for one imported source row |
| `event_fingerprint` | Non-unique semantic fingerprint for matching analysis |
| `source_native_id` | Provider-native identifier when available |
| `posted_date` | Transaction posted date |
| `transaction_date` | Transaction date, if available |
| `description_raw` | Raw bank description |
| `description_clean` | Cleaned description |
| `merchant` | Normalised merchant, where known |
| `amount` | Signed transaction amount |
| `currency` | Currency of original transaction |
| `direction` | `inflow` or `outflow` |
| `excluded` | Boolean flag |
| `exclusion_reason` | Reason for exclusion |
| `exclusion_rule_id` | Rule id that excluded this transaction |
| `excluded_at` | Timestamp of exclusion assignment |
| `created_at` | Row creation timestamp |
| `updated_at` | Row last update timestamp |
****
## Spending sign convention

Use the following convention internally:

```text
negative amount = money leaving the account
positive amount = money entering the account
```

For reports, use a positive `spend` column:

```text
spend = abs(amount) when amount < 0 and excluded = false
```

## Categories

Start deliberately small.

Suggested first-pass categories:

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

Avoid creating too many categories early. The first goal is signal, not taxonomy perfection.

## Exclusion reasons

Suggested first-pass exclusion reasons:

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

Excluded transactions should remain in the database. They should not be deleted.

## Pipeline commands

The first version can expose simple scripts.

Example:

```bash
python -m finance_obs.load data/raw --db db/finance.sqlite3
python -m finance_obs.normalize --db db/finance.sqlite3
python -m finance_obs.dedupe --db db/finance.sqlite3
python -m finance_obs.exclude --db db/finance.sqlite3
python -m finance_obs.categorize --db db/finance.sqlite3
python -m finance_obs.report \
  --db db/finance.sqlite3 \
  --start 2026-04-09 \
  --end 2026-05-09 \
  --out reports/monthly_audit_2026-04-09_to_2026-05-09.xlsx
```

A later version can wrap this with a single command:

```bash
finance-obs audit --start 2026-04-09 --end 2026-05-09
```

## Rules

Rules should be easy to read and edit.

A simple YAML file is enough.

```yaml
exclusions:
  - name: credit card payment
    match:
      description_contains:
        - "payment thank you"
        - "autopay"
    reason: credit_card_payment

  - name: wise transfer
    match:
      description_contains:
        - "wise"
        - "transferwise"
    reason: wise_transfer

categories:
  - name: groceries
    category: Groceries
    match:
      description_contains:
        - "tesco"
        - "sainsbury"
        - "waitrose"
        - "whole foods"

  - name: dining
    category: Dining
    match:
      description_contains:
        - "restaurant"
        - "cafe"
        - "pret"
        - "deliveroo"
        - "uber eats"
```

## Manual review flow

Some transactions should not be guessed.

The system should mark them as:

```text
review_required = true
category = Manual Review
```

A manual review export can then be generated:

```bash
finance-obs review --start 2026-04-09 --end 2026-05-09
```

This should output a CSV containing only unresolved rows.

## Reports

The initial monthly report should include:

### Summary

- total imported outflows
- excluded outflows
- true spending
- income/inflows
- net cash flow
- number of transactions requiring review

### Category summary

- spending by category
- percentage of true spending
- transaction count

### Fixed vs variable

- fixed spending
- variable spending
- fixed percentage
- variable percentage

### Exclusions

- excluded amount by reason
- excluded transaction count by reason

### Manual review

- transactions needing review

## What not to build yet

Do not build these in v1:

- web app
- cloud sync
- Plaid integration
- envelope budgeting
- forecasting engine
- double-entry accounting
- investment performance tracking
- tax reporting
- beautiful dashboards

Those may come later. The first task is to make spending observable.

## Future directions

Possible later extensions:

- import from Plaid
- export to Beancount or Ledger
- recurring subscription detection
- merchant normalisation dictionary
- multi-currency FX normalisation
- monthly trend reports
- FIRE baseline spending model
- Actual Budget import/export
- anomaly detection
- Jupyter or Streamlit dashboard
- reconciliation against statement balances

## First milestone

A successful first milestone is:

```text
Given raw CSV exports for 9 April to 9 May,
produce a report that separates real spending from transfers,
summarises spending by category,
and lists ambiguous transactions for manual review.
```

Nothing more is required for v1.

## Phase 1: Django ingestion foundation

A Django project provides the database models, admin interface, and management commands needed to ingest raw CSVs.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Create the database

```bash
python manage.py migrate
```

### Import transactions

```bash
python manage.py import_transactions data/raw
```

Dry run is the default. To persist imports:

```bash
python manage.py import_transactions data/raw --apply
```

Current status:

- Citi, Amex, HSBC, and Wise loaders parse and import rows.
- `import_transactions --apply` now writes all three ingestion layers:
  - `ImportBatch` (file-level audit/provenance)
  - `RawTransaction` (source-row capture)
  - `Transaction` (canonical rows for downstream analysis)
- Currency inference is directory-based (`data/raw/<source>/<currency>/...`), e.g. `amex/gbp` or `hsbc/gbp`; missing currency directory defaults to USD.
- Duplicate imports are prevented by file hash.
- Rule-based exclusions are available through `apply_exclusions` using rules from `rules/rules.yml`.

### Verify imported row counts

Use `verify` to reconcile parser output with stored import data.

```bash
python manage.py verify
python manage.py verify data/raw/wise/wise.csv
python manage.py verify data/raw/citi data/raw/wise/wise.csv
```

`verify` fails when counts do not match, when imports are missing, or when parser/loading errors occur.

### Apply exclusion rules

Run exclusions after import so downstream analytics can ignore known non-spend rows.

```bash
python manage.py apply_exclusions
python manage.py apply_exclusions --dry-run
python manage.py apply_exclusions --source citi --source wise
python manage.py apply_exclusions --rules rules/rules.yml
```

Rules are defined in YAML under `rules/rules.yml`.

Example rule:

```yaml
exclusions:
  - id: credit_card_payment
    reason: credit_card_payment
    match:
      description_contains:
        - payment thank you
        - autopay
```

Rule matching uses first-match-wins semantics. Re-running `apply_exclusions` is idempotent.

### Transaction identity model

The ingestion model separates source-row identity from semantic matching:

- `source_row_key` (unique): provenance identity for one imported source row.
- `event_fingerprint` (non-unique): semantic matching key for overlap/candidate duplicate analysis.

This avoids collapsing legitimate repeated purchases (for example, two same-day coffees with the same amount and merchant).

