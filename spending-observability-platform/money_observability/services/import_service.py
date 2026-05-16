"""
Import service utilities.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

SUPPORTED_SOURCES = frozenset({"citi", "hsbc", "amex", "wise"})


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
    parent_name = path.parent.name
    if parent_name not in SUPPORTED_SOURCES:
        raise ValueError(
            f"Cannot infer source from directory '{parent_name}'. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_SOURCES))}."
        )
    return parent_name
