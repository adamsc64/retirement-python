from decimal import Decimal
from pathlib import Path
import tempfile
from unittest import TestCase

from money_observability.services.loaders import LoaderError, WiseLoader


class WiseLoaderTests(TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parents[2]
        self.wise_path = self.base_dir / "data" / "raw" / "wise" / "wise.csv"
        self.loader = WiseLoader(default_currency="USD")

    def test_parses_wise_rows_with_direction_based_sign(self):
        rows = self.loader.parse_rows(self.wise_path)

        self.assertGreater(len(rows), 50)

        first = rows[0]
        self.assertEqual(str(first["posted_date"]), "2026-05-07")
        self.assertEqual(first["description_raw"], "scans - 2.5 hrs")
        self.assertEqual(first["amount"], Decimal("-45.0"))
        self.assertEqual(first["currency"], "GBP")
        self.assertEqual(first["direction"], "debit")

        incoming = next(
            row
            for row in rows
            if row["description_raw"] == "Uber Eats" and row["direction"] == "credit"
        )
        self.assertEqual(incoming["amount"], Decimal("4.59"))
        self.assertEqual(incoming["currency"], "GBP")

    def test_uses_id_as_description_when_reference_and_target_missing(self):
        content = (
            "ID,Status,Direction,Created on,Source amount (after fees),Source currency,Target name,Reference\n"
            "CARD_TRANSACTION-123,COMPLETED,OUT,2026-05-01 10:10:10,9.99,GBP,,\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            fh.write(content)
            temp_path = Path(fh.name)

        try:
            rows = self.loader.parse_rows(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["description_raw"], "CARD_TRANSACTION-123")

    def test_validate_headers_raises_for_missing_required_columns(self):
        with self.assertRaises(LoaderError):
            self.loader.validate_headers(["ID", "Direction", "Created on"])
