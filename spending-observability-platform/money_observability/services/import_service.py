"""
Import service utilities.
"""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

SUPPORTED_SOURCES = frozenset({"citi", "hsbc", "amex", "wise"})
SUPPORTED_CURRENCIES = frozenset({"USD", "GBP", "EUR"})


@dataclass(frozen=True)
class SourceMetadata:
    source_institution: str
    source_profile: str
    default_currency: str


def compute_file_hash(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at *path*."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def infer_source_from_path(path: Path) -> str:
    """Return the source institution name inferred from *path*'s parent directory.

    The parent directory name must be one of: citi, hsbc, amex, wise.

    Raises ValueError for any other parent directory name.
    """
    return infer_source_metadata_from_path(path).source_institution


def infer_source_metadata_from_path(path: Path) -> SourceMetadata:
    """Infer source institution/profile/currency defaults from path.

    Expected directory shapes:
      data/raw/<source>/<file>.csv          -> default currency USD
      data/raw/<source>/<currency>/<file>   -> use that currency

    where <source> is one of: citi, hsbc, amex, wise
    and <currency> is one of: usd, gbp, eur (case-insensitive).
    """
    parts = [p.lower() for p in path.parts]
    source_index = next(
        (i for i, part in enumerate(parts) if part in SUPPORTED_SOURCES), None
    )
    if source_index is None:
        raise ValueError(
            f"Cannot infer source from path '{path}'. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_SOURCES))}."
        )
    source = parts[source_index]

    default_currency = "USD"
    if source_index + 1 < len(parts) - 1:
        currency_candidate = parts[source_index + 1].upper()
        if currency_candidate in SUPPORTED_CURRENCIES:
            default_currency = currency_candidate

    profile = f"{source}_{default_currency.lower()}"

    return SourceMetadata(
        source_institution=source,
        source_profile=profile,
        default_currency=default_currency,
    )


# ---------------------------------------------------------------------------
# Web-upload import
# ---------------------------------------------------------------------------


@dataclass
class ImportSummary:
    """Result of import_uploaded_bytes()."""

    institution: str
    imported: int  # new Transaction rows written
    duplicate: int  # rows skipped (source_row_key already exists)


# Default currency to assume when institution is known but no path hint exists.
_UPLOAD_DEFAULT_CURRENCY = {
    "citi": "USD",
    "hsbc": "GBP",
    "amex": "GBP",
    "wise": "GBP",
}


def _source_row_key(file_hash: str, row_number: int) -> str:
    return hashlib.sha256(f"{file_hash}:{row_number}".encode()).hexdigest()


def _event_fingerprint(account_identifier: str, row: dict) -> str:
    parts = [
        account_identifier,
        row["posted_date"].isoformat(),
        row.get("description_raw", "").strip().lower(),
        str(row["amount"]),
        row.get("currency", "").upper(),
        row.get("direction", "").lower(),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def create_transactions_from_rows(
    batch, account, rows: list[dict], default_currency: str
) -> int:
    """Create Transaction objects from parsed rows, skipping semantic duplicates.

    Deduplication logic:
    1. Skip rows already present in this specific file hash (via source_row_key).
    2. Skip rows that semantically match transactions in OTHER batches
       (via event_fingerprint).

    Returns the number of new transactions actually written to the DB.
    """
    from money_observability.models import Transaction

    tx_objs = [
        Transaction(
            source_row_key=_source_row_key(file_hash=batch.file_hash, row_number=i),
            event_fingerprint=_event_fingerprint(
                account_identifier=account.account_identifier,
                row=row,
            ),
            source_native_id=str(row.get("source_native_id", "")).strip(),
            import_batch=batch,
            account=account,
            source_file=batch.source_file,
            source_institution=batch.source_institution,
            posted_date=row["posted_date"],
            description_raw=row.get("description_raw", ""),
            description_clean=row.get("description_raw", ""),
            amount=row["amount"],
            currency=row.get("currency", default_currency),
            direction=row["direction"],
        )
        for i, row in enumerate(rows, start=1)
    ]

    # Cross-batch overlap check: skip individual transactions whose
    # fingerprint already exists from a different import batch.
    new_fingerprints = [tx.event_fingerprint for tx in tx_objs]
    existing_fingerprints = set(
        Transaction.objects.filter(event_fingerprint__in=new_fingerprints)
        .exclude(import_batch=batch)
        .values_list("event_fingerprint", flat=True)
    )

    if existing_fingerprints:
        tx_objs = [
            tx for tx in tx_objs if tx.event_fingerprint not in existing_fingerprints
        ]

    before = Transaction.objects.filter(import_batch=batch).count()
    Transaction.objects.bulk_create(tx_objs, ignore_conflicts=True)
    after = Transaction.objects.filter(import_batch=batch).count()

    return after - before


def import_uploaded_bytes(raw_bytes: bytes, filename: str) -> ImportSummary:
    """Parse *raw_bytes* as a CSV, detect the institution, and save transactions.

    Uses get_or_create on ImportBatch keyed by file hash, so re-uploading the
    same file is idempotent: existing transactions are silently skipped via
    ignore_conflicts rather than raising an error.

    Returns an ImportSummary with the institution name, number of new
    transactions written, and number of duplicates skipped.

    Raises LoaderError if the file cannot be identified or parsed.
    """
    from django.db import transaction as db_transaction
    from money_observability.models import Account, ImportBatch
    from .loaders import GenericLoader, LoaderError, LOADER_REGISTRY

    sniff_result = GenericLoader().sniff(io.BytesIO(raw_bytes))
    institution = sniff_result.institution

    if institution is None:
        institution = "generic"
        default_currency = "USD"
        profile = "generic_usd"
        from .loaders import GenericAILoader

        loader = GenericAILoader(
            mapping=sniff_result.mapping, default_currency=default_currency
        )
    else:
        default_currency = _UPLOAD_DEFAULT_CURRENCY.get(institution, "USD")
        profile = f"{institution}_{default_currency.lower()}"
        loader_cls = LOADER_REGISTRY.get(institution)
        if loader_cls is None:
            raise LoaderError(f"No loader registered for '{institution}'")
        loader = loader_cls(default_currency=default_currency)

    file_hash = hashlib.sha256(raw_bytes).hexdigest()

    # Write to a temp file because all parse_rows() methods take a Path.
    tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(tmp_fd, "wb") as tmp:
            tmp.write(raw_bytes)
        rows = loader.parse_rows(Path(tmp_path_str))
    finally:
        os.unlink(tmp_path_str)

    with db_transaction.atomic():
        account, _ = Account.objects.get_or_create(
            institution=institution,
            account_identifier=profile,
            defaults={
                "name": f"{institution.upper()} {profile.upper()}",
                "currency": default_currency,
            },
        )

        batch, _ = ImportBatch.objects.get_or_create(
            file_hash=file_hash,
            defaults={
                "account": account,
                "source_file": filename,
                "source_institution": institution,
                "source_profile": profile,
                "row_count": len(rows),
            },
        )

        new_count = create_transactions_from_rows(
            batch=batch,
            account=account,
            rows=rows,
            default_currency=default_currency,
        )

    return ImportSummary(
        institution=institution,
        imported=new_count,
        duplicate=len(rows) - new_count,
    )
