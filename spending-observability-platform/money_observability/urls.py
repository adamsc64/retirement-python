from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("categorize/", views.categorize_queue, name="categorize_queue"),
    path("categorize/assign/", views.assign_category, name="assign_category"),
]
