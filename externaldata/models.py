from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

class ArchivosProcesados(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nombre_archivo = models.CharField(_("nombre_archivo"), max_length=100)
    archivo_principal = models.CharField(_("archivo_principal"), max_length=100, blank=True, null=True)  # ESTE CAMPO SÍ EXISTE
    version_formdet = models.CharField(_("versión FormDet"), max_length=10, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Archivo Procesado")
        verbose_name_plural = _("Archivos Procesados")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.nombre_archivo} - {self.usuario.username}"


class FormDet(models.Model):
    archivo_procesado = models.ForeignKey(ArchivosProcesados, on_delete=models.CASCADE, related_name="formularios_detalle", null=True, blank=True)
    
    # Campos principales
    CODIGO_EJE = models.CharField(max_length=3, db_index=True)
    CODIGO_PRE = models.CharField(max_length=11, db_index=True)
    TIPSUM = models.CharField(max_length=1)
    ANNOMES = models.CharField(max_length=6, db_index=True)
    CODIGO_MED = models.CharField(max_length=7, db_index=True)
    
    # Campos numéricos optimizados
    # max_digits = dígitos totales, decimal_places = decimales
    SALDO = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    PRECIO = models.DecimalField(max_digits=11, decimal_places=2, default=0.00)
    INGRE = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    REINGRE = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    VENTA = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    SIS = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    INTERSAN = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    FAC_PERD = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    DEFNAC = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    EXO = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    SOAT = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    CREDHOSP = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    OTR_CONV = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    DEVOL = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    VENCIDO = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    MERMA = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    DISTRI = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    TRANSF = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    VENTAINST = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    DEV_VEN = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    DEV_MERMA = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    OTRAS_SAL = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    STOCK_FIN = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    STOCK_FIN1 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    REQ = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    TOTAL = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    
    # Campos de fecha
    FEC_EXP = models.DateField(null=True, blank=True)
    DO_FECEXP = models.DateField(null=True, blank=True)
    FECHA = models.DateField(null=True, blank=True)
    
    # Campos DO
    DO_SALDO = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    DO_INGRE = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    DO_CON = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    DO_OTR = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    DO_TOT = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    DO_STK = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Campos de usuario y estado
    USUARIO = models.CharField(max_length=15, default='SISTEMA')
    INDIPROC = models.CharField(max_length=1, default='N')
    SIT = models.CharField(max_length=1, default='A')
    INDISIGA = models.CharField(max_length=1, default='N')
    
    # Más campos numéricos
    DSTKCERO = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    MPTOREPO = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    ING_REGULA = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    SAL_REGULA = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    SAL_CONINS = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    STOCKFIN = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    STOCKFIN1 = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    
    ESSALUD = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, null=True, blank=True)
    MEDLOTE = models.CharField(max_length=20, null=True, blank=True)
    MEDREGSAN = models.CharField(max_length=20, null=True, blank=True)
    MEDFECHVTO = models.DateField(null=True, blank=True)
    TIPSUM2 = models.CharField(max_length=2, null=True, blank=True)
    FFINAN = models.CharField(max_length=3, null=True, blank=True)
    PREADQ = models.DecimalField(max_digits=14, decimal_places=6, default=0.00, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'formDet'
        verbose_name = _("Formulario Detalle")
        verbose_name_plural = _("Formularios Detalle")
        ordering = ['ANNOMES', 'CODIGO_PRE']
        indexes = [
            models.Index(fields=['ANNOMES', 'CODIGO_PRE']),
            models.Index(fields=['CODIGO_EJE', 'ANNOMES']),
            models.Index(fields=['CODIGO_MED']),
        ]
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=['archivo_procesado', 'CODIGO_PRE', 'ANNOMES'],
        #         name='unique_formdet_per_file'
        #     )
        # ]
    
    def __str__(self):
        return f"{self.CODIGO_PRE} - {self.ANNOMES}"


class Ime1(models.Model):
    archivo_procesado = models.ForeignKey(
        ArchivosProcesados, 
        on_delete=models.CASCADE, 
        related_name="ime1_registros",null=True, blank=True
    )
    
    ANNOMES = models.CharField(max_length=6, db_index=True)
    CODIGO_EJE = models.CharField(max_length=3, db_index=True)
    CODIGO_PRE = models.CharField(max_length=11, db_index=True)
    
    # Todos los campos numéricos con valores por defecto 0
    # Usé max_digits=22 para cubrir números grandes
    IMPVTAS = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPCREDH = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPSOAT = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPOTRC = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPSIS = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPINTS = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPDN = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPEXO = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    
    # Campos D
    DVTAS80 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DVTAS20 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DCREH80 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DCREH20 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DSOAT80 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DSOAT20 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DOTRC80 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DOTRC20 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    TOTRDR = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DSIS80 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DSIS20 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DINTSAN80 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DINTSAN20 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DDN80 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    DDN20 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    
    # Campos CT
    CTCREDH = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    CTSOAT = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    CTOCONV = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    CTSIS = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    CTISAN = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    CTDN = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    
    # Otros campos
    SALMEDA = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    FORT110 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    EXO1 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    ABMEDIN = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    SMEDSIG = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    SADMA = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    FORT010 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    EXO0 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    GASTADM = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    SADMSIG = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    
    # Campos BV
    BVTASER1 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    BVTADEL1 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    BVTAAL1 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    BVTAAN1 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    BVTASER2 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    BVTADEL2 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    BVTAAL2 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    BVTAAN2 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    BVTASER3 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    BVTADEL3 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    BVTAAL3 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    BVTAAN3 = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    
    # Campos FACT
    FACTSER = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    FACTDEL = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    FACTAL = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    FACTAN = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    
    # Campos IMPBV
    IMPBVVTA = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPBVSIS = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPBVEXO = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPBVSOAT = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPBVOCONV = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPBVINTSA = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    IMPBVDN = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    
    # Fechas
    FECHREG = models.DateField(null=True, blank=True)
    FECHULTM = models.DateField(null=True, blank=True)
    
    USUARIO = models.CharField(max_length=15, default='SISTEMA')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'Ime1'
        verbose_name = _("IME1")
        verbose_name_plural = _("Registros IME1")
        ordering = ['ANNOMES', 'CODIGO_PRE']
        indexes = [
            models.Index(fields=['ANNOMES', 'CODIGO_PRE']),
            models.Index(fields=['CODIGO_EJE', 'ANNOMES']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['archivo_procesado', 'CODIGO_PRE', 'ANNOMES'],
                name='unique_ime1_per_file'
            )
        ]
    
    def __str__(self):
        return f"IME1 {self.CODIGO_PRE} - {self.ANNOMES}"


class Imed2(models.Model):
    archivo_procesado = models.ForeignKey(
        ArchivosProcesados, 
        on_delete=models.CASCADE, 
        related_name="imed2_registros",null=True, blank=True
    )
    
    ANNOMES = models.CharField(max_length=6, db_index=True)
    CODIGO_EJE = models.CharField(max_length=3, db_index=True)
    CODIGO_PRE = models.CharField(max_length=11, db_index=True)
    FECHDEPO = models.DateField(null=True, blank=True)
    NRODEPO = models.CharField(max_length=20)
    IMPDEPO = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'Imed2'
        verbose_name = _("IMED2")
        verbose_name_plural = _("Registros IMED2")
        ordering = ['FECHDEPO', 'NRODEPO']
        indexes = [
            models.Index(fields=['ANNOMES', 'CODIGO_PRE']),
            models.Index(fields=['FECHDEPO']),
        ]
    
    def __str__(self):
        return f"IMED2 {self.NRODEPO} - {self.FECHDEPO}"


class Imed3(models.Model):
    archivo_procesado = models.ForeignKey(
        ArchivosProcesados, 
        on_delete=models.CASCADE, 
        related_name="imed3_registros",null=True, blank=True
    )
    
    ANNOMES = models.CharField(max_length=6, db_index=True)
    CODIGO_EJE = models.CharField(max_length=3, db_index=True)
    CODIGO_PRE = models.CharField(max_length=11, db_index=True)
    FECHGUIA = models.DateField(null=True, blank=True)
    NROGUIA = models.CharField(max_length=20)
    IMPGUIA = models.DecimalField(max_digits=22, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'Imed3'
        verbose_name = _("IMED3")
        verbose_name_plural = _("Registros IMED3")
        ordering = ['FECHGUIA', 'NROGUIA']
        indexes = [
            models.Index(fields=['ANNOMES', 'CODIGO_PRE']),
            models.Index(fields=['FECHGUIA']),
        ]
    
    def __str__(self):
        return f"IMED3 {self.NROGUIA} - {self.FECHGUIA}"