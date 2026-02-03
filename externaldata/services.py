# app/services.py
from .models import FormDet
from django.db import transaction

def guardar_formdet_desde_df(df):
    """
    Guarda el contenido de un DataFrame en la tabla FormDet de manera transaccional.
    Si ocurre un error, se hace rollback y no se guarda nada.
    """
    df = df.fillna("")

    registros = []
    for _, row in df.iterrows():
        registros.append(FormDet(
            CODIGO_EJE=row.get("CODIGO_EJE"),
            CODIGO_PRE=row.get("CODIGO_PRE"),
            TIPSUM=row.get("TIPSUM"),
            ANNOMES=row.get("ANNOMES"),
            CODIGO_MED=row.get("CODIGO_MED"),
            SALDO=row.get("SALDO"),
            PRECIO=row.get("PRECIO"),
            INGRE=row.get("INGRE"),
            REINGRE=row.get("REINGRE"),
            VENTA=row.get("VENTA"),
            SIS=row.get("SIS"),
            INTERSAN=row.get("INTERSAN"),
            FAC_PERD=row.get("FAC_PERD"),
            DEFNAC=row.get("DEFNAC"),
            EXO=row.get("EXO"),
            SOAT=row.get("SOAT"),
            CREDHOSP=row.get("CREDHOSP"),
            OTR_CONV=row.get("OTR_CONV"),
            DEVOL=row.get("DEVOL"),
            VENCIDO=row.get("VENCIDO"),
            MERMA=row.get("MERMA"),
            DISTRI=row.get("DISTRI"),
            TRANSF=row.get("TRANSF"),
            VENTAINST=row.get("VENTAINST"),
            DEV_VEN=row.get("DEV_VEN"),
            DEV_MERMA=row.get("DEV_MERMA"),
            OTRAS_SAL=row.get("OTRAS_SAL"),
            STOCK_FIN=row.get("STOCK_FIN"),
            STOCK_FIN1=row.get("STOCK_FIN1"),
            REQ=row.get("REQ"),
            TOTAL=row.get("TOTAL"),
            FEC_EXP=row.get("FEC_EXP"),
            DO_SALDO=row.get("DO_SALDO"),
            DO_INGRE=row.get("DO_INGRE"),
            DO_CON=row.get("DO_CON"),
            DO_OTR=row.get("DO_OTR"),
            DO_TOT=row.get("DO_TOT"),
            DO_STK=row.get("DO_STK"),
            DO_FECEXP=row.get("DO_FECEXP"),
            FECHA=row.get("FECHA"),
            USUARIO=row.get("USUARIO"),
            INDIPROC=row.get("INDIPROC"),
            SIT=row.get("SIT"),
            INDISIGA=row.get("INDISIGA"),
            DSTKCERO=row.get("DSTKCERO"),
            MPTOREPO=row.get("MPTOREPO"),
            ING_REGULA=row.get("ING_REGULA"),
            SAL_REGULA=row.get("SAL_REGULA"),
            SAL_CONINS=row.get("SAL_CONINS"),
            STOCKFIN=row.get("STOCKFIN"),
            STOCKFIN1=row.get("STOCKFIN1"),
        ))

    try:
        with transaction.atomic():  # 👈 Todo lo que esté aquí es atómico
            FormDet.objects.bulk_create(registros, batch_size=500)
        return len(registros)
    except Exception as e:
        # Aquí puedes loguear el error o lanzarlo
        raise e