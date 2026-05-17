import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Transaction
from .services.category_rules import CATEGORY_MANUAL_REVIEW

# Ordered by expected frequency of use.
CATEGORIES = [
    "Dining",
    "Groceries",
    "Transport",
    "Housing",
    "Subscriptions",
    "Shopping",
    "Entertainment",
    "Healthcare",
    "Travel",
    "Laundry",
    "Giving",
    "Fees / Finance Charges",
    "Other",
]

# Keyboard shortcut letter for each category (lowercase → category).
# Conflicts resolved: P=sho(P)ping, C=health(C)are, V=tra(V)el, I=g(I)ving.
# Keys j/k/a are reserved for navigation/select-all.
_KEY_TO_CATEGORY = {
    "d": "Dining",
    "g": "Groceries",
    "t": "Transport",
    "h": "Housing",
    "s": "Subscriptions",
    "p": "Shopping",
    "e": "Entertainment",
    "c": "Healthcare",
    "v": "Travel",
    "l": "Laundry",
    "i": "Giving",
    "f": "Fees / Finance Charges",
    "o": "Other",
}
_CATEGORY_TO_KEY = {v: k.upper() for k, v in _KEY_TO_CATEGORY.items()}

_CATEGORY_SET = set(CATEGORIES)


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
    raw = list(
        Transaction.objects.filter(
            category=CATEGORY_MANUAL_REVIEW,
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
            "categories_with_keys": [(cat, _CATEGORY_TO_KEY.get(cat, "")) for cat in CATEGORIES],
            "key_to_category_json": json.dumps(_KEY_TO_CATEGORY),
            "total_count": len(raw),
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
    if category not in _CATEGORY_SET:
        return JsonResponse({"error": "invalid category"}, status=400)
    try:
        ids = [int(i) for i in ids]
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid ids"}, status=400)

    updated = Transaction.objects.filter(
        id__in=ids,
        category=CATEGORY_MANUAL_REVIEW,
    ).update(
        category=category,
        categorized_at=timezone.now(),
        category_rule_id="manual_ui",
    )
    return JsonResponse({"updated": updated})
