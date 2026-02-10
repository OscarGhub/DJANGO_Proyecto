from django.contrib.auth import logout, authenticate, login
from django.db.models import Avg
from django.http import HttpResponse
from django.utils import timezone

from .forms import LoginForm, RegistroForm
from .models import Ranking
from .models import Review, Usuario
from .services import sync_simpsons_characters

import csv
import io
import re
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Character, Category


# Create your views here.

def actualizar_desde_api(request):
    if request.user.is_authenticated and request.user.rol == 'admin':
        try:
            sync_simpsons_characters()
            messages.success(request, "¡Mosquis! Los datos se han sincronizado con la API correctamente.")
        except Exception as e:
            messages.error(request, f"Hubo un error al conectar con la API: {e}")

    return redirect('gestion')


def inicio(request):
    return render(request, 'inicio.html')


def characters(request):
    if not Character.objects.using('mongodb').exists():
        sync_simpsons_characters()

    todos_personajes = Character.objects.using('mongodb').all()

    votos_usuario = []
    if request.user.is_authenticated:
        votos_usuario = Review.objects.using('mongodb').filter(
            user=request.user.email
        ).values_list('comment', flat=True)

    for c in todos_personajes:
        marca_voto = f"Voto para: {c.name}"

        c.ya_votado = marca_voto in votos_usuario

        votos = Review.objects.using('mongodb').filter(comment=marca_voto)
        promedio = votos.aggregate(Avg('rating'))['rating__avg'] or 0

        c.media = round(promedio, 1)
        c.estrellas_completas = range(int(promedio))

    return render(request, 'characters.html', {'characters': todos_personajes})


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

    return render(request, 'ranking.html', {
        'characters': characters,
        'category_code': category_code
    })


def mejores_votados(request):
    characters = Character.objects.using('mongodb').all()

    ranking_final = []

    for c in characters:
        votos = Review.objects.using('mongodb').filter(comment=f"Voto para: {c.name}")
        promedio = votos.aggregate(Avg('rating'))['rating__avg'] or 0

        ranking_final.append({
            'character': c,
            'puntuacion': round(promedio, 1),
        })

    ranking_final = sorted(ranking_final, key=lambda x: x['puntuacion'], reverse=True)
    return render(request, 'ver_rankings.html', {'ranking': ranking_final})


def mejores_ranking(request):
    personajes = Character.objects.using('mongodb').all()
    todos_los_rankings = Ranking.objects.using('mongodb').all()

    ranking_final = []

    for p in personajes:
        posiciones = []

        for r in todos_los_rankings:
            if p.code in r.rankingList:
                posicion = r.rankingList.index(p.code) + 1
                posiciones.append(posicion)

        if posiciones:
            media_posicion = sum(posiciones) / len(posiciones)
            veces_rankeado = len(posiciones)

            ranking_final.append({
                'character': p,
                'posicion_media': round(media_posicion, 1),
                'total_listas': veces_rankeado
            })

    ranking_final = sorted(ranking_final, key=lambda x: x['posicion_media'])
    return render(request, 'ver_rankings.html', {'ranking': ranking_final})


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

    return render(request, 'user_panel.html', {'usuarios': usuarios})


def valorar_personaje(request):
    if request.method == 'POST' and request.user.is_authenticated:
        p_name = request.POST.get('character_name').strip()
        nota = int(request.POST.get('rating'))
        usuario_email = request.user.email
        marca_comentario = f"Voto para: {p_name}"

        actualizado = Review.objects.using('mongodb').filter(
            user=usuario_email,
            comment=marca_comentario
        ).update(
            rating=nota,
            reviewDate=timezone.now()
        )

        if actualizado == 0:
            Review.objects.using('mongodb').create(
                user=usuario_email,
                rating=nota,
                comment=marca_comentario,
                reviewDate=timezone.now()
            )
            messages.success(request, f"¡Has votado a {p_name}!")
        else:
            messages.success(request, f"¡Nota de {p_name} actualizada!")

    return redirect('characters')


def insertar_csv(request):
    if request.method == 'POST' and request.FILES.get('archivo_csv'):
        tipo = request.POST.get('tipo_dato')
        archivo = request.FILES['archivo_csv']

        try:
            data_set = archivo.read().decode('utf-8-sig')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)

            if reader.fieldnames:
                reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]

            contador = 0
            for row in reader:
                row = {k: v.strip() if v else v for k, v in row.items()}

                if not row.get('code'):
                    continue

                try:
                    codigo_val = int(row['code'])
                except ValueError:
                    continue

                if tipo == 'personaje':
                    actualizados = Character.objects.using('mongodb').filter(code=codigo_val).update(
                        name=row.get('name', ''),
                        description=row.get('description', ''),
                        image=row.get('image', '')
                    )

                    if actualizados == 0:
                        Character.objects.using('mongodb').create(
                            code=codigo_val,
                            name=row.get('name', ''),
                            description=row.get('description', ''),
                            image=row.get('image', '')
                        )

                else:
                    chars_raw = row.get('characters', '')
                    lista_ids = [int(n) for n in re.findall(r'\d+', str(chars_raw))]

                    actualizados = Category.objects.using('mongodb').filter(code=codigo_val).update(
                        name=row.get('name', ''),
                        description=row.get('description', ''),
                        image=row.get('image', ''),
                        characters=lista_ids
                    )

                    if actualizados == 0:
                        Category.objects.using('mongodb').create(
                            code=codigo_val,
                            name=row.get('name', ''),
                            description=row.get('description', ''),
                            image=row.get('image', ''),
                            characters=lista_ids
                        )

                contador += 1

            messages.success(request, f'¡Excelente! {contador} registros procesados correctamente.')

        except Exception as e:
            messages.error(request, f'Hubo un problema al procesar el archivo: {e}')

        return redirect('gestion')

    return render(request, 'insertar_csv.html')


def descargar_plantilla_csv(request):
    tipo = request.GET.get('tipo', 'personaje')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="plantilla_{tipo}.csv"'

    writer = csv.writer(response)

    if tipo == 'personaje':
        writer.writerow(['code', 'name', 'description', 'image'])
        writer.writerow(['150', 'Homer', 'Inspector de seguridad', 'www.png_ejemplo_personaje.com'])
    else:
        writer.writerow(['code', 'name', 'description', 'image', 'characters'])
        writer.writerow(['20', 'Familia', 'Los Simpson originales', 'www.png_ejemplo_personaje.com', '1,2,3,4,5'])

    return response


def borrar_personaje(request, code):
    if request.method == 'POST' and request.user.is_authenticated and request.user.rol == 'admin':
        deleted_count = Character.objects.using('mongodb').filter(code=code).delete()

        if deleted_count:
            messages.success(request, f"Personaje con código {code} eliminado correctamente.")
        else:
            messages.error(request, "No se pudo encontrar el personaje para borrar.")

    return redirect('characters')


def editar_categoria(request, code):
    if not (request.user.is_authenticated and request.user.rol == 'admin'):
        return redirect('categorias')

    categoria = Category.objects.using('mongodb').filter(code=code).first()
    todos_personajes = Character.objects.using('mongodb').all().order_by('name')

    if request.method == 'POST':
        nuevo_nombre = request.POST.get('name')
        nueva_desc = request.POST.get('description')
        nueva_img = request.POST.get('image')
        ids_seleccionados = [int(x) for x in request.POST.getlist('personajes_ids')]

        Category.objects.using('mongodb').filter(code=code).update(
            name=nuevo_nombre,
            description=nueva_desc,
            image=nueva_img,
            characters=ids_seleccionados
        )

        messages.success(request, f"Categoría '{nuevo_nombre}' actualizada correctamente.")
        return redirect('categorias')

    return render(request, 'mas_categorias.html', {
        'categoria': categoria,
        'personajes': todos_personajes
    })


def borrar_categoria(request, code):
    if request.method == 'POST' and request.user.is_authenticated and request.user.rol == 'admin':
        if code:
            res = Category.objects.using('mongodb').filter(code=int(code)).delete()
            messages.success(request, "Categoría eliminada con éxito.")
        else:
            messages.error(request, "Error: Código de categoría no válido.")

    return redirect('categorias')


def guardar_ranking(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Debes iniciar sesión para guardar tu ranking.")
            return redirect('login')

        category_code = request.POST.get('category_code')
        personajes_ids = request.POST.get('ranking_data')

        if not personajes_ids or not category_code:
            messages.error(request, "El ranking está vacío o no es válido.")
            return redirect('categorias')

        try:
            ranking_enteros = [int(pid) for pid in personajes_ids.split(',') if pid]

            Ranking.objects.using('mongodb').filter(
                user=request.user.email,
                categoryCode=int(category_code)
            ).delete()

            nuevo_ranking = Ranking(
                user=request.user.email,
                rankingDate=timezone.now(),
                categoryCode=int(category_code),
                rankingList=ranking_enteros
            )
            nuevo_ranking.save(using='mongodb')

            messages.success(request, "¡Yuju! Tu ranking se ha guardado correctamente.")

        except Exception as e:
            messages.error(request, f"Hubo un error al guardar: {e}")

    return redirect('categorias')
