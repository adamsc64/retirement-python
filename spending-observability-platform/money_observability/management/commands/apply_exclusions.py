from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from money_observability.services.exclusion_rules import make_exclusions


class Command(BaseCommand):
    help = (
        "Apply rule-based exclusions to all Transaction rows. "
        "Excluded transactions are flagged as noise (e.g. internal transfers, credit card "
        "repayments, zero-amount artefacts) and hidden from spending reports and category "
        "analysis. Transactions that no longer match any exclusion rule are automatically "
        "un-excluded. Run this before apply_categories."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--rules",
            type=str,
            default="rules/rules.yml",
            help="Path to exclusion rules YAML file (default: rules/rules.yml).",
        )

    def handle(self, *args, **options):
        rules_path = Path(options["rules"])

        try:
            changes = make_exclusions(
                rules_path=rules_path,
            )
            for change in changes:
                desc = change.tx.description_clean or change.tx.description_raw
                status = "EXCLUDED" if change.excluded else "RESTORED"
                self.stdout.write(
                    f"  [{status:10s}] {desc[:60]:60s}  (reason: {change.reason}, rule: {change.rule_id})"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nApplied exclusions. Updated {len(changes)} transaction(s)."
                )
            )

        except ValueError as exc:
            raise CommandError(str(exc)) from exc
