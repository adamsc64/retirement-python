from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum

from money_observability.models import Transaction
from money_observability.services.category_rules import CATEGORY_MANUAL_REVIEW


class Command(BaseCommand):
    help = (
        "Show the most expensive uncategorized spending groups, ranked by total spend. "
        "'Uncategorized' means the transaction is marked for Manual Review."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Number of groups to display (default: 20).",
        )
        parser.add_argument(
            "--source",
            action="append",
            dest="sources",
            help="Optional source institution filter. Can be specified multiple times.",
        )
        parser.add_argument(
            "--currency",
            type=str,
            default=None,
            help="Filter to a specific currency (e.g. USD, GBP).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        source_filter = [s.lower() for s in (options.get("sources") or [])]
        currency_filter = (options.get("currency") or "").upper() or None

        queryset = Transaction.objects.filter(
            excluded=False,
            direction="debit",
            category=CATEGORY_MANUAL_REVIEW,
        )

        if source_filter:
            queryset = queryset.filter(source_institution__in=source_filter)

        if currency_filter:
            queryset = queryset.filter(currency=currency_filter)

        groups = (
            queryset
            .values("description_clean", "currency")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("total")[:limit]
        )

        groups = list(groups)
        if not groups:
            self.stdout.write(self.style.WARNING("No uncategorized debit transactions found."))
            return

        header = f"{'Description':<55} {'Curr':>4} {'Txns':>5} {'Total':>12}"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))

        for row in groups:
            desc = (row["description_clean"] or "(blank)")[:55]
            self.stdout.write(
                f"{desc:<55} {row['currency']:>4} {row['count']:>5} {row['total']:>12.2f}"
            )

        total_rows = queryset.count()
        self.stdout.write(
            f"\nShowing top {len(groups)} group(s) of {total_rows} uncategorized debit transaction(s)."
        )
