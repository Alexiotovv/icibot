from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Count, Sum, Avg, Q
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .forms import BuscarInconsistenciasForm
from .models import InconsistenciaFormDet, EstadisticaVerificacion
from externaldata.models import FormDet, ArchivosProcesados
from decimal import Decimal


@login_required
def verificar_inconsistencias(request):
    """
    Vista principal para verificar inconsistencias STOCKFIN-SALDO
    """
    form = BuscarInconsistenciasForm(request.GET or None)
    inconsistencias = []
    estadisticas = {}
    resumen_codigo_pre = []
    
    if request.method == 'GET' and any(request.GET.values()):
        if form.is_valid():
            # Obtener parámetros del formulario
            codigo_pre = form.cleaned_data.get('CODIGO_PRE')
            codigo_med = form.cleaned_data.get('CODIGO_MED')
            medlote = form.cleaned_data.get('MEDLOTE')
            ffinan = form.cleaned_data.get('FFINAN')
            tipsum = form.cleaned_data.get('TIPSUM')
            medregsan = form.cleaned_data.get('MEDREGSAN')
            annomes_inicio = form.cleaned_data.get('ANNOMES_inicio')
            annomes_fin = form.cleaned_data.get('ANNOMES_fin')
            severidad = form.cleaned_data.get('severidad')
            solo_no_resueltas = form.cleaned_data.get('solo_no_resueltas', True)
            
            # Filtrar inconsistencias existentes
            queryset = InconsistenciaFormDet.objects.all()
            
            if codigo_pre:
                queryset = queryset.filter(CODIGO_PRE__icontains=codigo_pre)
            
            if codigo_med:
                queryset = queryset.filter(CODIGO_MED__icontains=codigo_med)
            
            if medlote:
                queryset = queryset.filter(
                    Q(MEDLOTE_anterior__icontains=medlote) |
                    Q(MEDLOTE_actual__icontains=medlote)
                )
            
            if ffinan:
                queryset = queryset.filter(
                    Q(FFINAN_anterior__icontains=ffinan) |
                    Q(FFINAN_actual__icontains=ffinan)
                )
            
            if tipsum:
                queryset = queryset.filter(
                    Q(TIPSUM_anterior__icontains=tipsum) |
                    Q(TIPSUM_actual__icontains=tipsum)
                )
            
            if medregsan:
                queryset = queryset.filter(
                    Q(MEDREGSAN_anterior__icontains=medregsan) |
                    Q(MEDREGSAN_actual__icontains=medregsan)
                )
            
            if annomes_inicio:
                queryset = queryset.filter(ANNOMES_actual__gte=annomes_inicio)
            
            if annomes_fin:
                queryset = queryset.filter(ANNOMES_actual__lte=annomes_fin)
            
            if severidad:
                queryset = queryset.filter(severidad=severidad)
            
            if solo_no_resueltas:
                queryset = queryset.filter(resuelta=False)
            
            # Ordenar y paginar
            inconsistencias = queryset.order_by('-fecha_deteccion')
            
            # Estadísticas
            total_inconsistencias = inconsistencias.count()
            estadisticas = {
                'total': total_inconsistencias,
                'por_severidad': list(queryset.values('severidad').annotate(
                    total=Count('id')
                )),
                'por_tipo': list(queryset.values('tipo').annotate(
                    total=Count('id')
                )),
            }
            
            # Resumen por CODIGO_PRE
            resumen_codigo_pre = list(queryset.values('CODIGO_PRE').annotate(
                total=Count('id'),
                diferencia_promedio=Avg('diferencia')
            ).order_by('-total')[:20])
    
    # Verificar si se solicita ejecutar nueva verificación
    ejecutar = request.GET.get('ejecutar', False)
    if ejecutar and request.method == 'GET':
        return redirect('ejecutar_verificacion')
    
    context = {
        'form': form,
        'inconsistencias': inconsistencias,
        'estadisticas': estadisticas,
        'resumen_codigo_pre': resumen_codigo_pre,
        'ejecutar_verificacion_url': 'ejecutar_verificacion',
    }
    
    return render(request, 'verificaciones/verificar_inconsistencias.html', context)

@login_required
def ejecutar_verificacion(request):
    """
    Ejecuta la verificación de inconsistencias STOCK_FIN-SALDO
    Usa TIPSUM2 en lugar de TIPSUM
    """
    from django.db import transaction
    import time
    
    print(f"[DEBUG] Iniciando verificación - Usuario: {request.user}")
    print(f"[DEBUG] Usando TIPSUM2 en lugar de TIPSUM")
    tiempo_inicio = timezone.now()
    start_time = time.time()
    
    try:
        # Obtener todos los meses disponibles ordenados
        meses = FormDet.objects.values_list('ANNOMES', flat=True).distinct().order_by('ANNOMES')
        meses_list = list(meses)
        
        print(f"[DEBUG] Meses encontrados: {len(meses_list)} - {meses_list[:10]}...")
        
        if len(meses_list) < 2:
            messages.warning(request, 'No hay suficientes meses para realizar la verificación. Se necesitan al menos 2 meses.')
            return redirect('verificaciones:verificar_inconsistencias')
        
        total_inconsistencias_encontradas = 0
        inconsistencias_creadas = []
        
        with transaction.atomic():
            # Iterar sobre pares de meses consecutivos
            for i in range(1, len(meses_list)):
                mes_anterior = meses_list[i-1]
                mes_actual = meses_list[i]
                
                print(f"[DEBUG] Procesando: {mes_anterior} -> {mes_actual}")
                
                # Obtener registros del mes anterior - USAR TIPSUM2
                registros_anterior = FormDet.objects.filter(
                    ANNOMES=mes_anterior
                ).values(
                    'CODIGO_PRE', 'CODIGO_MED', 'MEDLOTE', 'FFINAN', 
                    'TIPSUM2', 'MEDFECHVTO', 'MEDREGSAN', 'STOCK_FIN'  # <-- TIPSUM2
                )
                
                print(f"[DEBUG] Registros mes anterior ({mes_anterior}): {registros_anterior.count()}")
                
                # Crear diccionario para búsqueda rápida - USAR TIPSUM2
                stock_fin_anterior = {}
                for reg in registros_anterior:
                    # Normalizar valores - USAR TIPSUM2
                    codigo_pre = str(reg['CODIGO_PRE']).strip()
                    codigo_med = str(reg['CODIGO_MED']).strip()
                    medlote = str(reg['MEDLOTE']).strip() if reg['MEDLOTE'] is not None else ''
                    ffinan = str(reg['FFINAN']).strip() if reg['FFINAN'] is not None else ''
                    tipsum2 = str(reg['TIPSUM2']).strip() if reg['TIPSUM2'] is not None else ''  # <-- TIPSUM2
                    medregsan = str(reg['MEDREGSAN']).strip() if reg['MEDREGSAN'] is not None else ''
                    
                    # Convertir fecha a string ISO
                    if reg['MEDFECHVTO']:
                        try:
                            medfechvto = reg['MEDFECHVTO'].isoformat()
                        except AttributeError:
                            medfechvto = str(reg['MEDFECHVTO'])
                    else:
                        medfechvto = ''
                    
                    # Crear key con TIPSUM2
                    key = (
                        f"{codigo_pre}|{codigo_med}|"
                        f"{medlote}|{ffinan}|{tipsum2}|"  # <-- TIPSUM2
                        f"{medregsan}|{medfechvto}"
                    )
                    
                    stock_fin_anterior[key] = {
                        'STOCK_FIN': reg['STOCK_FIN'],
                        'MEDLOTE': medlote,
                        'FFINAN': ffinan,
                        'TIPSUM2': tipsum2,  # <-- TIPSUM2
                        'MEDFECHVTO': medfechvto,
                        'MEDREGSAN': medregsan,
                        'CODIGO_PRE': codigo_pre,
                        'CODIGO_MED': codigo_med
                    }
                
                print(f"[DEBUG] Diccionario creado con {len(stock_fin_anterior)} entradas")
                
                # Obtener registros del mes actual
                registros_actual = FormDet.objects.filter(
                    ANNOMES=mes_actual
                ).select_related('archivo_procesado')
                
                print(f"[DEBUG] Registros mes actual ({mes_actual}): {registros_actual.count()}")
                
                # Verificar inconsistencias - USAR TIPSUM2
                for j, registro in enumerate(registros_actual):
                    # Normalizar valores - USAR TIPSUM2
                    codigo_pre_actual = str(registro.CODIGO_PRE).strip()
                    codigo_med_actual = str(registro.CODIGO_MED).strip()
                    medlote_actual = str(registro.MEDLOTE).strip() if registro.MEDLOTE is not None else ''
                    ffinan_actual = str(registro.FFINAN).strip() if registro.FFINAN is not None else ''
                    tipsum2_actual = str(registro.TIPSUM2).strip() if registro.TIPSUM2 is not None else ''  # <-- TIPSUM2
                    medregsan_actual = str(registro.MEDREGSAN).strip() if registro.MEDREGSAN is not None else ''
                    
                    # Convertir fecha a string ISO
                    if registro.MEDFECHVTO:
                        try:
                            medfechvto_actual = registro.MEDFECHVTO.isoformat()
                        except AttributeError:
                            medfechvto_actual = str(registro.MEDFECHVTO)
                    else:
                        medfechvto_actual = ''
                    
                    # Crear key con TIPSUM2
                    key = (
                        f"{codigo_pre_actual}|{codigo_med_actual}|"
                        f"{medlote_actual}|{ffinan_actual}|{tipsum2_actual}|"  # <-- TIPSUM2
                        f"{medregsan_actual}|{medfechvto_actual}"
                    )
                    
                    # DEBUG ESPECIAL para los registros que nos interesan
                    debug_especial = (
                        codigo_pre_actual == "27572" and 
                        codigo_med_actual == "05964" and
                        mes_anterior == "202512" and 
                        mes_actual == "202601"
                    )
                    
                    if debug_especial:
                        print(f"\n[DEBUG ESPECIAL] Registro encontrado:")
                        print(f"  CODIGO_PRE: '{codigo_pre_actual}'")
                        print(f"  CODIGO_MED: '{codigo_med_actual}'")
                        print(f"  TIPSUM (columna): '{registro.TIPSUM}'")
                        print(f"  TIPSUM2 (columna): '{tipsum2_actual}'")  # <-- IMPORTANTE
                        print(f"  MEDLOTE: '{medlote_actual}'")
                        print(f"  FFINAN: '{ffinan_actual}'")
                        print(f"  MEDREGSAN: '{medregsan_actual}'")
                        print(f"  MEDFECHVTO: '{medfechvto_actual}'")
                        print(f"  Key generada: {key}")
                        print(f"  SALDO actual: {registro.SALDO}")
                        
                        # Buscar keys similares en el diccionario
                        print(f"  Buscando en diccionario...")
                        encontrado = False
                        for k, v in stock_fin_anterior.items():
                            if "27572" in k and "05964" in k:
                                print(f"  Key en diccionario: {k}")
                                print(f"  TIPSUM2: '{v['TIPSUM2']}'")
                                print(f"  STOCK_FIN: {v['STOCK_FIN']}")
                                print(f"  ¿Keys iguales? {k == key}")
                                if k == key:
                                    encontrado = True
                        if not encontrado:
                            print(f"  ¡NO se encontró key exacta en diccionario!")
                    
                    # Solo comparar si existe un registro anterior con EXACTAMENTE los mismos campos
                    if key in stock_fin_anterior:
                        datos_anterior = stock_fin_anterior[key]
                        stock_fin_previo = datos_anterior['STOCK_FIN']
                        saldo_actual = registro.SALDO
                        
                        if debug_especial:
                            print(f"  ¡COINCIDENCIA EXACTA ENCONTRADA!")
                            print(f"  STOCK_FIN anterior: {stock_fin_previo}")
                            print(f"  SALDO actual: {saldo_actual}")
                            print(f"  Diferencia: {abs(float(stock_fin_previo) - float(saldo_actual))}")
                        
                        # Verificar si hay diferencia significativa (mayor a 0.01)
                        diferencia_valor = abs(float(stock_fin_previo) - float(saldo_actual))
                        
                        if debug_especial and diferencia_valor > 0.01:
                            print(f"  ¡INCONSISTENCIA DETECTADA!")
                            print(f"  Diferencia: {diferencia_valor}")
                        
                        if diferencia_valor > 0.01:
                            # Crear registro de inconsistencia
                            if diferencia_valor > 1000:
                                severidad = 'alta'
                            elif diferencia_valor > 100:
                                severidad = 'media'
                            else:
                                severidad = 'baja'
                            
                            inconsistencia = InconsistenciaFormDet(
                                archivo_procesado=registro.archivo_procesado,
                                tipo='stock_saldo',
                                
                                # Campos principales
                                CODIGO_PRE=registro.CODIGO_PRE,
                                CODIGO_MED=registro.CODIGO_MED,
                                ANNOMES_actual=registro.ANNOMES,
                                ANNOMES_anterior=mes_anterior,
                                
                                # Campos de agrupación actuales (del registro actual)
                                MEDLOTE=medlote_actual,
                                FFINAN=ffinan_actual,
                                TIPSUM2=tipsum2_actual,
                                MEDFECHVTO=registro.MEDFECHVTO if medfechvto_actual else None,
                                MEDREGSAN=medregsan_actual,
                                
                                # Campos de agrupación anteriores (del mes anterior)
                                MEDLOTE_anterior=datos_anterior['MEDLOTE'],
                                MEDLOTE_actual=medlote_actual,
                                
                                FFINAN_anterior=datos_anterior['FFINAN'],
                                FFINAN_actual=ffinan_actual,
                                
                                TIPSUM_anterior=datos_anterior.get('TIPSUM', datos_anterior.get('TIPSUM2', '')),  # Maneja TIPSUM y TIPSUM2
                                TIPSUM_actual=registro.TIPSUM,
                                
                                MEDFECHVTO_anterior=datos_anterior['MEDFECHVTO'] if datos_anterior['MEDFECHVTO'] else None,
                                MEDFECHVTO_actual=registro.MEDFECHVTO if medfechvto_actual else None,
                                
                                MEDREGSAN_anterior=datos_anterior['MEDREGSAN'],
                                MEDREGSAN_actual=medregsan_actual,
                                
                                # Valores numéricos
                                SALDO_actual=saldo_actual,
                                STOCKFIN_anterior=stock_fin_previo,
                                diferencia=diferencia_valor,
                                
                                # Información adicional
                                descripcion=f'STOCK_FIN anterior ({mes_anterior}): {stock_fin_previo}, '
                                        f'SALDO actual ({mes_actual}): {saldo_actual}, '
                                        f'CÓDIGO_PRE: {registro.CODIGO_PRE}, '
                                        f'CÓDIGO_MED: {registro.CODIGO_MED}, '
                                        f'MEDLOTE: {medlote_actual}, '
                                        f'FFINAN: {ffinan_actual}, '
                                        f'TIPSUM2: {tipsum2_actual}, '
                                        f'MEDREGSAN: {medregsan_actual}',
                                severidad=severidad,
                                usuario_deteccion=request.user,
                                datos_contexto={
                                    'CODIGO_EJE': registro.CODIGO_EJE,
                                    'MEDLOTE': medlote_actual,
                                    'FFINAN': ffinan_actual,
                                    'TIPSUM': registro.TIPSUM,
                                    'TIPSUM2': tipsum2_actual,
                                    'MEDFECHVTO': medfechvto_actual,
                                    'MEDREGSAN': medregsan_actual,
                                    'nombre_archivo': registro.archivo_procesado.nombre_archivo if registro.archivo_procesado else None,
                                }
                            )
                            inconsistencias_creadas.append(inconsistencia)
                            total_inconsistencias_encontradas += 1
                    
                    elif debug_especial:
                        print(f"  No se creará inconsistencia para este registro (no hay coincidencia exacta)")
            
            print(f"[DEBUG] Total inconsistencias encontradas: {total_inconsistencias_encontradas}")
            print(f"[DEBUG] Inconsistencias a crear: {len(inconsistencias_creadas)}")
            
            # Guardar todas las inconsistencias de una vez
            if inconsistencias_creadas:
                InconsistenciaFormDet.objects.bulk_create(inconsistencias_creadas)
                print(f"[DEBUG] Inconsistencias guardadas en BD")
            else:
                print(f"[DEBUG] No hay inconsistencias para guardar")
            
            # Crear estadística
            tiempo_fin = timezone.now()
            duracion = time.time() - start_time
            
            total_registros = FormDet.objects.count()
            print(f"[DEBUG] Total registros FormDet: {total_registros}")
            
            estadistica = EstadisticaVerificacion.objects.create(
                usuario=request.user,
                total_registros_analizados=total_registros,
                total_inconsistencias=total_inconsistencias_encontradas,
                total_inconsistencias_stock_saldo=total_inconsistencias_encontradas,
                tiempo_inicio=tiempo_inicio,
                tiempo_fin=tiempo_fin,
                duracion_segundos=duracion,
                parametros={
                    'tipo_verificacion': 'stock_saldo',
                    'campos_comparacion': ['CODIGO_PRE', 'CODIGO_MED', 'MEDLOTE', 'FFINAN', 'TIPSUM2', 'MEDFECHVTO', 'MEDREGSAN'],  # <-- TIPSUM2
                    'comparacion': 'exacta_todos_campos',
                    'version': 'con_tipsum2'
                },
            )
            
            print(f"[DEBUG] Estadística creada con ID: {estadistica.id}")
        
        messages.success(
            request,
            f'Verificación completada (usando TIPSUM2). Se encontraron {total_inconsistencias_encontradas} inconsistencias.'
        )
        print(f"[DEBUG] Mensaje de éxito mostrado")
        
    except Exception as e:
        print(f"[ERROR] Excepción en ejecutar_verificacion: {str(e)}")
        import traceback
        traceback.print_exc()
        
        messages.error(request, f'Error durante la verificación: {str(e)}')
        return redirect('verificaciones:verificar_inconsistencias')
    
    print(f"[DEBUG] Redirigiendo a la vista principal")
    return redirect('verificaciones:verificar_inconsistencias')

@login_required
def detalle_inconsistencia(request, inconsistencia_id):
    """
    Vista para ver detalles de una inconsistencia específica
    """
    inconsistencia = get_object_or_404(InconsistenciaFormDet, id=inconsistencia_id)
    
    # Obtener registros relacionados
    registros_actuales = FormDet.objects.filter(
        CODIGO_PRE=inconsistencia.CODIGO_PRE,
        CODIGO_MED=inconsistencia.CODIGO_MED,
        ANNOMES=inconsistencia.ANNOMES_actual
    ).first()
    
    registros_anteriores = FormDet.objects.filter(
        CODIGO_PRE=inconsistencia.CODIGO_PRE,
        CODIGO_MED=inconsistencia.CODIGO_MED,
        ANNOMES=inconsistencia.ANNOMES_anterior
    ).first()
    
    # Obtener historial de este CODIGO_PRE/CODIGO_MED
    historial = FormDet.objects.filter(
        CODIGO_PRE=inconsistencia.CODIGO_PRE,
        CODIGO_MED=inconsistencia.CODIGO_MED
    ).order_by('ANNOMES')[:12]
    
    context = {
        'inconsistencia': inconsistencia,
        'registro_actual': registros_actuales,
        'registro_anterior': registros_anteriores,
        'historial': historial,
    }
    
    return render(request, 'verificaciones/detalle_inconsistencia.html', context)

@login_required
@require_POST
def marcar_resuelta(request, inconsistencia_id):
    """
    Marca una inconsistencia como resuelta
    """
    inconsistencia = get_object_or_404(InconsistenciaFormDet, id=inconsistencia_id)
    inconsistencia.marcar_resuelta(request.user)
    
    messages.success(request, 'Inconsistencia marcada como resuelta.')
    return redirect('verificar_inconsistencias')

@login_required
def estadisticas_verificacion(request):
    """
    Vista para mostrar estadísticas de verificaciones
    """
    estadisticas = EstadisticaVerificacion.objects.all().order_by('-fecha_ejecucion')[:50]
    
    # Resumen general
    total_verificaciones = estadisticas.count()
    total_inconsistencias = sum(e.total_inconsistencias for e in estadisticas)
    
    context = {
        'estadisticas': estadisticas,
        'total_verificaciones': total_verificaciones,
        'total_inconsistencias': total_inconsistencias,
    }
    
    return render(request, 'verificaciones/estadisticas.html', context)

@login_required
def exportar_inconsistencias(request):
    """
    Exporta inconsistencias a CSV - Ahora incluye todos los campos
    """
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inconsistencias_completas.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'CODIGO_PRE', 'CODIGO_MED', 
        'MEDLOTE_ANTERIOR', 'MEDLOTE_ACTUAL',
        'FFINAN_ANTERIOR', 'FFINAN_ACTUAL',
        'TIPSUM_ANTERIOR', 'TIPSUM_ACTUAL',
        'MEDFECHVTO_ANTERIOR', 'MEDFECHVTO_ACTUAL',
        'MEDREGSAN_ANTERIOR', 'MEDREGSAN_ACTUAL',
        'MES_ANTERIOR', 'MES_ACTUAL', 
        'STOCKFIN_ANTERIOR', 'SALDO_ACTUAL', 
        'DIFERENCIA', 'SEVERIDAD', 
        'FECHA_DETECCION', 'RESUELTA', 'DESCRIPCION'
    ])
    
    inconsistencias = InconsistenciaFormDet.objects.filter(resuelta=False)
    
    for inc in inconsistencias:
        writer.writerow([
            inc.CODIGO_PRE, inc.CODIGO_MED,
            inc.MEDLOTE_anterior or 'SIN_LOTE', inc.MEDLOTE_actual or 'SIN_LOTE',
            inc.FFINAN_anterior or 'SIN_FFINAN', inc.FFINAN_actual or 'SIN_FFINAN',
            inc.TIPSUM_anterior or 'SIN_TIPSUM', inc.TIPSUM_actual or 'SIN_TIPSUM',
            inc.MEDFECHVTO_anterior or '', inc.MEDFECHVTO_actual or '',
            inc.MEDREGSAN_anterior or 'SIN_REGSAN', inc.MEDREGSAN_actual or 'SIN_REGSAN',
            inc.ANNOMES_anterior, inc.ANNOMES_actual,
            inc.STOCKFIN_anterior, inc.SALDO_actual,
            inc.diferencia, inc.severidad, inc.fecha_deteccion,
            'Sí' if inc.resuelta else 'No', inc.descripcion[:100]  # Limitar descripción
        ])
    
    return response


@login_required
def debug_verificacion(request):
    """Vista para debugging"""
    total_formdet = FormDet.objects.count()
    meses = list(FormDet.objects.values_list('ANNOMES', flat=True).distinct().order_by('ANNOMES'))
    total_inconsistencias = InconsistenciaFormDet.objects.count()
    
    # Verificar algunas inconsistencias manualmente
    debug_info = []
    
    # Tomar un ejemplo específico
    if total_formdet > 0:
        ejemplo = FormDet.objects.first()
        debug_info.append({
            'tipo': 'Primer registro FormDet',
            'datos': {
                'CODIGO_PRE': ejemplo.CODIGO_PRE,
                'CODIGO_MED': ejemplo.CODIGO_MED,
                'ANNOMES': ejemplo.ANNOMES,
                'STOCKFIN': float(ejemplo.STOCKFIN),
                'SALDO': float(ejemplo.SALDO),
            }
        })
    
    context = {
        'total_formdet': total_formdet,
        'total_meses': len(meses),
        'meses': meses[:10],  # Primeros 10 meses
        'total_inconsistencias': total_inconsistencias,
        'debug_info': debug_info,
    }
    
    return render(request, 'verificaciones/debug.html', context)