"""AI-powered transaction categorization service.

Provides run_ai_categorize() for use by both the management command and the
web-upload pipeline.  Requires the OPENAI_KEY environment variable; returns 0
silently when it is absent or when the openai package is not installed.
"""

from __future__ import annotations

import json


from dataclasses import dataclass

from money_observability.models import Transaction
from money_observability.services.categories import (
    CATEGORIES,
    CATEGORY_MANUAL_REVIEW,
    CATEGORY_SET,
)
from utils.ai_client import DEFAULT_MODEL, AIClient, get_ai_client

DEFAULT_BATCH_SIZE = 20


@dataclass(frozen=True)
class CategorizationChange:
    tx: Transaction
    category: str
    rule_id: str


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


def build_user_message(batch: list[Transaction]) -> str:
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


def categorize_batch(client: AIClient, batch: list[Transaction]) -> dict[str, str]:
    return client.get_json_response(SYSTEM_PROMPT, build_user_message(batch))


def make_ai_categorizations(
    model: str = DEFAULT_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[CategorizationChange]:
    """AI-categorize Manual Review transactions and save.

    Returns a list of CategorizationChange records for each update.
    Returns an empty list without raising if OPENAI_KEY is unset or the openai
    package is not installed.
    """
    from django.utils import timezone

    client = get_ai_client(model=model)
    if client is None:
        return []
    txs = list(
        Transaction.objects.filter(
            category=CATEGORY_MANUAL_REVIEW, excluded=False
        ).order_by("id")
    )
    if not txs:
        return []

    now = timezone.now()
    to_update: list[Transaction] = []
    changes: list[CategorizationChange] = []
    valid_set = CATEGORY_SET

    for batch_start in range(0, len(txs), batch_size):
        batch = txs[batch_start : batch_start + batch_size]
        results = categorize_batch(client, batch)
        for tx in batch:
            category = results.get(str(tx.id))
            if category not in valid_set:
                continue
            rule_id = f"ai:{model}"
            changes.append(
                CategorizationChange(tx=tx, category=category, rule_id=rule_id)
            )
            tx.category = category
            tx.category_rule_id = rule_id
            tx.categorized_at = tx.categorized_at or now
            to_update.append(tx)

    if to_update:
        Transaction.objects.bulk_update(
            to_update,
            ["category", "category_rule_id", "categorized_at"],
        )

    return changes
