from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from money_observability.models import ImportBatch, RawTransaction, Transaction


class ImportTransactionsIdempotencyTests(TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parents[2]
        self.citi_dir = self.base_dir / "data" / "raw" / "citi"

    def test_apply_mode_is_idempotent_for_same_citi_input_files(self):
        first_stdout = StringIO()
        call_command(
            "import_transactions",
            str(self.citi_dir),
            "--apply",
            stdout=first_stdout,
        )

        first_batches = ImportBatch.objects.count()
        first_raw_rows = RawTransaction.objects.count()
        first_transactions = Transaction.objects.count()

        self.assertEqual(first_batches, 4)
        self.assertEqual(first_raw_rows, 37)
        self.assertEqual(first_transactions, 37)

        second_stdout = StringIO()
        call_command(
            "import_transactions",
            str(self.citi_dir),
            "--apply",
            stdout=second_stdout,
        )

        self.assertEqual(ImportBatch.objects.count(), first_batches)
        self.assertEqual(RawTransaction.objects.count(), first_raw_rows)
        self.assertEqual(Transaction.objects.count(), first_transactions)
        self.assertIn("Already imported: matching file hash", second_stdout.getvalue())
