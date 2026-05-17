# Personal Finance Observability Platform

Local-first Django pipeline for importing account/card CSVs, preserving raw records, excluding non-spend flows, and categorizing transactions via rules and a keyboard-driven web UI.

## Read this first

- Operational guide: this file
- Vision and principles: [VISION.md](VISION.md)
- Roadmap and future ideas: [ROADMAP.md](ROADMAP.md)

## Current status

- Citi, Amex, HSBC, and Wise loaders are implemented.
- `import_transactions --apply` writes all ingestion layers:
  - `ImportBatch` (file-level audit)
  - `RawTransaction` (source-row capture)
  - `Transaction` (canonical analysis rows)
- Duplicate imports are prevented by file hash; overlapping date-range rows are skipped with a warning.
- Rule-based exclusions via `apply_exclusions`.
- Rule-based categorization via `apply_categories`, with `Manual Review` fallback.
- Web UI at `/` for stats and `/categorize/` for keyboard-driven batch categorization.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # one-time
```

## Running the web UI

```bash
python manage.py runserver
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). The categorization queue is at `/categorize/`.

Key bindings are shown in the status bar at the bottom of the categorization page.

## Data layout

Source account inventory: [Google Sheet](https://docs.google.com/spreadsheets/d/1o2eYO7TNud3fYdDiUWjNSNmFNXc1qBOuD9AeYTJrDYQ/edit?gid=1376229671#gid=1376229671)

Raw files are discovered under `data/raw`.

- Source convention: `data/raw/<source>/...`
- Currency convention: `data/raw/<source>/<currency>/...`
- Missing currency folder defaults to USD.

Examples:

- `data/raw/amex/gbp/...`
- `data/raw/hsbc/gbp/...`
- `data/raw/citi/...`

## Core commands

### Import

Dry run (default):

```bash
python manage.py import_transactions data/raw
```

Persist rows:

```bash
python manage.py import_transactions data/raw --apply
```

### Verify imports

```bash
python manage.py verify
python manage.py verify data/raw/wise/wise.csv
python manage.py verify data/raw/citi data/raw/wise/wise.csv
```

`verify` fails when counts do not match, imports are missing, or parser errors occur.

### Apply exclusions

```bash
python manage.py apply_exclusions
python manage.py apply_exclusions --dry-run
python manage.py apply_exclusions --source citi --source wise
python manage.py apply_exclusions --rules rules/rules.yml
```

Behavior:

- first-match-wins
- idempotent on re-run
- transactions are never deleted, only flagged

### Apply categories

```bash
python manage.py apply_categories
python manage.py apply_categories --dry-run
python manage.py apply_categories --rules rules/rules.yml
```

Transactions that match no rule are set to `Manual Review`. Re-running is idempotent.

### Review uncategorized transactions

```bash
python manage.py uncategorized_top_spend
python manage.py uncategorized_top_spend --sort count
python manage.py uncategorized_top_spend --filter coffee --limit 20
```

Shows the most expensive unresolved debit transactions grouped by description and currency.

## Rule format

Rules are in `rules/rules.yml`.

```yaml
exclusions:
  - id: credit_card_payment
    reason: credit_card_payment
    match:
      description_contains:
        - payment thank you
        - autopay
```

## Sign convention

```text
negative amount = money leaving the account
positive amount = money entering the account
```

