#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import os
import random
import sys


RETURNS = """
year,stock_total_return,t_bond_10y_total_return,inflation_rate
1928,0.438111551528879,0.00835470858979919,-0.01724137931034464
1929,-0.0829794661190966,0.0420380415632043,0.0
1930,-0.251236363636364,0.0454093143489704,-0.023391812865497186
1931,-0.438375488917862,-0.0255885596194225,-0.08982035928143717
1932,-0.086423645320197,0.0879030699047733,-0.09868421052631582
1933,0.49982225433526,0.0185527208918574,-0.05109489051094884
1934,-0.0118856569709128,0.0796344261796561,0.030769230769230882
1935,0.467404210526316,0.0447204772965661,0.02238805970149249
1936,0.319434102755026,0.0501787540454508,0.014598540145985384
1937,-0.353367287543655,0.0137914605964605,0.03597122302158273
1938,0.29282654028436,0.0421324853220461,-0.02083333333333337
1939,-0.0109756468797564,0.0441226139420607,-0.014184397163120477
1940,-0.106728731942215,0.0540248159628455,0.007194244604316502
1941,-0.127714555765596,-0.0202219758485802,0.050000000000000044
1942,0.191737629459148,0.0229486823744842,0.10884353741496611
1943,0.250613101330604,0.0249,0.06134969325153383
1944,0.19030676949443,0.0257761115790703,0.01734104046242768
1945,0.358210843373494,0.0380441734192372,0.022727272727272707
1946,-0.0842914746543778,0.0312837453756957,0.08333333333333326
1947,0.052,0.00919696806283213,0.14358974358974352
1948,0.0570457516339868,0.019510369413175,0.08071748878923768
1949,0.183032236842105,0.0466348518279731,-0.012448132780083054
1950,0.308055390113163,0.00429595741710961,0.012605042016806678
1951,0.236784630445423,-0.00295313922083199,0.07883817427385886
1952,0.181509886411443,0.0226799619183057,0.019230769230769162
1953,-0.0120820474219045,0.0414384025890885,0.007547169811320753
1954,0.525633212414349,0.0328980345580956,0.0074906367041198685
1955,0.325973318510284,-0.0133643912886187,-0.0037174721189590088
1956,0.0743951187335094,-0.0225577381731542,0.014925373134328401
1957,-0.10457360188558,0.0679701284662501,0.03308823529411775
1958,0.437199549887472,-0.0209901817552747,0.028469750889679624
1959,0.120564571635573,-0.0264663125913851,0.006920415224913601
1960,0.00336535314743695,0.116395036909634,0.01718213058419238
1961,0.266377129581828,0.0206092080763232,0.010135135135135087
1962,-0.0881146051712089,0.0569354405400844,0.010033444816053505
1963,0.226119270998415,0.0168416207395461,0.013245033112582849
1964,0.164154558784324,0.0372806489115408,0.013071895424836555
1965,0.123992424778761,0.00718855093592635,0.016129032258064502
1966,-0.0997095423563779,0.0290794093242996,0.02857142857142847
1967,0.238029665131333,-0.0158062099328247,0.030864197530864113
1968,0.108148626516015,0.0327461969507684,0.041916167664670656
1969,-0.0824137107644906,-0.0501404932099261,0.054597701149425415
1970,0.0356114490549642,0.167547371834123,0.05722070844686633
1971,0.142211502984265,0.097868966197123,0.04381443298969079
1972,0.187553629150749,0.0281844905044498,0.032098765432098775
1973,-0.143080474375265,0.0365866460241501,0.062200956937799035
1974,-0.25901785750897,0.0198860869323786,0.11036036036036023
1975,0.369951371061844,0.0360525360260337,0.09127789046653145
1976,0.238309990021067,0.159845607429092,0.05762081784386619
1977,-0.0697970407593523,0.0128996060710706,0.06502636203866441
1978,0.0650928391167193,-0.00777580690750876,0.07590759075907583
1979,0.185194901675164,0.00670720312472355,0.11349693251533721
1980,0.31735245506763,-0.0298974425199941,0.13498622589531695
1981,-0.0470239024749558,0.0819921533589235,0.10315533980582514
1982,0.204190550795594,0.328145494862956,0.06160616061606161
1983,0.223371558589306,0.0320020944514293,0.032124352331606154
1984,0.0614614199963621,0.137333643441024,0.0431726907630523
1985,0.31235149485769,0.257124882126064,0.03561116458132818
1986,0.184945787580462,0.242842151417676,0.018587360594795488
1987,0.0581272164182187,-0.0496050893792625,0.03649635036496357
1988,0.165371928120447,0.0822359584348417,0.041373239436619746
1989,0.314751836381967,0.176936471594462,0.048182586644125225
1990,-0.0306445161290321,0.0623537533355336,0.05403225806451606
1991,0.302348431348798,0.150045100195173,0.0420811017597551
1992,0.0749372797238006,0.0936163731620794,0.03010279001468441
1993,0.0996705147919488,0.142109575892631,0.029935851746258013
1994,0.0132592067745739,-0.080366555509986,0.02560553633217988
1995,0.371951989026063,0.234807801125389,0.028340080971660075
1996,0.226809660188658,0.0142860779340184,0.029527559055118058
1997,0.331036531036531,0.0993913027297753,0.02294455066921608
1998,0.283379532784436,0.149214319226062,0.015576323987538832
1999,0.208853509920845,-0.0825421479626858,0.02208588957055202
2000,-0.0903181895524928,0.166552671253975,0.03361344537815114
2001,-0.118497591420002,0.0557218118924926,0.028455284552845628
2002,-0.219660479579127,0.151164003781093,0.015810276679842028
2003,0.283558000500102,0.00375318588177585,0.022790439132851503
2004,0.107427759440962,0.0449068370227455,0.026630434782608736
2005,0.0483447752326885,0.0286753295977795,0.03388035997882488
2006,0.156125579793157,0.0196100124175684,0.032258064516129004
2007,0.0548473524642177,0.102099219300128,0.0284821428571429
2008,-0.365523441117982,0.20101279926977,0.03839550115268486
2009,0.25935233877664,-0.111166953132592,-0.003557776714676497
2010,0.148210922787194,0.0846293388035575,0.016402765024214894
2011,0.0209837473362805,0.160353349994613,0.0315652859815827
2012,0.158905852417303,0.0297157197801895,0.020694499397614363
2013,0.321450858581255,-0.0910456879434727,0.014647595320435247
2014,0.135244216494622,0.107461804520047,0.016221877857286904
2015,0.0137889164116761,0.0128429967097922,0.0011869762097864722
2016,0.117730808747982,0.00690550469874779,0.012615128872612624
2017,0.216054814344993,0.0280171627077895,0.02130354531326173
2018,-0.0422686928908854,-0.000166923857134026,0.02442477154046996
2019,0.312116799968088,0.0963563074154839,0.01811976567757978
2020,0.180232018274225,0.113318976466141,0.012336841940568721
2021,0.284688517519642,-0.0441603444860448,0.04698022881562247
2022,-0.180375059271786,-0.178281715382506,0.08002730929623181
2023,0.260606849850241,0.0388,0.04116451111376884
2024,0.248786112625267,-0.0163718014366298,0.029494391241278395
2025,0.177236582375974,0.077954808707674,0.02631268549423149
"""

MIN_YEARS_REMAINING = 1
DEFAULT_STOCK_WEIGHT = 0.75
DEFAULT_FIRST_YEAR_SPEND_RATE = 0.05
MAX_GAME_YEARS = 40

GAME_TITLE = "Retirement Time Machine"
ASCII_ART = r"""
  ____      _   _                                _     _______ _                 __  __            _     _
 |  _ \ ___| |_(_)_ __ ___ _ __ ___   ___ _ __ | |_  |_   _(_) | ___   ___     |  \/  | __ _  ___| |__ (_)_ __   ___
 | |_) / _ \ __| | '__/ _ \ '_ ` _ \ / _ \ '_ \| __|   | | | | |/ _ \ / _ \    | |\/| |/ _` |/ __| '_ \| | '_ \ / _ \
 |  _ <  __/ |_| | | |  __/ | | | | |  __/ | | | |_    | | | | | (_) |  __/    | |  | | (_| | (__| | | | | | | |  __/
 |_| \_\___|\__|_|_|  \___|_| |_| |_|\___|_| |_|\__|   |_| |_|_|\___/ \___|    |_|  |_|\__,_|\___|_| |_|_|_| |_|\___|
"""


USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
RESET = "\033[0m" if USE_COLOR else ""
BOLD = "\033[1m" if USE_COLOR else ""
DIM = "\033[2m" if USE_COLOR else ""
CYAN = "\033[36m" if USE_COLOR else ""
GREEN = "\033[32m" if USE_COLOR else ""
RED = "\033[31m" if USE_COLOR else ""
YELLOW = "\033[33m" if USE_COLOR else ""
MAGENTA = "\033[35m" if USE_COLOR else ""


def load_market_data() -> list[dict[str, float | int]]:
    reader = csv.DictReader(RETURNS.strip().splitlines())
    rows = []
    for row in reader:
        rows.append(
            {
                "year": int(row["year"]),
                "stock_return": float(row["stock_total_return"]),
                "bond_return": float(row["t_bond_10y_total_return"]),
                "inflation_rate": float(row["inflation_rate"]),
            }
        )
    if len(rows) < MIN_YEARS_REMAINING:
        raise ValueError("Not enough data rows to support the game.")
    return rows


def parse_shorthand_number(raw: str) -> float:
    cleaned = raw.strip().lower().replace(",", "").replace("$", "")
    multiplier = 1.0
    if cleaned.endswith("k"):
        multiplier = 1_000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("m"):
        multiplier = 1_000_000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("b"):
        multiplier = 1_000_000_000.0
        cleaned = cleaned[:-1]
    return float(cleaned) * multiplier


def prompt_float(
    prompt: str, minimum: float | None = None, maximum: float | None = None
) -> float:
    while True:
        try:
            value = parse_shorthand_number(input(prompt))
        except ValueError:
            print("Please enter a number.")
            continue

        if minimum is not None and value < minimum:
            print(f"Please enter a value greater than or equal to {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Please enter a value less than or equal to {maximum}.")
            continue
        return value


def prompt_stock_allocation() -> float:
    while True:
        raw = input(
            "What is your stock allocation? Press Enter for 75/25, or enter a stock percentage like 75 or 75/25: "
        ).strip()
        if not raw:
            return DEFAULT_STOCK_WEIGHT
        parsed = parse_stock_allocation(raw)
        if parsed is not None:
            return parsed
        print("Please enter something like 80 or 80/20.")


def parse_stock_allocation(raw: str) -> float | None:
    text = raw.strip()
    if "/" in text:
        stock_part, _, bond_part = text.partition("/")
        try:
            stock_pct = float(stock_part.strip())
            bond_pct = float(bond_part.strip())
        except ValueError:
            return None
        total = stock_pct + bond_pct
        if total <= 0:
            return None
        return stock_pct / total

    cleaned = text.replace("%", "").strip()
    try:
        stock_pct = float(cleaned)
    except ValueError:
        return None

    if 0 <= stock_pct <= 1:
        return stock_pct
    if 0 <= stock_pct <= 100:
        return stock_pct / 100.0
    return None


def select_start_index(
    rows: list[dict[str, float | int]],
    start_year: int | None = None,
) -> int:
    if start_year is not None:
        for idx, row in enumerate(rows):
            if int(row["year"]) == start_year:
                return idx
        raise ValueError(f"Start year {start_year} is not in the dataset.")

    return random.randint(0, len(rows) - 1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Retirement Time Machine simulation.",
    )
    parser.add_argument(
        "--net-worth",
        type=str,
        help="Starting net worth. Supports shorthand like 1.5m, 800k, or 2500000.",
    )
    parser.add_argument(
        "--stock-allocation",
        type=str,
        help="Stock allocation as 0-1, 0-100, or ratio (examples: 0.75, 75, 75/25).",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        help="Force a specific starting year from the embedded dataset.",
    )
    parser.add_argument(
        "--max-years",
        type=int,
        default=None,
        help=(
            "Maximum number of years to simulate. "
            "Defaults to all available years from the selected start year."
        ),
    )
    parser.add_argument(
        "--strategy",
        choices=["guardrails"],
        default=None,
        help="Strategy mode. 'guardrails' runs Guyton-Klinger guardrail rules automatically.",
    )
    return parser


def gk_spend(net_worth: float, last_spend: float | None) -> float:
    rules = [
        {"threshold": 0.04, "condition": "__lt__", "adjustment": +0.10},
        {"threshold": 0.06, "condition": "__gt__", "adjustment": -0.10},
    ]
    if last_spend is None:
        return net_worth * DEFAULT_FIRST_YEAR_SPEND_RATE
    rate = last_spend / net_worth if net_worth > 0 else 0.0
    spend = last_spend
    for rule in rules:
        if getattr(rate, rule["condition"])(rule["threshold"]):
            spend *= 1.0 + rule["adjustment"]
    return spend


def calculate_real_return(
    stock_weight: float, stock_return: float, bond_return: float, inflation_rate: float
) -> float:
    bond_weight = 1.0 - stock_weight
    nominal_return = (stock_weight * stock_return) + (bond_weight * bond_return)
    return ((1.0 + nominal_return) / (1.0 + inflation_rate)) - 1.0


def format_money(amount: float) -> str:
    return f"${amount:,.2f}"


def format_percent(value: float) -> str:
    return f"{value:.2%}"


def format_signed_percent(value: float) -> str:
    return f"{value:+.2%}"


def style(text: str, *codes: str) -> str:
    if not USE_COLOR or not codes:
        return text
    return f"{''.join(codes)}{text}{RESET}"


def format_return_label(value: float) -> str:
    color = GREEN if value >= 0 else RED
    return style(format_signed_percent(value), BOLD, color)


def print_summary_table(history: list[dict[str, float | int]]) -> None:
    if not history:
        return

    headers = ["year", "portfolio", "return", "spending", "spend % of portfolio"]
    rows = [
        [
            str(int(entry["year"])),
            format_money(float(entry["portfolio"])),
            format_signed_percent(float(entry["return"])),
            format_money(float(entry["spending"])),
            format_percent(float(entry["spend_pct"])),
        ]
        for entry in history
    ]
    widths = [
        max(len(header), max(len(row[idx]) for row in rows))
        for idx, header in enumerate(headers)
    ]

    print()
    print(style("=" * 72, CYAN))
    print(style("FINAL SUMMARY", BOLD, CYAN))
    print(style("All return figures are real returns, after inflation.", DIM))
    print(style("=" * 72, CYAN))
    print(" | ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)))


def print_notable_stats(history: list[dict[str, float | int]]) -> None:
    if not history:
        return

    lowest_spending = min(history, key=lambda entry: float(entry["spending"]))
    highest_spending = max(history, key=lambda entry: float(entry["spending"]))
    lowest_portfolio = min(history, key=lambda entry: float(entry["portfolio"]))
    highest_portfolio = max(history, key=lambda entry: float(entry["portfolio"]))

    print()
    print(style("Notable moments", BOLD, MAGENTA))
    print(
        f"Lowest spending: {format_money(float(lowest_spending['spending']))} "
        f"in {int(lowest_spending['year'])}"
    )
    print(
        f"Highest spending: {format_money(float(highest_spending['spending']))} "
        f"in {int(highest_spending['year'])}"
    )
    print(
        f"Lowest portfolio value: {format_money(float(lowest_portfolio['portfolio']))} "
        f"in {int(lowest_portfolio['year'])}"
    )
    print(
        f"Highest portfolio value: {format_money(float(highest_portfolio['portfolio']))} "
        f"in {int(highest_portfolio['year'])}"
    )


def parse_spending_input(
    raw: str, current_net_worth: float, last_spend: float | None
) -> float | None:
    cleaned = raw.strip().lower().replace(",", "").replace("$", "")
    if cleaned == "":
        if last_spend is None:
            return current_net_worth * DEFAULT_FIRST_YEAR_SPEND_RATE
        return last_spend
    if cleaned.endswith("%"):
        try:
            percentage = float(cleaned[:-1].strip())
        except ValueError:
            return None
        if cleaned.startswith(("+", "-")):
            if last_spend is None:
                return None
            return last_spend * (1.0 + (percentage / 100.0))
        return current_net_worth * (percentage / 100.0)

    try:
        amount = parse_shorthand_number(cleaned)
    except ValueError:
        return None
    if cleaned.startswith(("+", "-")):
        if last_spend is None:
            return None
        return last_spend + amount
    return amount


def resolve_net_worth(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> float:
    if args.net_worth is None:
        return prompt_float("What is your net worth? ", minimum=0.0)
    try:
        net_worth = parse_shorthand_number(args.net_worth)
    except ValueError:
        parser.error(
            "--net-worth must be a valid number (for example: 1500000 or 1.5m)."
        )
    if net_worth < 0:
        parser.error("--net-worth must be greater than or equal to 0.")
    return net_worth


def resolve_stock_weight(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> float:
    if args.stock_allocation is None:
        return prompt_stock_allocation()
    parsed = parse_stock_allocation(args.stock_allocation)
    if parsed is None:
        parser.error("--stock-allocation must be like 75, 0.75, or 75/25.")
    return parsed


def print_intro(
    rows: list[dict[str, float | int]],
    start_index: int,
    available_years: int,
    stock_weight: float,
    strategy: str | None,
) -> None:
    print(style(ASCII_ART, CYAN))
    print(style(GAME_TITLE, BOLD, CYAN))
    print("Loaded embedded market return data.")
    print("Run a spending strategy through a hidden slice of market history.")
    print(
        "All portfolio returns shown in the game are real returns, meaning inflation-adjusted."
    )
    start_year_label = int(rows[start_index]["year"])
    end_year_label = int(rows[-1]["year"])
    print(
        f"Loaded a historical sequence from {start_year_label} to {end_year_label} "
        f"({available_years} years available from the start point)."
    )
    bond_weight = 1.0 - stock_weight
    print(
        f"Using allocation: {style(f'{stock_weight:.0%} stocks / {bond_weight:.0%} bonds', BOLD, YELLOW)}"
    )
    if strategy == "guardrails":
        print("Running Guyton-Klinger guardrail strategy automatically.")
    else:
        print("Each year, enter how much you want to spend.")
        print(
            "You can enter a dollar amount (negative to save), a percent of net worth like 6% or -3%, "
            "a change from last year like +10% / -10%, or press Enter."
        )
        print("Type 'q', 'quit', or 'end' when you want to end the game.")


def prompt_spend(net_worth: float, last_spend: float | None) -> float | None:
    """Returns spend amount, or None if the user quits."""
    while True:
        if last_spend is None:
            print("  (Press Enter for 5% of net worth.)")
        else:
            print(f"  (Press Enter to repeat {format_money(last_spend)}.)")
        spend_raw = input("What would you like to spend this year? ").strip().lower()
        if spend_raw in {"q", "quit", "exit", "end"}:
            return None
        spend = parse_spending_input(spend_raw, net_worth, last_spend)
        if spend is not None:
            return spend
        if last_spend is None:
            print(
                "Please enter a dollar amount like 60000, a percentage like 6%, press Enter for 5%, or 'q' to quit."
            )
        else:
            print(
                "Please enter a dollar amount, a percentage like 6%, a change like +10% or -10%, press Enter to reuse last year's spending, or 'q' to quit."
            )


def apply_year_return(
    row: dict[str, float | int],
    net_worth: float,
    spend: float,
    stock_weight: float,
    year: int,
    year_number: int,
    history: list[dict[str, float | int]],
) -> float | None:
    """Withdraws spend, applies market return, records history. Returns new net_worth or None if bankrupt."""
    if spend < 0:
        print(
            f"You will save {style(format_money(-spend), BOLD, GREEN)} this year (net income)."
        )
    else:
        print(f"You will spend {style(format_money(spend), BOLD, YELLOW)} this year.")
    print(style("-" * 72, DIM))
    print(style("Applying this year's market results...", BOLD, MAGENTA))

    spend_pct = spend / net_worth if net_worth > 0 else 0.0
    net_worth -= spend
    if net_worth <= 0:
        print(style(f"You ran out of money during year {year_number}.", BOLD, RED))
        return None

    stock_return = float(row["stock_return"])
    bond_return = float(row["bond_return"])
    inflation_rate = float(row["inflation_rate"])
    bond_weight = 1.0 - stock_weight
    nominal_return = (stock_weight * stock_return) + (bond_weight * bond_return)
    real_return = calculate_real_return(
        stock_weight=stock_weight,
        stock_return=stock_return,
        bond_return=bond_return,
        inflation_rate=inflation_rate,
    )
    history.append(
        {
            "year": year,
            "portfolio": net_worth + spend,
            "spending": spend,
            "spend_pct": spend_pct,
            "return": real_return,
        }
    )
    net_worth *= 1.0 + real_return

    print(
        f"Stocks returned {format_return_label(stock_return)} and bonds returned {format_return_label(bond_return)}."
    )
    print(
        f"Your {stock_weight:.0%}/{bond_weight:.0%} mix produced a nominal return of {format_return_label(nominal_return)}."
    )
    print(
        f"Inflation was {format_percent(inflation_rate)}, so the real return was "
        f"((1 + {nominal_return:.4f}) / (1 + {inflation_rate:.4f})) - 1 = {format_return_label(real_return)}."
    )
    print(f"End-of-year net worth: {style(format_money(net_worth), BOLD)}")

    if net_worth <= 0:
        print(
            style(
                f"You ran out of money after year {year_number}'s return was applied.",
                BOLD,
                RED,
            )
        )
        return None
    return net_worth


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.max_years is not None and args.max_years <= 0:
        parser.error("--max-years must be greater than 0.")

    rows = load_market_data()
    try:
        start_index = select_start_index(rows, start_year=args.start_year)
    except ValueError as exc:
        parser.error(str(exc))
    available_years = len(rows) - start_index
    max_years = (
        available_years
        if args.max_years is None
        else min(args.max_years, available_years)
    )

    net_worth = resolve_net_worth(args, parser)
    stock_weight = resolve_stock_weight(args, parser)
    print_intro(rows, start_index, available_years, stock_weight, args.strategy)

    year_index = start_index
    last_spend: float | None = None
    history: list[dict[str, float | int]] = []
    while year_index < len(rows) and (year_index - start_index) < max_years:
        row = rows[year_index]
        year = int(row["year"])
        year_number = (year_index - start_index) + 1
        print()
        print(style(f"Year {year_number}", BOLD, CYAN))
        print(f"Current net worth: {style(format_money(net_worth), BOLD)}")
        if last_spend is not None:
            spending_rate = (last_spend / net_worth) * 100 if net_worth > 0 else 0.0
            print(
                f"Last year's spending: {style(format_money(last_spend), YELLOW)} ({style(f'{spending_rate:.2f}%', BOLD)} of current net worth)"
            )

        if args.strategy == "guardrails":
            spend = gk_spend(net_worth, last_spend)
        else:
            spend = prompt_spend(net_worth, last_spend)
            if spend is None:
                print(
                    f"Game ended after year {year_number - 1} with {style(format_money(net_worth), BOLD)} remaining."
                )
                print_summary_table(history)
                print_notable_stats(history)
                return

        net_worth = apply_year_return(
            row, net_worth, spend, stock_weight, year, year_number, history
        )
        if net_worth is None:
            print_summary_table(history)
            print_notable_stats(history)
            return
        last_spend = spend
        year_index += 1

    print(
        f"You reached the end of year {max_years} with {style(format_money(net_worth), BOLD, GREEN)} remaining."
    )
    print_summary_table(history)
    print_notable_stats(history)


if __name__ == "__main__":
    main()
