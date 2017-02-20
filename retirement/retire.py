#!/usr/bin/env python
import argparse
import math
import datetime

from target_fund import TargetFund

ANNUAL_RAISE = 3.0


def do_month(salary, contribution, num_years, growth, year, month, fund):
    monthly = (salary / 12.0) * (contribution / 100.0)
    gain = fund.do_month(contribution=monthly)
    inflation_total = fund.total * math.pow(1.0 - (3.22 / 100.0), year)
    print ("Year {}, "
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
            fund.total,
            inflation_total,
            )


def get_fund(num_years, start_with=0.0):
    return TargetFund(target_year=num_years, start_with=start_with)


def main():
    args = parser.parse_args()
    fund = get_fund(args.num_years, args.start_with)
    salary = args.salary
    num_years = args.num_years
    contribution = args.contribution
    growth = args.growth
    for year in range(num_years):
        for month in range(12):
            years_left = num_years - year
            fund.set_years_left(years_left)
            do_month(salary, contribution, num_years, growth, year, month, fund=fund)
        salary *= (1 + (ANNUAL_RAISE / 100.0))




if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Calculate projected investment total each month.')
    parser.add_argument('--salary', type=int, required=True,
        help='Annual salary.')
    parser.add_argument('--contribution', type=int, required=True,
        help='Contribution of salary per month, in percent.')
    parser.add_argument('--num-years', type=int, required=True,
        help='Number of years to save.')
    parser.add_argument('--growth', type=float, default=5.5,
        help='Growth rate, in percentage.')
    parser.add_argument('--start-with', type=int, default=0,
        help='Starting amount.')
    main()