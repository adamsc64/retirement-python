import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Transaction
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
    all_view_categories = [CATEGORY_MANUAL_REVIEW] + CATEGORY_NAMES
    view_category = request.GET.get("view_category", CATEGORY_MANUAL_REVIEW)
    if view_category not in frozenset(all_view_categories):
        view_category = CATEGORY_MANUAL_REVIEW

    raw = list(
        Transaction.objects.filter(
            category=view_category,
            excluded=False,
            direction="debit",
        )
        .order_by("posted_date", "description_clean")
        .values(
            "id",
            "posted_date",
            "description_clean",
            "description_raw",
            "amount",
            "currency",
            "source_institution",
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
