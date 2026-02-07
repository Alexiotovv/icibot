# correccion_dbf/urls.py
from django.urls import path
from correccion_dbf.views import *

app_name = 'correccion_dbf'

urlpatterns = [
    # Dashboard y páginas principales
    path('correccion-dbf/', dashboard_correcciones, name='dashboard'),
    path('correccion-dbf/historial/', historial_correcciones, name='historial'),
    
    # Flujo de corrección
    path('correccion-dbf/subir/', subir_archivo_correccion, name='subir_archivo'),
    path('correccion-dbf/seleccionar/', seleccionar_inconsistencias, name='seleccionar_inconsistencias'),
    path('correccion-dbf/ejecutar/', ejecutar_correccion, name='ejecutar_correccion'),
    path('correccion-dbf/descargar/', descargar_archivo, name='descargar_archivo'),
    path('correccion-dbf/limpiar/', limpiar_archivo, name='limpiar_archivo'), 


]