#!/usr/bin/env python
"""
Finds recent recurring banking transactions and prints them to stdout.

Source files are tab-separated transaction files from Citibank web.

Example usage:
    $ ./recurring_charges.py data/*
"""
from collections import defaultdict, namedtuple
import argparse
import datetime
import os
import re
import sys

import dateutil.parser


REPEAT_NUMBER = 3


def load(tsv_files):
    repeating = defaultdict(list)
    for tsv_file in tsv_files:
        with open(tsv_file, mode="r") as infile:
            last4 = get_account_last4(tsv_file)
            if last4 is None:
                raise Exception(f"no last4 - not valid {tsv_file}")
            Transaction = namedtuple("Transaction", (get_columns(next(infile)) + ["account"]))
            while True:
                try:
                    raw_row = next(infile)
                    transaction = Transaction(*(get_columns(raw_row) + [last4]))
                except TypeError:
                    import ipdb; ipdb.set_trace()  # noqa
                    pass
                except StopIteration:
                    break
                charger = transaction.Description
                amount = (
                    transaction.Debit
                    if "Debit" in transaction._fields
                    else transaction.Amount
                )
                if amount == "":
                    continue
                if amount.startswith("-"):
                    continue
                key = charger, amount
                repeating[key].append(transaction)
    exclude_few_transactions(repeating)
    exclude_non_current(repeating)
    return repeating


def get_columns(raw_row):
    items = raw_row.split("\t\t")
    items = [item.strip() for item in items]
    return items


def get_account_last4(filename):
    matched = re.search(r"\d{4}", filename)
    if not matched:
        return None
    return matched.group()


def exclude_few_transactions(repeating):
    few_transactions = list()
    for key, transactions in repeating.items():
        if len(transactions) < REPEAT_NUMBER:
            few_transactions.append(key)
    for key in few_transactions:
        del repeating[key]


def exclude_non_current(repeating):
    non_current = list()
    most_recent = None
    for _, transactions in repeating.items():
        for transaction in transactions:
            date = dateutil.parser.parse(transaction.Date).date()
            if most_recent is None or date > most_recent:
                most_recent = date
    for key, transactions in repeating.items():
        dates = [dateutil.parser.parse(t.Date).date()
                 for t in transactions]
        if not any([d > most_recent - datetime.timedelta(days=60)
                    for d in dates]):
            non_current.append(key)
    for key in non_current:
        del repeating[key]


def main(args):
    repeating = load(args.tsv_files)
    for key, transactions in repeating.items():
        charger, amount = key
        amount = amount.lstrip("$")
        amount = amount.strip()
        print(f"{charger:<50}| ${amount:>7}")
        if args.dates:
            for transaction in transactions:
                print(f"- {transaction.Date}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('tsv_files', type=str, nargs='+',
                        help='Citibank tab-separated files to process',
                        )
    parser.add_argument('--dates')
    args = parser.parse_args()
    main(args)
