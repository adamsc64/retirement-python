# Personal Finance Observability Platform

Local-first Django pipeline for importing account/card CSVs, preserving raw records, and marking non-spend transactions with explicit exclusion rules.

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
- Duplicate imports are prevented by file hash.
- Rule-based exclusions are available via `apply_exclusions`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

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

## Identity model

Canonical identity separates source provenance from semantic matching:

- `source_row_key` (unique): one imported source row
- `event_fingerprint` (non-unique): semantic candidate matching key

This prevents accidental collapsing of legitimate repeated purchases.

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

