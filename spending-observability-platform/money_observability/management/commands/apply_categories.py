from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from money_observability.models import Transaction
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
            changed = make_categorizations(
                Transaction.objects.filter(excluded=False), rules_path
            )
            self.stdout.write(
                self.style.SUCCESS(f"Applied categories. Updated {changed} transaction(s).")
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
