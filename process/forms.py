from django import forms

class FechaForm(forms.Form):
    fecha_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    fecha_final = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
