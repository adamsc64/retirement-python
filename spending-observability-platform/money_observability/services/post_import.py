from __future__ import annotations

from pathlib import Path
from django.db.models import QuerySet
from .exclusion_rules import make_exclusions
from .category_rules import make_categorizations
from .ai_categorize import make_ai_categorizations


def run_post_import_pipeline(
    rules_path: Path | None = None,
) -> dict[str, int]:
    """
    Orchestrate the full suite of post-import tasks.
    Used for bulk processing after a new import.
    """
    exclusions_updated = make_exclusions(rules_path=rules_path)
    categories_updated = make_categorizations(rules_path=rules_path)
    ai_updated = make_ai_categorizations()

    return {
        "exclusions_updated": exclusions_updated,
        "categories_updated": categories_updated,
        "ai_updated": ai_updated,
    }
