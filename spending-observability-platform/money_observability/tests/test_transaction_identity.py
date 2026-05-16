from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from money_observability.models import Transaction


class TransactionIdentityTests(TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parents[2]

    def test_repeated_legitimate_purchases_are_not_collapsed(self):
        call_command(
            "import_transactions",
            str(self.base_dir / "data" / "raw" / "wise"),
            "--apply",
            stdout=StringIO(),
        )

        # Two distinct real-world purchases with same semantic attributes exist in Wise data:
        # 2026-04-25, Morse Bar, 8.21 GBP, debit.
        duplicates = Transaction.objects.filter(
            source_institution="wise",
            posted_date="2026-04-25",
            description_raw="Morse Bar",
            amount="-8.21",
            currency="GBP",
            direction="debit",
        ).order_by("source_row_key")

        self.assertEqual(duplicates.count(), 2)
        self.assertNotEqual(duplicates[0].source_row_key, duplicates[1].source_row_key)
        self.assertEqual(duplicates[0].event_fingerprint, duplicates[1].event_fingerprint)
