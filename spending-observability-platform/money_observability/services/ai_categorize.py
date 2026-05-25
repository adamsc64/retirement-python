"""AI-powered transaction categorization service.

Provides run_ai_categorize() for use by both the management command and the
web-upload pipeline.  Requires the OPENAI_KEY environment variable; returns 0
silently when it is absent or when the openai package is not installed.
"""
from __future__ import annotations

import json
import os

from money_observability.models import Transaction
from money_observability.services.categories import (
    CATEGORIES,
    CATEGORY_MANUAL_REVIEW,
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


def categorize_batch(client, batch: list[Transaction], model: str) -> dict[str, str]:
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(batch)},
        ],
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


def make_ai_categorizations(
    queryset,
    model: str = MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    """AI-categorize Manual Review transactions in *queryset* and save.

    Returns the number of transactions updated.  Returns 0 without raising if
    OPENAI_KEY is unset or the openai package is not installed.
    """
    from django.utils import timezone

    api_key = os.environ.get("OPENAI_KEY")
    if not api_key:
        return 0

    try:
        from openai import OpenAI
    except ImportError:
        return 0

    client = OpenAI(api_key=api_key)
    txs = list(
        queryset.filter(category=CATEGORY_MANUAL_REVIEW, excluded=False).order_by("id")
    )
    if not txs:
        return 0

    now = timezone.now()
    to_update: list[Transaction] = []
    valid_set = CATEGORY_SET

    for batch_start in range(0, len(txs), batch_size):
        batch = txs[batch_start : batch_start + batch_size]
        results = categorize_batch(client, batch, model)
        for tx in batch:
            category = results.get(str(tx.id))
            if category not in valid_set:
                continue
            tx.category = category
            tx.category_rule_id = f"ai:{model}"
            tx.categorized_at = tx.categorized_at or now
            to_update.append(tx)

    if to_update:
        Transaction.objects.bulk_update(
            to_update,
            ["category", "category_rule_id", "categorized_at"],
        )

    return len(to_update)
