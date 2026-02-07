# correccion_dbf/models.py
from django.db import models
from django.contrib.auth.models import User
from verificaciones.models import InconsistenciaFormDet

class CorreccionDBF(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'),
        ('corregido', 'Corregido'),
        ('error', 'Error'),
    ]
    
    inconsistencia = models.ForeignKey(
        InconsistenciaFormDet, 
        on_delete=models.CASCADE,
        related_name='correcciones'
    )
    
    # Información del archivo original
    nombre_archivo_original = models.CharField(max_length=255)
    ruta_archivo_original = models.TextField()
    
    # Información del archivo corregido
    nombre_archivo_corregido = models.CharField(max_length=255, blank=True)
    ruta_archivo_corregido = models.TextField(blank=True)
    
    # Metadatos de corrección
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_correccion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    
    # Detalles de la corrección
    valor_anterior = models.DecimalField(max_digits=15, decimal_places=2)
    valor_corregido = models.DecimalField(max_digits=15, decimal_places=2)
    diferencia = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Corrección DBF"
        verbose_name_plural = "Correcciones DBF"
        ordering = ['-fecha_correccion']
    
    def __str__(self):
        return f"Corrección: {self.inconsistencia.CODIGO_PRE} - {self.inconsistencia.CODIGO_MED}"