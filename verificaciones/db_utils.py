# verificaciones/db_utils.py
import MySQLdb 
from MySQLdb.cursors import DictCursor  # <-- IMPORTANTE: Agregar esto
from django.conf import settings
from django.core.cache import cache

def get_mysql_connection():
    """Establece conexión a la base de datos MySQL externa"""
    try:
        print(f"[DEBUG DB] Intentando conectar a MySQL...")
        print(f"[DEBUG DB] Host: {settings.EXTERNAL_DB_HOST}")
        print(f"[DEBUG DB] DB: {settings.EXTERNAL_DB_NAME}")
        print(f"[DEBUG DB] User: {settings.EXTERNAL_DB_USER}")
        print(f"[DEBUG DB] Port: {settings.EXTERNAL_DB_PORT}")
        
        conn = MySQLdb.connect(
            host=settings.EXTERNAL_DB_HOST,
            user=settings.EXTERNAL_DB_USER,
            password=settings.EXTERNAL_DB_PASSWORD,
            database=settings.EXTERNAL_DB_NAME,
            port=settings.EXTERNAL_DB_PORT,
            charset='utf8mb4'
        )
        print(f"[DEBUG DB] ✅ Conexión exitosa a MySQL")
        return conn
    except MySQLdb.Error as e:
        print(f"[DEBUG DB] ❌ Error específico MySQL: {e}")
        return None
    except Exception as e:
        print(f"[DEBUG DB] ❌ Error general conectando a MySQL: {str(e)}")
        return None

def get_nombre_establecimiento(cod_ipress):
    """Obtiene el nombre del establecimiento desde MySQL"""
    print(f"[DEBUG DB] get_nombre_establecimiento llamado para: {cod_ipress}")
    
    # Verificar si está en cache primero
    cache_key = f'establecimiento_{cod_ipress}'
    nombre = cache.get(cache_key)
    
    if nombre is not None:
        print(f"[DEBUG DB] ✅ Encontrado en cache: {cod_ipress} → {nombre}")
        return nombre
    else:
        print(f"[DEBUG DB] ⚠️ No en cache, consultando BD para: {cod_ipress}")
    
    conn = None
    cursor = None
    try:
        conn = get_mysql_connection()
        if conn is None:
            print(f"[DEBUG DB] ❌ No hay conexión, devolviendo código: {cod_ipress}")
            return cod_ipress
        
        # MySQLdb usa DictCursor en lugar de dictionary=True
        cursor = conn.cursor(DictCursor)  # <-- CAMBIO AQUÍ
        query = "SELECT nombre_ipress FROM almacenes WHERE cod_ipress = %s"
        print(f"[DEBUG DB] Ejecutando query: {query} con parámetro: {cod_ipress}")
        cursor.execute(query, (cod_ipress,))
        resultado = cursor.fetchone()
        
        if resultado:
            nombre = resultado['nombre_ipress']
            print(f"[DEBUG DB] ✅ Resultado encontrado: {cod_ipress} → {nombre}")
        else:
            nombre = cod_ipress
            print(f"[DEBUG DB] ⚠️ No se encontró registro para: {cod_ipress}")
        
        # Guardar en cache por 1 hora
        cache.set(cache_key, nombre, 3600)
        print(f"[DEBUG DB] Guardado en cache: {cache_key} → {nombre}")
        
        return nombre
    except Exception as e:
        print(f"[DEBUG DB] ❌ Error obteniendo nombre establecimiento {cod_ipress}: {str(e)}")
        return cod_ipress
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print(f"[DEBUG DB] Conexión cerrada")

def get_nombres_establecimientos_batch(codigos_ipress):
    """Obtiene múltiples nombres de establecimientos en batch"""
    print(f"[DEBUG DB] get_nombres_establecimientos_batch llamado")
    print(f"[DEBUG DB] Número de códigos: {len(codigos_ipress)}")
    print(f"[DEBUG DB] Primeros 5 códigos: {codigos_ipress[:5]}")
    
    if not codigos_ipress:
        print(f"[DEBUG DB] Lista vacía, retornando dict vacío")
        return {}
    
    # Separar códigos ya en cache y los que no
    nombres = {}
    codigos_faltantes = []
    
    for codigo in codigos_ipress:
        cache_key = f'establecimiento_{codigo}'
        nombre = cache.get(cache_key)
        if nombre is not None:
            nombres[codigo] = nombre
        else:
            codigos_faltantes.append(codigo)
    
    print(f"[DEBUG DB] En cache: {len(nombres)}")
    print(f"[DEBUG DB] Faltantes en BD: {len(codigos_faltantes)}")
    print(f"[DEBUG DB] Códigos faltantes: {codigos_faltantes[:10]}")
    
    if not codigos_faltantes:
        print(f"[DEBUG DB] ✅ Todos en cache, retornando {len(nombres)} nombres")
        return nombres
    
    # Consultar los faltantes a la BD
    conn = None
    cursor = None
    try:
        conn = get_mysql_connection()
        if conn is None:
            print(f"[DEBUG DB] ❌ No hay conexión, devolviendo códigos como nombres")
            return {cod: cod for cod in codigos_ipress}
        
        # MySQLdb usa DictCursor en lugar de dictionary=True
        cursor = conn.cursor(DictCursor)  # <-- CAMBIO AQUÍ
        
        # Crear placeholders para la consulta IN
        placeholders = ', '.join(['%s'] * len(codigos_faltantes))
        query = f"SELECT cod_ipress, nombre_ipress FROM almacenes WHERE cod_ipress IN ({placeholders})"
        
        print(f"[DEBUG DB] Ejecutando query batch:")
        print(f"[DEBUG DB] Query: {query}")
        print(f"[DEBUG DB] Parámetros: {codigos_faltantes}")
        
        cursor.execute(query, codigos_faltantes)
        resultados = cursor.fetchall()
        
        print(f"[DEBUG DB] Resultados obtenidos: {len(resultados)} registros")
        
        # Mostrar primeros resultados para debug
        for i, row in enumerate(resultados[:5]):
            print(f"[DEBUG DB] Resultado {i+1}: {row['cod_ipress']} → {row['nombre_ipress']}")
        
        # Procesar resultados
        resultados_dict = {row['cod_ipress']: row['nombre_ipress'] for row in resultados}
        
        for codigo in codigos_faltantes:
            nombre = resultados_dict.get(codigo, codigo)
            nombres[codigo] = nombre
            
            # Guardar en cache
            cache_key = f'establecimiento_{codigo}'
            cache.set(cache_key, nombre, 3600)
        
        print(f"[DEBUG DB] ✅ Batch completado, total nombres: {len(nombres)}")
        print(f"[DEBUG DB] Ejemplos: {list(nombres.items())[:3]}")
        
        return nombres
    except Exception as e:
        print(f"[DEBUG DB] ❌ Error obteniendo nombres batch: {str(e)}")
        import traceback
        traceback.print_exc()
        
        for codigo in codigos_faltantes:
            nombres[codigo] = codigo
        return nombres
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print(f"[DEBUG DB] Conexión batch cerrada")