from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from money_observability.models import Transaction


@dataclass(frozen=True)
class ExclusionRule:
    rule_id: str
    reason: str
    description_contains: tuple[str, ...] = ()
    source_institution_in: tuple[str, ...] = ()
    direction_in: tuple[str, ...] = ()
    amount_is_zero: bool = False


def load_exclusion_rules(path: Path) -> list[ExclusionRule]:
    if not path.exists():
        raise ValueError(f"Rules file not found: {path}")

    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    raw_rules = data.get("exclusions") or []
    rules: list[ExclusionRule] = []
    for idx, raw in enumerate(raw_rules, start=1):
        match = raw.get("match") or {}
        rule_id = str(raw.get("id") or raw.get("name") or f"rule_{idx}").strip()
        reason = str(raw.get("reason") or "unknown_non_spend").strip()
        rules.append(
            ExclusionRule(
                rule_id=rule_id,
                reason=reason,
                description_contains=tuple(
                    s.lower() for s in (match.get("description_contains") or []) if str(s).strip()
                ),
                source_institution_in=tuple(
                    s.lower() for s in (match.get("source_institution_in") or []) if str(s).strip()
                ),
                direction_in=tuple(
                    s.lower() for s in (match.get("direction_in") or []) if str(s).strip()
                ),
                amount_is_zero=bool(match.get("amount_is_zero", False)),
            )
        )
    return rules


def match_exclusion_rule(tx: Transaction, rule: ExclusionRule) -> bool:
    desc = (tx.description_raw or "").lower()
    source = (tx.source_institution or "").lower()
    direction = (tx.direction or "").lower()

    if rule.description_contains and not any(token in desc for token in rule.description_contains):
        return False
    if rule.source_institution_in and source not in rule.source_institution_in:
        return False
    if rule.direction_in and direction not in rule.direction_in:
        return False
    if rule.amount_is_zero and tx.amount != Decimal("0"):
        return False
    return True
