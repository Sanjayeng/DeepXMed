from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_prescription, name='upload_prescription'),
    path('my/', views.prescriptions_list, name='prescriptions_list'),

    # new route used by your template
    path('medicine/<int:pk>/compare/', views.compare_medicine_prices, name='compare_medicine_prices'),
]
