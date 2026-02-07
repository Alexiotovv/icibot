# limpieza/urls.py
from django.urls import path
from limpieza.views import *

app_name = 'limpieza'

urlpatterns = [
    path('limpieza/', dashboard_limpieza, name='dashboard'),
    path('limpieza/consultar/', consultar_tabla, name='consultar_tabla'),
    path('limpieza/limpiar/', limpiar_tabla, name='limpiar_tabla'),
    path('limpieza/exportar/<str:nombre_tabla>/', exportar_backup, name='exportar_backup'),
    path('limpieza/optimizar/<str:nombre_tabla>/', optimizar_tabla, name='optimizar_tabla'),
    path('limpieza/estadisticas/ajax/', obtener_estadisticas_ajax, name='estadisticas_ajax'),
]