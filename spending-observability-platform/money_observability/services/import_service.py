"""
Import service utilities.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
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
    source_index = next((i for i, part in enumerate(parts) if part in SUPPORTED_SOURCES), None)
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
