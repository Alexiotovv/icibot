from django.urls import path
from tokens.views import *

urlpatterns = [
    path('enlaces/', lista_enlaces, name='lista_enlaces'),
    path('nuevo/', crear_enlace, name='crear_enlace'),
    path('editar/<int:id>/', editar_enlace, name='editar_enlace'),
]
