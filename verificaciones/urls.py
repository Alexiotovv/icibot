from django.urls import path
from verificaciones.views import *

app_name = 'verificaciones'

urlpatterns = [
    path('verificaciones/', verificar_inconsistencias, name='verificar_inconsistencias'),
    path('verificaciones/ejecutar/', ejecutar_verificacion, name='ejecutar_verificacion'),
    path('verificaciones/detalle/<int:inconsistencia_id>/', detalle_inconsistencia, name='detalle_inconsistencia'),

    path('marcar-resuelta/<int:inconsistencia_id>/', marcar_resuelta, name='marcar_resuelta'),
    path('verificaciones/estadisticas/', estadisticas_verificacion, name='estadisticas'),
    path('verificaciones/exportar/', exportar_inconsistencias, name='exportar'),

    path('debug/verificacion/', debug_verificacion, name='debug_verificacion'),
]