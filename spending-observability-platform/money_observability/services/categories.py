"""Canonical category definitions for the spending observability platform.

Every consumer — views, management commands, AI prompts — should import from
here rather than defining its own list.

Each Category carries:
  name      : the stored string value (used in Transaction.category)
  shortcut  : single lowercase letter for the categorisation UI keyboard nav
              (j / k / a are reserved for navigation / select-all)
  ai_hint   : plain-English description fed to the LLM prompt
"""
from __future__ import annotations

from dataclasses import dataclass

# Sentinel value for transactions that still need a human (or AI) decision.
# Kept here rather than in category_rules.py because it is fundamentally a
# category concept used across views, commands, and services alike.
CATEGORY_MANUAL_REVIEW = "Manual Review"


@dataclass(frozen=True)
class Category:
    name: str
    shortcut: str   # single lowercase letter
    ai_hint: str    # description for LLM classification prompts


# Ordered by expected frequency of use (also controls UI button order).
# Keyboard conflict notes: P=sho(P)ping, C=health(C)are, V=tra(V)el, I=g(I)ving.
CATEGORIES: list[Category] = [
    Category("Dining",                 "d", "restaurants, cafes, takeaways, food delivery"),
    Category("Groceries",              "g", "supermarkets, food shops"),
    Category("Transport",              "t", "public transit, taxis, rideshares, fuel, parking, buses"),
    Category("Housing",                "h", "rent, utilities, home services, repairs"),
    Category("Subscriptions",          "s", "recurring software, streaming, club memberships"),
    Category("Shopping",               "p", "retail, clothing, online shopping, general merchandise"),
    Category("Entertainment",          "e", "cinema, events, games, hobbies, sport venues"),
    Category("Healthcare",             "c", "medical, pharmacy, dental, optician"),
    Category("Travel",                 "v", "flights, hotels, travel agencies, foreign-trip expenses"),
    Category("Laundry",                "l", "laundry and dry-cleaning services"),
    Category("Giving",                 "i", "charitable donations"),
    Category("Fees / Finance Charges", "f", "bank fees, interest, ATM fees, FX charges"),
    Category("Other",                  "o", "anything that doesn't fit the above"),
]

# Derived helpers — computed once so callers don't repeat the comprehensions.
CATEGORY_NAMES: list[str] = [c.name for c in CATEGORIES]
CATEGORY_SET: frozenset[str] = frozenset(CATEGORY_NAMES)
KEY_TO_CATEGORY: dict[str, str] = {c.shortcut: c.name for c in CATEGORIES}
CATEGORY_TO_KEY: dict[str, str] = {c.name: c.shortcut.upper() for c in CATEGORIES}
