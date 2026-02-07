# correccion_dbf/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.conf import settings
import os
import tempfile
import shutil
from datetime import datetime

from .forms import SubirArchivoCorreccionForm, SeleccionarInconsistenciasForm
from .utils import ProcesadorDBF
from .models import CorreccionDBF
from verificaciones.models import InconsistenciaFormDet
from externaldata.models import ArchivosProcesados
from django.db.models import Count, Sum  
import traceback

# correccion_dbf/views.py - función subir_archivo_correccion
@login_required
@permission_required('correccion_dbf.can_correct_dbf', raise_exception=True)
def subir_archivo_correccion(request):
    """
    Vista para subir archivo ZIP con DBF a corregir
    """
    if request.method == 'POST':
        form = SubirArchivoCorreccionForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                archivo_zip = request.FILES['archivo_zip']
                contraseña = form.cleaned_data['contraseña']
                mes_archivo = form.cleaned_data['mes_archivo']  # AQUÍ TAMBIÉN
                crear_backup = form.cleaned_data['crear_backup']
                
                print(f"[DEBUG] Mes recibido del formulario: {mes_archivo}")
                
                # Validar formato del mes
                if len(mes_archivo) != 6 or not mes_archivo.isdigit():
                    messages.error(request, 'El mes debe tener formato AAAAMM (ej: 202601)')
                    return redirect('correccion_dbf:subir_archivo')
                
                # Calcular mes anterior automáticamente
                def calcular_mes_anterior(mes):
                    año = int(mes[:4])
                    mes_num = int(mes[4:])
                    if mes_num == 1:
                        return f"{año-1}12"
                    else:
                        return f"{año}{mes_num-1:02d}"
                
                mes_anterior = calcular_mes_anterior(mes_archivo)
                
                print(f"[UPLOAD] Archivo: {archivo_zip.name}")
                print(f"[UPLOAD] Mes archivo: {mes_archivo}")
                print(f"[UPLOAD] Mes anterior (para comparar): {mes_anterior}")
                
                # Verificar si hay inconsistencias para ese mes anterior
                inconsistencias_count = InconsistenciaFormDet.objects.filter(
                    ANNOMES_anterior=mes_anterior,
                    resuelta=False
                ).count()
                
                if inconsistencias_count == 0:
                    messages.warning(
                        request, 
                        f'No se encontraron inconsistencias para el mes anterior ({mes_anterior}). '
                        f'Verifique que haya ejecutado la detección de inconsistencias primero.'
                    )
                    return redirect('correccion_dbf:subir_archivo')
                
                # Guardar archivo temporalmente
                temp_dir = tempfile.mkdtemp()
                temp_zip_path = os.path.join(temp_dir, archivo_zip.name)
                
                with open(temp_zip_path, 'wb+') as destination:
                    for chunk in archivo_zip.chunks():
                        destination.write(chunk)
                
                # Procesar el archivo
                request.session['correccion_temp'] = {
                    'temp_dir': temp_dir,
                    'temp_zip': temp_zip_path,
                    'mes_archivo': mes_archivo,
                    'mes_anterior': mes_anterior,
                    'contraseña': contraseña,
                    'crear_backup': crear_backup,
                    'nombre_original': archivo_zip.name
                }
                
                messages.info(request, 
                    f'Archivo {archivo_zip.name} cargado exitosamente. '
                    f'Encontradas {inconsistencias_count} inconsistencias para corregir.'
                )
                return redirect('correccion_dbf:seleccionar_inconsistencias')
                
            except Exception as e:
                messages.error(request, f'Error al procesar archivo: {str(e)}')
                if 'temp_dir' in locals():
                    shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        form = SubirArchivoCorreccionForm()
    
    context = {
        'form': form,
        'title': 'Subir Archivo para Corrección'
    }
    
    return render(request, 'correccion_dbf/subir_archivo.html', context)

# correccion_dbf/views.py - función seleccionar_inconsistencias
@login_required
@permission_required('correccion_dbf.can_correct_dbf', raise_exception=True)
def seleccionar_inconsistencias(request):
    """
    Vista para seleccionar qué inconsistencias corregir
    """
    # Verificar que hay datos en sesión
    if 'correccion_temp' not in request.session:
        messages.error(request, 'No hay archivo cargado. Por favor, suba un archivo primero.')
        return redirect('correccion_dbf:subir_archivo')
    
    datos_sesion = request.session['correccion_temp']
    mes_archivo = datos_sesion['mes_archivo']
    mes_anterior = datos_sesion['mes_anterior']
    
    print(f"[CORRECCIÓN] Archivo del mes: {mes_archivo}")
    print(f"[CORRECCIÓN] Mes anterior: {mes_anterior}")
    
    # Obtener inconsistencias del mes anterior
    inconsistencias = InconsistenciaFormDet.objects.filter(
        ANNOMES_anterior=mes_anterior,
        resuelta=False
    ).order_by('-diferencia')
    
    print(f"[CORRECCIÓN] Encontradas {inconsistencias.count()} inconsistencias")
    
    if request.method == 'POST':
        print(f"[DEBUG] POST recibido")
        print(f"[DEBUG] POST data: {dict(request.POST)}")
        
        # Obtener IDs de las inconsistencias seleccionadas
        inconsistencias_ids = request.POST.getlist('inconsistencias')
        
        if not inconsistencias_ids:
            messages.warning(request, 'Debe seleccionar al menos una inconsistencia a corregir.')
            return redirect('correccion_dbf:seleccionar_inconsistencias')
        
        try:
            # Convertir a enteros
            inconsistencias_ids = [int(id) for id in inconsistencias_ids if id]
            
            # Guardar en sesión
            request.session['inconsistencias_seleccionadas'] = inconsistencias_ids
            
            messages.success(request, 
                f'{len(inconsistencias_ids)} inconsistencias seleccionadas. '
                f'Procediendo a la corrección...'
            )
            
            return redirect('correccion_dbf:ejecutar_correccion')
            
        except Exception as e:
            print(f"[ERROR] Error procesando selección: {str(e)}")
            messages.error(request, f'Error en la selección: {str(e)}')
            return redirect('correccion_dbf:seleccionar_inconsistencias')
    
    # GET request - Mostrar página
    context = {
        'mes_archivo': mes_archivo,
        'mes_anterior': mes_anterior,
        'total_inconsistencias': inconsistencias.count(),
        'inconsistencias': inconsistencias
    }
    
    return render(request, 'correccion_dbf/seleccionar_inconsistencias.html', context)

# correccion_dbf/views.py - función ejecutar_correccion
# correccion_dbf/views.py - función ejecutar_correccion (VERSIÓN SIMPLIFICADA)
@login_required
@permission_required('correccion_dbf.can_correct_dbf', raise_exception=True)
def ejecutar_correccion(request):
    """
    Ejecuta la corrección del archivo DBF usando STOCKFIN_anterior
    """
    # Verificar datos en sesión
    if 'correccion_temp' not in request.session or 'inconsistencias_seleccionadas' not in request.session:
        messages.error(request, 'Datos de sesión no encontrados. Inicie el proceso nuevamente.')
        return redirect('correccion_dbf:subir_archivo')
    
    datos_sesion = request.session['correccion_temp']
    inconsistencias_ids = request.session['inconsistencias_seleccionadas']
    
    try:
        print(f"[CORRECCIÓN] Iniciando corrección para {len(inconsistencias_ids)} inconsistencias")
        
        # Inicializar procesador
        procesador = ProcesadorDBF()
        
        # Descomprimir archivo ZIP
        temp_dir, archivos_dbf = procesador.descomprimir_zip_con_contraseña(
            datos_sesion['temp_zip'],
            datos_sesion['contraseña']
        )
        print(f"[CORRECCIÓN] Archivos DBF encontrados: {len(archivos_dbf)}")
        
        # DEBUG: Mostrar todos los archivos
        for i, archivo in enumerate(archivos_dbf, 1):
            nombre = os.path.basename(archivo)
            print(f"[DEBUG] Archivo {i}: {nombre}")
        
        # Encontrar archivo FORMDET - VERSIÓN DIRECTA
        ruta_formdet = None
        for archivo in archivos_dbf:
            nombre = os.path.basename(archivo)
            if nombre.lower() == 'formdet.dbf':  # Comparar en minúsculas
                ruta_formdet = archivo
                print(f"[CORRECCIÓN] ¡Archivo formDet.dbf encontrado!: {ruta_formdet}")
                break
        
        if not ruta_formdet:
            # Si no lo encuentra, intentar otras variaciones
            for archivo in archivos_dbf:
                nombre = os.path.basename(archivo).upper()
                if 'FORMDET' in nombre or ('FORM' in nombre and 'DET' in nombre):
                    ruta_formdet = archivo
                    print(f"[CORRECCIÓN] Archivo similar encontrado: {ruta_formdet}")
                    break
        
        if not ruta_formdet:
            messages.error(request, 
                'No se encontró el archivo formDet.dbf en el ZIP. '
                'Verifique que el archivo esté correctamente nombrado.'
            )
            shutil.rmtree(temp_dir, ignore_errors=True)
            return redirect('correccion_dbf:subir_archivo')
        
        # Leer DBF
        datos_dbf = procesador.leer_dbf(ruta_formdet)
        print(f"[CORRECCIÓN] DBF leído: {datos_dbf['total_registros']} registros")
        print(f"[CORRECCIÓN] Campos disponibles: {datos_dbf['campos']}")
        
        # Obtener inconsistencias seleccionadas
        inconsistencias = InconsistenciaFormDet.objects.filter(
            id__in=inconsistencias_ids
        )
        print(f"[CORRECCIÓN] Inconsistencias obtenidas de BD: {inconsistencias.count()}")
        
        # Buscar inconsistencias en el DBF
        registros_a_corregir = procesador.buscar_inconsistencias_en_dbf(
            datos_dbf, 
            inconsistencias
        )
        
        if not registros_a_corregir:
            messages.warning(request, 
                'No se encontraron las inconsistencias seleccionadas en el archivo DBF. '
                'Puede que los códigos no coincidan o que ya hayan sido corregidos.'
            )
            shutil.rmtree(temp_dir, ignore_errors=True)
            return redirect('correccion_dbf:subir_archivo')
        
        print(f"[CORRECCIÓN] Registros a corregir: {len(registros_a_corregir)}")
        
        # Corregir DBF - IMPORTANTE: Usar STOCKFIN_anterior para corregir SALDO
        resultado = procesador.corregir_saldo_en_dbf(
            ruta_formdet,
            registros_a_corregir,
            crear_backup=datos_sesion.get('crear_backup', True)
        )
        
        # Crear nuevo ZIP con los archivos corregidos
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        nombre_base = os.path.splitext(datos_sesion['nombre_original'])[0]
        nombre_zip_corregido = f"corregido_{nombre_base}_{timestamp}.zip"
        
        zip_corregido = procesador.crear_nuevo_zip(
            temp_dir,
            nombre_zip_corregido,
        )
        
        # Guardar registros de corrección
        for correccion in resultado['correcciones_aplicadas']:
            inc = correccion['inconsistencia']
            
            # Crear registro de corrección
            CorreccionDBF.objects.create(
                inconsistencia=inc,
                nombre_archivo_original=datos_sesion['nombre_original'],
                ruta_archivo_original=datos_sesion['temp_zip'],
                nombre_archivo_corregido=nombre_zip_corregido,
                ruta_archivo_corregido=zip_corregido,
                usuario=request.user,
                estado='corregido',
                valor_anterior=correccion['saldo_anterior'],
                valor_corregido=correccion['saldo_nuevo'],
                diferencia=abs(correccion['saldo_nuevo'] - correccion['saldo_anterior']),
                observaciones=f'SALDO corregido con STOCK_FIN anterior: {correccion["saldo_anterior"]} -> {correccion["saldo_nuevo"]}'
            )
            
            # IMPORTANTE: Marcar inconsistencia como resuelta
            inc.resuelta = True
            inc.fecha_resolucion = timezone.now()
            inc.save()
            print(f"[CORRECCIÓN] Inconsistencia {inc.id} marcada como resuelta")
        
        # Limpiar temporales
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Preparar respuesta con archivo para descargar
        request.session['archivo_corregido'] = {
            'nombre': nombre_zip_corregido,
            'ruta': zip_corregido,
            'total_corregido': resultado['total_corregido']
        }
        
        messages.success(request, 
            f'✅ Corrección completada exitosamente.<br>'
            f'<strong>{resultado["total_corregido"]} registros</strong> corregidos.<br>'
            f'Archivo disponible para descargar.'
        )
        return redirect('correccion_dbf:descargar_archivo')
        
    except Exception as e:
        print(f"[ERROR] Error durante la corrección: {str(e)}")
        traceback.print_exc()
        
        messages.error(request, 
            f'❌ Error durante la corrección:<br>'
            f'<strong>{str(e)}</strong>'
        )
        
        # Limpiar temporales
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        return redirect('correccion_dbf:subir_archivo')

# correccion_dbf/views.py - función descargar_archivo (ACTUALIZADA)
@login_required
def descargar_archivo(request):
    """
    Muestra página de resultados y permite descargar el archivo ZIP corregido
    """
    if 'archivo_corregido' not in request.session:
        messages.error(request, 'No hay archivo corregido para descargar.')
        return redirect('correccion_dbf:subir_archivo')
    
    archivo_info = request.session['archivo_corregido']
    
    # Si el usuario solicita descargar el archivo (con ?download=true)
    if request.GET.get('download') == 'true':
        try:
            # Verificar que el archivo exista físicamente
            if not os.path.exists(archivo_info['ruta']):
                messages.error(request, 'El archivo corregido ya no existe en el servidor.')
                # Limpiar sesión
                if 'archivo_corregido' in request.session:
                    del request.session['archivo_corregido']
                return redirect('correccion_dbf:dashboard')
            
            # Abrir archivo y crear respuesta de descarga
            with open(archivo_info['ruta'], 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="{archivo_info["nombre"]}"'
                
                # Registrar en logs
                print(f"[DESCARGAR] Archivo descargado: {archivo_info['nombre']}")
                print(f"[DESCARGAR] Ruta: {archivo_info['ruta']}")
                print(f"[DESCARGAR] Usuario: {request.user.username}")
                
                # NO eliminar el archivo físicamente aquí
                # Solo limpiar la sesión después de descargar
                if 'correccion_temp' in request.session:
                    del request.session['correccion_temp']
                if 'inconsistencias_seleccionadas' in request.session:
                    del request.session['inconsistencias_seleccionadas']
                # Mantener archivo_corregido por si quiere descargar de nuevo
                
                return response
                
        except Exception as e:
            print(f"[ERROR] Error al descargar archivo: {str(e)}")
            messages.error(request, f'Error al descargar archivo: {str(e)}')
            return redirect('correccion_dbf:dashboard')
    
    # Si es GET normal, mostrar página de resultados
    context = {
        'archivo_info': archivo_info,
        'fecha_correccion': timezone.now()
    }
    
    return render(request, 'correccion_dbf/descargar_archivo.html', context)

@login_required
def historial_correcciones(request):
    """
    Muestra historial de correcciones realizadas
    """
    correcciones = CorreccionDBF.objects.all().order_by('-fecha_correccion')[:50]
    
    context = {
        'correcciones': correcciones,
        'total_correcciones': correcciones.count()
    }
    
    return render(request, 'correccion_dbf/historial.html', context)

@login_required
def dashboard_correcciones(request):
    """
    Dashboard de correcciones
    """
    # Estadísticas
    total_correcciones = CorreccionDBF.objects.count()
    correcciones_hoy = CorreccionDBF.objects.filter(
        fecha_correccion__date=timezone.now().date()
    ).count()
    
    # Últimas correcciones
    ultimas_correcciones = CorreccionDBF.objects.all().order_by('-fecha_correccion')[:10]
    
    # Correcciones por usuario
    correcciones_por_usuario = CorreccionDBF.objects.values(
        'usuario__username'
    ).annotate(
        total=Count('id'),
        valor_total=Sum('diferencia')
    ).order_by('-total')[:5]
    
    context = {
        'total_correcciones': total_correcciones,
        'correcciones_hoy': correcciones_hoy,
        'ultimas_correcciones': ultimas_correcciones,
        'correcciones_por_usuario': correcciones_por_usuario
    }
    
    return render(request, 'correccion_dbf/dashboard.html', context)


# correccion_dbf/views.py - función limpiar_archivo
@login_required
def limpiar_archivo(request):
    """
    Limpia el archivo corregido de la sesión y del disco si el usuario ya no lo necesita
    """
    if 'archivo_corregido' in request.session:
        archivo_info = request.session['archivo_corregido']
        
        try:
            # Intentar eliminar el archivo físico
            if os.path.exists(archivo_info['ruta']):
                os.remove(archivo_info['ruta'])
                print(f"[LIMPIEZA] Archivo eliminado: {archivo_info['ruta']}")
        except Exception as e:
            print(f"[LIMPIEZA] Error al eliminar archivo: {str(e)}")
        
        # Limpiar sesión
        del request.session['archivo_corregido']
        messages.info(request, 'Archivo temporal limpiado correctamente.')
    
    # También limpiar otras variables de sesión si existen
    for key in ['correccion_temp', 'inconsistencias_seleccionadas', 'mes_info']:
        if key in request.session:
            del request.session[key]
    
    return redirect('correccion_dbf:dashboard')