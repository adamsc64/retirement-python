#!/usr/bin/env python
import argparse
import math
import datetime

from vanguard import Vanguard

ANNUAL_RAISE = 3.0


class Fund(object):
    def __init__(self, growth, start_with=0):
        self.growth = growth
        self.total = start_with

    def do_month(self, contribution, yields):
        adding = float(contribution)
        self.total += adding
        gain = self.total * yields
        gain = (int(gain * 100.0) / 100.0)
        self.total += gain
        return gain


def retire(salary, contribution, num_years, growth, start_with=0.0):
    vanguard = Vanguard(target_year=num_years)
    fund = Fund(growth=vanguard, start_with=start_with)
    for year in range(num_years):
        salary *= (1 + (ANNUAL_RAISE / 100.0))
        for month in range(0, 12):
            year_allocation = vanguard.get_allocation(num_years - year)
            yields_per_year = vanguard.get_yield(year_allocation)
            yields_per_month = yields_per_year / 12.0
            monthly = (salary / 12.0) * (contribution / 100.0)
            gain = fund.do_month(contribution=monthly, yields=yields_per_month)
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
    args = parser.parse_args()
    retire(args.salary, args.contribution, args.num_years, args.growth, args.start_with)
