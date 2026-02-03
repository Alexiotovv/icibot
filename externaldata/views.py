from django.shortcuts import render

from process.models import ProcesamientoHistorico

def historico_index(request):
    historicos = ProcesamientoHistorico.objects.all().order_by('-creado_en')
    return render(request, 'historicos/index.html', {'historicos': historicos})