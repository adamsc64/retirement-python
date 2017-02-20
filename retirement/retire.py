#!/usr/bin/env python
import argparse
import math

from target_fund import TargetFund

ANNUAL_RAISE = 3.0


def print_state(*args, **kwargs):
    print(format_state(*args, **kwargs))


def format_state(year, month, monthly, gain, total):
    inflation_total = total * math.pow(1.0 - (3.22 / 100.0), year)
    return ("Year {}, "
            "Month {}, "
            "Adding: ${:,.2f}, "
            "Gain: ${:,.2f}, "
            "Total: ${:,.2f} "
            "(Inflation-Adusted: ${:,.2f})"
            ).format(
                year + 1,
                month + 1,
                monthly,
                gain,
                total,
                inflation_total)


def main():
    args = parser.parse_args()
    fund = TargetFund(args.num_years, args.start_with)
    salary = args.salary
    num_years = args.num_years
    contribution = args.contribution
    for year in range(num_years):
        monthly = (salary / 12.0) * (contribution / 100.0)
        years_left = num_years - year
        fund.set_years_left(years_left)
        for month in range(12):
            gain = fund.do_month(contribution=monthly)
            print_state(year, month, monthly, gain, fund.total)
        salary *= (1 + (ANNUAL_RAISE / 100.0))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Calculate projected investment total each month.')
    parser.add_argument(
        '--salary', type=int, required=True,
        help='Annual salary.')
    parser.add_argument(
        '--contribution', type=int, required=True,
        help='Contribution of salary per month, in percent.')
    parser.add_argument(
        '--num-years', type=int, required=True,
        help='Number of years to save.')
    parser.add_argument(
        '--growth', type=float, default=5.5,
        help='Growth rate, in percentage.')
    parser.add_argument(
        '--start-with', type=int, default=0,
        help='Starting amount.')
    main()
