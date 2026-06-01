from django.test import TestCase

from money_observability.models import Transaction
from money_observability.services.import_service import import_uploaded_bytes


class DeduplicationScenariosTests(TestCase):
    def test_same_batch_multiple_identical_transactions_preserved(self):
        """Case 1: Two identical coffees in the same file should both be imported."""
        # Citi format
        content = (
            b"Status,Date,Description,Debit,Credit\n"
            b"Cleared,13/01/2026,Coffee,5.00,\n"
            b"Cleared,13/01/2026,Coffee,5.00,\n"
        )

        summary = import_uploaded_bytes(content, "citi_multi.csv")

        self.assertEqual(summary.imported, 2)
        self.assertEqual(Transaction.objects.count(), 2)

        txs = Transaction.objects.all()
        self.assertEqual(txs[0].event_fingerprint, txs[1].event_fingerprint)
        self.assertNotEqual(txs[0].source_row_key, txs[1].source_row_key)

    def test_different_batches_identical_transactions_deduped(self):
        """Case 2: Same item in two different uploads should be deduped."""
        # Upload 1
        content1 = (
            b"Status,Date,Description,Debit,Credit\n"
            b"Cleared,13/01/2026,Unique Purchase,10.00,\n"
            b"Cleared,13/01/2026,Coffee,5.00,\n"
        )
        summary1 = import_uploaded_bytes(content1, "batch1.csv")
        self.assertEqual(summary1.imported, 2)

        # Upload 2 (Coffee is a duplicate, New Item is new)
        content2 = (
            b"Status,Date,Description,Debit,Credit\n"
            b"Cleared,13/01/2026,Coffee,5.00,\n"
            b"Cleared,13/01/2026,New Item,20.00,\n"
        )
        summary2 = import_uploaded_bytes(content2, "batch2.csv")

        self.assertEqual(summary2.imported, 1)  # Only "New Item"
        self.assertEqual(summary2.duplicate, 1)  # "Coffee" skipped
        self.assertEqual(Transaction.objects.count(), 3)

        # Verify specific items
        self.assertTrue(
            Transaction.objects.filter(description_raw="Unique Purchase").exists()
        )
        self.assertTrue(
            Transaction.objects.filter(description_raw="Coffee").count() == 1
        )
        self.assertTrue(Transaction.objects.filter(description_raw="New Item").exists())
