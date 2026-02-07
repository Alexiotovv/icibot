# limpieza/admin.py
from django.contrib import admin
from limpieza.models import OperacionLimpieza

@admin.register(OperacionLimpieza)
class OperacionLimpiezaAdmin(admin.ModelAdmin):
    list_display = ('tipo_operacion', 'tabla', 'estado', 'usuario', 'fecha_inicio', 'total_registros', 'registros_eliminados')
    list_filter = ('tipo_operacion', 'estado', 'tabla')
    search_fields = ('tabla', 'observaciones', 'usuario__username')
    readonly_fields = ('fecha_inicio', 'fecha_fin')
    ordering = ('-fecha_inicio',)
    
    def has_delete_permission(self, request, obj=None):
        # Solo superusuarios pueden eliminar registros de operaciones
        return request.user.is_superuser