from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("categorize/", views.categorize_queue, name="categorize_queue"),
    path("categorize/assign/", views.assign_category, name="assign_category"),
    path(
        "categorize/exclude/", views.exclude_transactions, name="exclude_transactions"
    ),
    path("summary/", views.monthly_summary, name="monthly_summary"),
    path("annual/", views.annual_expenses, name="annual_expenses"),
    path("trends/", views.spending_trends, name="spending_trends"),
    path("upload/", views.upload_csv, name="upload_csv"),
    path("repeating/", views.repeating_items, name="repeating_items"),
]
