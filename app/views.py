from django.contrib.auth import logout, authenticate, login
from django.shortcuts import render, redirect

from .forms import LoginForm, RegistroForm
from .models import Character
from .services import sync_simpsons_characters


# Create your views here.
def inicio(request):
    return render(request, 'inicio.html')


def characters(request):
    if not Character.objects.using('mongodb').exists():
        sync_simpsons_characters()

    characters = Character.objects.using('mongodb').all()
    return render(request, 'characters.html', {'characters': characters})


def registrar_usuario(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.set_password(form.cleaned_data['password'])
            usuario.save()
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'registro.html', {'form': form})


def login_usuario(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            usuario = authenticate(request, email=email, password=password)
            if usuario is not None:
                login(request, usuario)
                return redirect('inicio')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def logout_usuario(request):
    logout(request)
    return redirect('login')
