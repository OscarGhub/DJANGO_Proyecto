from django.contrib.auth import logout, authenticate, login
from django.db.models import Avg
from django.shortcuts import render, redirect

from .forms import LoginForm, RegistroForm
from .models import Character, Review
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


def ranking(request):
    if not Character.objects.using('mongodb').exists():
        sync_simpsons_characters()

    characters = Character.objects.using('mongodb').all()
    return render(request, 'ranking.html', {'characters': characters})


def ver_rankings(request):
    return render(request, 'ver_rankigs.html')


def mejores_votados(request):
    characters = Character.objects.using('mongodb').all()

    ranking_final = []

    for c in characters:
        votos = Review.objects.using('mongodb').filter(comment__icontains=c.name)
        promedio = votos.aggregate(Avg('rating'))['rating__avg'] or 0

        ranking_final.append({
            'character': c,
            'puntuacion': round(promedio, 1),
            'estrellas': range(int(promedio))
        })

    ranking_final = sorted(ranking_final, key=lambda x: x['puntuacion'], reverse=True)
    return render(request, 'ver_rankigs.html', {'ranking': ranking_final})
