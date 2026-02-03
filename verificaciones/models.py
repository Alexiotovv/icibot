from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from datetime import datetime
import json

class TipoInconsistencia(models.TextChoices):
    STOCK_SALDO = 'stock_saldo', _('Inconsistencia Stock-Saldo')
    # Puedes agregar más tipos aquí

class InconsistenciaFormDet(models.Model):
    """Modelo para almacenar inconsistencias encontradas"""
    archivo_procesado = models.ForeignKey(
        'externaldata.ArchivosProcesados',
        on_delete=models.CASCADE,
        related_name='inconsistencias',
        null=True,
        blank=True
    )
    
    tipo = models.CharField(
        max_length=50,
        choices=TipoInconsistencia.choices,
        default=TipoInconsistencia.STOCK_SALDO
    )
    
    # Información del registro con inconsistencia
    CODIGO_PRE = models.CharField(max_length=11, db_index=True)
    CODIGO_MED = models.CharField(max_length=7, db_index=True)
    ANNOMES_actual = models.CharField(max_length=6, db_index=True)
    ANNOMES_anterior = models.CharField(max_length=6, null=True, blank=True)
    
    # Valores que generan la inconsistencia
    MEDLOTE = models.CharField(max_length=20, null=True, blank=True)
    FFINAN = models.CharField(max_length=3, null=True, blank=True)
    TIPSUM2 = models.CharField(max_length=2, null=True, blank=True)
    MEDFECHVTO = models.DateField(null=True, blank=True)
    MEDREGSAN = models.CharField(max_length=20, null=True, blank=True)
    SALDO_actual = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)

    STOCKFIN_anterior = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    
    MEDLOTE_anterior = models.CharField(max_length=20, null=True, blank=True)
    MEDLOTE_actual = models.CharField(max_length=20, null=True, blank=True)
    
    FFINAN_anterior = models.CharField(max_length=3, null=True, blank=True)
    FFINAN_actual = models.CharField(max_length=3, null=True, blank=True)
    
    TIPSUM_anterior = models.CharField(max_length=2, null=True, blank=True)
    TIPSUM_actual = models.CharField(max_length=2, null=True, blank=True)
    
    MEDFECHVTO_anterior = models.DateField(null=True, blank=True)
    MEDFECHVTO_actual = models.DateField(null=True, blank=True)
    
    MEDREGSAN_anterior = models.CharField(max_length=20, null=True, blank=True)
    MEDREGSAN_actual = models.CharField(max_length=20, null=True, blank=True)

    # Diferencia calculada
    diferencia = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    
    # Información adicional
    descripcion = models.TextField(blank=True)
    severidad = models.CharField(
        max_length=20,
        choices=[
            ('alta', 'Alta'),
            ('media', 'Media'),
            ('baja', 'Baja'),
        ],
        default='media'
    )
    
    # Metadata
    usuario_deteccion = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    fecha_deteccion = models.DateTimeField(auto_now_add=True)
    resuelta = models.BooleanField(default=False)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    
    # Campos para análisis adicional
    datos_contexto = models.JSONField(null=True, blank=True)
    
    class Meta:
        verbose_name = _("Inconsistencia FormDet")
        verbose_name_plural = _("Inconsistencias FormDet")
        ordering = ['-fecha_deteccion', 'severidad']
        indexes = [
            models.Index(fields=['CODIGO_PRE', 'ANNOMES_actual']),
            models.Index(fields=['tipo', 'resuelta']),
            models.Index(fields=['fecha_deteccion']),
        ]
    
        def __str__(self):
            return f"Inconsistencia {self.tipo} - {self.CODIGO_PRE}/{self.CODIGO_MED} ({self.ANNOMES_actual})"
    
    def get_detalle_contexto(self):
        """Retorna detalles adicionales en formato legible"""
        if self.datos_contexto:
            return self.datos_contexto
        return {}
    
    def marcar_resuelta(self, usuario=None):
        """Marca la inconsistencia como resuelta"""
        self.resuelta = True
        self.fecha_resolucion = datetime.now()
        if usuario:
            self.usuario_deteccion = usuario
        self.save()

class EstadisticaVerificacion(models.Model):
    """Modelo para almacenar estadísticas de verificaciones realizadas"""
    fecha_ejecucion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    total_registros_analizados = models.IntegerField(default=0)
    total_inconsistencias = models.IntegerField(default=0)
    total_inconsistencias_stock_saldo = models.IntegerField(default=0)
    
    # Tiempos de ejecución
    tiempo_inicio = models.DateTimeField()
    tiempo_fin = models.DateTimeField(null=True, blank=True)
    duracion_segundos = models.FloatField(null=True, blank=True)
    
    # Parámetros de búsqueda
    parametros = models.JSONField(null=True, blank=True)
    
    # Resumen por CODIGO_PRE
    resumen_codigo_pre = models.JSONField(null=True, blank=True)
    
    class Meta:
        verbose_name = _("Estadística de Verificación")
        verbose_name_plural = _("Estadísticas de Verificación")
        ordering = ['-fecha_ejecucion']
    
    def __str__(self):
        return f"Verificación {self.fecha_ejecucion.date()} - {self.total_inconsistencias} inconsistencias"
    
    def calcular_duracion(self):
        """Calcula la duración de la verificación"""
        if self.tiempo_fin and self.tiempo_inicio:
            diferencia = self.tiempo_fin - self.tiempo_inicio
            self.duracion_segundos = diferencia.total_seconds()
            self.save()