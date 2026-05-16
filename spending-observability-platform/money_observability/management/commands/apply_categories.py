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
            "--source",
            action="append",
            dest="sources",
            help="Optional source institution filter. Can be specified multiple times.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )

    def handle(self, *args, **options):
        rules_path = Path(options["rules"])
        dry_run = options["dry_run"]
        source_filter = [s.lower() for s in (options.get("sources") or [])]

        try:
            rules = load_category_rules(rules_path)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        queryset = Transaction.objects.filter(excluded=False).order_by("id")
        if source_filter:
            queryset = queryset.filter(source_institution__in=source_filter)

        txs = list(queryset)
        if not txs:
            self.stdout.write(self.style.WARNING("No non-excluded transactions found."))
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

        if dry_run:
            self.stdout.write(
                f"Dry run: would update {changed} transaction(s) out of {len(txs)} non-excluded."
            )
            return

        if changed:
            Transaction.objects.bulk_update(
                txs,
                ["category", "category_rule_id", "categorized_at"],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Applied categories. Updated {changed} transaction(s) out of {len(txs)} non-excluded."
            )
        )
