# correccion_dbf/forms.py
from django import forms
from django.core.validators import FileExtensionValidator
from verificaciones.models import InconsistenciaFormDet

# correccion_dbf/forms.py
class SubirArchivoCorreccionForm(forms.Form):
    archivo_zip = forms.FileField(
        label="Archivo ZIP con DBF",
        validators=[FileExtensionValidator(allowed_extensions=['zip'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.zip'
        })
    )
    
    contraseña = forms.CharField(
        label="Contraseña del ZIP",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese la contraseña del archivo ZIP',
            'value':'VEINTE4512'
        }),
        required=False
    )
    
    mes_archivo = forms.CharField(  # CAMBIÉ EL NOMBRE AQUÍ
        label="Mes del archivo (AAAAMM)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 202601'
        }),
        max_length=6,
        required=True,
        help_text="Mes del archivo que está subiendo (ej: Enero 2026 = 202601)"
    )
    
    confirmar_correccion = forms.BooleanField(
        label="Confirmar corrección automática",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    crear_backup = forms.BooleanField(
        label="Crear copia de seguridad",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class SeleccionarInconsistenciasForm(forms.Form):
    inconsistencias = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Seleccionar inconsistencias a corregir"
    )
    
    def __init__(self, *args, **kwargs):
        mes_anterior = kwargs.pop('mes_anterior', None)
        super().__init__(*args, **kwargs)
        
        if mes_anterior:
            # Buscar inconsistencias donde el mes ANTERIOR sea el que tenemos en BD
            queryset = InconsistenciaFormDet.objects.filter(
                ANNOMES_anterior=mes_anterior,  # 202512
                resuelta=False
            ).order_by('-diferencia')[:100]
            self.fields['inconsistencias'].queryset = queryset