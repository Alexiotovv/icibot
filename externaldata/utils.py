# app/utils.py
import os, tempfile, zipfile
import pandas as pd
import dbf

def extraer_formdet_desde_zip(zip_file, password=None):
    df_formdet_total = pd.DataFrame()

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Extraer el principal.zip (SIN contraseña)
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)

        # Iterar sobre los ZIPs internos
        for subzip in os.listdir(tmp_dir):
            if subzip.lower().endswith(".zip"):
                ruta_subzip = os.path.join(tmp_dir, subzip)

                with tempfile.TemporaryDirectory() as sub_dir:
                    with zipfile.ZipFile(ruta_subzip, 'r') as zf_sub:
                        zf_sub.extractall(sub_dir, pwd=password)

                    # Buscar formDet.dbf dentro del subzip
                    archivo_formdet = next(
                        (f for f in os.listdir(sub_dir) if f.lower().startswith("formdet") and f.lower().endswith(".dbf")),
                        None
                    )

                    if archivo_formdet:
                        ruta_dbf = os.path.join(sub_dir, archivo_formdet)
                        table = dbf.Table(ruta_dbf, codepage='utf8')
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
                        df_sub = pd.DataFrame(registros)
                        df_formdet_total = pd.concat([df_formdet_total, df_sub], ignore_index=True)

    return df_formdet_total
