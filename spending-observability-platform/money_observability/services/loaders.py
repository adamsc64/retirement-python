"""
Source-specific CSV loaders.

Each loader is responsible for:
  - validating that a file has the expected headers
  - parsing rows into a normalised list of dicts

parse_rows return value
-----------------------
Each dict in the returned list contains:

  posted_date     : datetime.date
  description_raw : str
  amount          : Decimal  — signed; negative = money out, positive = money in
  currency        : str      — ISO 4217 code, e.g. "USD"
  direction       : str      — "debit" or "credit"

Loaders that do not yet have real implementations raise NotImplementedError from
validate_headers / parse_rows.
"""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


class LoaderError(Exception):
    """Raised when a loader cannot process a file."""


class BaseLoader:
    source_institution: str = ""

    def validate_headers(self, headers: list[str]) -> None:
        """Verify that *headers* match the expected columns for this source.

        Raises LoaderError if validation fails.
        """
        raise NotImplementedError

    def parse_rows(self, file_path: Path) -> list[dict]:
        """Parse *file_path* and return a list of normalised row dicts."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Citi
# ---------------------------------------------------------------------------

class CitiLoader(BaseLoader):
    """Loader for Citi credit-card and checking-account exports.

    Citi produces two subtly different CSV formats:

    Credit card (e.g. citi-3135.CSV, citi-6518.CSV)
      Headers : Status, Date, Description, Debit, Credit
      Date    : MM/DD/YYYY
      Debit   : positive charge amount  → amount = -Debit
      Credit  : stored as a negative number for payments/refunds
                → amount = -Credit  (so payments become positive = money in)

    Checking (e.g. CHK_5296_CURRENT_VIEW.csv)
      Headers : Status, Date, Description, Debit, Credit  (+ trailing empty col)
      Date    : MM-DD-YYYY
      Debit   : positive outgoing amount → amount = -Debit
      Credit  : positive incoming amount → amount = +Credit

    Sub-format is detected from the filename: files whose stem starts with
    "CHK" (case-insensitive) are treated as checking; all others as credit card.
    """

    source_institution = "citi"
    EXPECTED_HEADERS = {"Status", "Date", "Description", "Debit", "Credit"}

    # ------------------------------------------------------------------ helpers

    def _is_checking(self, file_path: Path) -> bool:
        return file_path.stem.upper().startswith("CHK")

    def _parse_date(self, value: str, fmt: str, file_path: Path) -> datetime.date:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError as exc:
            raise LoaderError(
                f"Cannot parse date '{value}' in {file_path.name}: {exc}"
            ) from exc

    def _parse_decimal(self, value: str, file_path: Path) -> Decimal:
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise LoaderError(
                f"Cannot parse amount '{value}' in {file_path.name}: {exc}"
            ) from exc

    # --------------------------------------------------------- public interface

    def validate_headers(self, headers: list[str]) -> None:
        """Raise LoaderError if any expected header is missing.

        Tolerates a trailing empty column produced by some Citi exports.
        """
        actual = {h for h in headers if h}
        missing = self.EXPECTED_HEADERS - actual
        if missing:
            raise LoaderError(
                f"Citi CSV is missing expected headers: {sorted(missing)}"
            )

    def parse_rows(self, file_path: Path) -> list[dict]:
        """Return a list of normalised row dicts for *file_path*."""
        is_checking = self._is_checking(file_path)
        date_fmt = "%m-%d-%Y" if is_checking else "%m/%d/%Y"
        rows: list[dict] = []

        with open(file_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            self.validate_headers(reader.fieldnames or [])

            for raw in reader:
                debit_raw = (raw.get("Debit") or "").strip()
                credit_raw = (raw.get("Credit") or "").strip()

                if debit_raw:
                    amount = -self._parse_decimal(debit_raw, file_path)
                    direction = "debit"
                elif credit_raw:
                    credit_val = self._parse_decimal(credit_raw, file_path)
                    if is_checking:
                        # Checking credits are positive in the file (money in)
                        amount = credit_val
                    else:
                        # Credit-card credits are negative in the file (payments /
                        # refunds); negate so money-in becomes positive.
                        amount = -credit_val
                    direction = "credit"
                else:
                    # Row has neither debit nor credit; skip silently.
                    continue

                posted_date = self._parse_date(
                    raw["Date"].strip(), date_fmt, file_path
                )

                rows.append(
                    {
                        "posted_date": posted_date,
                        "description_raw": raw["Description"].strip(),
                        "amount": amount,
                        "currency": "USD",
                        "direction": direction,
                    }
                )

        return rows


class HSBCLoader(BaseLoader):
    source_institution = "hsbc"

    def validate_headers(self, headers: list[str]) -> None:
        raise NotImplementedError

    def parse_rows(self, file_path: Path) -> list[dict]:
        raise NotImplementedError


class AmexLoader(BaseLoader):
    source_institution = "amex"

    def validate_headers(self, headers: list[str]) -> None:
        raise NotImplementedError

    def parse_rows(self, file_path: Path) -> list[dict]:
        raise NotImplementedError


class WiseLoader(BaseLoader):
    source_institution = "wise"

    def validate_headers(self, headers: list[str]) -> None:
        raise NotImplementedError

    def parse_rows(self, file_path: Path) -> list[dict]:
        raise NotImplementedError


LOADER_REGISTRY: dict[str, type[BaseLoader]] = {
    "citi": CitiLoader,
    "hsbc": HSBCLoader,
    "amex": AmexLoader,
    "wise": WiseLoader,
}
