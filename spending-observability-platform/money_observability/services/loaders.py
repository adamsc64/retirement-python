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

    def __init__(self, *, default_currency: str = "USD"):
        self.default_currency = default_currency

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
                        "currency": self.default_currency,
                        "direction": direction,
                    }
                )

        return rows


class HSBCLoader(BaseLoader):
    source_institution = "hsbc"

    def validate_headers(self, headers: list[str]) -> None:
        # HSBC sample exports currently have no header row.
        if headers:
            raise LoaderError("HSBC CSV expected no header row")

    def parse_rows(self, file_path: Path) -> list[dict]:
        rows: list[dict] = []
        date_formats = ["%d/%m/%Y", "%m/%d/%Y"]
        if self.default_currency != "GBP":
            date_formats = ["%m/%d/%Y", "%d/%m/%Y"]

        with open(file_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            for raw in reader:
                if len(raw) < 3:
                    continue
                date_raw = raw[0].strip()
                description = raw[1].strip()
                amount_raw = raw[2].replace(",", "").strip()
                if not (date_raw or description or amount_raw):
                    continue

                posted_date = None
                for fmt in date_formats:
                    try:
                        posted_date = datetime.strptime(date_raw, fmt).date()
                        break
                    except ValueError:
                        continue
                if posted_date is None:
                    raise LoaderError(
                        f"Cannot parse date '{date_raw}' in {file_path.name}"
                    )

                try:
                    amount = Decimal(amount_raw)
                except InvalidOperation as exc:
                    raise LoaderError(
                        f"Cannot parse amount '{amount_raw}' in {file_path.name}: {exc}"
                    ) from exc

                rows.append(
                    {
                        "posted_date": posted_date,
                        "description_raw": description,
                        "amount": amount,
                        "currency": self.default_currency,
                        "direction": "credit" if amount > 0 else "debit",
                    }
                )

        return rows


class AmexLoader(BaseLoader):
    source_institution = "amex"
    EXPECTED_HEADERS = {"Date", "Description", "Amount"}

    def validate_headers(self, headers: list[str]) -> None:
        actual = {h for h in headers if h}
        missing = self.EXPECTED_HEADERS - actual
        if missing:
            raise LoaderError(
                f"Amex CSV is missing expected headers: {sorted(missing)}"
            )

    def parse_rows(self, file_path: Path) -> list[dict]:
        rows: list[dict] = []

        with open(file_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            self.validate_headers(reader.fieldnames or [])

            for raw in reader:
                date_raw = (raw.get("Date") or "").strip()
                description = (raw.get("Description") or "").strip()
                amount_raw = (raw.get("Amount") or "").replace(",", "").strip()
                if not (date_raw or description or amount_raw):
                    continue

                try:
                    posted_date = datetime.strptime(date_raw, "%d/%m/%Y").date()
                except ValueError as exc:
                    raise LoaderError(
                        f"Cannot parse date '{date_raw}' in {file_path.name}: {exc}"
                    ) from exc

                try:
                    amount = -Decimal(amount_raw)
                except InvalidOperation as exc:
                    raise LoaderError(
                        f"Cannot parse amount '{amount_raw}' in {file_path.name}: {exc}"
                    ) from exc

                rows.append(
                    {
                        "posted_date": posted_date,
                        "description_raw": description,
                        "amount": amount,
                        "currency": self.default_currency,
                        "direction": "credit" if amount > 0 else "debit",
                    }
                )

        return rows


class WiseLoader(BaseLoader):
    source_institution = "wise"
    EXPECTED_HEADERS = {
        "ID",
        "Status",
        "Direction",
        "Created on",
        "Source amount (after fees)",
        "Source currency",
        "Target name",
        "Reference",
    }

    def validate_headers(self, headers: list[str]) -> None:
        actual = {h for h in headers if h}
        missing = self.EXPECTED_HEADERS - actual
        if missing:
            raise LoaderError(
                f"Wise CSV is missing expected headers: {sorted(missing)}"
            )

    def parse_rows(self, file_path: Path) -> list[dict]:
        rows: list[dict] = []

        with open(file_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            self.validate_headers(reader.fieldnames or [])

            for raw in reader:
                created_on = (raw.get("Created on") or "").strip()
                amount_raw = (raw.get("Source amount (after fees)") or "").replace(",", "").strip()
                direction_raw = (raw.get("Direction") or "").strip().upper()

                if not (created_on and amount_raw and direction_raw):
                    continue

                try:
                    posted_date = datetime.strptime(created_on, "%Y-%m-%d %H:%M:%S").date()
                except ValueError as exc:
                    raise LoaderError(
                        f"Cannot parse Created on '{created_on}' in {file_path.name}: {exc}"
                    ) from exc

                try:
                    amount_value = Decimal(amount_raw)
                except InvalidOperation as exc:
                    raise LoaderError(
                        f"Cannot parse amount '{amount_raw}' in {file_path.name}: {exc}"
                    ) from exc

                if direction_raw == "OUT":
                    amount = -abs(amount_value)
                    direction = "debit"
                    counterparty = (raw.get("Target name") or "").strip() or (raw.get("Source name") or "").strip()
                elif direction_raw == "IN":
                    amount = abs(amount_value)
                    direction = "credit"
                    counterparty = (raw.get("Source name") or "").strip() or (raw.get("Target name") or "").strip()
                else:
                    raise LoaderError(
                        f"Unknown Direction '{direction_raw}' in {file_path.name}"
                    )

                currency = (raw.get("Source currency") or "").strip().upper() or self.default_currency
                description = (
                    (raw.get("Reference") or "").strip()
                    or counterparty
                    or (raw.get("ID") or "").strip()
                )

                rows.append(
                    {
                        "source_native_id": (raw.get("ID") or "").strip(),
                        "posted_date": posted_date,
                        "description_raw": description,
                        "amount": amount,
                        "currency": currency,
                        "direction": direction,
                    }
                )

        return rows


LOADER_REGISTRY: dict[str, type[BaseLoader]] = {
    "citi": CitiLoader,
    "hsbc": HSBCLoader,
    "amex": AmexLoader,
    "wise": WiseLoader,
}
