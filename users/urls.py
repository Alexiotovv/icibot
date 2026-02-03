from django.urls import path
from users.views import *
from django.contrib.auth import views as auth_views
from users.views import dashboard, generate_token, user_token_list


urlpatterns = [
    # path("index/", index , name="appmetricas"),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', dashboard, name='dashboard'),
    #Rutas para Tokens
    path('api/generate-token/', generate_token, name='generate_token'),
    path('tokens/users', user_token_list, name='token_list'),
]



