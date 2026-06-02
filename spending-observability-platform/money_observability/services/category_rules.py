from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from money_observability.models import Transaction
from money_observability.services.categories import CATEGORY_MANUAL_REVIEW
from .ai_categorize import CategorizationChange


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
        rule_id = str(
            raw.get("id") or raw.get("name") or f"category_rule_{idx}"
        ).strip()
        category = str(raw.get("category") or CATEGORY_MANUAL_REVIEW).strip()
        rules.append(
            CategoryRule(
                rule_id=rule_id,
                category=category,
                description_contains=tuple(
                    s.lower()
                    for s in (match.get("description_contains") or [])
                    if str(s).strip()
                ),
                source_institution_in=tuple(
                    s.lower()
                    for s in (match.get("source_institution_in") or [])
                    if str(s).strip()
                ),
                direction_in=tuple(
                    s.lower()
                    for s in (match.get("direction_in") or [])
                    if str(s).strip()
                ),
            )
        )
    return rules


def match_category_rule(tx: Transaction, rule: CategoryRule) -> bool:
    return best_match_token_len(tx, rule) is not None


def best_match_token_len(tx: Transaction, rule: CategoryRule) -> int | None:
    """Return the length of the longest matching description_contains token for
    *rule* against *tx*, or ``None`` if the rule does not match at all.

    Rules that match purely on non-description criteria (source_institution_in /
    direction_in) score 0 so they lose to any description-based match.
    """
    desc = (tx.description_raw or "").lower()
    source = (tx.source_institution or "").lower()
    direction = (tx.direction or "").lower()

    if rule.source_institution_in and source not in rule.source_institution_in:
        return None
    if rule.direction_in and direction not in rule.direction_in:
        return None

    if rule.description_contains:
        matching_lens = [len(t) for t in rule.description_contains if t in desc]
        if not matching_lens:
            return None
        return max(matching_lens)

    return 0  # matches on non-description criteria only


def make_categorizations(
    rules_path: Path | None = None,
) -> list[CategorizationChange]:
    """Apply category rules to non-excluded transactions and save.

    Targets transactions where ``categorized_at`` is null or category is still
    ``CATEGORY_MANUAL_REVIEW``.  Returns a list of CategorizationChange records.
    """
    from django.utils import timezone

    rules_path = rules_path or Path("rules/rules.yml")
    rules = load_category_rules(rules_path)
    base = Transaction.objects.filter(excluded=False)
    txs = list(base.filter(categorized_at__isnull=True).order_by("id")) + list(
        base.filter(category=CATEGORY_MANUAL_REVIEW).order_by("id")
    )
    now = timezone.now()
    to_update: list[Transaction] = []
    changes: list[CategorizationChange] = []

    for tx in txs:
        best_rule: CategoryRule | None = None
        best_len = -1
        for rule in rules:
            token_len = best_match_token_len(tx, rule)
            if token_len is not None and token_len > best_len:
                best_len = token_len
                best_rule = rule
        matched_rule = best_rule
        desired_category = (
            matched_rule.category if matched_rule else CATEGORY_MANUAL_REVIEW
        )
        desired_rule_id = matched_rule.rule_id if matched_rule else ""

        if tx.category != desired_category or tx.category_rule_id != desired_rule_id:
            changes.append(
                CategorizationChange(
                    tx=tx,
                    category=desired_category,
                    rule_id=desired_rule_id,
                )
            )
            tx.category = desired_category
            tx.category_rule_id = desired_rule_id
            tx.categorized_at = tx.categorized_at or now
            to_update.append(tx)

    if to_update:
        Transaction.objects.bulk_update(
            to_update,
            ["category", "category_rule_id", "categorized_at"],
        )

    return changes
