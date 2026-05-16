from decimal import Decimal
from pathlib import Path
from unittest import TestCase

from money_observability.services.loaders import CitiLoader, LoaderError


class CitiLoaderTests(TestCase):
    def setUp(self):
        self.loader = CitiLoader()
        self.base_dir = Path(__file__).resolve().parents[2]
        self.citi_dir = self.base_dir / "data" / "raw" / "citi"

    def test_parses_credit_card_csv_with_expected_sign_convention(self):
        rows = self.loader.parse_rows(self.citi_dir / "citi-3135.CSV")

        self.assertEqual(len(rows), 6)

        payment = rows[0]
        self.assertEqual(payment["amount"], Decimal("1479.45"))
        self.assertEqual(payment["direction"], "credit")
        self.assertEqual(str(payment["posted_date"]), "2026-05-05")
        self.assertEqual(payment["currency"], "USD")

        charge = rows[1]
        self.assertEqual(charge["amount"], Decimal("-75.00"))
        self.assertEqual(charge["direction"], "debit")

    def test_parses_checking_csv_with_expected_sign_convention(self):
        rows = self.loader.parse_rows(self.citi_dir / "CHK_5296_CURRENT_VIEW.csv")

        self.assertEqual(len(rows), 3)

        debit = rows[0]
        self.assertEqual(debit["amount"], Decimal("-126.53"))
        self.assertEqual(debit["direction"], "debit")
        self.assertEqual(str(debit["posted_date"]), "2026-05-04")

        credit = rows[2]
        self.assertEqual(credit["amount"], Decimal("266.00"))
        self.assertEqual(credit["direction"], "credit")
        self.assertEqual(str(credit["posted_date"]), "2026-04-21")

    def test_validate_headers_raises_for_missing_required_columns(self):
        with self.assertRaises(LoaderError):
            self.loader.validate_headers(["Status", "Date", "Description", "Debit"])
