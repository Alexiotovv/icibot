# vencimientos/models.py
from django.db import models
from django.contrib.auth.models import User
from externaldata.models import FormDet
from django.utils import timezone


class MedicamentoVencido(models.Model):
    SEVERIDAD_CHOICES = [
        ('vencido', 'Vencido'),
        ('por_vencer', 'Por Vencer (30 días)'),
        ('alerta', 'Alerta (60 días)'),
    ]
    
    # Relación con el registro original
    registro_formdet = models.ForeignKey(
        FormDet, 
        on_delete=models.CASCADE,
        related_name='vencimientos_detectados'
    )
    
    # Información del medicamento
    CODIGO_PRE = models.CharField(max_length=20, verbose_name="Código Establecimiento")
    CODIGO_MED = models.CharField(max_length=20, verbose_name="Código Medicamento")
    MEDLOTE = models.CharField(max_length=50, verbose_name="Lote", blank=True, null=True)
    MEDFECHVTO = models.DateField(verbose_name="Fecha de Vencimiento")
    SALDO = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Saldo Actual")
    
    # Información de la detección
    severidad = models.CharField(max_length=20, choices=SEVERIDAD_CHOICES)
    dias_restantes = models.IntegerField(verbose_name="Días Restantes para Vencimiento")
    fecha_deteccion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Detección")
    usuario_deteccion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resuelto = models.BooleanField(default=False, verbose_name="Resuelto")
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    usuario_resolucion = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='vencimientos_resueltos'
    )
    ANNOMES = models.CharField(
        max_length=6, 
        verbose_name="Mes/Año",
        help_text="Formato: AAAAMM (ej: 202501)",
        blank=True,
        null=True
    )
    # Observaciones
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    class Meta:
        verbose_name = "Medicamento Vencido"
        verbose_name_plural = "Medicamentos Vencidos"
        ordering = ['MEDFECHVTO', 'severidad']
        indexes = [
            models.Index(fields=['MEDFECHVTO']),
            models.Index(fields=['severidad']),
            models.Index(fields=['CODIGO_PRE']),
            models.Index(fields=['resuelto']),
        ]
    
    def __str__(self):
        return f"{self.CODIGO_MED} - Lote: {self.MEDLOTE} - Vence: {self.MEDFECHVTO}"
    
    def marcar_resuelto(self, usuario, observaciones=""):
        """Marca el vencimiento como resuelto"""
        self.resuelto = True
        self.fecha_resolucion = timezone.now()
        self.usuario_resolucion = usuario
        if observaciones:
            self.observaciones = observaciones
        self.save()
    
    @property
    def estado(self):
        """Devuelve el estado legible"""
        if self.resuelto:
            return "Resuelto"
        return self.get_severidad_display()