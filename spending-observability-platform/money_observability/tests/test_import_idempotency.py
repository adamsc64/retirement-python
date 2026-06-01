from pathlib import Path

from django.test import TestCase

from money_observability.models import ImportBatch, Transaction
from money_observability.services.import_service import import_uploaded_bytes


class ImportIdempotencyTests(TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parents[2]
        self.citi_dir = self.base_dir / "data" / "raw" / "citi"

    def test_upload_is_idempotent_for_same_citi_input_files(self):
        # Read a real Citi file from test data
        citi_file = sorted(self.citi_dir.rglob("*.csv"))[0]
        content = citi_file.read_bytes()

        # First import
        summary1 = import_uploaded_bytes(content, citi_file.name)
        self.assertGreater(summary1.imported, 0)

        first_batches = ImportBatch.objects.count()
        first_transactions = Transaction.objects.count()

        # Second import (identical file)
        summary2 = import_uploaded_bytes(content, citi_file.name)

        self.assertEqual(ImportBatch.objects.count(), first_batches)
        self.assertEqual(Transaction.objects.count(), first_transactions)
        self.assertEqual(summary2.imported, 0)
        self.assertEqual(summary2.duplicate, summary1.imported)

    def test_overlapping_csv_skips_duplicate_rows(self):
        """A second CSV that shares a boundary transaction with a first CSV
        should skip only that row, importing the rest cleanly.
        """
        # Citi format with unambiguous dates
        CSV_HEADER = b"Status,Date,Description,Debit,Credit\n"
        ROW_A = b"Cleared,13/04/2026,Coffee Shop,5.00,\n"
        ROW_B = b"Cleared,13/05/2026,Boundary Purchase,12.00,\n"
        ROW_C = b"Cleared,13/06/2026,New Purchase,8.00,\n"

        # Import first file (A and B)
        import_uploaded_bytes(CSV_HEADER + ROW_A + ROW_B, "file1.csv")
        self.assertEqual(Transaction.objects.count(), 2)

        # Import second file (B and C) - B is duplicate, C is new
        summary = import_uploaded_bytes(CSV_HEADER + ROW_B + ROW_C, "file2.csv")

        self.assertEqual(summary.imported, 1)  # Only C
        self.assertEqual(summary.duplicate, 1)  # B skipped
        self.assertEqual(Transaction.objects.count(), 3)
