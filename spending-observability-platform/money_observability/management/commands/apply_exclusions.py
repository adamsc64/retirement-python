from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from money_observability.models import Transaction
from money_observability.services.exclusion_rules import load_exclusion_rules, match_exclusion_rule


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
            rules = load_exclusion_rules(rules_path)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        queryset = Transaction.objects.all().order_by("id")
        if source_filter:
            queryset = queryset.filter(source_institution__in=source_filter)

        txs = list(queryset)
        if not txs:
            self.stdout.write(self.style.WARNING("No transactions found for exclusion run."))
            return

        now = timezone.now()
        changed = 0
        excluded_count = 0

        for tx in txs:
            matched_rule = next((rule for rule in rules if match_exclusion_rule(tx, rule)), None)
            if matched_rule is None:
                desired = (False, "", "", None)
            else:
                desired = (True, matched_rule.reason, matched_rule.rule_id, tx.excluded_at or now)

            current = (tx.excluded, tx.exclusion_reason, tx.exclusion_rule_id, tx.excluded_at)
            if current != desired:
                changed += 1
                tx.excluded = desired[0]
                tx.exclusion_reason = desired[1]
                tx.exclusion_rule_id = desired[2]
                tx.excluded_at = desired[3]

            if tx.excluded:
                excluded_count += 1

        if dry_run:
            self.stdout.write(
                f"Dry run: would update {changed} transaction(s). Excluded after run: {excluded_count}/{len(txs)}"
            )
            return

        if changed:
            Transaction.objects.bulk_update(
                txs,
                ["excluded", "exclusion_reason", "exclusion_rule_id", "excluded_at"],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Applied exclusions. Updated {changed} transaction(s). Excluded: {excluded_count}/{len(txs)}"
            )
        )
