from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime

class BuscarInconsistenciasForm(forms.Form):
    """Formulario para buscar inconsistencias - Incluye todos los campos"""
    CODIGO_PRE = forms.CharField(
        required=False,
        label='Código de Establecimiento',
        max_length=11,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 00012345678'
        })
    )
    
    CODIGO_MED = forms.CharField(
        required=False,
        label='Código de Medicamento',
        max_length=7,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 1234567'
        })
    )
    
    MEDLOTE = forms.CharField(
        required=False,
        label='Lote de Medicamento',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: LOTE12345'
        })
    )
    
    FFINAN = forms.CharField(
        required=False,
        label='Financiamiento',
        max_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 001'
        })
    )
    
    TIPSUM = forms.CharField(
        required=False,
        label='Tipo de Suministro',
        max_length=1,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: A'
        })
    )
    
    MEDREGSAN = forms.CharField(
        required=False,
        label='Registro Sanitario',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: RS12345'
        })
    )
    
    ANNOMES_inicio = forms.CharField(
        required=False,
        label='Mes/Año Inicio',
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 202511',
            'pattern': r'\d{6}',
            'title': 'Formato: AAAAMM'
        })
    )
    
    ANNOMES_fin = forms.CharField(
        required=False,
        label='Mes/Año Fin',
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 202512',
            'pattern': r'\d{6}',
            'title': 'Formato: AAAAMM'
        })
    )
    
    TIPSUM2 = forms.CharField(
        required=False,
        label='Tipo Suministro 2',
        max_length=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: CN, SC'
        })
    )

    severidad = forms.ChoiceField(
        required=False,
        label='Severidad',
        choices=[
            ('', 'Todas'),
            ('alta', 'Alta'),
            ('media', 'Media'),
            ('baja', 'Baja'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    solo_no_resueltas = forms.BooleanField(
        required=False,
        initial=True,
        label='Solo no resueltas',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_ANNOMES_inicio(self):
        annomes = self.cleaned_data.get('ANNOMES_inicio')
        if annomes and len(annomes) != 6:
            raise forms.ValidationError("El formato debe ser AAAAMM (6 dígitos)")
        return annomes
    
    def clean_ANNOMES_fin(self):
        annomes = self.cleaned_data.get('ANNOMES_fin')
        if annomes and len(annomes) != 6:
            raise forms.ValidationError("El formato debe ser AAAAMM (6 dígitos)")
        return annomes