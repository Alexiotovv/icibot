from django.db import models


class ProcesamientoHistorico(models.Model):
    tiempo = models.CharField(max_length=50)  # Ej: "00:01:23.456"
    total_registros = models.IntegerField()
    guardados = models.IntegerField()
    columnas = models.TextField()  # Guardamos como string separado por comas
    tablas_guardadas = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Procesamiento {self.creado_en} - {self.total_registros} registros"

class ExternalAPI(models.Model):
    nombre = models.CharField(max_length=100)
    url = models.URLField()
    token = models.CharField(max_length=255)

    def __str__(self):
        return self.nombre

