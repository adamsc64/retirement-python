import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import BudgetTreatment, Transaction
from .services.categories import (
    CATEGORIES,
    CATEGORY_MANUAL_REVIEW,
    CATEGORY_NAMES,
    CATEGORY_SET,
    CATEGORY_TO_KEY,
    KEY_TO_CATEGORY,
)


@login_required(login_url="/admin/login/")
def index(request):
    total = Transaction.objects.filter(excluded=False, direction="debit").count()
    uncategorized = Transaction.objects.filter(
        category=CATEGORY_MANUAL_REVIEW, excluded=False, direction="debit"
    ).count()
    categorized = total - uncategorized
    pct = round(100 * categorized / total) if total else 0
    return render(
        request,
        "money_observability/index.html",
        {
            "total": total,
            "uncategorized": uncategorized,
            "categorized": categorized,
            "pct": pct,
        },
    )


@login_required(login_url="/admin/login/")
def categorize_queue(request):
    VIEW_ALL = "__all__"
    all_view_categories = [VIEW_ALL] + [CATEGORY_MANUAL_REVIEW] + CATEGORY_NAMES
    view_category = request.GET.get("view_category", CATEGORY_MANUAL_REVIEW)
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

    qs = Transaction.objects.filter(excluded=False, direction="debit")
    if start:
        qs = qs.filter(posted_date__gte=start)
    if end:
        qs = qs.filter(posted_date__lte=end)
    if view_category != VIEW_ALL:
        qs = qs.filter(category=view_category)

    raw = list(
        qs.order_by("posted_date", "description_clean")
        .values(
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
            "categories_with_keys": [(c.name, c.shortcut.upper()) for c in CATEGORIES],
            "key_to_category_json": json.dumps(KEY_TO_CATEGORY),
            "total_count": len(raw),
            "view_category": view_category,
            "all_view_categories": all_view_categories,
            "view_all_sentinel": VIEW_ALL,
            "show_category": view_category == VIEW_ALL,
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
def monthly_summary(request):
    today = date.today()
    default_start = today.replace(day=1)
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
    ).values("category", "currency", "budget_treatment", "amount")

    # Accumulate per (category, currency).
    # Shape: {category: {currency: {"cash": D, "baseline": D, "planning": D, "count": int}}}
    raw_data: dict = defaultdict(lambda: defaultdict(lambda: {
        "cash": Decimal(0),
        "baseline": Decimal(0),
        "planning": Decimal(0),
        "count": 0,
    }))

    for tx in qs:
        cat = tx["category"] or CATEGORY_MANUAL_REVIEW
        cur = tx["currency"]
        amt = abs(tx["amount"])
        bt = tx["budget_treatment"]
        cell = raw_data[cat][cur]
        cell["cash"] += amt
        cell["count"] += 1
        if bt == BudgetTreatment.ORDINARY:
            cell["baseline"] += amt
            cell["planning"] += amt
        elif bt == BudgetTreatment.ANNUAL:
            cell["planning"] += amt / 12
        elif bt == BudgetTreatment.IRREGULAR:
            cell["planning"] += amt / 12
        # ONE_OFF and UNKNOWN do not contribute to baseline or planning

    # Determine canonical category order: CATEGORY_NAMES first, then Manual Review, then anything else.
    ordered_cats = [c for c in CATEGORY_NAMES if c in raw_data]
    if CATEGORY_MANUAL_REVIEW in raw_data:
        ordered_cats.append(CATEGORY_MANUAL_REVIEW)
    for cat in sorted(raw_data):
        if cat not in ordered_cats:
            ordered_cats.append(cat)

    # Build rows for template.
    rows = []
    totals: dict[str, dict] = defaultdict(lambda: {
        "cash": Decimal(0), "baseline": Decimal(0), "planning": Decimal(0), "count": 0
    })

    for cat in ordered_cats:
        currency_entries = []
        for cur in sorted(raw_data[cat]):
            cell = raw_data[cat][cur]
            currency_entries.append({
                "currency": cur,
                "cash": cell["cash"].quantize(Decimal("0.01")),
                "baseline": cell["baseline"].quantize(Decimal("0.01")),
                "planning": cell["planning"].quantize(Decimal("0.01")),
                "count": cell["count"],
            })
            totals[cur]["cash"] += cell["cash"]
            totals[cur]["baseline"] += cell["baseline"]
            totals[cur]["planning"] += cell["planning"]
            totals[cur]["count"] += cell["count"]
        rows.append({"category": cat, "entries": currency_entries})

    total_rows = [
        {
            "currency": cur,
            "cash": totals[cur]["cash"].quantize(Decimal("0.01")),
            "baseline": totals[cur]["baseline"].quantize(Decimal("0.01")),
            "planning": totals[cur]["planning"].quantize(Decimal("0.01")),
            "count": totals[cur]["count"],
        }
        for cur in sorted(totals)
    ]

    # Count transactions with UNKNOWN budget_treatment (excluded from planning/baseline).
    unknown_budget_count = Transaction.objects.filter(
        excluded=False,
        direction="debit",
        posted_date__gte=start,
        posted_date__lte=end,
        budget_treatment=BudgetTreatment.UNKNOWN,
    ).count()

    return render(request, "money_observability/monthly_summary.html", {
        "start": start,
        "end": end,
        "rows": rows,
        "total_rows": total_rows,
        "unknown_budget_count": unknown_budget_count,
    })

