from io import StringIO
from pathlib import Path
import tempfile

from django.core.management import call_command
from django.test import TestCase

from money_observability.models import Transaction
from money_observability.services.category_rules import CATEGORY_MANUAL_REVIEW


class ApplyCategoriesTests(TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parents[2]
        call_command(
            "import_transactions",
            str(self.base_dir / "data" / "raw" / "citi"),
            "--apply",
            stdout=StringIO(),
        )

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
            call_command("apply_categories", "--rules", str(rules_path), stdout=StringIO())
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
            call_command("apply_categories", "--rules", str(rules_path), stdout=StringIO())
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
            first = StringIO()
            call_command("apply_categories", "--rules", str(rules_path), stdout=first)
            second = StringIO()
            call_command("apply_categories", "--rules", str(rules_path), stdout=second)
        finally:
            rules_path.unlink(missing_ok=True)

        self.assertIn("Updated", first.getvalue())
        self.assertIn("Updated 0 transaction(s)", second.getvalue())

    def test_dry_run_does_not_modify_rows(self):
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
            call_command(
                "apply_categories", "--rules", str(rules_path), "--dry-run", stdout=StringIO()
            )
        finally:
            rules_path.unlink(missing_ok=True)

        self.assertFalse(Transaction.objects.filter(category="Subscriptions").exists())

    def test_excluded_rows_are_skipped(self):
        # Exclude all transactions first, then categorize — nothing should be categorized.
        Transaction.objects.all().update(excluded=True)
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
            out = StringIO()
            call_command("apply_categories", "--rules", str(rules_path), stdout=out)
        finally:
            rules_path.unlink(missing_ok=True)

        self.assertIn("No non-excluded transactions found", out.getvalue())
        self.assertFalse(Transaction.objects.filter(category="Other").exists())
