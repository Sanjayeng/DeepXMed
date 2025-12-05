# pharmacy/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path(
        "compare/<int:medicine_id>/",
        views.compare_medicine_prices,
        name="compare_medicine_prices",
    ),
]
