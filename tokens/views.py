from django.shortcuts import render, redirect, get_object_or_404
from .models import EnlaceToken
from django.contrib.auth.decorators import login_required

@login_required
def lista_enlaces(request):
    enlaces = EnlaceToken.objects.all()
    return render(request, 'tokens/lista.html', {'enlaces': enlaces})

@login_required
def crear_enlace(request):
    if request.method == 'POST':
        nombre = request.POST['nombre']
        url = request.POST['url']
        token = request.POST['token']
        EnlaceToken.objects.create(nombre=nombre, url=url, token=token)
        return redirect('lista_enlaces')
    return render(request, 'tokens/formulario.html')

@login_required
def editar_enlace(request, id):
    enlace = get_object_or_404(EnlaceToken, pk=id)
    if request.method == 'POST':
        enlace.nombre = request.POST['nombre']
        enlace.url = request.POST['url']
        enlace.token = request.POST['token']
        enlace.save()
        return redirect('lista_enlaces')
    return render(request, 'tokens/formulario.html', {'enlace': enlace})