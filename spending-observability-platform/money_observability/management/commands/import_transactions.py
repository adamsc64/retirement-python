"""Management command: import_transactions

Phase 1: discover CSV files and print what would be imported.
Parsing is not yet implemented.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from money_observability.models import ImportBatch, RawTransaction
from money_observability.services.import_service import (
    compute_file_hash,
    infer_source_metadata_from_path,
)
from money_observability.services.loaders import LOADER_REGISTRY, LoaderError


class Command(BaseCommand):
    help = "Find CSV files under a directory and import supported sources."

    def add_arguments(self, parser):
        parser.add_argument(
            "data_dir",
            type=str,
            help="Root directory to search for CSV files (e.g. data/raw).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist imports to the database. Without this flag, command runs in dry-run mode.",
        )

    def _to_jsonable(self, value):
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    def _row_to_json(self, row: dict) -> dict:
        return {key: self._to_jsonable(value) for key, value in row.items()}

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        apply = options["apply"]
        if not data_dir.exists():
            raise CommandError(f"Directory not found: {data_dir}")
        if not data_dir.is_dir():
            raise CommandError(f"Not a directory: {data_dir}")

        csv_files = sorted(data_dir.rglob("*.csv")) + sorted(data_dir.rglob("*.CSV"))
        # Deduplicate (rglob is case-sensitive on Linux but may overlap on macOS)
        seen: set[Path] = set()
        unique_files: list[Path] = []
        for f in csv_files:
            resolved = f.resolve()
            if resolved not in seen:
                seen.add(resolved)
                unique_files.append(f)

        if not unique_files:
            self.stdout.write(self.style.WARNING(f"No CSV files found under {data_dir}"))
            return

        mode = "APPLY" if apply else "DRY-RUN"
        self.stdout.write(f"Mode: {mode}")
        self.stdout.write(f"Found {len(unique_files)} CSV file(s) under {data_dir}:\n")

        imported_count = 0
        skipped_count = 0

        for csv_path in unique_files:
            try:
                source_meta = infer_source_metadata_from_path(csv_path)
                source = source_meta.source_institution
                profile = source_meta.source_profile
                loader_cls = LOADER_REGISTRY.get(source)
                if loader_cls is None:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [SKIP  ]  {csv_path}  (No loader registered for source '{source}')"
                        )
                    )
                    continue

                file_hash = compute_file_hash(csv_path)
                if ImportBatch.objects.filter(file_hash=file_hash).exists():
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [SKIP  ]  {csv_path}  (Already imported: matching file hash)"
                        )
                    )
                    continue

                loader = loader_cls(default_currency=source_meta.default_currency)
                rows = loader.parse_rows(csv_path)

                if not apply:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [{source:6s}/{profile}]  {csv_path}  (would import {len(rows)} rows)"
                        )
                    )
                    continue

                with transaction.atomic():
                    batch = ImportBatch.objects.create(
                        account=None,
                        source_file=str(csv_path),
                        source_institution=source,
                        source_profile=profile,
                        file_hash=file_hash,
                        row_count=len(rows),
                    )
                    raw_rows = [
                        RawTransaction(
                            import_batch=batch,
                            row_number=index,
                            raw_json=self._row_to_json(row),
                        )
                        for index, row in enumerate(rows, start=1)
                    ]
                    RawTransaction.objects.bulk_create(raw_rows)

                imported_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [{source:6s}/{profile}]  {csv_path}  (imported {len(rows)} rows)"
                    )
                )
            except (LoaderError, NotImplementedError) as exc:
                skipped_count += 1
                reason = str(exc) or exc.__class__.__name__
                self.stdout.write(
                    self.style.WARNING(
                        f"  [SKIP  ]  {csv_path}  (Loader not ready: {reason})"
                    )
                )
            except ValueError as exc:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f"  [SKIP  ]  {csv_path}  ({exc})"))

        self.stdout.write("")
        self.stdout.write(f"Summary: imported files={imported_count}, skipped files={skipped_count}")
        if not apply:
            self.stdout.write(
                self.style.NOTICE("Dry run complete. Use --apply to persist imports.")
            )
