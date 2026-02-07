# limpieza/models.py
from django.db import models
from django.contrib.auth.models import User

class OperacionLimpieza(models.Model):
    TIPO_OPERACION = [
        ('vaciar', 'Vaciar Tabla'),
        ('eliminar', 'Eliminar Registros Filtrados'),
        ('backup', 'Crear Backup'),
        ('restaurar', 'Restaurar Backup'),
        ('optimizar', 'Optimizar Tabla'),
    ]
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completado', 'Completado'),
        ('error', 'Error'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    tipo_operacion = models.CharField(max_length=20, choices=TIPO_OPERACION)
    tabla = models.CharField(max_length=100)
    filtros = models.JSONField(null=True, blank=True)
    total_registros = models.IntegerField(default=0)
    registros_eliminados = models.IntegerField(default=0)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Operación de Limpieza"
        verbose_name_plural = "Operaciones de Limpieza"
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f"{self.tipo_operacion} - {self.tabla} - {self.estado}"