#!/usr/bin/env python
import argparse
import math
import datetime


class Fund(object):
    def __init__(self, growth, start_with=0):
        self.growth = float(growth) / 100.0
        self.total = start_with

    def do_month(self, per_month):
        adding = float(per_month)
        self.total += adding
        gain = self.total * (self.growth / 12.0) + 1.0
        self.total += gain
        return gain


def retire(per_month, num_years, growth, start_with=0.0):
    fund = Fund(growth=growth, start_with=start_with)
    for year in range(num_years):
        for month in range(0, 12):
            gain = fund.do_month(per_month=per_month)
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
                    per_month,
                    gain,
                    fund.total,
                    inflation_total,
                    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Calculate projected investment total each month.')
    parser.add_argument('--per-month', type=int, required=True,
        help='Amount to save per month, in dollars.')
    parser.add_argument('--num-years', type=int, required=True,
        help='Number of years to save.')
    parser.add_argument('--growth', type=float, default=5.5,
        help='Growth rate, in percentage.')
    parser.add_argument('--start-with', type=int, default=0,
        help='Starting amount.')
    args = parser.parse_args()
    retire(args.per_month, args.num_years, args.growth, args.start_with)
