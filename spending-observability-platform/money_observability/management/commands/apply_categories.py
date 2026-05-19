from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from money_observability.models import Transaction
from money_observability.services.category_rules import (
    CATEGORY_MANUAL_REVIEW,
    load_category_rules,
    match_category_rule,
)


class Command(BaseCommand):
    help = "Apply rule-based categories to non-excluded Transaction rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--rules",
            type=str,
            default="rules/rules.yml",
            help="Path to rules YAML file (default: rules/rules.yml).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print each categorisation as it is applied.",
        )

    def handle(self, *args, **options):
        rules_path = Path(options["rules"])
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        try:
            rules = load_category_rules(rules_path)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        base = Transaction.objects.filter(excluded=False)

        txs = (
            list(base.filter(categorized_at__isnull=True).order_by("id"))
            + list(base.filter(category=CATEGORY_MANUAL_REVIEW).order_by("id"))
        )
        if not txs:
            self.stdout.write(self.style.WARNING("No uncategorised transactions found."))
            return

        now = timezone.now()
        changed = 0

        for tx in txs:
            matched_rule = next((rule for rule in rules if match_category_rule(tx, rule)), None)
            if matched_rule is not None:
                desired_category = matched_rule.category
                desired_rule_id = matched_rule.rule_id
            else:
                desired_category = CATEGORY_MANUAL_REVIEW
                desired_rule_id = ""

            if tx.category != desired_category or tx.category_rule_id != desired_rule_id:
                changed += 1
                tx.category = desired_category
                tx.category_rule_id = desired_rule_id
                tx.categorized_at = tx.categorized_at or now
                if verbose:
                    self.stdout.write(f"  {tx.description_raw} -> {desired_category}")

        if dry_run:
            self.stdout.write(
                f"Dry run: would update {changed} transaction(s) out of {len(txs)} uncategorised."
            )
            return

        if changed:
            Transaction.objects.bulk_update(
                txs,
                ["category", "category_rule_id", "categorized_at"],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Applied categories. Updated {changed} transaction(s) out of {len(txs)} uncategorised."
            )
        )
