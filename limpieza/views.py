from django.shortcuts import render

# Create your views here.
# limpieza/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import connection, models
from django.db.models import Count, Min, Max
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
import csv
import json

from .forms import LimpiarTablaForm, ConsultaEstadisticasForm
from .models import OperacionLimpieza

# Importar todos los modelos necesarios
from verificaciones.models import InconsistenciaFormDet, EstadisticaVerificacion
from externaldata.models import FormDet, ArchivosProcesados, Ime1, Imed2, Imed3
from vencimientos.models import MedicamentoVencido
from process.models import ProcesamientoHistorico

# Mapeo de nombres de tablas a modelos
MODELOS = {
    'InconsistenciaFormDet': InconsistenciaFormDet,
    'EstadisticaVerificacion': EstadisticaVerificacion,
    'FormDet': FormDet,
    'ArchivosProcesados': ArchivosProcesados,
    'ProcesamientoHistorico': ProcesamientoHistorico,
    # 'ExternalAPI': ExternalAPI,
    'MedicamentoVencido': MedicamentoVencido,
    'Ime1': Ime1,
    'Imed2': Imed2,
    'Imed3': Imed3,
}

@login_required
@permission_required('limpieza.can_clean_data', raise_exception=True)
def dashboard_limpieza(request):
    """
    Dashboard principal de limpieza de datos
    """
    estadisticas = {}
    
    # Obtener estadísticas de cada tabla
    for nombre_tabla, modelo in MODELOS.items():
        try:
            total = modelo.objects.count()
            if hasattr(modelo, 'fecha_creacion'):
                fecha_min = modelo.objects.aggregate(Min('fecha_creacion'))['fecha_creacion__min']
                fecha_max = modelo.objects.aggregate(Max('fecha_creacion'))['fecha_creacion__max']
            elif hasattr(modelo, 'fecha_deteccion'):
                fecha_min = modelo.objects.aggregate(Min('fecha_deteccion'))['fecha_deteccion__min']
                fecha_max = modelo.objects.aggregate(Max('fecha_deteccion'))['fecha_deteccion__max']
            elif hasattr(modelo, 'fecha_procesamiento'):
                fecha_min = modelo.objects.aggregate(Min('fecha_procesamiento'))['fecha_procesamiento__min']
                fecha_max = modelo.objects.aggregate(Max('fecha_procesamiento'))['fecha_procesamiento__max']
            else:
                fecha_min = fecha_max = None
            
            estadisticas[nombre_tabla] = {
                'total': total,
                'fecha_min': fecha_min,
                'fecha_max': fecha_max,
                'tamaño_aprox': total * 100,  # Estimación aproximada en bytes
            }
        except Exception as e:
            estadisticas[nombre_tabla] = {
                'total': 'Error',
                'error': str(e)
            }
    
    # Obtener historial de operaciones recientes
    operaciones_recientes = OperacionLimpieza.objects.all().order_by('-fecha_inicio')[:10]
    
    context = {
        'estadisticas': estadisticas,
        'operaciones_recientes': operaciones_recientes,
        'total_tablas': len(MODELOS),
        'total_registros': sum(stat['total'] for stat in estadisticas.values() if isinstance(stat.get('total'), int)),
    }
    
    return render(request, 'limpieza/dashboard.html', context)

@login_required
@permission_required('limpieza.can_clean_data', raise_exception=True)
def consultar_tabla(request):
    """
    Consulta estadísticas y detalles de una tabla
    """
    form = ConsultaEstadisticasForm(request.GET or None)
    datos_tabla = None
    detalles = []
    
    if request.method == 'GET' and form.is_valid():
        nombre_tabla = form.cleaned_data['tabla']
        ver_detalles = form.cleaned_data['ver_detalles']
        
        if nombre_tabla in MODELOS:
            modelo = MODELOS[nombre_tabla]
            
            # Estadísticas básicas
            total = modelo.objects.count()
            
            # Obtener algunas columnas comunes para estadísticas
            datos_tabla = {
                'nombre': nombre_tabla,
                'total': total,
                'campos': [field.name for field in modelo._meta.fields],
            }
            
            # Si es FormDet, obtener estadísticas por ANNOMES
            if nombre_tabla == 'FormDet':
                annomes_stats = FormDet.objects.values('ANNOMES').annotate(
                    total=Count('id'),
                    saldo_total=models.Sum('SALDO')
                ).order_by('-ANNOMES')[:12]
                datos_tabla['annomes_stats'] = annomes_stats
            
            # Si se solicitan detalles, obtener algunos registros de ejemplo
            if ver_detalles and total > 0:
                detalles = list(modelo.objects.all()[:10].values())
    
    context = {
        'form': form,
        'datos_tabla': datos_tabla,
        'detalles': detalles,
    }
    
    return render(request, 'limpieza/consultar_tabla.html', context)

@login_required
@permission_required('limpieza.can_clean_data', raise_exception=True)
def limpiar_tabla(request):
    """
    Limpia o vacía una tabla seleccionada
    """
    form = LimpiarTablaForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        nombre_tabla = form.cleaned_data['tabla']
        operacion = form.cleaned_data['operacion']
        fecha_hasta = form.cleaned_data['fecha_hasta']
        
        if nombre_tabla not in MODELOS:
            messages.error(request, f'Tabla {nombre_tabla} no encontrada.')
            return redirect('limpieza:dashboard')
        
        modelo = MODELOS[nombre_tabla]
        
        # Crear registro de operación
        operacion_log = OperacionLimpieza.objects.create(
            usuario=request.user,
            tipo_operacion='vaciar' if operacion in ['vaciar', 'backup_vaciar'] else 'eliminar',
            tabla=nombre_tabla,
            estado='en_progreso'
        )
        
        try:
            total_inicial = modelo.objects.count()
            operacion_log.total_registros = total_inicial
            
            if operacion == 'vaciar':
                # Vaciar tabla completamente
                modelo.objects.all().delete()
                registros_eliminados = total_inicial
                
            elif operacion == 'backup_vaciar':
                # Crear backup primero
                backup_file = crear_backup_tabla(nombre_tabla, request.user)
                # Luego vaciar
                modelo.objects.all().delete()
                registros_eliminados = total_inicial
                operacion_log.observaciones = f'Backup creado: {backup_file}'
                
            elif operacion == 'eliminar_filtros' and fecha_hasta:
                # Eliminar por fecha
                filtros = {'fecha_hasta': fecha_hasta.isoformat()}
                
                # Determinar campo de fecha según el modelo
                if hasattr(modelo, 'fecha_creacion'):
                    queryset = modelo.objects.filter(fecha_creacion__lt=fecha_hasta)
                elif hasattr(modelo, 'fecha_deteccion'):
                    queryset = modelo.objects.filter(fecha_deteccion__lt=fecha_hasta)
                elif hasattr(modelo, 'fecha_procesamiento'):
                    queryset = modelo.objects.filter(fecha_procesamiento__lt=fecha_hasta)
                else:
                    queryset = modelo.objects.none()
                
                registros_eliminados = queryset.count()
                queryset.delete()
                operacion_log.filtros = filtros
            else:
                registros_eliminados = 0
            
            # Actualizar operación
            operacion_log.registros_eliminados = registros_eliminados
            operacion_log.estado = 'completado'
            operacion_log.fecha_fin = timezone.now()
            operacion_log.save()
            
            messages.success(
                request,
                f'Operación completada. {registros_eliminados} registros eliminados de {nombre_tabla}.'
            )
            
        except Exception as e:
            operacion_log.estado = 'error'
            operacion_log.observaciones = f'Error: {str(e)}'
            operacion_log.save()
            
            messages.error(request, f'Error durante la limpieza: {str(e)}')
        
        return redirect('limpieza:dashboard')
    
    context = {
        'form': form,
    }
    
    return render(request, 'limpieza/limpiar_tabla.html', context)

@login_required
@permission_required('limpieza.can_clean_data', raise_exception=True)
def exportar_backup(request, nombre_tabla):
    """
    Exporta una tabla completa a CSV
    """
    if nombre_tabla not in MODELOS:
        messages.error(request, f'Tabla {nombre_tabla} no encontrada.')
        return redirect('limpieza:dashboard')
    
    modelo = MODELOS[nombre_tabla]
    
    # Crear respuesta HTTP con archivo CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="backup_{nombre_tabla}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Configurar writer con encoding UTF-8-BOM para Excel
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    
    # Obtener nombres de campos
    campos = [field.name for field in modelo._meta.fields]
    writer.writerow(campos)
    
    # Escribir datos
    for registro in modelo.objects.all().iterator(chunk_size=1000):
        fila = []
        for campo in campos:
            valor = getattr(registro, campo)
            if isinstance(valor, (datetime, timezone.datetime)):
                fila.append(valor.strftime('%Y-%m-%d %H:%M:%S'))
            elif valor is None:
                fila.append('')
            else:
                fila.append(str(valor))
        writer.writerow(fila)
    
    # Registrar operación
    OperacionLimpieza.objects.create(
        usuario=request.user,
        tipo_operacion='backup',
        tabla=nombre_tabla,
        total_registros=modelo.objects.count(),
        estado='completado',
        observaciones=f'Backup exportado a CSV'
    )
    
    messages.success(request, f'Backup de {nombre_tabla} exportado exitosamente.')
    return response

@login_required
@permission_required('limpieza.can_clean_data', raise_exception=True)
def optimizar_tabla(request, nombre_tabla):
    """
    Optimiza una tabla (VACUUM en PostgreSQL, OPTIMIZE en MySQL)
    """
    if nombre_tabla not in MODELOS:
        return JsonResponse({'error': 'Tabla no encontrada'}, status=404)
    
    # Crear registro de operación
    operacion_log = OperacionLimpieza.objects.create(
        usuario=request.user,
        tipo_operacion='optimizar',
        tabla=nombre_tabla,
        estado='en_progreso'
    )
    
    try:
        with connection.cursor() as cursor:
            # Dependiendo del motor de base de datos
            db_engine = connection.vendor
            
            if db_engine == 'postgresql':
                cursor.execute(f'VACUUM ANALYZE "{nombre_tabla.lower()}";')
            elif db_engine == 'mysql':
                cursor.execute(f'OPTIMIZE TABLE {nombre_tabla};')
            elif db_engine == 'sqlite':
                cursor.execute(f'VACUUM;')
            
            operacion_log.estado = 'completado'
            operacion_log.observaciones = f'Optimización completada (motor: {db_engine})'
            operacion_log.save()
            
            messages.success(request, f'Tabla {nombre_tabla} optimizada exitosamente.')
            
    except Exception as e:
        operacion_log.estado = 'error'
        operacion_log.observaciones = f'Error: {str(e)}'
        operacion_log.save()
        
        messages.error(request, f'Error optimizando tabla: {str(e)}')
    
    return redirect('limpieza:dashboard')

@login_required
def obtener_estadisticas_ajax(request):
    """
    Endpoint AJAX para obtener estadísticas en tiempo real
    """
    estadisticas = {}
    
    for nombre_tabla, modelo in MODELOS.items():
        try:
            total = modelo.objects.count()
            estadisticas[nombre_tabla] = total
        except:
            estadisticas[nombre_tabla] = 0
    
    return JsonResponse(estadisticas)

# Funciones auxiliares
def crear_backup_tabla(nombre_tabla, usuario):
    """
    Crea un backup de una tabla y lo guarda en el sistema de archivos
    """
    import os
    from django.conf import settings
    
    if nombre_tabla not in MODELOS:
        return None
    
    modelo = MODELOS[nombre_tabla]
    
    # Crear directorio de backups si no existe
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Nombre del archivo
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backup_{nombre_tabla}_{timestamp}.json"
    filepath = os.path.join(backup_dir, filename)
    
    # Exportar datos a JSON
    datos = list(modelo.objects.all().values())
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            'tabla': nombre_tabla,
            'fecha_backup': timestamp,
            'usuario': usuario.username,
            'total_registros': len(datos),
            'datos': datos
        }, f, ensure_ascii=False, indent=2)
    
    return filename