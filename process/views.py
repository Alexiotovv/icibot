import csv
import os
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from tokens.models import EnlaceToken
from .forms import FechaForm

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
import zipfile, os, tempfile, dbf,json

from dbf import Table  # Librería moderna para DBF
from django.views.decorators.csrf import csrf_exempt
import dbf
import pandas as pd
from django.http import JsonResponse

from externaldata.utils import extraer_formdet_desde_zip
from externaldata.services import guardar_formdet_desde_df
from process.models import ProcesamientoHistorico
import time

from datetime import datetime, date
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from dbfread import DBF
from externaldata.models import ArchivosProcesados, FormDet, Ime1, Imed2, Imed3
from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import HttpResponse

from django.contrib.auth.models import User

# views.py
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from externaldata.models import ArchivosProcesados, FormDet, Ime1, Imed2, Imed3

@login_required
def ver_registros_archivo(request, archivo_id):
    archivo = get_object_or_404(ArchivosProcesados, id=archivo_id, usuario=request.user)
    
    # Obtener el tipo de pestaña activa
    active_tab = request.GET.get('tab', 'formdet')
    
    # Configurar paginación para cada tipo de registro
    registros_por_pagina = 50
    
    # FormDet
    registros_formdet = archivo.formularios_detalle.all().order_by('-created_at')
    paginator_formdet = Paginator(registros_formdet, registros_por_pagina)
    page_formdet = request.GET.get('page_formdet', 1)
    
    try:
        registros_formdet_paginados = paginator_formdet.page(page_formdet)
    except PageNotAnInteger:
        registros_formdet_paginados = paginator_formdet.page(1)
    except EmptyPage:
        registros_formdet_paginados = paginator_formdet.page(paginator_formdet.num_pages)
    
    # IME1
    registros_ime1 = archivo.ime1_registros.all().order_by('-created_at')
    paginator_ime1 = Paginator(registros_ime1, registros_por_pagina)
    page_ime1 = request.GET.get('page_ime1', 1)
    
    try:
        registros_ime1_paginados = paginator_ime1.page(page_ime1)
    except PageNotAnInteger:
        registros_ime1_paginados = paginator_ime1.page(1)
    except EmptyPage:
        registros_ime1_paginados = paginator_ime1.page(paginator_ime1.num_pages)
    
    # IMED2
    registros_imed2 = archivo.imed2_registros.all().order_by('-created_at')
    paginator_imed2 = Paginator(registros_imed2, registros_por_pagina)
    page_imed2 = request.GET.get('page_imed2', 1)
    
    try:
        registros_imed2_paginados = paginator_imed2.page(page_imed2)
    except PageNotAnInteger:
        registros_imed2_paginados = paginator_imed2.page(1)
    except EmptyPage:
        registros_imed2_paginados = paginator_imed2.page(paginator_imed2.num_pages)
    
    # IMED3
    registros_imed3 = archivo.imed3_registros.all().order_by('-created_at')
    paginator_imed3 = Paginator(registros_imed3, registros_por_pagina)
    page_imed3 = request.GET.get('page_imed3', 1)
    
    try:
        registros_imed3_paginados = paginator_imed3.page(page_imed3)
    except PageNotAnInteger:
        registros_imed3_paginados = paginator_imed3.page(1)
    except EmptyPage:
        registros_imed3_paginados = paginator_imed3.page(paginator_imed3.num_pages)
    
    # Totales
    total_formdet = registros_formdet.count()
    total_ime1 = registros_ime1.count()
    total_imed2 = registros_imed2.count()
    total_imed3 = registros_imed3.count()
    total_registros = total_formdet + total_ime1 + total_imed2 + total_imed3
    
    context = {
        'archivo': archivo,
        'active_tab': active_tab,
        'registros_formdet': registros_formdet_paginados,
        'registros_ime1': registros_ime1_paginados,
        'registros_imed2': registros_imed2_paginados,
        'registros_imed3': registros_imed3_paginados,
        'total_formdet': total_formdet,
        'total_ime1': total_ime1,
        'total_imed2': total_imed2,
        'total_imed3': total_imed3,
        'total_registros': total_registros,
    }
    
    return render(request, 'process_volumen/ver_registros.html', context)

def consumir_api(request):
    data = None
    error = None

    if request.method == 'POST':
        form = FechaForm(request.POST)
        if form.is_valid():
            fecha_inicio = form.cleaned_data['fecha_inicio']
            fecha_final = form.cleaned_data['fecha_final']

            try:
                api_config = EnlaceToken.objects.first()
                headers = {
                    'Authorization': f'Bearer {api_config.token}',
                    'Accept': 'application/json',
                }

                payload = {
                    'fecha_inicio': str(fecha_inicio),
                    'fecha_final': str(fecha_final)
                }

                response = requests.post(api_config.url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    registros = data.get("data", [])  # extrae la lista de registros

                    media_path = os.path.join(settings.MEDIA_ROOT, "descargas")
                    os.makedirs(media_path, exist_ok=True)

                    for registro in registros:
                        url = registro.get("archivo_url")
                        if url:
                            file_name = url.split("/")[-1]
                            file_path = os.path.join(media_path, file_name)

                            file_response = requests.get(url)
                            if file_response.status_code == 200:
                                with open(file_path, "wb") as f:
                                    f.write(file_response.content)
                else:
                    error = f"Error en la solicitud: {response.status_code}"
            except Exception as e:
                error = str(e)
    else:
        form = FechaForm()

    return render(request, 'process/consumir_api.html', {'form': form, 'error': error})

def subir_zip_volumen(request):
    return render(request, 'process_volumen/index.html')


@login_required
def subir_formulario_zip(request):
    """Muestra el formulario para subir archivos (GET)"""
    return render(request, 'process_volumen/subir_archivo.html')

#Desde aqui nuevo codigo
@login_required
def procesar_archivos_zip(request):
    """Procesa el archivo ZIP (POST) - Guarda sub-zips con referencia al principal"""
    if request.method == 'POST':
        # Verificar si es AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if not request.FILES.get('archivo_zip'):
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Debe seleccionar un archivo ZIP'
                })
            else:
                messages.error(request, 'Debe seleccionar un archivo ZIP')
                return redirect('subir_archivo')
        
        archivo_zip = request.FILES['archivo_zip']
        password = request.POST.get('password', '')
        
        if not password:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Debe ingresar la contraseña para los archivos ZIP internos'
                })
            else:
                messages.error(request, 'Debe ingresar la contraseña para los archivos ZIP internos')
                return redirect('subir_archivo')
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Guardar archivo ZIP principal
                zip_principal_path = os.path.join(temp_dir, archivo_zip.name)
                with open(zip_principal_path, 'wb') as f:
                    for chunk in archivo_zip.chunks():
                        f.write(chunk)
                
                # Extraer ZIP principal
                with zipfile.ZipFile(zip_principal_path, 'r') as zip_principal:
                    zip_principal.extractall(temp_dir)
                
                # Buscar y procesar ZIPs internos
                resultados_totales = {
                    'zips_procesados': 0,
                    'zips_con_error': 0,
                    'total_dbf': 0,
                    'formdet_registros': 0,
                    'ime1_registros': 0,
                    'imed2_registros': 0,
                    'imed3_registros': 0,
                    'archivo_principal': archivo_zip.name,  # Guardamos nombre del principal
                    'archivos_procesados': []  # Lista de sub-archivos procesados
                }
                
                # **MODIFICACIÓN IMPORTANTE: Evitar procesar el archivo principal**
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        # **EXCLUIR el archivo principal de ser procesado**
                        if file.lower().endswith('.zip') and file != archivo_zip.name:
                            zip_secundario_path = os.path.join(root, file)
                            
                            try:
                                # CREAR REGISTRO SOLO PARA SUB-ZIP CON REFERENCIA AL PRINCIPAL
                                archivo_procesado = ArchivosProcesados.objects.create(
                                    usuario=request.user,
                                    nombre_archivo=file,  # Nombre del sub-zip
                                    archivo_principal=archivo_zip.name  # Nombre del zip principal
                                )
                                
                                # Procesar este sub-zip específico
                                resultado_zip = procesar_single_zip(zip_secundario_path, archivo_procesado, password)
                                
                                # Actualizar conteos
                                resultados_totales['zips_procesados'] += 1
                                resultados_totales['total_dbf'] += resultado_zip.get('total_dbf', 0)
                                resultados_totales['formdet_registros'] += resultado_zip.get('formdet', 0)
                                resultados_totales['ime1_registros'] += resultado_zip.get('ime1', 0)
                                resultados_totales['imed2_registros'] += resultado_zip.get('imed2', 0)
                                resultados_totales['imed3_registros'] += resultado_zip.get('imed3', 0)
                                
                                # Guardar información del archivo procesado
                                resultados_totales['archivos_procesados'].append({
                                    'nombre': file,
                                    'registros_formdet': resultado_zip.get('formdet', 0),
                                    'registros_ime1': resultado_zip.get('ime1', 0),
                                    'version': archivo_procesado.version_formdet or 'Desconocida'
                                })
                                
                            except Exception as e:
                                resultados_totales['zips_con_error'] += 1
                                print(f"⚠️ Error en {file}: {str(e)}")
                
                # Respuesta AJAX
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Procesados {resultados_totales["zips_procesados"]} sub-archivos del ZIP principal "{archivo_zip.name}"',
                        'resultados': resultados_totales
                    })
                else:
                    messages.success(request, f'Procesados {resultados_totales["zips_procesados"]} sub-archivos del ZIP principal "{archivo_zip.name}"')
                    return redirect('archivos_procesados')
                
        except Exception as e:
            error_msg = f'Error al procesar el archivo: {str(e)}'
            
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': error_msg
                })
            else:
                messages.error(request, error_msg)
                return redirect('subir_archivo')
    
    # Si es GET, redirigir al formulario
    return redirect('subir_archivo')


def procesar_archivo_completo(archivo_zip, password, archivo_procesado):
    """Función principal que procesa todo el archivo"""
    import tempfile
    import os
    import zipfile
    
    resultados = {
        'zips_procesados': 0,
        'zips_con_error': 0,
        'total_dbf': 0,
        'formdet_registros': 0,
        'ime1_registros': 0,
        'imed2_registros': 0,
        'imed3_registros': 0
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Guardar archivo ZIP principal
        zip_principal_path = os.path.join(temp_dir, archivo_zip.name)
        with open(zip_principal_path, 'wb') as f:
            for chunk in archivo_zip.chunks():
                f.write(chunk)
        
        # Extraer ZIP principal
        try:
            with zipfile.ZipFile(zip_principal_path, 'r') as zip_principal:
                zip_principal.extractall(temp_dir)
        except zipfile.BadZipFile as e:
            raise Exception(f'El archivo ZIP principal está corrupto: {str(e)}')
        
        # Buscar y procesar ZIPs internos
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith('.zip'):
                    zip_secundario_path = os.path.join(root, file)
                    
                    try:
                        resultado_zip = procesar_single_zip(zip_secundario_path, archivo_procesado, password)
                        resultados['zips_procesados'] += 1
                        resultados['total_dbf'] += resultado_zip.get('total_dbf', 0)
                        resultados['formdet_registros'] += resultado_zip.get('formdet', 0)
                        resultados['ime1_registros'] += resultado_zip.get('ime1', 0)
                        resultados['imed2_registros'] += resultado_zip.get('imed2', 0)
                        resultados['imed3_registros'] += resultado_zip.get('imed3', 0)
                        
                    except Exception as e:
                        resultados['zips_con_error'] += 1
                        print(f"⚠️ Error en {file}: {str(e)}")
    
    return resultados

def procesar_zip_internos(temp_dir, archivo_procesado, password):
    """Procesa todos los ZIPs internos y devuelve resultados"""
    resultados = {
        'zips_procesados': 0,
        'zips_con_error': 0,
        'total_dbf': 0,
        'formdet_registros': 0,
        'ime1_registros': 0,
        'imed2_registros': 0,
        'imed3_registros': 0
    }
    
    # Buscar todos los ZIPs recursivamente
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith('.zip'):
                zip_path = os.path.join(root, file)
                try:
                    # Procesar cada ZIP con timeout
                    resultado_zip = procesar_single_zip(zip_path, archivo_procesado, password)
                    resultados['zips_procesados'] += 1
                    resultados['total_dbf'] += resultado_zip.get('total_dbf', 0)
                    resultados['formdet_registros'] += resultado_zip.get('formdet', 0)
                    resultados['ime1_registros'] += resultado_zip.get('ime1', 0)
                    resultados['imed2_registros'] += resultado_zip.get('imed2', 0)
                    resultados['imed3_registros'] += resultado_zip.get('imed3', 0)
                    
                except Exception as e:
                    resultados['zips_con_error'] += 1
                    print(f"Error procesando {file}: {str(e)}")
    
    return resultados


def procesar_formdet_chunked(dbf_path, archivo_procesado, chunk_size=500):
    """Procesa FormDet en chunks con detección de versión"""
    try:
        table = DBF(dbf_path, encoding='latin-1', char_decode_errors='ignore')
        
        # Detectar versión
        version = detectar_version_formdet(table)
        print(f"📊 Detectada versión FormDet: {version}")
        
        total = 0
        batch = []
        
        for i, record in enumerate(table):
            try:
                # Pasar la versión como parámetro si necesitas lógica diferente
                datos = preparar_datos_formdet(record, archivo_procesado)
                batch.append(FormDet(**datos))
                total += 1
                
                if len(batch) >= chunk_size:
                    FormDet.objects.bulk_create(batch)
                    batch = []
                    
                    # Mostrar progreso cada 1000 registros
                    if total % 1000 == 0:
                        print(f"  ✅ Procesados {total} registros...")
                    
            except Exception as e:
                # Log del error pero continuar
                print(f"  ⚠️ Error en registro {i}: {e}")
                continue
        
        # Insertar los registros restantes
        if batch:
            FormDet.objects.bulk_create(batch)
        
        print(f"✅ FormDet v{version}: {total} registros creados")
        return total
        
    except Exception as e:
        print(f"❌ Error procesando FormDet: {e}")
        return 0
    
def preparar_datos_formdet(record, archivo_procesado):
    """Prepara datos optimizados para FormDet, maneja versiones 2.4 y 2.5"""
    datos = {
        # Relación y campos principales
        'archivo_procesado': archivo_procesado,
        'CODIGO_EJE': convertir_texto_simple(record.get('CODIGO_EJE', ''), 3),
        'CODIGO_PRE': convertir_texto_simple(record.get('CODIGO_PRE', ''), 11),
        'TIPSUM': convertir_texto_simple(record.get('TIPSUM', ''), 1),
        'ANNOMES': convertir_texto_simple(record.get('ANNOMES', ''), 6),
        'CODIGO_MED': convertir_texto_simple(record.get('CODIGO_MED', ''), 7),
        
        # Campos numéricos comunes (versión 2.4 y 2.5)
        'SALDO': convertir_valor_simple(record.get('SALDO')),
        'PRECIO': convertir_valor_simple(record.get('PRECIO')),
        'INGRE': convertir_valor_simple(record.get('INGRE')),
        'REINGRE': convertir_valor_simple(record.get('REINGRE')),
        'VENTA': convertir_valor_simple(record.get('VENTA')),
        'SIS': convertir_valor_simple(record.get('SIS')),
        'INTERSAN': convertir_valor_simple(record.get('INTERSAN')),
        'FAC_PERD': convertir_valor_simple(record.get('FAC_PERD')),
        'DEFNAC': convertir_valor_simple(record.get('DEFNAC')),
        'EXO': convertir_valor_simple(record.get('EXO')),
        'SOAT': convertir_valor_simple(record.get('SOAT')),
        'CREDHOSP': convertir_valor_simple(record.get('CREDHOSP')),
        'OTR_CONV': convertir_valor_simple(record.get('OTR_CONV')),
        'DEVOL': convertir_valor_simple(record.get('DEVOL')),
        'VENCIDO': convertir_valor_simple(record.get('VENCIDO')),
        'MERMA': convertir_valor_simple(record.get('MERMA')),
        'DISTRI': convertir_valor_simple(record.get('DISTRI')),
        'TRANSF': convertir_valor_simple(record.get('TRANSF')),
        'VENTAINST': convertir_valor_simple(record.get('VENTAINST')),
        'DEV_VEN': convertir_valor_simple(record.get('DEV_VEN')),
        'DEV_MERMA': convertir_valor_simple(record.get('DEV_MERMA')),
        'OTRAS_SAL': convertir_valor_simple(record.get('OTRAS_SAL')),
        'STOCK_FIN': convertir_valor_simple(record.get('STOCK_FIN')),
        'STOCK_FIN1': convertir_valor_simple(record.get('STOCK_FIN1')),
        'REQ': convertir_valor_simple(record.get('REQ')),
        'TOTAL': convertir_valor_simple(record.get('TOTAL')),
        
        # Campos de fecha comunes
        'FEC_EXP': convertir_fecha_simple(record.get('FEC_EXP')),
        'DO_FECEXP': convertir_fecha_simple(record.get('DO_FECEXP')),
        'FECHA': convertir_fecha_simple(record.get('FECHA')),
        
        # Campos DO comunes
        'DO_SALDO': convertir_valor_simple(record.get('DO_SALDO')),
        'DO_INGRE': convertir_valor_simple(record.get('DO_INGRE')),
        'DO_CON': convertir_valor_simple(record.get('DO_CON')),
        'DO_OTR': convertir_valor_simple(record.get('DO_OTR')),
        'DO_TOT': convertir_valor_simple(record.get('DO_TOT')),
        'DO_STK': convertir_valor_simple(record.get('DO_STK')),
        
        # Campos de usuario y estado comunes
        'USUARIO': convertir_texto_simple(record.get('USUARIO', 'SISTEMA'), 15),
        'INDIPROC': convertir_texto_simple(record.get('INDIPROC', 'N'), 1),
        'SIT': convertir_texto_simple(record.get('SIT', 'A'), 1),
        'INDISIGA': convertir_texto_simple(record.get('INDISIGA', 'N'), 1),
        
        # Campos adicionales comunes (pueden no existir en alguna versión)
        'DSTKCERO': convertir_valor_simple(record.get('DSTKCERO')),
        'MPTOREPO': convertir_valor_simple(record.get('MPTOREPO')),
        'ING_REGULA': convertir_valor_simple(record.get('ING_REGULA')),
        'SAL_REGULA': convertir_valor_simple(record.get('SAL_REGULA')),
        'SAL_CONINS': convertir_valor_simple(record.get('SAL_CONINS')),
        'STOCKFIN': convertir_valor_simple(record.get('STOCKFIN')),
        'STOCKFIN1': convertir_valor_simple(record.get('STOCKFIN1')),
        
        # **AQUÍ ESTÁ EL PROBLEMA - FALTAN LOS CAMPOS DE VERSIÓN 2.5:**
        'ESSALUD': convertir_valor_simple(record.get('ESSALUD')),
        'MEDLOTE': convertir_texto_simple(record.get('MEDLOTE', ''), 20),
        'MEDREGSAN': convertir_texto_simple(record.get('MEDREGSAN', ''), 20),
        'MEDFECHVTO': convertir_fecha_simple(record.get('MEDFECHVTO')),
        'TIPSUM2': convertir_texto_simple(record.get('TIPSUM2', ''), 2),
        'FFINAN': convertir_texto_simple(record.get('FFINAN', ''), 3),
        'PREADQ': convertir_valor_simple(record.get('PREADQ')),
    }
    
    # Ajustes para CODIGO_PRE si es muy largo
    codigo_pre = datos['CODIGO_PRE']
    if len(codigo_pre) > 11:
        datos['CODIGO_PRE'] = codigo_pre[:11]

    # Ajuste para TRANSF si es muy grande
    transf = datos['TRANSF']
    if transf > Decimal('99999999.99'):  # Si excede 10 dígitos
        datos['TRANSF'] = Decimal('99999999.99')

    return datos


def convertir_valor_simple(valor):
    """Conversión rápida y segura de valores numéricos"""
    if valor is None or valor == '':
        return Decimal('0.00')
    
    try:
        # Si es string, limpiarlo
        if isinstance(valor, str):
            # Remover espacios y comas
            valor_limpio = valor.strip().replace(',', '')
            # Remover caracteres no numéricos excepto punto y signo
            valor_limpio = ''.join(c for c in valor_limpio if c.isdigit() or c in '.-')
            
            # Si quedó vacío, retornar 0
            if not valor_limpio or valor_limpio == '.' or valor_limpio == '-':
                return Decimal('0.00')
            
            # Convertir a Decimal
            return Decimal(valor_limpio)
        
        # Si ya es numérico
        elif isinstance(valor, (int, float, Decimal)):
            return Decimal(str(valor))
        
        # Para bytes u otros tipos
        else:
            return Decimal('0.00')
            
    except (ValueError, InvalidOperation, TypeError):
        return Decimal('0.00')


def convertir_fecha_simple(valor):
    """Conversión rápida de fechas - VERSIÓN MÁS ROBUSTA"""
    if not valor:
        return None
    
    try:
        # Si ya es datetime o date
        if isinstance(valor, (datetime, date)):
            return valor.date() if isinstance(valor, datetime) else valor
        
        # Si es string
        if isinstance(valor, str):
            valor = valor.strip()
            
            # Si está vacío después de strip
            if not valor:
                return None
            
            # Intentar varios formatos comunes
            formatos_a_probar = [
                '%Y%m%d',      # 20250123
                '%d/%m/%Y',    # 23/01/2025
                '%Y-%m-%d',    # 2025-01-23
                '%d.%m.%Y',    # 23.01.2025
                '%Y/%m/%d',    # 2025/01/23
                '%d-%m-%Y',    # 23-01-2025
            ]
            
            for formato in formatos_a_probar:
                try:
                    return datetime.strptime(valor, formato).date()
                except ValueError:
                    continue
            
            # Si tiene formato de fecha de DBF (ej: datetime.date(2025, 1, 23))
            if valor.startswith('datetime.date(') or valor.startswith('date('):
                try:
                    # Extraer año, mes, día del string
                    import re
                    match = re.search(r'(\d{4}).*?(\d{1,2}).*?(\d{1,2})', valor)
                    if match:
                        año, mes, dia = map(int, match.groups())
                        return date(año, mes, dia)
                except:
                    pass
        
        # Si tiene atributos de fecha
        if hasattr(valor, 'year') and hasattr(valor, 'month') and hasattr(valor, 'day'):
            try:
                return date(valor.year, valor.month, valor.day)
            except:
                pass
        
        return None
        
    except Exception as e:
        print(f"⚠️ Error convirtiendo fecha '{valor}' (tipo: {type(valor)}): {e}")
        return None


def convertir_texto_simple(valor, max_length=None):
    """Conversión rápida de texto"""
    if valor is None:
        return ''
    
    try:
        # Convertir a string
        texto = str(valor).strip()
        
        # Si es bytes, decodificar
        if isinstance(valor, bytes):
            try:
                texto = valor.decode('utf-8')
            except UnicodeDecodeError:
                texto = valor.decode('latin-1', errors='ignore')
        
        # Limitar longitud si se especifica
        if max_length and len(texto) > max_length:
            return texto[:max_length]
        
        return texto
        
    except Exception:
        return ''


def procesar_single_zip(zip_path, archivo_procesado, password):
    """Procesa un solo ZIP con timeout - SOLO formDet.dbf"""
    import threading
    import queue
    
    resultado = queue.Queue()
    
    def worker():
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_path, 'r') as zip_sec:
                    zip_sec.setpassword(password.encode('utf-8'))
                    
                    # Lista de tablas que queremos procesar
                    TABLAS_PROCESAR = {
                        'formdet.dbf': procesar_formdet_chunked,
                        # 'ime1.dbf': procesar_ime1_chunked,
                        # 'imed2.dbf': procesar_imed2_chunked,
                        # 'imed3.dbf': procesar_imed3_chunked,
                    }
                    
                    # Filtrar solo los archivos que queremos procesar
                    dbf_files = []
                    for file_info in zip_sec.infolist():
                        file_name = file_info.filename.lower()
                        if file_name in TABLAS_PROCESAR:
                            dbf_files.append(file_info.filename)
                    
                    if not dbf_files:
                        print(f"ℹ️ No se encontraron tablas procesables en {os.path.basename(zip_path)}")
                        resultado.put({'total_dbf': 0, 'formdet': 0, 'ime1': 0, 'imed2': 0, 'imed3': 0})
                        return
                    
                    print(f"📁 Archivos a procesar en {os.path.basename(zip_path)}: {dbf_files}")
                    
                    # Extraer solo los archivos que vamos a procesar
                    for dbf_file in dbf_files:
                        zip_sec.extract(dbf_file, temp_dir, pwd=password.encode('utf-8'))
                    
                    # Procesar cada DBF
                    conteos = {'total_dbf': len(dbf_files), 'formdet': 0, 'ime1': 0, 'imed2': 0, 'imed3': 0}
                    
                    for dbf_file in dbf_files:
                        dbf_path = os.path.join(temp_dir, dbf_file)
                        nombre = os.path.basename(dbf_file).lower()
                        
                        if nombre in TABLAS_PROCESAR:
                            # Debug solo para formDet
                            if nombre == 'formdet.dbf':
                                debug_formdet_dbf(dbf_path)
                            
                            # Detectar versión si es formDet
                            version_detectada = None
                            if nombre == 'formdet.dbf':
                                version_detectada = detectar_version_formdet_dbf(dbf_path)
                                # **GUARDAR VERSIÓN EN EL REGISTRO**
                                archivo_procesado.version_formdet = version_detectada
                                archivo_procesado.save()
                                print(f"📊 Versión detectada para {os.path.basename(zip_path)}: {version_detectada}")
                            
                            # Llamar a la función de procesamiento
                            funcion_procesar = TABLAS_PROCESAR[nombre]
                            count = funcion_procesar(dbf_path, archivo_procesado)
                            
                            # Actualizar conteos
                            if nombre == 'formdet.dbf':
                                conteos['formdet'] += count
                            elif nombre == 'ime1.dbf':
                                conteos['ime1'] += count
                            elif nombre == 'imed2.dbf':
                                conteos['imed2'] += count
                            elif nombre == 'imed3.dbf':
                                conteos['imed3'] += count
                    
                    resultado.put(conteos)
                    
        except Exception as e:
            resultado.put({'error': str(e), 'total_dbf': 0, 'formdet': 0, 'ime1': 0, 'imed2': 0, 'imed3': 0})
    
    # Ejecutar con timeout
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout=300)
    
    if thread.is_alive():
        raise TimeoutError(f"Timeout procesando {os.path.basename(zip_path)}")
    
    if resultado.empty():
        raise Exception(f"Error desconocido procesando {os.path.basename(zip_path)}")
    
    return resultado.get()


def procesar_zip_secundario(zip_path, archivo_procesado, password):
    """Procesa un ZIP secundario con contraseña"""
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_sec:
                # Establecer la contraseña para todos los archivos en el ZIP
                zip_sec.setpassword(password.encode('utf-8'))
                
                # Verificar que el ZIP no esté corrupto
                zip_sec.testzip()
                
                # Extraer todos los archivos
                zip_sec.extractall(temp_dir)
                
                # Procesar cada archivo DBF en el ZIP
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.lower().endswith('.dbf'):
                            dbf_path = os.path.join(root, file)
                            procesar_dbf(dbf_path, file, archivo_procesado)
                                
        except RuntimeError as e:
            if 'Bad password' in str(e) or 'password' in str(e).lower():
                raise RuntimeError(f"Contraseña incorrecta para {os.path.basename(zip_path)}")
            else:
                raise
        except zipfile.BadZipFile:
            raise RuntimeError(f"Archivo ZIP corrupto: {os.path.basename(zip_path)}")
        except Exception as e:
            raise RuntimeError(f"Error al procesar {os.path.basename(zip_path)}: {str(e)}")

def procesar_dbf(dbf_path, nombre_archivo, archivo_procesado):
    """Procesa un archivo DBF específico - SOLO formDet.dbf"""
    nombre_base = nombre_archivo.lower()
    
    # SOLO procesar formDet.dbf (nombre exacto)
    if nombre_base == 'formdet.dbf':
        procesar_formdet(dbf_path, archivo_procesado)
    # elif nombre_base == 'ime1.dbf':
    #     procesar_ime1(dbf_path, archivo_procesado)
    # elif nombre_base == 'imed2.dbf':
    #     procesar_imed2(dbf_path, archivo_procesado)
    # elif nombre_base == 'imed3.dbf':
    #     procesar_imed3(dbf_path, archivo_procesado)
    else:
        print(f"ℹ️ Archivo {nombre_archivo} ignorado (no está en la lista de procesamiento)")

def convertir_valor(valor, tipo='decimal'):
    """Convierte valores del DBF al tipo correcto"""
    if valor is None or valor == '':
        return None if tipo == 'date' else 0
    
    try:
        if tipo == 'decimal':
            # Remover comas, espacios, etc.
            if isinstance(valor, str):
                valor = valor.strip().replace(',', '')
            return Decimal(str(valor))
        elif tipo == 'date':
            # Intentar diferentes formatos de fecha
            if isinstance(valor, str):
                valor = valor.strip()
                if len(valor) == 8:  # YYYYMMDD
                    return datetime.strptime(valor, '%Y%m%d').date()
                elif len(valor) == 10:  # DD/MM/YYYY
                    return datetime.strptime(valor, '%d/%m/%Y').date()
            elif isinstance(valor, datetime):
                return valor.date()
        elif tipo == 'string':
            return str(valor).strip() if valor else ''
    except (ValueError, InvalidOperation):
        return None if tipo == 'date' else 0
    
    return valor if valor else (None if tipo == 'date' else 0)

@transaction.atomic
def procesar_formdet(dbf_path, archivo_procesado):
    """Procesa archivo FormDet.dbf"""
    try:
        # Leer DBF con encoding apropiado
        table = DBF(dbf_path, encoding='latin-1', char_decode_errors='ignore')
        
        registros_creados = 0
        batch_size = 1000
        batch = []
        
        for record in table:
            try:
                # Preparar datos
                datos = {
                    'archivo_procesado': archivo_procesado,
                    'CODIGO_EJE': convertir_valor(record.get('CODIGO_EJE'), 'string') or '',
                    'CODIGO_PRE': convertir_valor(record.get('CODIGO_PRE'), 'string') or '',
                    'TIPSUM': convertir_valor(record.get('TIPSUM'), 'string') or '',
                    'ANNOMES': convertir_valor(record.get('ANNOMES'), 'string') or '',
                    'CODIGO_MED': convertir_valor(record.get('CODIGO_MED'), 'string') or '',
                    'SALDO': convertir_valor(record.get('SALDO'), 'decimal'),
                    'PRECIO': convertir_valor(record.get('PRECIO'), 'decimal'),
                    'INGRE': convertir_valor(record.get('INGRE'), 'decimal'),
                    'REINGRE': convertir_valor(record.get('REINGRE'), 'decimal'),
                    'VENTA': convertir_valor(record.get('VENTA'), 'decimal'),
                    'SIS': convertir_valor(record.get('SIS'), 'decimal'),
                    'INTERSAN': convertir_valor(record.get('INTERSAN'), 'decimal'),
                    'FAC_PERD': convertir_valor(record.get('FAC_PERD'), 'decimal'),
                    'DEFNAC': convertir_valor(record.get('DEFNAC'), 'decimal'),
                    'EXO': convertir_valor(record.get('EXO'), 'decimal'),
                    'SOAT': convertir_valor(record.get('SOAT'), 'decimal'),
                    'CREDHOSP': convertir_valor(record.get('CREDHOSP'), 'decimal'),
                    'OTR_CONV': convertir_valor(record.get('OTR_CONV'), 'decimal'),
                    'DEVOL': convertir_valor(record.get('DEVOL'), 'decimal'),
                    'VENCIDO': convertir_valor(record.get('VENCIDO'), 'decimal'),
                    'MERMA': convertir_valor(record.get('MERMA'), 'decimal'),
                    'DISTRI': convertir_valor(record.get('DISTRI'), 'decimal'),
                    'TRANSF': convertir_valor(record.get('TRANSF'), 'decimal'),
                    'VENTAINST': convertir_valor(record.get('VENTAINST'), 'decimal'),
                    'DEV_VEN': convertir_valor(record.get('DEV_VEN'), 'decimal'),
                    'DEV_MERMA': convertir_valor(record.get('DEV_MERMA'), 'decimal'),
                    'OTRAS_SAL': convertir_valor(record.get('OTRAS_SAL'), 'decimal'),
                    'STOCK_FIN': convertir_valor(record.get('STOCK_FIN'), 'decimal'),
                    'STOCK_FIN1': convertir_valor(record.get('STOCK_FIN1'), 'decimal'),
                    'REQ': convertir_valor(record.get('REQ'), 'decimal'),
                    'TOTAL': convertir_valor(record.get('TOTAL'), 'decimal'),
                    'FEC_EXP': convertir_valor(record.get('FEC_EXP'), 'date'),
                    'DO_SALDO': convertir_valor(record.get('DO_SALDO'), 'decimal'),
                    'DO_INGRE': convertir_valor(record.get('DO_INGRE'), 'decimal'),
                    'DO_CON': convertir_valor(record.get('DO_CON'), 'decimal'),
                    'DO_OTR': convertir_valor(record.get('DO_OTR'), 'decimal'),
                    'DO_TOT': convertir_valor(record.get('DO_TOT'), 'decimal'),
                    'DO_STK': convertir_valor(record.get('DO_STK'), 'decimal'),
                    'DO_FECEXP': convertir_valor(record.get('DO_FECEXP'), 'date'),
                    'FECHA': convertir_valor(record.get('FECHA'), 'date'),
                    'USUARIO': convertir_valor(record.get('USUARIO'), 'string') or 'SISTEMA',
                    'INDIPROC': convertir_valor(record.get('INDIPROC'), 'string') or 'N',
                    'SIT': convertir_valor(record.get('SIT'), 'string') or 'A',
                    'INDISIGA': convertir_valor(record.get('INDISIGA'), 'string') or 'N',
                    'DSTKCERO': convertir_valor(record.get('DSTKCERO'), 'decimal'),
                    'MPTOREPO': convertir_valor(record.get('MPTOREPO'), 'decimal'),
                    'ING_REGULA': convertir_valor(record.get('ING_REGULA'), 'decimal'),
                    'SAL_REGULA': convertir_valor(record.get('SAL_REGULA'), 'decimal'),
                    'SAL_CONINS': convertir_valor(record.get('SAL_CONINS'), 'decimal'),
                    'STOCKFIN': convertir_valor(record.get('STOCKFIN'), 'decimal'),
                    'STOCKFIN1': convertir_valor(record.get('STOCKFIN1'), 'decimal'),
                }
                
                # Crear registro
                batch.append(FormDet(**datos))
                registros_creados += 1
                
                # Insertar por lotes para mejor performance
                if len(batch) >= batch_size:
                    FormDet.objects.bulk_create(batch)
                    batch = []
                    
            except Exception as e:
                print(f"Error procesando registro FormDet: {e}")
                continue
        
        # Insertar registros restantes
        if batch:
            FormDet.objects.bulk_create(batch)
        
        print(f"✅ FormDet: {registros_creados} registros creados")
        
    except Exception as e:
        print(f"❌ Error procesando FormDet.dbf: {e}")
        raise

@transaction.atomic
def procesar_ime1(dbf_path, archivo_procesado):
    """Procesa archivo Ime1.dbf"""
    try:
        table = DBF(dbf_path, encoding='latin-1', char_decode_errors='ignore')
        
        registros_creados = 0
        batch = []
        batch_size = 1000
        
        campos_numericos = [
            'IMPVTAS', 'IMPCREDH', 'IMPSOAT', 'IMPOTRC', 'IMPSIS', 'IMPINTS', 
            'IMPDN', 'IMPEXO', 'DVTAS80', 'DVTAS20', 'DCREH80', 'DCREH20',
            # ... añade todos los campos numéricos
        ]
        
        for record in table:
            try:
                # Datos básicos
                datos = {
                    'archivo_procesado': archivo_procesado,
                    'ANNOMES': convertir_valor(record.get('ANNOMES'), 'string') or '',
                    'CODIGO_EJE': convertir_valor(record.get('CODIGO_EJE'), 'string') or '',
                    'CODIGO_PRE': convertir_valor(record.get('CODIGO_PRE'), 'string') or '',
                    'FECHREG': convertir_valor(record.get('FECHREG'), 'date'),
                    'FECHULTM': convertir_valor(record.get('FECHULTM'), 'date'),
                    'USUARIO': convertir_valor(record.get('USUARIO'), 'string') or 'SISTEMA',
                }
                
                # Añadir campos numéricos
                for campo in campos_numericos:
                    datos[campo] = convertir_valor(record.get(campo), 'decimal')
                
                batch.append(Ime1(**datos))
                registros_creados += 1
                
                if len(batch) >= batch_size:
                    Ime1.objects.bulk_create(batch)
                    batch = []
                    
            except Exception as e:
                print(f"Error procesando registro Ime1: {e}")
                continue
        
        if batch:
            Ime1.objects.bulk_create(batch)
        
        print(f"✅ Ime1: {registros_creados} registros creados")
        
    except Exception as e:
        print(f"❌ Error procesando Ime1.dbf: {e}")
        raise

@transaction.atomic
def procesar_imed2(dbf_path, archivo_procesado):
    """Procesa archivo Imed2.dbf"""
    try:
        table = DBF(dbf_path, encoding='latin-1', char_decode_errors='ignore')
        
        registros = []
        for record in table:
            try:
                imed2 = Imed2(
                    archivo_procesado=archivo_procesado,
                    ANNOMES=convertir_valor(record.get('ANNOMES'), 'string') or '',
                    CODIGO_EJE=convertir_valor(record.get('CODIGO_EJE'), 'string') or '',
                    CODIGO_PRE=convertir_valor(record.get('CODIGO_PRE'), 'string') or '',
                    FECHDEPO=convertir_valor(record.get('FECHDEPO'), 'date'),
                    NRODEPO=convertir_valor(record.get('NRODEPO'), 'string') or '',
                    IMPDEPO=convertir_valor(record.get('IMPDEPO'), 'decimal'),
                )
                registros.append(imed2)
            except Exception as e:
                print(f"Error procesando registro Imed2: {e}")
                continue
        
        Imed2.objects.bulk_create(registros)
        print(f"✅ Imed2: {len(registros)} registros creados")
        
    except Exception as e:
        print(f"❌ Error procesando Imed2.dbf: {e}")
        raise

@transaction.atomic
def procesar_imed3(dbf_path, archivo_procesado):
    """Procesa archivo Imed3.dbf"""
    try:
        table = DBF(dbf_path, encoding='latin-1', char_decode_errors='ignore')
        
        registros = []
        for record in table:
            try:
                imed3 = Imed3(
                    archivo_procesado=archivo_procesado,
                    ANNOMES=convertir_valor(record.get('ANNOMES'), 'string') or '',
                    CODIGO_EJE=convertir_valor(record.get('CODIGO_EJE'), 'string') or '',
                    CODIGO_PRE=convertir_valor(record.get('CODIGO_PRE'), 'string') or '',
                    FECHGUIA=convertir_valor(record.get('FECHGUIA'), 'date'),
                    NROGUIA=convertir_valor(record.get('NROGUIA'), 'string') or '',
                    IMPGUIA=convertir_valor(record.get('IMPGUIA'), 'decimal'),
                )
                registros.append(imed3)
            except Exception as e:
                print(f"Error procesando registro Imed3: {e}")
                continue
        
        Imed3.objects.bulk_create(registros)
        print(f"✅ Imed3: {len(registros)} registros creados")
        
    except Exception as e:
        print(f"❌ Error procesando Imed3.dbf: {e}")
        raise

#Hasta aqui nuevo codigo

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
#@csrf_exempt  # Solo si necesitas deshabilitar CSRF para pruebas
def procesar_zip(request): 
    if 'archivo' not in request.FILES:
        return Response({'error': 'Debe proporcionar un archivo ZIP'}, status=400)
    
    zip_file = request.FILES['archivo']
    password = request.POST.get('password', '').encode('utf-8') or None

    TABLAS_OBJETIVO = {
        'formdet': 'formDet',
        # 'ime1': 'Ime1',
        # 'imed2': 'Imed2',
        # 'imed3': 'Imed3'
    }

    resultados = {nombre: [] for nombre in TABLAS_OBJETIVO.values()}

    #print(f"Tamaño recibido: {zip_file.size / (1024*1024):.2f} MB")


    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir, pwd=password)
            
            for filename in os.listdir(tmp_dir):
                file_lower = filename.lower()
                
                if filename in TABLAS_OBJETIVO:  # Para formDet.dbf (exact match)
                    tabla_key = filename
                else:
                    file_lower = filename.lower()
                    tabla_key = next(
                        (key for key in TABLAS_OBJETIVO 
                        if file_lower.startswith(key) and not file_lower == 'formdet1.dbf'),
                        None
                    )

                if tabla_key:
                    ruta_dbf = os.path.join(tmp_dir, filename)
                    try:
                        # SOLUCIÓN ACTUALIZADA: Sin parámetros no soportados
                        table = dbf.Table(
                            filename=ruta_dbf,
                            codepage='utf8'  # Mantenemos solo el parámetro esencial
                        )
                        table.open()

                        # Procesamiento seguro con manejo de errores por registro
                        registros = []
                        for record in table:
                            try:
                                registro_limpio = {}
                                for field in table.field_names:
                                    try:
                                        value = record[field]
                                        if isinstance(value, str):
                                            value = value.strip()  # Elimina espacios al inicio/fin
                                            value = ' '.join(value.split())  # Elimina espacios múltiples internos
                                            
                                        elif isinstance(value, bytes):
                                            try:
                                                value = value.decode('utf-8')
                                            except UnicodeDecodeError:
                                                value = value.decode('latin1', errors='replace')
                                        registro_limpio[field] = value
                                    except:
                                        registro_limpio[field] = None  # Valor por defecto si hay error
                                registros.append(registro_limpio)
                            except:
                                continue  # Si el registro completo falla, lo omitimos
                        registros_unicos = list({tuple(sorted(r.items())): r for r in registros}.values())
                        resultados[TABLAS_OBJETIVO[tabla_key]] = registros_unicos
                        # resultados[TABLAS_OBJETIVO[tabla_key]] = registros
                        table.close()
                        
                    except Exception as e:
                        # Error más específico para diagnóstico
                        return Response(
                            {
                                'error': f'Error al procesar {filename}',
                                'detalle': str(e),
                                'sugerencia': 'Verifique la estructura del archivo DBF'
                            },
                            status=400
                        )

        except zipfile.BadZipFile:
            return Response({'error': 'Archivo ZIP corrupto o contraseña incorrecta'}, status=400)
        except Exception as e:
            return Response({'error': f'Error inesperado: {str(e)}'}, status=500)

 
    if 'formDet' in resultados:
        resultados['FormDet'] = resultados.pop('formDet')

    return Response({
        'status': 'success',
        'tablas_procesadas': resultados,
        'archivos_procesados': [k for k, v in resultados.items() if v]
    })

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def validar_zip(request):
    """
    Valida que el ZIP contenga las tablas formDet.dbf y Imed3.dbf
    y que ambas tengan registros. Si no cumple, devuelve error 400.
    """

    if 'archivo' not in request.FILES:
        return Response({'error': 'Debe proporcionar un archivo ZIP'}, status=400)
    
    zip_file = request.FILES['archivo']
    password = request.POST.get('password', '').encode('utf-8') or None

    TABLAS_REQUERIDAS = {
        'formdet': 'formDet',
        'imed3': 'Imed3'
    }

    resultados = {nombre: [] for nombre in TABLAS_REQUERIDAS.values()}
    faltantes = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir, pwd=password)
        except zipfile.BadZipFile:
            return Response({'error': 'Archivo ZIP corrupto o contraseña incorrecta'}, status=400)
        except RuntimeError:
            return Response({'error': 'Contraseña incorrecta o ZIP encriptado'}, status=400)

        # --- Buscar archivos .dbf en todas las subcarpetas ---
        archivos_dbf = []
        for root, dirs, files in os.walk(tmp_dir):
            for f in files:
                if f.lower().endswith(".dbf"):
                    archivos_dbf.append(os.path.join(root, f))

        # --- Validar existencia y lectura de tablas ---
        for key, nombre in TABLAS_REQUERIDAS.items():
            archivo_objetivo = next(
                (ruta for ruta in archivos_dbf if os.path.basename(ruta).lower().startswith(key)
                  and not os.path.basename(ruta).lower() == 'formdet1.dbf'),
                None
            )

            if not archivo_objetivo:
                faltantes.append(nombre)
                continue

            try:
                table = dbf.Table(filename=archivo_objetivo, codepage='utf8')
                table.open()
                registros = []
                for record in table:
                    registro_limpio = {}
                    for field in table.field_names:
                        try:
                            value = record[field]
                            if isinstance(value, str):
                                value = ' '.join(value.strip().split())
                            elif isinstance(value, bytes):
                                try:
                                    value = value.decode('utf-8')
                                except UnicodeDecodeError:
                                    value = value.decode('latin1', errors='replace')
                            registro_limpio[field] = value
                        except:
                            registro_limpio[field] = None
                    registros.append(registro_limpio)
                table.close()
                resultados[nombre] = registros
            except Exception as e:
                return Response({
                    'error': f'Error al leer {nombre}.dbf',
                    'detalle': str(e),
                    'sugerencia': 'Verifique que el archivo no esté dañado o con formato distinto a DBF estándar.'
                }, status=400)

    # --- Evaluar condiciones ---
    if faltantes:
        return Response({
            'status': 'error',
            'error': f"Faltan las siguientes tablas requeridas: {', '.join(faltantes)}"
        }, status=400)

    sin_registros = [k for k, v in resultados.items() if len(v) == 0]
    if sin_registros:
        return Response({
            'status': 'error',
            'error': f"Las tablas {', '.join(sin_registros)} no contienen registros."
        }, status=400)

    return Response({
        'status': 'ok',
        'mensaje': 'ZIP válido, tablas requeridas encontradas y con registros.',
        'tablas_validadas': list(resultados.keys())
    })


@api_view(['POST'])
def procesar_zip_grande(request):
   pass

@login_required
def listar_archivos_procesados(request):
    # Obtener parámetros de filtro
    search_query = request.GET.get('search', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    
    # Filtrar por usuario actual
    archivos = ArchivosProcesados.objects.filter(usuario=request.user)
    
    # Aplicar filtros
    if search_query:
        archivos = archivos.filter(
            Q(nombre_archivo__icontains=search_query) |
            Q(usuario__username__icontains=search_query)
        )
    
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            archivos = archivos.filter(created_at__date__gte=fecha_inicio_dt)
        except ValueError:
            pass
    
    if fecha_fin:
        try:
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            archivos = archivos.filter(created_at__date__lte=fecha_fin_dt)
        except ValueError:
            pass
    
    # Ordenar por fecha descendente
    archivos = archivos.order_by('-created_at')
    
    # Prefetch relacionadas para contar eficientemente
    archivos = archivos.prefetch_related(
        'formularios_detalle',
        'ime1_registros',
        'imed2_registros',
        'imed3_registros'
    )
    
    # Estadísticas
    total_formdet = FormDet.objects.filter(
        archivo_procesado__usuario=request.user
    ).count()
    
    hoy = timezone.now().date()
    hoy_count = ArchivosProcesados.objects.filter(
        usuario=request.user,
        created_at__date=hoy
    ).count()
    
    usuarios_count = User.objects.filter(
        archivosprocesados__isnull=False
    ).distinct().count()
    
    # Paginación
    paginator = Paginator(archivos, 10)  # 10 por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'archivos': page_obj,
        'total_formdet': total_formdet,
        'hoy_count': hoy_count,
        'usuarios_count': usuarios_count,
        'search_query': search_query,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    
    return render(request, 'process_volumen/archivos_procesados.html', context)

@csrf_exempt
def eliminar_archivo(request, archivo_id):
    archivo = get_object_or_404(ArchivosProcesados, id=archivo_id, usuario=request.user)
    
    if request.method == 'POST':
        nombre_archivo = archivo.nombre_archivo
        archivo.delete()
        messages.success(request, f'Archivo "{nombre_archivo}" eliminado correctamente.')
        return redirect('archivos_procesados')
    
    return redirect('archivos_procesados')

@login_required
def exportar_archivo(request, archivo_id):
    archivo = get_object_or_404(ArchivosProcesados, id=archivo_id, usuario=request.user)
    
    # Crear respuesta CSV/Excel según necesites
    # Esta es una implementación básica
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{archivo.nombre_archivo}_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Tabla', 'Registros'])
    writer.writerow(['FormDet', archivo.formularios_detalle.count()])
    writer.writerow(['IME1', archivo.ime1_registros.count()])
    writer.writerow(['IMED2', archivo.imed2_registros.count()])
    writer.writerow(['IMED3', archivo.imed3_registros.count()])
    
    return response


def detectar_version_formdet(table):
    """Detecta si el archivo FormDet es versión 2.4 o 2.5"""
    campos = table.field_names
    
    # Versión 2.5 tiene estos campos adicionales
    campos_v25 = ['ESSALUD', 'MEDLOTE', 'MEDREGSAN', 'MEDFECHVTO', 'TIPSUM2', 'FFINAN', 'PREADQ']
    
    # Verificar si alguno de los campos de v2.5 está presente
    for campo in campos_v25:
        if campo in campos:
            return '2.5'
    
    # Por defecto asumimos 2.4
    return '2.4'


def debug_formdet_dbf(dbf_path):
    """Muestra información de debug del archivo DBF"""
    try:
        table = DBF(dbf_path, encoding='latin-1', char_decode_errors='ignore')
        
        print(f"   DEBUG: Archivo {os.path.basename(dbf_path)}")
        print(f"   Número de registros: {len(table)}")
        print(f"   Campos encontrados: {table.field_names}")
        
        # CORRECCIÓN: Obtener primer registro iterando
        primer_registro = None
        for i, record in enumerate(table):
            if i == 0:
                primer_registro = record
                break
        
        if primer_registro:
            # Mostrar solo primeros 5 campos
            primeros_campos = {}
            for j, (key, value) in enumerate(primer_registro.items()):
                if j < 5:
                    primeros_campos[key] = value
            print(f"   Primer registro (primeros 5 campos): {primeros_campos}")
        
        # Contar registros no vacíos
        campos_clave = ['CODIGO_PRE', 'SALDO', 'TOTAL', 'INGRE']
        for campo in campos_clave:
            if campo in table.field_names:
                # Reiniciar iteración
                table = DBF(dbf_path, encoding='latin-1', char_decode_errors='ignore')
                no_vacios = sum(1 for r in table if r.get(campo) not in (None, '', 0))
                print(f"   {campo}: {no_vacios} no vacíos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en debug: {e}")
        return False
    

def procesar_ime1_chunked(dbf_path, archivo_procesado):
    """Procesa IME1 en chunks"""
    # Por ahora retorna 0 hasta que implementes
    print(f"⚠️ IME1 procesamiento no implementado aún: {dbf_path}")
    return 0

def procesar_imed2_chunked(dbf_path, archivo_procesado):
    """Procesa IMED2 en chunks"""
    # Por ahora retorna 0 hasta que implementes
    print(f"⚠️ IMED2 procesamiento no implementado aún: {dbf_path}")
    return 0

def procesar_imed3_chunked(dbf_path, archivo_procesado):
    """Procesa IMED3 en chunks"""
    # Por ahora retorna 0 hasta que implementes
    print(f"⚠️ IMED3 procesamiento no implementado aún: {dbf_path}")
    return 0

def detectar_version_formdet_dbf(dbf_path):
    """Detecta la versión de un archivo formDet.dbf específico"""
    try:
        table = DBF(dbf_path, encoding='latin-1', char_decode_errors='ignore')
        campos = table.field_names
        
        # Verificar campos de versión 2.5
        campos_v25 = ['ESSALUD', 'MEDLOTE', 'MEDREGSAN', 'MEDFECHVTO', 'TIPSUM2', 'FFINAN', 'PREADQ']
        
        for campo in campos_v25:
            if campo in campos:
                return '2.5'
        
        return '2.4'
    except Exception as e:
        print(f"⚠️ Error detectando versión: {e}")
        return 'Desconocida'