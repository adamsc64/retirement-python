from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest import TestCase

from django.core.management import call_command
from django.test import TestCase as DjangoTestCase

from money_observability.models import ImportBatch
from money_observability.services.import_service import infer_source_metadata_from_path
from money_observability.services.loaders import AmexLoader, HSBCLoader


class SourceMetadataTests(TestCase):
    def test_infers_gbp_profile_from_currency_directory(self):
        path = Path("data/raw/amex/gbp/uk-amex-2026-04-07_to-05-07.csv")
        metadata = infer_source_metadata_from_path(path)

        self.assertEqual(metadata.source_institution, "amex")
        self.assertEqual(metadata.source_profile, "amex_gbp")
        self.assertEqual(metadata.default_currency, "GBP")

    def test_defaults_to_usd_when_currency_directory_missing(self):
        path = Path("data/raw/hsbc/hsbc.csv")
        metadata = infer_source_metadata_from_path(path)

        self.assertEqual(metadata.source_institution, "hsbc")
        self.assertEqual(metadata.source_profile, "hsbc_usd")
        self.assertEqual(metadata.default_currency, "USD")


class UkLoaderCurrencyTests(TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parents[2]

    def test_amex_loader_uses_configured_default_currency(self):
        loader = AmexLoader(default_currency="GBP")
        rows = loader.parse_rows(
            self.base_dir / "data" / "raw" / "amex" / "gbp" / "uk-amex-2026-04-07_to-05-07.csv"
        )

        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["currency"], "GBP")
        self.assertEqual(rows[0]["amount"], Decimal("-16.99"))
        self.assertEqual(rows[0]["direction"], "debit")
        # "PAYMENT RECEIVED" is negative in source file and should become money-in.
        self.assertEqual(rows[2]["amount"], Decimal("90.90"))
        self.assertEqual(rows[2]["direction"], "credit")

    def test_hsbc_loader_uses_configured_default_currency(self):
        loader = HSBCLoader(default_currency="GBP")
        rows = loader.parse_rows(
            self.base_dir / "data" / "raw" / "hsbc" / "gbp" / "hsbc.csv"
        )

        self.assertEqual(len(rows), 17)
        self.assertEqual(rows[0]["currency"], "GBP")
        self.assertEqual(rows[0]["amount"], Decimal("-10.00"))
        self.assertEqual(rows[0]["direction"], "debit")
        self.assertEqual(rows[5]["amount"], Decimal("4128.00"))
        self.assertEqual(rows[5]["direction"], "credit")


class SourceProfileImportTests(DjangoTestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parents[2]

    def test_apply_records_profile_for_amex_and_hsbc(self):
        stdout = StringIO()
        call_command(
            "import_transactions",
            str(self.base_dir / "data" / "raw" / "amex"),
            "--apply",
            stdout=stdout,
        )
        call_command(
            "import_transactions",
            str(self.base_dir / "data" / "raw" / "hsbc"),
            "--apply",
            stdout=stdout,
        )

        amex_batch = ImportBatch.objects.get(source_institution="amex")
        hsbc_batch = ImportBatch.objects.get(source_institution="hsbc")

        self.assertEqual(amex_batch.source_profile, "amex_gbp")
        self.assertEqual(hsbc_batch.source_profile, "hsbc_gbp")
