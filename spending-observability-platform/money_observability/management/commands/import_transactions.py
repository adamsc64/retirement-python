"""Management command: import_transactions

Phase 1: discover CSV files and print what would be imported.
Parsing is not yet implemented.
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from money_observability.services.import_service import infer_source_from_path


class Command(BaseCommand):
    help = "Find CSV files under a directory and (in later phases) import them."

    def add_arguments(self, parser):
        parser.add_argument(
            "data_dir",
            type=str,
            help="Root directory to search for CSV files (e.g. data/raw).",
        )

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
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

        self.stdout.write(f"Found {len(unique_files)} CSV file(s) under {data_dir}:\n")
        for csv_path in unique_files:
            try:
                source = infer_source_from_path(csv_path)
                label = self.style.SUCCESS(f"  [{source:6s}]  {csv_path}")
            except ValueError as exc:
                label = self.style.WARNING(f"  [SKIP  ]  {csv_path}  ({exc})")
            self.stdout.write(label)

        self.stdout.write(
            self.style.NOTICE("\nPhase 1: dry run only — no data has been imported.")
        )
