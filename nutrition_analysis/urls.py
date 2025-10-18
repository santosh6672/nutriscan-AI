from django.urls import path
from . import views

urlpatterns = [
    path('scan/', views.scan_product, name='scan_product'),
    path('result/', views.result, name='result'),
    path('clear-session/', views.clear_scan_session, name='clear_scan_session'),
]