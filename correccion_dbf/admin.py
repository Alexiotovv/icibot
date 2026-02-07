# correccion_dbf/admin.py
from django.contrib import admin
from .models import CorreccionDBF

@admin.register(CorreccionDBF)
class CorreccionDBFAdmin(admin.ModelAdmin):
    list_display = ('fecha_correccion', 'nombre_archivo_original', 'usuario', 'estado', 'valor_anterior', 'valor_corregido', 'diferencia')
    list_filter = ('estado', 'usuario', 'fecha_correccion')
    search_fields = ('nombre_archivo_original', 'nombre_archivo_corregido', 'inconsistencia__CODIGO_PRE')
    readonly_fields = ('fecha_correccion',)
    ordering = ('-fecha_correccion',)