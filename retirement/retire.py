#!/usr/bin/env python
import argparse
import math
import datetime


def retire(per_month, num_years, growth, start_with=0.0):
    growth = float(growth) / 100.0
    total = start_with
    for year in range(num_years):
        for month in range(0, 12):
            adding = float(per_month)
            total += adding
            gain = total * (growth / 12.0) + 1.0
            total += gain
            inflation_total = total * math.pow(1.0 - (3.22 / 100.0), year)
            print ("Year {}, "
                   "Month {}, "
                   "Adding: ${:,.2f}, "
                   "Gain: ${:,.2f}, "
                   "Total: ${:,.2f} "
                   "(Inflation-Adusted: ${:,.2f})"
                   ).format(
                    year + 1,
                    month + 1,
                    adding,
                    gain,
                    total,
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
