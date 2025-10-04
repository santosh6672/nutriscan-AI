from django.urls import path
from . import views

urlpatterns = [
    path('scan/', views.scan_product, name='scan_product'),

    path('result/', views.result, name='result'),
]