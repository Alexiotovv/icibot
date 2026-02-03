from django.db import models


class EnlaceToken(models.Model):
    nombre = models.CharField(max_length=100)
    url = models.URLField()
    token = models.CharField(max_length=255)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre