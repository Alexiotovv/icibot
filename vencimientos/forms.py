# vencimientos/forms.py
from django import forms
from django.utils import timezone
from externaldata.models import FormDet  # Importar el modelo

class BuscarVencimientosForm(forms.Form):
    CODIGO_PRE = forms.CharField(
        required=False,
        label="Código Establecimiento",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 00026'})
    )
    
    CODIGO_MED = forms.CharField(
        required=False,
        label="Código Medicamento",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 05964'})
    )
    
    MEDLOTE = forms.CharField(
        required=False,
        label="Lote",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de lote'})
    )
    
    ANNOMES = forms.ChoiceField(
        required=False,
        label="Mes/Año",
        widget=forms.Select(attrs={'class': 'form-control'}),
        choices=[]  # Se llenará dinámicamente en la vista
    )
    
    severidad = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Todos'),
            ('vencido', 'Vencidos'),
            ('por_vencer', 'Por Vencer (30 días)'),
            ('alerta', 'Alerta (60 días)'),
        ],
        label="Estado",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    fecha_desde = forms.DateField(
        required=False,
        label="Vencimiento desde",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        label="Vencimiento hasta",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    solo_no_resueltos = forms.BooleanField(
        required=False,
        initial=True,
        label="Solo pendientes",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Obtener ANNOMES únicos de la base de datos
        annomes_choices = FormDet.objects.values_list('ANNOMES', flat=True).distinct().order_by('-ANNOMES')
        
        # Crear choices formateados
        choices = [('', 'Todos los meses')]
        for annomes in annomes_choices:
            # Formatear ANNOMES (ej: "202501" -> "Enero 2025")
            try:
                if len(annomes) == 6:
                    año = annomes[:4]
                    mes = annomes[4:]
                    meses = {
                        '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
                        '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
                        '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
                    }
                    mes_nombre = meses.get(mes, mes)
                    display = f"{mes_nombre} {año}"
                else:
                    display = annomes
            except:
                display = annomes
            
            choices.append((annomes, display))
        
        # Asignar choices al campo ANNOMES
        self.fields['ANNOMES'].choices = choices