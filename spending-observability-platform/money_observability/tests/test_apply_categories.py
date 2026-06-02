import tempfile
from pathlib import Path

from django.test import TestCase

from money_observability.models import Transaction
from money_observability.services.categories import CATEGORY_MANUAL_REVIEW
from money_observability.services.category_rules import make_categorizations
from money_observability.services.import_service import import_uploaded_bytes


class ApplyCategoriesTests(TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parents[2]
        # Use the specific file known to contain NETFLIX
        citi_file = self.base_dir / "data" / "raw" / "citi" / "citi-6518.CSV"
        import_uploaded_bytes(citi_file.read_bytes(), citi_file.name)

    def _make_rules_file(self, content: str) -> Path:
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as fh:
            fh.write(content)
            return Path(fh.name)

    def test_apply_categories_marks_matching_rows(self):
        rules_path = self._make_rules_file(
            """
categories:
  - id: test_subscriptions
    category: Subscriptions
    match:
      description_contains:
        - netflix
""".strip()
        )
        try:
            # We must clear any existing categorization applied by the upload pipeline
            # to ensure the test specifically verifies the make_categorizations call.
            Transaction.objects.all().update(
                category=CATEGORY_MANUAL_REVIEW,
                category_rule_id="",
                categorized_at=None,
            )
            make_categorizations(rules_path=rules_path)
        finally:
            rules_path.unlink(missing_ok=True)

        matched = Transaction.objects.filter(category="Subscriptions")
        self.assertTrue(matched.exists())
        for tx in matched:
            self.assertIn("netflix", tx.description_raw.lower())
            self.assertEqual(tx.category_rule_id, "test_subscriptions")
            self.assertIsNotNone(tx.categorized_at)

    def test_unmatched_rows_get_manual_review(self):
        rules_path = self._make_rules_file(
            """
categories:
  - id: nothing_matches
    category: Groceries
    match:
      description_contains:
        - zzznomatch
""".strip()
        )
        try:
            Transaction.objects.all().update(
                category=CATEGORY_MANUAL_REVIEW,
                category_rule_id="",
                categorized_at=None,
            )
            make_categorizations(rules_path=rules_path)
        finally:
            rules_path.unlink(missing_ok=True)

        non_excluded = Transaction.objects.filter(excluded=False)
        self.assertTrue(non_excluded.exists())
        for tx in non_excluded:
            self.assertEqual(tx.category, CATEGORY_MANUAL_REVIEW)

    def test_apply_categories_is_idempotent_on_second_run(self):
        rules_path = self._make_rules_file(
            """
categories:
  - id: test_subscriptions
    category: Subscriptions
    match:
      description_contains:
        - netflix
""".strip()
        )
        try:
            Transaction.objects.all().update(
                category=CATEGORY_MANUAL_REVIEW,
                category_rule_id="",
                categorized_at=None,
            )
            first_updated = make_categorizations(rules_path=rules_path)
            second_updated = make_categorizations(rules_path=rules_path)
        finally:
            rules_path.unlink(missing_ok=True)

        self.assertGreater(len(first_updated), 0)
        self.assertEqual(len(second_updated), 0)

    def test_excluded_rows_are_skipped(self):
        # Exclude all transactions first, then categorize — nothing should be categorized.
        Transaction.objects.all().update(excluded=True, category=CATEGORY_MANUAL_REVIEW)
        rules_path = self._make_rules_file(
            """
categories:
  - id: catch_all
    category: Other
    match:
      description_contains: []
""".strip()
        )
        try:
            updated = make_categorizations(rules_path=rules_path)
        finally:
            rules_path.unlink(missing_ok=True)

        self.assertEqual(len(updated), 0)
        self.assertFalse(Transaction.objects.filter(category="Other").exists())
