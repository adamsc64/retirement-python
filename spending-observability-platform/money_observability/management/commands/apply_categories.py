from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from money_observability.services.category_rules import make_categorizations


class Command(BaseCommand):
    help = "Apply rule-based categories to non-excluded Transaction rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--rules",
            type=str,
            default="rules/rules.yml",
            help="Path to rules YAML file (default: rules/rules.yml).",
        )

    def handle(self, *args, **options):
        rules_path = Path(options["rules"])

        try:
            changes = make_categorizations(
                rules_path=rules_path,
            )
            for change in changes:
                desc = change.tx.description_clean or change.tx.description_raw
                self.stdout.write(
                    f"  [{change.category:20s}] {desc[:60]:60s}  (rule: {change.rule_id})"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nApplied categories. Updated {len(changes)} transaction(s)."
                )
            )

        except ValueError as exc:
            raise CommandError(str(exc)) from exc
