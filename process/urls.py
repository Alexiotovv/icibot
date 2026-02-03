from django.urls import path
from process.views import *

urlpatterns = [
    path('process/consumir/', consumir_api, name='consumir_api'),
    path('api/procesar-zip/', procesar_zip, name='procesar-zip'),
    path('api/validar-zip/', validar_zip, name='validar-zip'),


  # Página para mostrar el formulario de subida
    path('subir/', subir_formulario_zip, name='subir_archivo'),
    
    # Endpoint para procesar el archivo (POST)
    path('procesar/', procesar_archivos_zip, name='procesar_archivo'),
    
    # Listar archivos procesados
    path('archivos/', listar_archivos_procesados, name='archivos_procesados'),
    
    # Acciones sobre archivos
    path('archivos/exportar/<int:archivo_id>/', exportar_archivo, name='exportar_archivo'),
    path('archivos/eliminar/<int:archivo_id>/', eliminar_archivo, name='eliminar_archivo'),
    path('archivos/ver/<int:archivo_id>/', ver_registros_archivo, name='ver_registros'),
    
    # URLs antiguas (mantener para compatibilidad si es necesario)
    path('volumen/subir-zip/', subir_formulario_zip, name='subir_zip_volumen'),
    path('volumen/procesar-zip/', procesar_archivos_zip, name='procesar_zip_volumen'),
]