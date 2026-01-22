from django.contrib.auth import logout, authenticate, login
from django.db.models import Avg
from django.shortcuts import render, redirect

from .forms import LoginForm, RegistroForm
from .models import Character, Review, Category, Usuario
from .services import sync_simpsons_characters
from .models import Character, Category


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

    category_code = request.GET.get('category')

    if category_code:
        category = Category.objects.using('mongodb').filter(code=category_code).first()

        if category:
            characters = Character.objects.using('mongodb').filter(code__in=category.characters)
        else:
            characters = []
    else:
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


def gestion(request):
    return render(request, 'gestion.html')


def categorias(request):
    lista_categorias = Category.objects.using('mongodb').all().order_by('code')
    return render(request, 'categorias.html', {'categorias': lista_categorias})


def mas_personajes(request):
    if request.method == 'POST':
        Character.objects.using('mongodb').create(
            code=int(request.POST.get('code')),
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            image=request.POST.get('image')
        )
        return redirect('gestion')

    ultimo_personaje = Character.objects.using('mongodb').order_by('-code').first()

    if ultimo_personaje and ultimo_personaje.code >= 150:
        siguiente_codigo = ultimo_personaje.code + 1
    else:
        siguiente_codigo = 150

    return render(request, 'mas_personajes.html', {'siguiente_codigo': siguiente_codigo})


def mas_categorias(request):
    if request.method == 'POST':
        ids_seleccionados = [int(x) for x in request.POST.getlist('personajes_ids')]

        Category.objects.using('mongodb').create(
            code=int(request.POST.get('code')),
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            image=request.POST.get('image'),
            characters=ids_seleccionados
        )
        return redirect('gestion')

    ultima_cat = Category.objects.using('mongodb').order_by('-code').first()
    siguiente_codigo = ultima_cat.code + 1 if ultima_cat else 20

    todos_personajes = Character.objects.using('mongodb').all().order_by('name')

    return render(request, 'mas_categorias.html', {
        'siguiente_codigo': siguiente_codigo,
        'personajes': todos_personajes})

def user_panel(request):
    usuarios = Usuario.objects.all()

    return render(request,'user_panel.html', {'usuarios': usuarios})