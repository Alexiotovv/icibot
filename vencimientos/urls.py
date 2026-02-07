# vencimientos/urls.py
from django.urls import path
from vencimientos.views import *

app_name = 'vencimientos'

urlpatterns = [
    path('vencimientos/', lista_vencimientos, name='lista_vencimientos'),
    path('vencimientos/detectar/', detectar_vencimientos, name='detectar_vencimientos'),
    path('vencimientos/<int:vencimiento_id>/', detalle_vencimiento, name='detalle_vencimiento'),
    path('vencimientos/<int:vencimiento_id>/resolver/', marcar_resuelto, name='marcar_resuelto'),
    path('vencimientos/exportar/', exportar_csv, name='exportar_csv'),
    path('vencimientos/dashboard/', dashboard_vencimientos, name='dashboard'),
]