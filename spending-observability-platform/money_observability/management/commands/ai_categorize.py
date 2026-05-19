"""Management command: ai_categorize

Uses OpenAI to categorize transactions that are still sitting in
CATEGORY_MANUAL_REVIEW.  Transactions are sent in batches to minimise API
calls.  Results are stored with category_rule_id="ai:<model>" so the
rule-based apply_categories command can distinguish them.

Usage:
    python manage.py ai_categorize
    python manage.py ai_categorize --dry-run
    python manage.py ai_categorize --batch-size 10
    python manage.py ai_categorize --model gpt-5.4-mini
"""
from __future__ import annotations

import json
import os

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from money_observability.models import Transaction
from money_observability.services.categories import (
    CATEGORIES,
    CATEGORY_MANUAL_REVIEW,
    CATEGORY_NAMES,
    CATEGORY_SET,
)

MODEL = "gpt-5.4-nano"
DEFAULT_BATCH_SIZE = 20

_CATEGORY_LIST = "\n".join(f"  - {c.name}: {c.ai_hint}" for c in CATEGORIES)

SYSTEM_PROMPT = f"""\
You are a personal finance categorization assistant.

Given a JSON array of bank transactions, assign each one to exactly one of
these categories:
{_CATEGORY_LIST}

Respond with a single JSON object whose keys are the transaction IDs (strings)
and whose values are the chosen category strings.  Use only the categories
listed above.  Output nothing except valid JSON.
"""


def _build_user_message(batch: list[Transaction]) -> str:
    items = [
        {
            "id": str(tx.id),
            "description": tx.description_clean or tx.description_raw,
            "amount": str(abs(tx.amount)),
            "currency": tx.currency,
            "institution": tx.source_institution,
            "date": str(tx.posted_date),
        }
        for tx in batch
    ]
    return json.dumps(items, ensure_ascii=False)


def _categorize_batch(client, batch: list[Transaction], model: str) -> dict[str, str]:
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(batch)},
        ],
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


class Command(BaseCommand):
    help = "Use OpenAI to auto-categorize transactions still in Manual Review."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print categorisations without writing to the database.",
        )
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
        api_key = os.environ.get("OPENAI_KEY")
        if not api_key:
            raise CommandError(
                "OPENAI_KEY environment variable is not set. Aborting."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise CommandError(
                "openai package is not installed. Run: pip install openai"
            ) from exc

        client = OpenAI(api_key=api_key)
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        model = options["model"]

        txs = list(
            Transaction.objects.filter(
                category=CATEGORY_MANUAL_REVIEW,
                excluded=False,
            ).order_by("id")
        )

        if not txs:
            self.stdout.write(self.style.WARNING("No Manual Review transactions found."))
            return

        self.stdout.write(
            f"Categorizing {len(txs)} transaction(s) using {model}"
            + (" (dry run)" if dry_run else "")
            + "…"
        )

        now = timezone.now()
        to_update: list[Transaction] = []
        valid_set = CATEGORY_SET

        for batch_start in range(0, len(txs), batch_size):
            batch = txs[batch_start : batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(txs) + batch_size - 1) // batch_size

            try:
                results = _categorize_batch(client, batch, model)
            except Exception as exc:
                raise CommandError(
                    f"OpenAI API error on batch {batch_num}/{total_batches}: {exc}"
                ) from exc

            for tx in batch:
                category = results.get(str(tx.id))
                desc = tx.description_clean or tx.description_raw

                if category not in valid_set:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [SKIP] #{tx.id} {desc!r}: model returned {category!r}"
                        )
                    )
                    continue

                self.stdout.write(
                    f"  #{tx.id} {tx.posted_date} {abs(tx.amount):.2f} {tx.currency}"
                    f"  {desc!r}  →  {category}"
                )
                tx.category = category
                tx.category_rule_id = f"ai:{model}"
                tx.categorized_at = tx.categorized_at or now
                to_update.append(tx)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run: would update {len(to_update)} transaction(s)."
                )
            )
            return

        if to_update:
            Transaction.objects.bulk_update(
                to_update,
                ["category", "category_rule_id", "categorized_at"],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Updated {len(to_update)} of {len(txs)} transaction(s)."
            )
        )
