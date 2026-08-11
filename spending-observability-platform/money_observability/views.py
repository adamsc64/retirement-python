from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Transaction
from .services.ai_categorize import make_ai_categorizations
from .services.categories import (
    CATEGORIES,
    CATEGORY_MANUAL_REVIEW,
    CATEGORY_NAMES,
    CATEGORY_SET,
    KEY_TO_CATEGORY,
)
from .services.category_rules import make_categorizations
from .services.exclusion_rules import make_exclusions
from .services.import_service import import_uploaded_bytes
from .services.loaders import LoaderError

# Fixed exchange rates to USD for the summary report.
# Update these as needed; original transaction currencies are never modified.
FX_TO_USD: dict[str, Decimal] = {
    "USD": Decimal("1.00"),
    "GBP": Decimal("1.27"),
    "EUR": Decimal("1.08"),
}


@login_required(login_url="/admin/login/")
def index(request):
    uncategorized = Transaction.objects.filter(
        category=CATEGORY_MANUAL_REVIEW, excluded=False, direction="debit"
    ).count()
    return render(
        request,
        "money_observability/index.html",
        {"uncategorized": uncategorized},
    )


@login_required(login_url="/admin/login/")
def categorize_queue(request):
    VIEW_ALL = "__all__"
    all_view_categories = [VIEW_ALL] + [CATEGORY_MANUAL_REVIEW] + CATEGORY_NAMES
    view_category = request.GET.get("category", CATEGORY_MANUAL_REVIEW)
    if view_category not in frozenset(all_view_categories):
        view_category = CATEGORY_MANUAL_REVIEW

    start_str = request.GET.get("start", "")
    end_str = request.GET.get("end", "")
    try:
        start = date.fromisoformat(start_str) if start_str else None
    except ValueError:
        start = None
    try:
        end = date.fromisoformat(end_str) if end_str else None
    except ValueError:
        end = None

    SORT_OPTIONS = {
        "date": ("posted_date", "description_clean"),
        "-date": ("-posted_date", "description_clean"),
        "amount": ("amount",),
        "-amount": ("-amount",),
    }
    sort = request.GET.get("sort", "date")
    if sort not in SORT_OPTIONS:
        sort = "date"
    sort_base = sort.lstrip("-")
    sort_dir = "desc" if sort.startswith("-") else "asc"

    qs = Transaction.objects.filter(excluded=False, direction="debit")
    if start:
        qs = qs.filter(posted_date__gte=start)
    if end:
        qs = qs.filter(posted_date__lte=end)
    if view_category != VIEW_ALL:
        qs = qs.filter(category=view_category)

    raw = list(
        qs.order_by(*SORT_OPTIONS[sort]).values(
            "id",
            "posted_date",
            "description_clean",
            "description_raw",
            "amount",
            "currency",
            "source_institution",
            "category",
        )
    )
    for tx in raw:
        tx["display_amount"] = abs(tx["amount"])
        tx["display_desc"] = tx["description_clean"] or tx["description_raw"]

    return render(
        request,
        "money_observability/categorize.html",
        {
            "transactions": raw,
            "categories_with_keys": [
                (c.name, c.shortcut.upper(), c.ai_hint) for c in CATEGORIES
            ],
            "key_to_category_json": json.dumps(KEY_TO_CATEGORY),
            "total_count": len(raw),
            "view_category": view_category,
            "all_view_categories": all_view_categories,
            "view_all_sentinel": VIEW_ALL,
            "sort": sort,
            "sort_base": sort_base,
            "sort_dir": sort_dir,
            "start": start,
            "end": end,
        },
    )


@login_required(login_url="/admin/login/")
@require_http_methods(["POST"])
def assign_category(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON"}, status=400)

    ids = data.get("ids", [])
    category = data.get("category", "")

    if not ids or not isinstance(ids, list):
        return JsonResponse({"error": "ids required"}, status=400)
    if category not in CATEGORY_SET and category != CATEGORY_MANUAL_REVIEW:
        return JsonResponse({"error": "invalid category"}, status=400)
    try:
        ids = [int(i) for i in ids]
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid ids"}, status=400)

    updated = Transaction.objects.filter(
        id__in=ids,
    ).update(
        category=category,
        categorized_at=timezone.now(),
        category_rule_id="manual_ui",
    )
    return JsonResponse({"updated": updated})


@login_required(login_url="/admin/login/")
@require_http_methods(["POST"])
def exclude_transactions(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON"}, status=400)

    ids = data.get("ids", [])
    if not ids or not isinstance(ids, list):
        return JsonResponse({"error": "ids required"}, status=400)
    try:
        ids = [int(i) for i in ids]
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid ids"}, status=400)

    excluded = Transaction.objects.filter(id__in=ids).update(
        excluded=True,
        exclusion_reason="manual_ui",
        exclusion_rule_id="manual_ui",
        excluded_at=timezone.now(),
    )
    return JsonResponse({"excluded": excluded})


@login_required(login_url="/admin/login/")
def annual_expenses(request):
    txs = (
        Transaction.objects.filter(
            excluded=False,
            direction="debit",
            category="Annual",
        )
        .values(
            "id",
            "posted_date",
            "description_clean",
            "description_raw",
            "amount",
            "currency",
        )
        .order_by("-amount")
    )

    rows = []
    total_annual_usd = Decimal(0)
    for tx in txs:
        native_amt = abs(tx["amount"])
        fx = FX_TO_USD.get(tx["currency"], Decimal("1.00"))
        usd = (native_amt * fx).quantize(Decimal("0.01"))
        monthly = (usd / 12).quantize(Decimal("0.01"))
        total_annual_usd += usd
        rows.append(
            {
                "id": tx["id"],
                "date": tx["posted_date"],
                "desc": tx["description_clean"] or tx["description_raw"],
                "native_amount": native_amt.quantize(Decimal("0.01")),
                "currency": tx["currency"],
                "usd": usd,
                "monthly": monthly,
            }
        )

    total_monthly_usd = (total_annual_usd / 12).quantize(Decimal("0.01"))
    total_annual_usd = total_annual_usd.quantize(Decimal("0.01"))

    return render(
        request,
        "money_observability/annual_expenses.html",
        {
            "rows": rows,
            "total_annual_usd": total_annual_usd,
            "total_monthly_usd": total_monthly_usd,
        },
    )


@login_required(login_url="/admin/login/")
def monthly_summary(request):
    # 1. Discover all months that actually have non-excluded transaction data.
    # We want unique year/month pairs, ordered newest first.
    db_months = (
        Transaction.objects.filter(excluded=False)
        .annotate(month=TruncMonth("posted_date"))
        .values_list("month", flat=True)
        .distinct()
        .order_by("-month")
    )

    # 2. Limit to most recent 12 months that have data.
    # If the current month has no data yet, it will naturally be excluded.
    available_months = []
    for m_date in db_months[:12]:
        available_months.append(
            {
                "label": m_date.strftime("%b %Y"),
                "start": m_date.strftime("%Y-%m-%d"),
                # Last day of month
                "end": (
                    m_date.replace(
                        month=m_date.month % 12 + 1,
                        day=1,
                        year=m_date.year + (m_date.month // 12),
                    )
                    - timezone.timedelta(days=1)
                ).strftime("%Y-%m-%d"),
            }
        )

    # Reverse back to "oldest first" for the UI buttons if preferred,
    # but the user said "starting from current month, counting back",
    # so we'll keep the "newest first" order for the buttons.

    # 3. Handle default range if none provided.
    today = date.today()
    default_start = today.replace(day=1)
    if available_months and not request.GET.get("start"):
        # Default to the most recent month with data
        default_start = date.fromisoformat(available_months[0]["start"])
        default_end = date.fromisoformat(available_months[0]["end"])
    else:
        default_end = today

    start_str = request.GET.get("start", default_start.isoformat())
    end_str = request.GET.get("end", default_end.isoformat())
    try:
        start = date.fromisoformat(start_str)
    except ValueError:
        start = default_start
    try:
        end = date.fromisoformat(end_str)
    except ValueError:
        end = default_end

    qs = Transaction.objects.filter(
        excluded=False,
        direction="debit",
        posted_date__gte=start,
        posted_date__lte=end,
    ).values("category", "currency", "amount")

    # Accumulate per category, converting all amounts to USD via FX_TO_USD.
    raw_data: dict = defaultdict(
        lambda: defaultdict(lambda: {"cash": Decimal(0), "count": 0})
    )

    for tx in qs:
        cat = tx["category"] or CATEGORY_MANUAL_REVIEW
        cur = tx["currency"]
        fx = FX_TO_USD.get(cur, Decimal("1.00"))
        amt = abs(tx["amount"]) * fx
        cell = raw_data[cat]["USD"]
        cell["cash"] += amt
        cell["count"] += 1

    # Determine canonical category order: all CATEGORY_NAMES first (even if zero
    # spend), then Manual Review if present, then any unexpected categories.
    ordered_cats = list(CATEGORY_NAMES)
    if CATEGORY_MANUAL_REVIEW in raw_data:
        ordered_cats.append(CATEGORY_MANUAL_REVIEW)
    for cat in sorted(raw_data):
        if cat not in ordered_cats:
            ordered_cats.append(cat)

    # Build rows for template.
    days_in_range = (end - start).days + 1
    annualize = Decimal(365) / Decimal(days_in_range)

    rows = []
    totals: dict[str, dict] = defaultdict(lambda: {"cash": Decimal(0), "count": 0})

    for cat in ordered_cats:
        currency_entries = []
        for cur in sorted(raw_data[cat]) if cat in raw_data else ["USD"]:
            cell = (
                raw_data[cat][cur]
                if cat in raw_data
                else {"cash": Decimal(0), "count": 0}
            )
            currency_entries.append(
                {
                    "currency": cur,
                    "cash": cell["cash"].quantize(Decimal("0.01")),
                    "annualized": (cell["cash"] * annualize).quantize(Decimal("0.01")),
                    "count": cell["count"],
                }
            )
            totals[cur]["cash"] += cell["cash"]
            totals[cur]["count"] += cell["count"]
        rows.append({"category": cat, "entries": currency_entries})

    total_rows = [
        {
            "currency": cur,
            "cash": totals[cur]["cash"].quantize(Decimal("0.01")),
            "annualized": (totals[cur]["cash"] * annualize).quantize(Decimal("0.01")),
            "count": totals[cur]["count"],
        }
        for cur in sorted(totals)
    ]

    return render(
        request,
        "money_observability/monthly_summary.html",
        {
            "start": start,
            "end": end,
            "available_months": available_months,
            "rows": rows,
            "total_rows": total_rows,
        },
    )


@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
def upload_csv(request):
    if request.method == "POST":
        uploaded = request.FILES.getlist("csv_files")
        if not uploaded:
            messages.error(request, "No files selected.")
            return redirect("upload_csv")

        accepted = []
        errors = []
        for f in uploaded:
            if not f.name.lower().endswith(".csv"):
                errors.append(f"{f.name}: only .csv files are accepted.")
                continue
            try:
                summary = import_uploaded_bytes(f.read(), f.name)
            except LoaderError as exc:
                errors.append(f"{f.name}: {exc}")
                continue
            except Exception as exc:
                errors.append(f"{f.name}: unexpected error \u2014 {exc}")
                continue

            if summary.imported > 0:
                note = f"{summary.imported} transaction(s) imported"
            else:
                note = "0 new transactions (already imported)"
            if summary.duplicate:
                note += f", {summary.duplicate} duplicate(s) skipped"
            accepted.append(f"{f.name} ({summary.institution} \u00b7 {note})")

        for msg in errors:
            messages.error(request, msg)
        if accepted:
            results = run_post_import_pipeline()
            pipeline_note = (
                f" Rules applied: {results['exclusions_updated']} exclusions, "
                f"{results['categories_updated']} categories."
            )
            messages.success(
                request,
                f"Processed {len(accepted)} file(s): {', '.join(accepted)}.{pipeline_note}",
            )

        return redirect("upload_csv")

    return render(request, "money_observability/upload.html")


@login_required(login_url="/admin/login/")
def spending_trends(request):
    """Category × month baseline burn table (ordinary spend only, USD)."""
    qs = (
        Transaction.objects.filter(
            excluded=False,
            direction="debit",
        )
        .exclude(category="Annual")
        .annotate(month=TruncMonth("posted_date"))
        .values("category", "month", "currency", "amount")
    )

    # Build grid: category -> month_label -> USD total
    month_dates: dict[str, date] = {}  # label -> date for sorting
    grid: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for tx in qs:
        m = tx["month"]  # date (DateField + TruncMonth)
        label = m.strftime("%b %Y")
        month_dates[label] = m
        cat = tx["category"] or CATEGORY_MANUAL_REVIEW
        fx = FX_TO_USD.get(tx["currency"], Decimal("1.00"))
        grid[cat][label] += abs(tx["amount"]) * fx

    # Chronological order, most recent 12 complete months (drop current/last month)
    month_labels = sorted(month_dates, key=lambda lbl: month_dates[lbl])[:-1][-12:]

    # Build month metadata with date ranges for link generation
    def _month_end(d: date) -> date:
        from datetime import timedelta

        if d.month == 12:
            return d.replace(year=d.year + 1, month=1, day=1) - timedelta(days=1)
        return d.replace(month=d.month + 1, day=1) - timedelta(days=1)

    months = [
        {
            "label": lbl,
            "start": month_dates[lbl].isoformat(),
            "end": _month_end(month_dates[lbl]).isoformat(),
        }
        for lbl in month_labels
    ]

    # Canonical category order — only categories that have any spend
    ordered_cats = [c for c in CATEGORY_NAMES if c in grid]
    if CATEGORY_MANUAL_REVIEW in grid:
        ordered_cats.append(CATEGORY_MANUAL_REVIEW)

    totals: dict[str, Decimal] = defaultdict(Decimal)
    rows = []
    for cat in ordered_cats:
        cells = []
        prior_had_spend = False
        for i, label in enumerate(month_labels):
            amt = grid[cat].get(label, Decimal(0)).quantize(Decimal("0.01"))
            totals[label] += amt
            if i == 0 or amt == grid[cat].get(month_labels[i - 1], Decimal(0)).quantize(
                Decimal("0.01")
            ):
                delta = None
            else:
                prev = grid[cat].get(month_labels[i - 1], Decimal(0))
                if prev == 0 and amt > 0:
                    delta = "new" if not prior_had_spend else "up"
                elif amt == 0:
                    delta = "gone"
                elif amt > prev * Decimal("1.05"):
                    delta = "up"
                elif amt < prev * Decimal("0.95"):
                    delta = "down"
                else:
                    delta = "same"
            if amt > 0:
                prior_had_spend = True
            cells.append(
                {
                    "amt": amt,
                    "delta": delta,
                    "start": months[i]["start"],
                    "end": months[i]["end"],
                }
            )
        annual_est = (
            (sum(c["amt"] for c in cells) / len(months) * 12).quantize(Decimal("0.01"))
            if months
            else Decimal(0)
        )
        rows.append({"category": cat, "cells": cells, "annual_est": annual_est})

    total_annual_est = (
        (sum(totals[lbl] for lbl in month_labels) / len(months) * 12).quantize(
            Decimal("0.01")
        )
        if months
        else Decimal(0)
    )
    total_cells = [
        {"amt": totals[lbl].quantize(Decimal("0.01")), "delta": None}
        for lbl in month_labels
    ]

    return render(
        request,
        "money_observability/trends.html",
        {
            "months": months,
            "rows": rows,
            "total_cells": total_cells,
            "total_annual_est": total_annual_est,
        },
    )


def run_post_import_pipeline(
    rules_path: Path | None = None,
) -> dict[str, int]:
    """
    Orchestrate the full suite of post-import tasks.
    Used for bulk processing after a new import.
    """
    exclusions_updated = make_exclusions(rules_path=rules_path)
    categories_updated = make_categorizations(rules_path=rules_path)
    ai_updated = make_ai_categorizations()

    return {
        "exclusions_updated": len(exclusions_updated),
        "categories_updated": len(categories_updated),
        "ai_updated": len(ai_updated),
    }
