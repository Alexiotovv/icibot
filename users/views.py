from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .serializers import UserSerializer, TokenSerializer
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication, SessionAuthentication

def user_token_list(request):    
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'tokens/user_list.html', {'users': users})

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])  # Soporta tanto web como API
@permission_classes([IsAuthenticated])
def generate_token(request):
    """
    Genera o recupera un token para el usuario autenticado
    Requiere autenticación previa (sesión web o token)
    """
    try:
        # Eliminar token existente si lo hay (para evitar múltiples tokens)
        Token.objects.filter(user=request.user).delete()
        
        # Crear nuevo token
        token, created = Token.objects.get_or_create(user=request.user)
        
        return Response({
            'status': 'success',
            'token': token.key,
            'user': {
                'username': request.user.username,
                'email': request.user.email
            },
            'message': 'Guarde este token en un lugar seguro'
        })
    
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=500)