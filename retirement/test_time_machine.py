import unittest

from time_machine import parse_spending_input


class TestParseSpendingInput(unittest.TestCase):
    def test_positive_signed_dollar_amount_is_relative_to_last_spend(self):
        # "+5k" means "$5k more than last year's spend," e.g. 90000 -> 95000.
        self.assertEqual(parse_spending_input("+5k", 2_082_285.27, 90_000), 95_000.0)

    def test_negative_signed_dollar_amount_is_relative_to_last_spend(self):
        # "-5k" means "$5k less than last year's spend."
        self.assertEqual(parse_spending_input("-5k", 2_082_285.27, 90_000), 85_000.0)

    def test_signed_dollar_amount_without_last_spend_is_invalid(self):
        self.assertIsNone(parse_spending_input("+5k", 3_000_000, None))

    def test_absolute_amount_without_sign_is_literal(self):
        self.assertEqual(parse_spending_input("60000", 3_000_000, -70_000), 60_000.0)

    def test_negative_percent_is_relative_to_last_spend(self):
        # Signed percentages ARE relative to last year's spend.
        self.assertEqual(parse_spending_input("-10%", 3_000_000, 100_000), 90_000.0)

    def test_positive_percent_is_relative_to_last_spend(self):
        self.assertAlmostEqual(
            parse_spending_input("+10%", 3_000_000, 100_000), 110_000.0
        )

    def test_unsigned_percent_is_percent_of_net_worth(self):
        self.assertEqual(parse_spending_input("6%", 1_000_000, 50_000), 60_000.0)


if __name__ == "__main__":
    unittest.main()
