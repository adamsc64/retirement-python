from collections import namedtuple

STOCK_YIELD = 5.5 / 100.0
BOND_YIELD = 2.0 / 100.0

YearAllocation = namedtuple('YearAllocation', ['years', 'stocks', 'bonds'])


class Vanguard(object):
    ALLOCATION = [YearAllocation(years=50, stocks=90.1, bonds=9.9),
                  YearAllocation(years=45, stocks=90.1, bonds=9.9),
                  YearAllocation(years=40, stocks=90.1, bonds=9.9),
                  YearAllocation(years=35, stocks=90.1, bonds=9.9),
                  YearAllocation(years=30, stocks=90.1, bonds=9.9),
                  YearAllocation(years=25, stocks=86.0, bonds=14.0),
                  YearAllocation(years=20, stocks=78.5, bonds=21.5),
                  YearAllocation(years=15, stocks=71.0, bonds=29.0),
                  YearAllocation(years=10, stocks=63.6, bonds=36.4),
                  YearAllocation(years=5, stocks=55.1, bonds=44.9),
                  YearAllocation(years=0, stocks=42.1, bonds=56.9),
                  ]

    def __init__(self, target_year):
        self.target_year = target_year

    def get_allocation(self, years_to_go):
        for year_allocation in reversed(self.ALLOCATION):
            if years_to_go <= year_allocation.years:
                return year_allocation
        return year_allocation

    def get_yield(self, year_allocation):
        stock_part = (year_allocation.stocks / 100.0) * (STOCK_YIELD)
        bond_part = (year_allocation.bonds / 100.0) * (BOND_YIELD)
        return stock_part + bond_part