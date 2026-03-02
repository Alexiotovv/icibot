# correccion_dbf/utils.py - VERSIÓN COMPLETA Y CORREGIDA
import os
import zipfile
import tempfile
import shutil
from datetime import datetime
from dbfread import DBF
import struct
from django.conf import settings
from django.core.files.storage import default_storage
import traceback

class ProcesadorDBF:
    def __init__(self):
        self.archivos_procesados = []
        self.errores = []
        
    def descomprimir_zip_con_contraseña(self, archivo_zip, contraseña=None, destino=None):
        """Descomprime un archivo ZIP protegido con contraseña"""
        try:
            if destino is None:
                destino = tempfile.mkdtemp()
            
            with zipfile.ZipFile(archivo_zip, 'r') as zip_ref:
                # Verificar si requiere contraseña
                archivos = zip_ref.namelist()
                primer_archivo = archivos[0] if archivos else None
                
                if primer_archivo:
                    try:
                        zip_ref.read(primer_archivo)
                        necesita_contraseña = False
                    except RuntimeError as e:
                        if 'encrypted' in str(e).lower():
                            necesita_contraseña = True
                        else:
                            raise e
                    except:
                        necesita_contraseña = False
                    
                    if necesita_contraseña and contraseña:
                        zip_ref.setpassword(contraseña.encode('utf-8'))
                    elif necesita_contraseña and not contraseña:
                        raise ValueError("El archivo ZIP requiere contraseña pero no se proporcionó")
                
                zip_ref.extractall(destino)
            
            # Buscar archivos .dbf en el directorio
            archivos_dbf = []
            for root, dirs, files in os.walk(destino):
                for file in files:
                    if file.lower().endswith('.dbf'):
                        archivos_dbf.append(os.path.join(root, file))
            
            return destino, archivos_dbf
            
        except Exception as e:
            raise Exception(f"Error al descomprimir ZIP: {str(e)}")
    
    def leer_dbf(self, ruta_dbf):
        """Lee un archivo DBF usando dbfread"""
        try:
            dbf = DBF(ruta_dbf, encoding='latin-1')
            registros = list(dbf)
            campos = dbf.field_names
            
            return {
                'ruta': ruta_dbf,
                'nombre': os.path.basename(ruta_dbf),
                'campos': campos,
                'registros': registros,
                'total_registros': len(registros)
            }
        except Exception as e:
            raise Exception(f"Error al leer DBF {ruta_dbf}: {str(e)}")
    
    def encontrar_archivo_formdet(self, archivos_dbf):
        """Encuentra el archivo FORMDET.DBF entre los archivos extraídos"""
        print(f"[DEBUG] Buscando FORMDET.DBF entre {len(archivos_dbf)} archivos")
        
        # Lista TODOS los archivos primero para debug
        for i, archivo in enumerate(archivos_dbf, 1):
            nombre = os.path.basename(archivo)
            print(f"[DEBUG] Archivo {i}: {nombre}")
        
        # ORDEN DE PRIORIDAD para búsqueda
        nombres_prioritarios = [
            'formDet.dbf',
            'FORMDET.DBF',
            'FormDet.dbf',
            'formdet.dbf',
            'formDet1.dbf',
            'FORMDET1.DBF',
        ]
        
        # Buscar por nombre exacto primero
        for nombre_buscado in nombres_prioritarios:
            for archivo in archivos_dbf:
                if os.path.basename(archivo) == nombre_buscado:
                    print(f"[DEBUG] ¡Encontrado por nombre exacto '{nombre_buscado}': {archivo}")
                    return archivo
        
        # Buscar por patrón
        for archivo in archivos_dbf:
            nombre = os.path.basename(archivo).upper()
            if 'FORM' in nombre and 'DET' in nombre:
                print(f"[DEBUG] ¡Encontrado por patrón FORM-DET!: {archivo}")
                return archivo
        
        # Buscar por campos
        for archivo in archivos_dbf:
            try:
                datos = self.leer_dbf(archivo)
                campos = datos['campos']
                
                # Buscar campos clave
                campos_clave = ['CODIGO_PRE', 'CODIGO_MED', 'SALDO']
                campos_encontrados = []
                
                for campo_clave in campos_clave:
                    if campo_clave.upper() in [c.upper() for c in campos]:
                        campos_encontrados.append(campo_clave)
                
                if len(campos_encontrados) >= 2:
                    print(f"[DEBUG] ¡Encontrado por campos {campos_encontrados}!: {archivo}")
                    return archivo
                    
            except Exception as e:
                continue
        
        raise Exception(f"No se encontró archivo FORMDET.DBF. Archivos: {[os.path.basename(f) for f in archivos_dbf]}")
    
    def buscar_inconsistencias_en_dbf(self, datos_dbf, inconsistencias):
        """Busca las inconsistencias dentro del archivo DBF"""
        print(f"[DEBUG] Buscando {len(inconsistencias)} inconsistencias en DBF con {len(datos_dbf['registros'])} registros")
        
        registros_con_inconsistencia = []
        
        for registro in datos_dbf['registros']:
            registro_dict = dict(registro)
            
            # Normalizar valores
            codigo_pre = str(registro_dict.get('CODIGO_PRE', '')).strip()
            codigo_med = str(registro_dict.get('CODIGO_MED', '')).strip()
            
            # Buscar coincidencia en inconsistencias
            for inc in inconsistencias:
                # Verificar coincidencia básica
                if codigo_pre == inc.CODIGO_PRE and codigo_med == inc.CODIGO_MED:
                    # Verificar campos adicionales
                    match = True
                    
                    # MEDLOTE
                    medlote_dbf = str(registro_dict.get('MEDLOTE', '')).strip() if registro_dict.get('MEDLOTE') else ''
                    medlote_inc = str(inc.MEDLOTE).strip() if inc.MEDLOTE else ''
                    if medlote_inc and medlote_dbf != medlote_inc:
                        continue
                    
                    # FFINAN
                    ffinan_dbf = str(registro_dict.get('FFINAN', '')).strip() if registro_dict.get('FFINAN') else ''
                    ffinan_inc = str(inc.FFINAN).strip() if inc.FFINAN else ''
                    if ffinan_inc and ffinan_dbf != ffinan_inc:
                        continue
                    
                    # TIPSUM2
                    tipsum2_dbf = str(registro_dict.get('TIPSUM2', '')).strip() if registro_dict.get('TIPSUM2') else ''
                    tipsum2_inc = str(inc.TIPSUM2).strip() if inc.TIPSUM2 else ''
                    if tipsum2_inc and tipsum2_dbf != tipsum2_inc:
                        continue
                    
                    # Si pasó todas las verificaciones, es el registro a corregir
                    registros_con_inconsistencia.append({
                        'registro': registro_dict,
                        'indice': datos_dbf['registros'].index(registro),
                        'inconsistencia': inc,
                        'saldo_actual': float(registro_dict.get('SALDO', 0)),
                        'stock_fin_anterior': float(inc.STOCKFIN_anterior)
                    })
                    print(f"[DEBUG] Encontrada inconsistencia: {codigo_pre}/{codigo_med}")
                    break
        
        print(f"[DEBUG] Total encontrados para corregir: {len(registros_con_inconsistencia)}")
        return registros_con_inconsistencia
    
    def corregir_saldo_en_dbf(self, ruta_dbf, correcciones, crear_backup=True):
        """Corrige los valores de SALDO en el archivo DBF usando STOCKFIN_anterior y actualiza STOCK_FIN, STOCK_FIN1"""
        try:
            # Crear backup si se solicita
            if crear_backup:
                backup_path = ruta_dbf + '.backup'
                shutil.copy2(ruta_dbf, backup_path)
                print(f"[DEBUG] Backup creado en: {backup_path}")
            
            # Leer el archivo DBF en modo binario
            with open(ruta_dbf, 'r+b') as f:
                # Leer cabecera DBF
                header = f.read(32)
                
                # Obtener número de registros
                num_records = struct.unpack('<I', header[4:8])[0]
                
                # Obtener longitud del registro
                record_length = struct.unpack('<H', header[10:12])[0]
                
                # Obtener offset de inicio de datos
                header_length = struct.unpack('<H', header[8:10])[0]
                
                # Leer definición de campos
                f.seek(32)
                fields = []
                
                while True:
                    field_bytes = f.read(32)
                    if field_bytes[0] == 0x0D or len(field_bytes) < 32:
                        break
                    
                    field_name = field_bytes[:11].strip(b'\x00').decode('latin-1')
                    field_type = chr(field_bytes[11])
                    field_length = field_bytes[16]
                    field_decimal = field_bytes[17]
                    
                    fields.append({
                        'name': field_name,
                        'type': field_type,
                        'length': field_length,
                        'decimal': field_decimal,
                        'offset': sum(f['length'] for f in fields) if fields else 0
                    })
                
                # Crear mapa de campos
                field_map = {field['name']: field for field in fields}
                
                # Verificar que exista el campo SALDO
                if 'SALDO' not in field_map:
                    raise Exception("Campo SALDO no encontrado en el DBF")
                
                saldo_field = field_map['SALDO']
                saldo_offset = saldo_field['offset']
                print(f"[DEBUG] Campo SALDO: longitud={saldo_field['length']}, decimales={saldo_field['decimal']}")
                
                # Buscar otros campos necesarios
                ingre_field = field_map.get('INGRE')
                total_field = field_map.get('TOTAL')
                stock_fin_field = field_map.get('STOCK_FIN')
                stock_fin1_field = field_map.get('STOCK_FIN1')
                
                if ingre_field:
                    print(f"[DEBUG] Campo INGRE encontrado: offset={ingre_field['offset']}")
                else:
                    print(f"[ADVERTENCIA] Campo INGRE no encontrado en el DBF")
                
                if total_field:
                    print(f"[DEBUG] Campo TOTAL encontrado: offset={total_field['offset']}")
                else:
                    print(f"[ADVERTENCIA] Campo TOTAL no encontrado en el DBF")
                
                if stock_fin_field:
                    print(f"[DEBUG] Campo STOCK_FIN encontrado: offset={stock_fin_field['offset']}")
                else:
                    print(f"[ADVERTENCIA] Campo STOCK_FIN no encontrado en el DBF")
                
                if stock_fin1_field:
                    print(f"[DEBUG] Campo STOCK_FIN1 encontrado: offset={stock_fin1_field['offset']}")
                else:
                    print(f"[ADVERTENCIA] Campo STOCK_FIN1 no encontrado en el DBF")
                
                # Ir al inicio de los registros
                f.seek(header_length)
                
                # Procesar cada corrección
                correcciones_aplicadas = []
                
                for correccion in correcciones:
                    indice = correccion['indice']
                    nuevo_saldo = correccion['stock_fin_anterior']  # STOCKFIN_anterior
                    
                    # Calcular posición del registro
                    record_pos = header_length + (indice * record_length)
                    f.seek(record_pos)
                    
                    # Leer el registro completo
                    record_data = f.read(record_length)
                    
                    if record_data[0] == 0x2A:  # Registro eliminado
                        continue
                    
                    # Obtener el valor actual de INGRE si existe
                    valor_ingre = 0
                    if ingre_field:
                        ingre_offset = ingre_field['offset']
                        f.seek(record_pos + 1 + ingre_offset)
                        ingre_bytes = f.read(ingre_field['length'])
                        try:
                            ingre_str = ingre_bytes.decode('latin-1').strip()
                            if ingre_str:
                                valor_ingre = float(ingre_str)
                            else:
                                valor_ingre = 0
                        except (ValueError, AttributeError) as e:
                            print(f"[DEBUG] Error al leer INGRE: {str(e)}, bytes: {ingre_bytes}")
                            valor_ingre = 0
                    
                    # Obtener el valor actual de TOTAL si existe
                    valor_total = 0
                    if total_field:
                        total_offset = total_field['offset']
                        f.seek(record_pos + 1 + total_offset)
                        total_bytes = f.read(total_field['length'])
                        try:
                            total_str = total_bytes.decode('latin-1').strip()
                            if total_str:
                                valor_total = float(total_str)
                            else:
                                valor_total = 0
                        except (ValueError, AttributeError) as e:
                            print(f"[DEBUG] Error al leer TOTAL: {str(e)}, bytes: {total_bytes}")
                            valor_total = 0
                    
                    # Calcular nuevo valor para STOCK_FIN/STOCK_FIN1
                    # Fórmula: (SALDO + INGRE) - TOTAL
                    nuevo_stock_fin = (nuevo_saldo + valor_ingre) - valor_total
                    
                    # 1. Actualizar SALDO con STOCKFIN_anterior
                    # Convertir nuevo valor de SALDO a formato DBF
                    if saldo_field['type'] == 'N':  # Numérico
                        saldo_format_str = f"{{:>{saldo_field['length']}.{saldo_field['decimal']}f}}"
                        saldo_str = saldo_format_str.format(float(nuevo_saldo))
                        saldo_bytes = saldo_str.encode('latin-1')
                    else:
                        saldo_str = str(nuevo_saldo)
                        saldo_bytes = saldo_str.ljust(saldo_field['length']).encode('latin-1')
                    
                    # Escribir nuevo SALDO
                    f.seek(record_pos + 1 + saldo_offset)
                    f.write(saldo_bytes)
                    
                    # 2. Actualizar STOCK_FIN si existe
                    if stock_fin_field:
                        if stock_fin_field['type'] == 'N':
                            stock_fin_format_str = f"{{:>{stock_fin_field['length']}.{stock_fin_field['decimal']}f}}"
                            stock_fin_str = stock_fin_format_str.format(float(nuevo_stock_fin))
                        else:
                            stock_fin_str = str(nuevo_stock_fin)
                        stock_fin_bytes = stock_fin_str.encode('latin-1')
                        f.seek(record_pos + 1 + stock_fin_field['offset'])
                        f.write(stock_fin_bytes)
                    
                    # 3. Actualizar STOCK_FIN1 si existe
                    if stock_fin1_field:
                        if stock_fin1_field['type'] == 'N':
                            stock_fin1_format_str = f"{{:>{stock_fin1_field['length']}.{stock_fin1_field['decimal']}f}}"
                            stock_fin1_str = stock_fin1_format_str.format(float(nuevo_stock_fin))
                        else:
                            stock_fin1_str = str(nuevo_stock_fin)
                        stock_fin1_bytes = stock_fin1_str.encode('latin-1')
                        f.seek(record_pos + 1 + stock_fin1_field['offset'])
                        f.write(stock_fin1_bytes)
                    
                    correcciones_aplicadas.append({
                        'indice': indice,
                        'saldo_anterior': correccion['saldo_actual'],
                        'saldo_nuevo': nuevo_saldo,
                        'inconsistencia': correccion['inconsistencia'],
                        'ingre_valor': valor_ingre,
                        'total_valor': valor_total,
                        'stock_fin_nuevo': nuevo_stock_fin
                    })
                    
                    print(f"[DEBUG] Corregido registro {indice}:")
                    print(f"  SALDO: {correccion['saldo_actual']} -> {nuevo_saldo}")
                    print(f"  INGRE: {valor_ingre}")
                    print(f"  TOTAL: {valor_total}")
                    print(f"  Cálculo: ({nuevo_saldo} + {valor_ingre}) - {valor_total} = {nuevo_stock_fin}")
                    print(f"  STOCK_FIN/STOCK_FIN1: {nuevo_stock_fin}")
                
                print(f"[DEBUG] Total correcciones aplicadas: {len(correcciones_aplicadas)}")
                return {
                    'ruta_corregida': ruta_dbf,
                    'correcciones_aplicadas': correcciones_aplicadas,
                    'total_corregido': len(correcciones_aplicadas)
                }
                
        except Exception as e:
            raise Exception(f"Error al corregir DBF: {str(e)}\n{traceback.format_exc()}")
    
    # correccion_dbf/utils.py - función crear_nuevo_zip (ACTUALIZADA)
    def crear_nuevo_zip(self, directorio, nombre_zip, contraseña=None):
        """
        Crea un nuevo archivo ZIP con los DBF corregidos
        Opcionalmente protege el ZIP con contraseña
        """
        try:
            # Crear directorio para correcciones
            correcciones_dir = os.path.join(settings.MEDIA_ROOT, 'correcciones')
            os.makedirs(correcciones_dir, exist_ok=True)
            
            zip_path = os.path.join(correcciones_dir, nombre_zip)
            
            # Importar zipfile de pythonzip para soporte de contraseñas
            try:
                # Intentar con zipfile estándar primero (soporta contraseñas en Python 3.6+)
                import zipfile
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Si hay contraseña, configurarla
                    if contraseña:
                        zipf.setpassword(contraseña.encode('utf-8'))
                        print(f"[DEBUG] ZIP protegido con contraseña")
                    
                    # Agregar archivos
                    for root, dirs, files in os.walk(directorio):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, directorio)
                            zipf.write(file_path, arcname)
                            
            except Exception as e:
                print(f"[DEBUG] Error con zipfile estándar: {str(e)}")
                # Si falla, intentar con pyminizip (mejor soporte para contraseñas)
                try:
                    import pyminizip
                    
                    # Crear lista de archivos para comprimir
                    archivos_a_comprimir = []
                    rutas_completas = []
                    
                    for root, dirs, files in os.walk(directorio):
                        for file in files:
                            file_path = os.path.join(root, file)
                            archivos_a_comprimir.append(file_path)
                            rutas_completas.append(file_path)
                    
                    # Comprimir con pyminizip (soporta contraseñas)
                    if contraseña:
                        pyminizip.compress_multiple(
                            rutas_completas,
                            [],  # paths vacíos para mantener estructura
                            zip_path,
                            contraseña,
                            5  # Nivel de compresión (0-9)
                        )
                        print(f"[DEBUG] ZIP creado con pyminizip (con contraseña)")
                    else:
                        # Sin contraseña, usar zipfile estándar
                        import zipfile
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            for file_path in rutas_completas:
                                arcname = os.path.relpath(file_path, directorio)
                                zipf.write(file_path, arcname)
                                
                except ImportError:
                    print("[DEBUG] pyminizip no instalado, usando zipfile sin contraseña")
                    # Volver a intentar con zipfile sin contraseña
                    import zipfile
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(directorio):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, directorio)
                                zipf.write(file_path, arcname)
            
            print(f"[DEBUG] ZIP creado en: {zip_path}")
            print(f"[DEBUG] Tamaño: {os.path.getsize(zip_path)} bytes")
            
            if contraseña:
                print(f"[DEBUG] ZIP protegido con contraseña: {'*' * len(contraseña)}")
            
            return zip_path
                
        except Exception as e:
            raise Exception(f"Error al crear ZIP: {str(e)}")