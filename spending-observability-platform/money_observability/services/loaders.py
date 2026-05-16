"""
Source-specific CSV loaders.

Each loader is responsible for:
  - validating that a file has the expected headers
  - parsing rows into a normalised list of dicts

Phase 1: stubs only — validate_headers and parse_rows are not yet implemented.
"""

from __future__ import annotations

from pathlib import Path


class LoaderError(Exception):
    """Raised when a loader cannot process a file."""


class BaseLoader:
    source_institution: str = ""

    def validate_headers(self, headers: list[str]) -> None:
        """Verify that *headers* match the expected columns for this source.

        Raises LoaderError if validation fails.
        Not yet implemented.
        """
        raise NotImplementedError

    def parse_rows(self, file_path: Path) -> list[dict]:
        """Parse *file_path* and return a list of normalised row dicts.

        Not yet implemented.
        """
        raise NotImplementedError


class CitiLoader(BaseLoader):
    source_institution = "citi"

    def validate_headers(self, headers: list[str]) -> None:
        raise NotImplementedError

    def parse_rows(self, file_path: Path) -> list[dict]:
        raise NotImplementedError


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
