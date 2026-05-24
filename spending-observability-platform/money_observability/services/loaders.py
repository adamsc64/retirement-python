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
import io
import re
from dataclasses import dataclass, field
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
                category = (raw.get("Category") or "").strip()
                if category:
                    description = f"{description} | {category}"

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


# ---------------------------------------------------------------------------
# Universal column map
#
# Institution-agnostic flat mapping: every known raw column name → the
# normalised Transaction field it feeds.  Used when the institution is not
# known upfront (e.g. web upload).
#
# Notes on ambiguous columns:
#   "Date"   — used by both Citi (MM/DD/YYYY or MM-DD-YYYY) and Amex
#               (DD/MM/YYYY); date-format detection must be applied at
#               parse time.
#   "Debit" / "Credit" — Citi splits a single amount across two columns;
#               sign convention differs between credit-card and checking
#               sub-formats.
#   "Status" — present in Citi and Wise exports; carries no transaction
#               semantics used by any current loader.
#   "Category" — Wise appends this to description_raw rather than storing
#               it as a standalone field.
# ---------------------------------------------------------------------------

UNIVERSAL_COLUMN_MAP: dict[str, str | None] = {
    # posted_date
    "Date": "posted_date",            # citi (MM/DD/YYYY | MM-DD-YYYY), amex (DD/MM/YYYY)
    "Created on": "posted_date",      # wise (YYYY-MM-DD HH:MM:SS)

    # description_raw
    "Description": "description_raw", # citi, amex
    "Reference": "description_raw",   # wise — primary description
    "Target name": "description_raw", # wise — counterparty on OUT
    "Source name": "description_raw", # wise — counterparty on IN

    # amount  (sign conventions vary; loader must handle)
    "Amount": "amount",                        # amex: positive = spend, negated
    "Debit": "amount",                         # citi: positive = spend, negated
    "Credit": "amount",                        # citi: sign logic differs by sub-format
    "Source amount (after fees)": "amount",    # wise: sign set by Direction column

    # currency
    "Source currency": "currency",    # wise; all other loaders use a default

    # direction
    "Direction": "direction",         # wise: "OUT" → debit, "IN" → credit

    # source_native_id
    "ID": "source_native_id",         # wise; also used as last-resort description

    # consumed by loader logic but not stored as a standalone field
    "Status": None,                   # citi, wise — ignored
    "Category": None,                 # wise — appended to description_raw
}

# ---------------------------------------------------------------------------
# GenericLoader
#
# Institution-agnostic parser for web-uploaded CSVs.  Does not rely on
# filenames.  Uses UNIVERSAL_COLUMN_MAP to validate that the file's headers
# can satisfy the three required output fields; attempts to identify the
# source institution by matching against each loader's EXPECTED_HEADERS.
# ---------------------------------------------------------------------------

# HSBC exports have no header row.  We detect them by inspecting the first
# non-empty data row and then prepend a synthetic header so the rest of the
# pipeline can treat the file uniformly.
_HSBC_DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
_HSBC_AMOUNT_RE = re.compile(r'^-?[\d,]+\.\d{2}$')
_HSBC_SYNTHETIC_HEADER = "Date,Description,Amount"

@dataclass
class ColumnMapping:
    """Which raw CSV columns feed each normalised Transaction field.

    Each attribute holds the list of raw column names that map to that field.
    Required fields (posted_date, amount, description_raw) are always
    non-empty; optional fields default to an empty list.
    """
    posted_date: list[str] = field(default_factory=list)
    amount: list[str] = field(default_factory=list)
    description_raw: list[str] = field(default_factory=list)
    currency: list[str] = field(default_factory=list)
    direction: list[str] = field(default_factory=list)
    source_native_id: list[str] = field(default_factory=list)


@dataclass
class SniffResult:
    """Result of GenericLoader.sniff()."""
    mapping: ColumnMapping
    # Number of data rows in the file (header excluded).
    row_count: int
    # Detected source institution (e.g. "citi", "wise"), or None if unknown.
    institution: str | None


class GenericLoader:
    """Validate and sniff an uploaded CSV without knowing the institution."""

    # Fields that must be derivable from the file's headers.
    REQUIRED_FIELDS = {"posted_date", "amount", "description_raw"}

    @staticmethod
    def _looks_like_hsbc(text: str) -> bool:
        """Return True if *text* looks like an HSBC headerless CSV.

        Detection rules (all must hold for the first non-empty line):
          - at least 3 comma-separated fields
          - field 0 matches DD/MM/YYYY
          - field 2 is a monetary value (optional minus, digits/commas, decimal)
        """
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = next(csv.reader([line]))
            except StopIteration:
                continue
            if len(row) < 3:
                return False
            return (
                _HSBC_DATE_RE.match(row[0].strip()) is not None
                and _HSBC_AMOUNT_RE.match(row[2].strip()) is not None
            )
        return False

    def detect_mapping(self, headers: list[str]) -> ColumnMapping:
        """Return a ColumnMapping for *headers*.

        Raises LoaderError if any required field cannot be covered.
        """
        grouped: dict[str, list[str]] = {}
        for col in headers:
            norm = UNIVERSAL_COLUMN_MAP.get(col)
            if norm is not None:
                grouped.setdefault(norm, []).append(col)
        covered = set(grouped)
        missing = self.REQUIRED_FIELDS - covered
        if missing:
            raise LoaderError(
                f"Cannot map required fields {sorted(missing)} from "
                f"columns: {[h for h in headers if h]}"
            )
        return ColumnMapping(
            posted_date=grouped.get("posted_date", []),
            amount=grouped.get("amount", []),
            description_raw=grouped.get("description_raw", []),
            currency=grouped.get("currency", []),
            direction=grouped.get("direction", []),
            source_native_id=grouped.get("source_native_id", []),
        )

    def detect_institution(self, headers: list[str]) -> str | None:
        """Return the source_institution name if headers match a known loader."""
        header_set = {h for h in headers if h}
        best: tuple[int, str] | None = None
        for name, loader_cls in LOADER_REGISTRY.items():
            expected = getattr(loader_cls, "EXPECTED_HEADERS", None)
            if expected is None:
                continue
            overlap = len(header_set & expected)
            if overlap == len(expected):  # all required headers present
                if best is None or overlap > best[0]:
                    best = (overlap, name)
        return best[1] if best else None

    def sniff(self, fileobj) -> SniffResult:
        """Read headers from *fileobj*, validate mapping, count rows.

        Returns a SniffResult with the detected column mapping, row count,
        and institution name (or None if unrecognized).

        Raises LoaderError on unrecognized or incomplete headers.
        No row-level parsing is performed.
        """
        text = fileobj.read().decode("utf-8-sig")

        if self._looks_like_hsbc(text):
            # Prepend a synthetic header so DictReader can process the file
            # uniformly.  Institution is set directly — we can't use header
            # fingerprinting because the synthetic headers (Date, Description,
            # Amount) are identical to Amex's.
            text = _HSBC_SYNTHETIC_HEADER + "\n" + text
            forced_institution: str | None = "hsbc"
        else:
            forced_institution = None

        reader = csv.DictReader(io.StringIO(text))
        headers = list(reader.fieldnames or [])
        mapping = self.detect_mapping(headers)
        row_count = sum(1 for _ in reader)
        institution = forced_institution if forced_institution is not None else self.detect_institution(headers)
        return SniffResult(mapping=mapping, row_count=row_count, institution=institution)

