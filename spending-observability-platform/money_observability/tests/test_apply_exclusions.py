from io import StringIO
from pathlib import Path
import tempfile

from django.core.management import call_command
from django.test import TestCase

from money_observability.models import Transaction


class ApplyExclusionsTests(TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parents[2]
        call_command(
            "import_transactions",
            str(self.base_dir / "data" / "raw" / "citi"),
            "--apply",
            stdout=StringIO(),
        )
        call_command(
            "import_transactions",
            str(self.base_dir / "data" / "raw" / "wise"),
            "--apply",
            stdout=StringIO(),
        )

    def _make_rules_file(self, content: str) -> Path:
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as fh:
            fh.write(content)
            return Path(fh.name)

    def test_apply_exclusions_marks_matching_rows(self):
        rules_path = self._make_rules_file(
            """
exclusions:
  - id: credit_card_payment
    reason: credit_card_payment
    match:
      description_contains:
        - payment thank you
""".strip()
        )
        try:
            call_command("apply_exclusions", "--rules", str(rules_path), stdout=StringIO())
        finally:
            rules_path.unlink(missing_ok=True)

        tx = Transaction.objects.get(description_raw__icontains="PAYMENT THANK YOU")
        self.assertTrue(tx.excluded)
        self.assertEqual(tx.exclusion_reason, "credit_card_payment")
        self.assertEqual(tx.exclusion_rule_id, "credit_card_payment")
        self.assertIsNotNone(tx.excluded_at)

    def test_apply_exclusions_is_idempotent_on_second_run(self):
        rules_path = self._make_rules_file(
            """
exclusions:
  - id: autopay
    reason: credit_card_payment
    match:
      description_contains:
        - autopay
""".strip()
        )
        try:
            first = StringIO()
            call_command("apply_exclusions", "--rules", str(rules_path), stdout=first)

            second = StringIO()
            call_command("apply_exclusions", "--rules", str(rules_path), stdout=second)
        finally:
            rules_path.unlink(missing_ok=True)

        self.assertIn("Updated", first.getvalue())
        self.assertIn("Updated 0 transaction(s)", second.getvalue())

    def test_amount_is_zero_rule_excludes_zero_rows(self):
        rules_path = self._make_rules_file(
            """
exclusions:
  - id: zero_amount_artifact
    reason: zero_amount_artifact
    match:
      amount_is_zero: true
""".strip()
        )
        try:
            call_command("apply_exclusions", "--rules", str(rules_path), stdout=StringIO())
        finally:
            rules_path.unlink(missing_ok=True)

        excluded_zero = Transaction.objects.filter(
            excluded=True,
            amount=0,
            exclusion_rule_id="zero_amount_artifact",
        ).count()
        self.assertGreaterEqual(excluded_zero, 1)
