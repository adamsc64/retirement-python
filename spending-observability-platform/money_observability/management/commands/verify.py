"""Management command: verify

Verifies that ingested data matches current loader parsing results.
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from money_observability.models import ImportBatch, RawTransaction
from money_observability.services.import_service import infer_source_metadata_from_path
from money_observability.services.loaders import LOADER_REGISTRY, LoaderError


class Command(BaseCommand):
    help = "Verify imported row counts against current parser output."

    def add_arguments(self, parser):
        parser.add_argument(
            "paths",
            nargs="*",
            default=["data/raw"],
            help="CSV files and/or directories to verify (default: data/raw).",
        )

    def handle(self, *args, **options):
        targets = [Path(p) for p in options.get("paths") or ["data/raw"]]
        csv_files: list[Path] = []

        for target in targets:
            if not target.exists():
                raise CommandError(f"Path not found: {target}")
            if target.is_file():
                if target.suffix.lower() != ".csv":
                    raise CommandError(f"Not a CSV file: {target}")
                csv_files.append(target)
                continue

            if target.is_dir():
                csv_files.extend(sorted(target.rglob("*.csv")))
                csv_files.extend(sorted(target.rglob("*.CSV")))
                continue

            raise CommandError(f"Unsupported path type: {target}")

        scope_label = ", ".join(str(t) for t in targets)
        seen: set[Path] = set()
        unique_files: list[Path] = []
        for f in csv_files:
            resolved = f.resolve()
            if resolved not in seen:
                seen.add(resolved)
                unique_files.append(f)

        if not unique_files:
            self.stdout.write(self.style.WARNING(f"No CSV files found for scope: {scope_label}"))
            return

        expected_total = 0
        imported_total = 0
        raw_total = 0
        ok_count = 0
        issue_count = 0

        self.stdout.write(f"Verifying {len(unique_files)} CSV file(s) under {scope_label}:\n")

        for csv_path in unique_files:
            try:
                source_meta = infer_source_metadata_from_path(csv_path)
                loader_cls = LOADER_REGISTRY.get(source_meta.source_institution)
                if loader_cls is None:
                    issue_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [ISSUE] {csv_path}  (No loader registered for source '{source_meta.source_institution}')"
                        )
                    )
                    continue

                loader = loader_cls(default_currency=source_meta.default_currency)
                parsed_rows = loader.parse_rows(csv_path)
                expected = len(parsed_rows)
                expected_total += expected

                batch = ImportBatch.objects.filter(source_file=str(csv_path)).order_by("-id").first()
                if batch is None:
                    issue_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [ISSUE] {csv_path}  (No ImportBatch found; expected_rows={expected})"
                        )
                    )
                    continue

                imported = batch.row_count
                raw_rows = RawTransaction.objects.filter(import_batch=batch).count()
                imported_total += imported
                raw_total += raw_rows

                if imported == expected and raw_rows == expected:
                    ok_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [OK]    {csv_path}  (expected={expected}, batch={imported}, raw={raw_rows})"
                        )
                    )
                else:
                    issue_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [ISSUE] {csv_path}  (expected={expected}, batch={imported}, raw={raw_rows})"
                        )
                    )
            except (LoaderError, ValueError, NotImplementedError) as exc:
                issue_count += 1
                reason = str(exc) or exc.__class__.__name__
                self.stdout.write(self.style.WARNING(f"  [ISSUE] {csv_path}  ({reason})"))

        self.stdout.write("")
        self.stdout.write(
            f"Summary: ok_files={ok_count}, issues={issue_count}, "
            f"expected_total={expected_total}, batch_total={imported_total}, raw_total={raw_total}"
        )

        if issue_count > 0:
            raise CommandError("Verification failed.")
