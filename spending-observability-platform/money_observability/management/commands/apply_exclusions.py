from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from money_observability.models import Transaction
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
        parser.add_argument(
            "--source",
            action="append",
            dest="sources",
            help="Optional source institution filter. Can be specified multiple times.",
        )

    def handle(self, *args, **options):
        rules_path = Path(options["rules"])
        source_filter = [s.lower() for s in (options.get("sources") or [])]

        queryset = Transaction.objects.all()
        if source_filter:
            queryset = queryset.filter(source_institution__in=source_filter)

        try:
            changed = make_exclusions(queryset, rules_path)
            self.stdout.write(
                self.style.SUCCESS(f"Applied exclusions. Updated {changed} transaction(s).")
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
