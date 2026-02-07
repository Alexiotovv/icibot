# vencimientos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import HttpResponse
import csv

from .models import MedicamentoVencido
from .forms import BuscarVencimientosForm
from externaldata.models import FormDet

@login_required
def detectar_vencimientos(request):
    """
    Ejecuta la detección de medicamentos vencidos o por vencer
    """
    from django.db import transaction
    import time
    
    start_time = time.time()
    fecha_actual = timezone.now().date()
    
    try:
        with transaction.atomic():
            # Obtener todos los registros con fecha de vencimiento
            registros = FormDet.objects.filter(
                MEDFECHVTO__isnull=False
            ).select_related('archivo_procesado')
            
            total_analizados = registros.count()
            vencimientos_detectados = []
            
            print(f"[VENCIMIENTOS] Analizando {total_analizados} registros con fecha de vencimiento")
            
            for registro in registros:
                try:
                    # Calcular días restantes
                    dias_restantes = (registro.MEDFECHVTO - fecha_actual).days
                    
                    # Determinar severidad
                    if dias_restantes < 0:
                        severidad = 'vencido'
                    elif dias_restantes <= 30:
                        severidad = 'por_vencer'
                    elif dias_restantes <= 60:
                        severidad = 'alerta'
                    else:
                        continue  # No crear registro si está fuera de los rangos
                    
                    # Verificar si ya existe un registro para este medicamento/lote
                    existe = MedicamentoVencido.objects.filter(
                        registro_formdet=registro,
                        resuelto=False
                    ).exists()
                    
                    if not existe:
                        vencimiento = MedicamentoVencido(
                            registro_formdet=registro,
                            CODIGO_PRE=registro.CODIGO_PRE,
                            CODIGO_MED=registro.CODIGO_MED,
                            MEDLOTE=registro.MEDLOTE,
                            MEDFECHVTO=registro.MEDFECHVTO,
                            SALDO=registro.SALDO,
                            severidad=severidad,
                            dias_restantes=dias_restantes,
                            usuario_deteccion=request.user
                        )
                        vencimientos_detectados.append(vencimiento)
                
                except Exception as e:
                    print(f"[ERROR] Procesando registro {registro.id}: {e}")
                    continue
            
            # Guardar todos los vencimientos detectados
            if vencimientos_detectados:
                MedicamentoVencido.objects.bulk_create(vencimientos_detectados)
                total_nuevos = len(vencimientos_detectados)
            else:
                total_nuevos = 0
            
            # Estadísticas
            tiempo_total = time.time() - start_time
            
            messages.success(
                request,
                f'Detección completada. Analizados {total_analizados} registros. '
                f'Encontrados {total_nuevos} medicamentos vencidos o por vencer.'
            )
            
    except Exception as e:
        messages.error(request, f'Error durante la detección: {str(e)}')
        return redirect('vencimientos:lista_vencimientos')
    
    return redirect('vencimientos:lista_vencimientos')

@login_required
def lista_vencimientos(request):
    """
    Muestra lista de medicamentos vencidos o por vencer
    """
    # Inicializar el formulario con request.GET
    form = BuscarVencimientosForm(request.GET or None)
    
    vencimientos = []
    estadisticas = {}
    resumen_codigo_pre = []
    
    if request.method == 'GET' and any(request.GET.values()):
        if form.is_valid():
            # Filtrar por parámetros
            queryset = MedicamentoVencido.objects.all()
            
            if form.cleaned_data['CODIGO_PRE']:
                queryset = queryset.filter(CODIGO_PRE__icontains=form.cleaned_data['CODIGO_PRE'])
            
            if form.cleaned_data['CODIGO_MED']:
                queryset = queryset.filter(CODIGO_MED__icontains=form.cleaned_data['CODIGO_MED'])
            
            if form.cleaned_data['MEDLOTE']:
                queryset = queryset.filter(MEDLOTE__icontains=form.cleaned_data['MEDLOTE'])
            
            # NUEVO FILTRO POR ANNOMES
            if form.cleaned_data['ANNOMES']:
                annomes = form.cleaned_data['ANNOMES']
                # Filtrar por ANNOMES del registro FormDet relacionado
                queryset = queryset.filter(registro_formdet__ANNOMES=annomes)
            
            if form.cleaned_data['severidad']:
                queryset = queryset.filter(severidad=form.cleaned_data['severidad'])
            
            if form.cleaned_data['fecha_desde']:
                queryset = queryset.filter(MEDFECHVTO__gte=form.cleaned_data['fecha_desde'])
            
            if form.cleaned_data['fecha_hasta']:
                queryset = queryset.filter(MEDFECHVTO__lte=form.cleaned_data['fecha_hasta'])
            
            if form.cleaned_data['solo_no_resueltos']:
                queryset = queryset.filter(resuelto=False)
            
            # Ordenar por severidad y fecha
            vencimientos = queryset.order_by('MEDFECHVTO', 'severidad')
            
            # Estadísticas
            total = vencimientos.count()
            estadisticas = {
                'total': total,
                'vencidos': queryset.filter(severidad='vencido').count(),
                'por_vencer': queryset.filter(severidad='por_vencer').count(),
                'alerta': queryset.filter(severidad='alerta').count(),
                'valor_total': queryset.aggregate(total=Sum('SALDO'))['total'] or 0,
            }
            
            # Resumen por establecimiento
            resumen_codigo_pre = list(queryset.values('CODIGO_PRE').annotate(
                total=Count('id'),
                valor_total=Sum('SALDO')
            ).order_by('-total')[:20])
    
    # Si no hay filtros, mostrar últimos detectados
    elif not any(request.GET.values()):
        vencimientos = MedicamentoVencido.objects.filter(resuelto=False).order_by('-fecha_deteccion')[:100]
    
    context = {
        'form': form,
        'vencimientos': vencimientos,
        'estadisticas': estadisticas,
        'resumen_codigo_pre': resumen_codigo_pre,
        'hoy': timezone.now().date(),
    }
    
    return render(request, 'vencimientos/lista_vencimientos.html', context)

@login_required
def detalle_vencimiento(request, vencimiento_id):
    """
    Muestra detalles de un medicamento vencido
    """
    vencimiento = get_object_or_404(MedicamentoVencido, id=vencimiento_id)
    
    # Calcular días absolutos para el template
    vencimiento.dias_absolutos = abs(vencimiento.dias_restantes)
    
    # Obtener otros lotes del mismo medicamento
    otros_lotes = MedicamentoVencido.objects.filter(
        CODIGO_PRE=vencimiento.CODIGO_PRE,
        CODIGO_MED=vencimiento.CODIGO_MED,
        resuelto=False
    ).exclude(id=vencimiento_id).order_by('MEDFECHVTO')
    
    # Calcular días absolutos para cada lote también
    for lote in otros_lotes:
        lote.dias_absolutos = abs(lote.dias_restantes)
    
    context = {
        'vencimiento': vencimiento,
        'otros_lotes': otros_lotes,
    }
    
    return render(request, 'vencimientos/detalle_vencimiento.html', context)

@login_required
def marcar_resuelto(request, vencimiento_id):
    """
    Marca un vencimiento como resuelto
    """
    if request.method == 'POST':
        vencimiento = get_object_or_404(MedicamentoVencido, id=vencimiento_id)
        observaciones = request.POST.get('observaciones', '')
        
        vencimiento.marcar_resuelto(request.user, observaciones)
        
        messages.success(request, 'Medicamento marcado como resuelto.')
    
    return redirect('vencimientos:detalle_vencimiento', vencimiento_id=vencimiento_id)
    # O si prefieres volver a la lista:
    # return redirect('vencimientos:lista_vencimientos')

@login_required
def exportar_csv(request):
    """
    Exporta vencimientos a CSV
    """
    # Aplicar filtros si existen
    form = BuscarVencimientosForm(request.GET or None)
    queryset = MedicamentoVencido.objects.all()
    
    if form.is_valid():
        if form.cleaned_data['CODIGO_PRE']:
            queryset = queryset.filter(CODIGO_PRE__icontains=form.cleaned_data['CODIGO_PRE'])
        if form.cleaned_data['CODIGO_MED']:
            queryset = queryset.filter(CODIGO_MED__icontains=form.cleaned_data['CODIGO_MED'])
        if form.cleaned_data['ANNOMES']:  # NUEVO FILTRO
            queryset = queryset.filter(registro_formdet__ANNOMES=form.cleaned_data['ANNOMES'])
        if form.cleaned_data['severidad']:
            queryset = queryset.filter(severidad=form.cleaned_data['severidad'])
        if form.cleaned_data['solo_no_resueltos']:
            queryset = queryset.filter(resuelto=False)
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="medicamentos_vencidos.csv"'
    
    # Usar encoding utf-8-sig para Excel
    response.write(u'\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    writer.writerow([
        'CODIGO_PRE', 'CODIGO_MED', 'MEDLOTE', 
        'FECHA_VENCIMIENTO', 'DIAS_RESTANTES', 'ESTADO',
        'SALDO', 'FECHA_DETECCION', 'RESUELTO'
    ])
    
    for venc in queryset:
        writer.writerow([
            venc.CODIGO_PRE,
            venc.CODIGO_MED,
            venc.MEDLOTE or '',
            venc.MEDFECHVTO.strftime('%d/%m/%Y'),
            venc.dias_restantes,
            venc.get_severidad_display(),
            float(venc.SALDO),
            venc.fecha_deteccion.strftime('%d/%m/%Y %H:%M'),
            'Sí' if venc.resuelto else 'No'
        ])
    
    return response

@login_required
def dashboard_vencimientos(request):
    """
    Dashboard con estadísticas de vencimientos
    """
    hoy = timezone.now().date()
    
    # Totales
    total = MedicamentoVencido.objects.count()
    pendientes = MedicamentoVencido.objects.filter(resuelto=False).count()
    resueltos = MedicamentoVencido.objects.filter(resuelto=True).count()
    
    # Por severidad
    vencidos = MedicamentoVencido.objects.filter(severidad='vencido', resuelto=False).count()
    por_vencer = MedicamentoVencido.objects.filter(severidad='por_vencer', resuelto=False).count()
    alerta = MedicamentoVencido.objects.filter(severidad='alerta', resuelto=False).count()
    
    # Valor monetario
    valor_total = MedicamentoVencido.objects.filter(resuelto=False).aggregate(
        total=Sum('SALDO')
    )['total'] or 0
    
    # Próximos vencimientos (7 días)
    semana_proxima = hoy + timedelta(days=7)
    proximos = MedicamentoVencido.objects.filter(
        MEDFECHVTO__range=[hoy, semana_proxima],
        resuelto=False
    ).count()
    
    # Top establecimientos con más vencimientos
    top_establecimientos = MedicamentoVencido.objects.filter(resuelto=False).values(
        'CODIGO_PRE'
    ).annotate(
        total=Count('id'),
        valor=Sum('SALDO')
    ).order_by('-total')[:10]
    
    context = {
        'total': total,
        'pendientes': pendientes,
        'resueltos': resueltos,
        'vencidos': vencidos,
        'por_vencer': por_vencer,
        'alerta': alerta,
        'valor_total': valor_total,
        'proximos': proximos,
        'top_establecimientos': top_establecimientos,
        'hoy': hoy,
    }
    
    return render(request, 'vencimientos/dashboard.html', context)