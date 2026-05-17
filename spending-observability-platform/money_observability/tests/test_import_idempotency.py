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

    def test_overlapping_csv_skips_duplicate_rows_with_warning(self):
        """A second CSV that shares a boundary transaction with a first CSV
        should warn and skip only that row, importing the rest cleanly.

        CSV 1 (Apr):  row A, row B
        CSV 2 (May):  row B (overlap), row C (new)

        Expected: A, B, C all in DB — B appears once, not twice.
        """
        import shutil
        import tempfile

        CSV_HEADER = "Status,Date,Description,Debit,Credit\n"
        ROW_A = "Cleared,04/15/2026,Coffee Shop,5.00,\n"
        ROW_B = "Cleared,05/15/2026,Boundary Purchase,12.00,\n"  # the overlap row
        ROW_C = "Cleared,06/15/2026,New Purchase,8.00,\n"

        with tempfile.TemporaryDirectory() as tmp:
            dir1 = Path(tmp) / "apr-may" / "citi"
            dir2 = Path(tmp) / "may-jun" / "citi"
            dir1.mkdir(parents=True)
            dir2.mkdir(parents=True)

            (dir1 / "citi-apr-may.csv").write_text(CSV_HEADER + ROW_A + ROW_B)
            (dir2 / "citi-may-jun.csv").write_text(CSV_HEADER + ROW_B + ROW_C)

            # Import first file
            call_command("import_transactions", str(dir1), "--apply", stdout=StringIO())
            self.assertEqual(Transaction.objects.count(), 2)  # A and B

            # Import second file — B is a duplicate, C is new
            out = StringIO()
            call_command("import_transactions", str(dir2), "--apply", stdout=out)

        output = out.getvalue()
        self.assertIn("overlapping transaction(s) skipped", output)
        # B should not be doubled; C should be added → total 3
        self.assertEqual(Transaction.objects.count(), 3)
