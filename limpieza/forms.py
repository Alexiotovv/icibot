# limpieza/forms.py
from django import forms
from django.utils import timezone
from datetime import timedelta

class LimpiarTablaForm(forms.Form):
    TABLAS_CHOICES = [
        ('InconsistenciaFormDet', 'Inconsistencias Stock/Saldo'),
        ('EstadisticaVerificacion', 'Estadísticas de Verificación'),
        ('FormDet', 'Datos FormDet (Principal)'),
        ('ArchivosProcesados', 'Archivos Procesados'),
        ('ProcesamientoHistorico', 'Historial de Procesamiento'),
        ('ExternalAPI', 'Logs de API Externa'),
        ('MedicamentoVencido', 'Medicamentos Vencidos'),
        ('Ime1', 'IMEI 1'),
        ('Imed2', 'IMEI 2'),
        ('Imed3', 'IMEI 3'),
    ]
    
    OPERACION_CHOICES = [
        ('vaciar', 'Vaciar Tabla Completamente'),
        ('eliminar_filtros', 'Eliminar Registros Filtrados'),
        ('backup_vaciar', 'Crear Backup y Vaciar'),
    ]
    
    tabla = forms.ChoiceField(
        choices=TABLAS_CHOICES,
        label="Tabla a Limpiar",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    operacion = forms.ChoiceField(
        choices=OPERACION_CHOICES,
        label="Tipo de Operación",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Filtros para eliminación selectiva
    fecha_hasta = forms.DateField(
        required=False,
        label="Eliminar hasta fecha",
        help_text="Eliminar registros anteriores a esta fecha",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    confirmacion = forms.CharField(
        required=True,
        label="Confirmación",
        help_text="Escriba 'ELIMINAR' para confirmar",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ELIMINAR'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        confirmacion = cleaned_data.get('confirmacion')
        
        if confirmacion != 'ELIMINAR':
            raise forms.ValidationError("Debe escribir 'ELIMINAR' para confirmar la operación.")
        
        return cleaned_data

class ConsultaEstadisticasForm(forms.Form):
    tabla = forms.ChoiceField(
        choices=LimpiarTablaForm.TABLAS_CHOICES,
        label="Tabla a Consultar",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    ver_detalles = forms.BooleanField(
        required=False,
        initial=False,
        label="Ver detalles de registros",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )