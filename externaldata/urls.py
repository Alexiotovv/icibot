from django.urls import path
from externaldata.views import *

urlpatterns = [
    path('historico/index', historico_index , name='historico_index'),
]