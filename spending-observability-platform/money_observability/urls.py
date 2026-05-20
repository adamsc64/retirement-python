from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("categorize/", views.categorize_queue, name="categorize_queue"),
    path("categorize/assign/", views.assign_category, name="assign_category"),
    path("categorize/assign-budget/", views.assign_budget, name="assign_budget"),
    path("summary/", views.monthly_summary, name="monthly_summary"),
]
