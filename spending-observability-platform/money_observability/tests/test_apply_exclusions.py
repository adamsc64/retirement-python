import tempfile
from pathlib import Path

from django.test import TestCase

from money_observability.models import Transaction
from money_observability.services.exclusion_rules import make_exclusions
from money_observability.services.import_service import import_uploaded_bytes


class ApplyExclusionsTests(TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parents[2]
        # Files known to contain triggers
        citi_file = self.base_dir / "data" / "raw" / "citi" / "citi-6518.CSV"
        wise_file = sorted((self.base_dir / "data" / "raw" / "wise").rglob("*.csv"))[0]
        import_uploaded_bytes(citi_file.read_bytes(), citi_file.name)
        import_uploaded_bytes(wise_file.read_bytes(), wise_file.name)

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
            # Reset exclusions applied by automatic pipeline
            Transaction.objects.all().update(
                excluded=False,
                exclusion_reason="",
                exclusion_rule_id="",
                excluded_at=None,
            )
            make_exclusions(rules_path=rules_path)
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
            Transaction.objects.all().update(
                excluded=False,
                exclusion_reason="",
                exclusion_rule_id="",
                excluded_at=None,
            )
            first_updated = make_exclusions(rules_path=rules_path)
            second_updated = make_exclusions(rules_path=rules_path)
        finally:
            rules_path.unlink(missing_ok=True)

        self.assertGreater(len(first_updated), 0)
        self.assertEqual(len(second_updated), 0)

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
            Transaction.objects.all().update(
                excluded=False,
                exclusion_reason="",
                exclusion_rule_id="",
                excluded_at=None,
            )
            make_exclusions(rules_path=rules_path)
        finally:
            rules_path.unlink(missing_ok=True)

        excluded_zero = Transaction.objects.filter(
            excluded=True,
            amount=0,
            exclusion_rule_id="zero_amount_artifact",
        ).count()
        self.assertGreaterEqual(excluded_zero, 1)
