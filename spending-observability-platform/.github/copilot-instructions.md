# Copilot Instructions

## Python / Django

- Always use `.venv/bin/python` to run Python in this project — `python` is not on PATH in this environment.
- Run Django management commands as: `.venv/bin/python manage.py <command>`
- Run one-off DB queries as: `.venv/bin/python manage.py shell -c "<code>"`

## Project conventions

- Categories are defined in `money_observability/services/categories.py` — add new ones there.
- Exclusion and category rules live in `rules/rules.yml` and are applied via `apply_exclusions` / `apply_categories` management commands.
- Annual (once-a-year) expenses are tagged with `category="Annual"` and are managed via `/annual/`.
- FX rates (USD/GBP/EUR) are hardcoded in `views.py` as `FX_TO_USD` — update there when rates change.
- The DB is SQLite at `db/finance.sqlite3`.
