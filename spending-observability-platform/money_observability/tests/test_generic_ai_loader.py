from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from money_observability.models import Transaction
from money_observability.services.import_service import import_uploaded_bytes


class GenericAILoaderTest(TestCase):
    def test_chase_csv_succeeds_with_universal_map(self):
        # Now that 'Posting Date' is in UNIVERSAL_COLUMN_MAP, it should work without AI.
        chase_content = (
            b"Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #\n"
            b'DEBIT,02/25/2026,"PAYPAL *STEAM GAMES 425-952-2985 WA          02/24",-10.85,DEBIT_CARD,2265.29,,\n'
        )

        summary = import_uploaded_bytes(chase_content, "Chase_Activity.csv")

        self.assertEqual(summary.institution, "generic")
        self.assertEqual(summary.imported, 1)

        tx = Transaction.objects.get(description_raw__contains="PAYPAL *STEAM GAMES")
        self.assertEqual(tx.amount, Decimal("-10.85"))

    @patch("money_observability.services.loaders.get_ai_client")
    def test_chase_csv_succeeds_with_ai_mapping(self, mock_get_ai_client):
        # Mock AI client to return the mapping for 'Posting Date'
        mock_client = mock_get_ai_client.return_value
        mock_client.get_json_response.return_value = {"posted_date": "Posting Date"}

        chase_content = (
            b"Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #\n"
            b'DEBIT,02/25/2026,"PAYPAL *STEAM GAMES 425-952-2985 WA          02/24",-10.85,DEBIT_CARD,2265.29,,\n'
        )

        summary = import_uploaded_bytes(chase_content, "Chase_Activity.csv")

        self.assertEqual(summary.institution, "generic")
        self.assertEqual(summary.imported, 1)

        # Verify transaction data
        tx = Transaction.objects.get(description_raw__contains="PAYPAL *STEAM GAMES")
        self.assertEqual(tx.amount, Decimal("-10.85"))
        self.assertEqual(tx.posted_date.isoformat(), "2026-02-25")
        self.assertEqual(tx.account.institution, "generic")
