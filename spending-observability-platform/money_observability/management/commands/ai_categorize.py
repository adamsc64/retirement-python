from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from money_observability.models import Transaction
from money_observability.services.ai_categorize import (
    DEFAULT_BATCH_SIZE,
    MODEL,
    make_ai_categorizations,
)


class Command(BaseCommand):
    help = "Use OpenAI to auto-categorize transactions still in Manual Review."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=DEFAULT_BATCH_SIZE,
            help=f"Transactions per API call (default: {DEFAULT_BATCH_SIZE}).",
        )
        parser.add_argument(
            "--model",
            type=str,
            default=MODEL,
            help=f"OpenAI model to use (default: {MODEL}).",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        model = options["model"]

        queryset = Transaction.objects.all()

        updated = make_ai_categorizations(
            queryset,
            model=model,
            batch_size=batch_size,
        )
        if updated > 0:
            self.stdout.write(
                self.style.SUCCESS(f"AI categorization complete. Updated {updated} transaction(s).")
            )
        else:
            self.stdout.write(
                self.style.WARNING("No transactions were updated by AI. Ensure OPENAI_KEY is set and transactions are in Manual Review.")
            )
