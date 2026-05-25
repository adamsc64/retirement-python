from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from money_observability.models import Transaction
from money_observability.services.categories import CATEGORY_MANUAL_REVIEW


@dataclass(frozen=True)
class CategoryRule:
    rule_id: str
    category: str
    description_contains: tuple[str, ...] = ()
    source_institution_in: tuple[str, ...] = ()
    direction_in: tuple[str, ...] = ()


def load_category_rules(path: Path) -> list[CategoryRule]:
    if not path.exists():
        raise ValueError(f"Rules file not found: {path}")

    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    raw_rules = data.get("categories") or []
    rules: list[CategoryRule] = []
    for idx, raw in enumerate(raw_rules, start=1):
        match = raw.get("match") or {}
        rule_id = str(raw.get("id") or raw.get("name") or f"category_rule_{idx}").strip()
        category = str(raw.get("category") or CATEGORY_MANUAL_REVIEW).strip()
        rules.append(
            CategoryRule(
                rule_id=rule_id,
                category=category,
                description_contains=tuple(
                    s.lower() for s in (match.get("description_contains") or []) if str(s).strip()
                ),
                source_institution_in=tuple(
                    s.lower() for s in (match.get("source_institution_in") or []) if str(s).strip()
                ),
                direction_in=tuple(
                    s.lower() for s in (match.get("direction_in") or []) if str(s).strip()
                ),
            )
        )
    return rules


def match_category_rule(tx: Transaction, rule: CategoryRule) -> bool:
    desc = (tx.description_raw or "").lower()
    source = (tx.source_institution or "").lower()
    direction = (tx.direction or "").lower()

    if rule.description_contains and not any(token in desc for token in rule.description_contains):
        return False
    if rule.source_institution_in and source not in rule.source_institution_in:
        return False
    if rule.direction_in and direction not in rule.direction_in:
        return False
    return True


def make_categorizations(queryset, rules_path: Path | None = None) -> int:
    """Apply category rules to non-excluded transactions in *queryset* and save.

    Targets transactions where ``categorized_at`` is null or category is still
    ``CATEGORY_MANUAL_REVIEW``.  Returns the number of transactions updated.
    """
    from django.utils import timezone

    rules_path = rules_path or Path("rules/rules.yml")
    rules = load_category_rules(rules_path)
    base = queryset.filter(excluded=False)
    txs = (
        list(base.filter(categorized_at__isnull=True).order_by("id"))
        + list(base.filter(category=CATEGORY_MANUAL_REVIEW).order_by("id"))
    )
    now = timezone.now()
    to_update: list[Transaction] = []

    for tx in txs:
        matched_rule = next((r for r in rules if match_category_rule(tx, r)), None)
        desired_category = matched_rule.category if matched_rule else CATEGORY_MANUAL_REVIEW
        desired_rule_id = matched_rule.rule_id if matched_rule else ""

        if tx.category != desired_category or tx.category_rule_id != desired_rule_id:
            tx.category = desired_category
            tx.category_rule_id = desired_rule_id
            tx.categorized_at = tx.categorized_at or now
            to_update.append(tx)

    if to_update:
        Transaction.objects.bulk_update(
            to_update,
            ["category", "category_rule_id", "categorized_at"],
        )

    return len(to_update)
