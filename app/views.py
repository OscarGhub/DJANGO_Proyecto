import csv
import io
import json
import re

from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from .forms import LoginForm, RegistroForm
from .models import Character, Category
from .models import Ranking
from .models import Review, Usuario
from .services import sync_simpsons_characters


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

        c.ya_votado = any(voto.startswith(marca_voto) for voto in votos_usuario)

        votos = Review.objects.using('mongodb').filter(comment__startswith=marca_voto)
        promedio = votos.aggregate(Avg('rating'))['rating__avg'] or 0

        c.total_votos = votos.count()
        c.media = round(promedio, 1)

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
    category_code = request.GET.get('category')
    ranking_guardado = None
    ids_ya_rankeados = []

    if category_code:
        category = Category.objects.using('mongodb').filter(code=int(category_code)).first()
        characters = Character.objects.using('mongodb').filter(code__in=category.characters)

        if request.user.is_authenticated:
            ranking_guardado = Ranking.objects.using('mongodb').filter(
                user=request.user.email,
                categoryCode=int(category_code)
            ).first()

            if ranking_guardado:
                for tier, ids in ranking_guardado.rankingList.items():
                    ids_ya_rankeados.extend([str(i) for i in ids])

    return render(request, 'ranking.html', {
        'characters': characters,
        'category_code': category_code,
        'ranking_guardado': ranking_guardado,
        'ids_ya_rankeados': ids_ya_rankeados
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
    categorias = Category.objects.using('mongodb').all()
    personajes = Character.objects.using('mongodb').all()
    todos_los_rankings = Ranking.objects.using('mongodb').all()

    pesos = {'S': 1, 'A': 2, 'B': 3, 'C': 4, 'D': 5, 'E': 6, 'F': 7}
    ranking_por_categorias = []

    for cat in categorias:
        ranking_categoria = []
        rankings_de_esta_cat = [r for r in todos_los_rankings if r.categoryCode == cat.code]

        if rankings_de_esta_cat:
            personajes_de_cat = [p for p in personajes if p.code in cat.characters]

            for p in personajes_de_cat:
                puntuaciones = []
                for r in rankings_de_esta_cat:
                    for tier, ids in r.rankingList.items():
                        if str(p.code) in [str(id) for id in ids]:
                            puntuaciones.append(pesos.get(tier, 7))
                            break

                if puntuaciones:
                    media = sum(puntuaciones) / len(puntuaciones)
                    ranking_categoria.append({
                        'character': p,
                        'posicion_media': round(media, 1),
                        'total_listas': len(puntuaciones)
                    })

            ranking_categoria = sorted(ranking_categoria, key=lambda x: x['posicion_media'])
            ranking_por_categorias.append({'categoria': cat, 'ranking': ranking_categoria})

    return render(request, 'ver_rankings.html', {'datos_agrupados': ranking_por_categorias})


def gestion(request):
    return render(request, 'gestion.html')


def categorias(request):
    lista_categorias = Category.objects.using('mongodb').all().order_by('code')

    categorias_rankeadas = []
    if request.user.is_authenticated:
        categorias_rankeadas = Ranking.objects.using('mongodb').filter(
            user=request.user.email
        ).values_list('categoryCode', flat=True)

    for cat in lista_categorias:
        cat.ya_rankeado = cat.code in categorias_rankeadas

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

        texto_usuario = request.POST.get('comentario_usuario', '').strip()
        marca_comentario = f"Voto para: {p_name}"

        comentario_final = f"{marca_comentario}. Comentario: {texto_usuario}" if texto_usuario else marca_comentario

        actualizado = Review.objects.using('mongodb').filter(
            user=usuario_email,
            comment__startswith=marca_comentario
        ).update(
            rating=nota,
            comment=comentario_final,
            reviewDate=timezone.now()
        )

        if actualizado == 0:
            Review.objects.using('mongodb').create(
                user=usuario_email,
                rating=nota,
                comment=comentario_final,
                reviewDate=timezone.now()
            )
            messages.success(request, f"¡Has votado a {p_name}!")
        else:
            messages.success(request, f"¡Nota y comentario de {p_name} actualizados!")

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
                row = {
                    k: (v.strip() if isinstance(v, str) else v)
                    for k, v in row.items()
                    if k is not None
                }

                if not row.get('code'):
                    continue

                try:
                    codigo_val = int(row['code'])
                except (ValueError, TypeError):
                    continue

                if tipo == 'personaje':
                    Character.objects.using('mongodb').update_or_create(
                        code=codigo_val,
                        defaults={
                            'name': row.get('name', ''),
                            'description': row.get('description', ''),
                            'image': row.get('image', '')
                        }
                    )
                else:
                    chars_raw = row.get('characters', '')
                    lista_ids = [int(n) for n in re.findall(r'\d+', str(chars_raw))]

                    Category.objects.using('mongodb').update_or_create(
                        code=codigo_val,
                        defaults={
                            'name': row.get('name', ''),
                            'description': row.get('description', ''),
                            'image': row.get('image', ''),
                            'characters': lista_ids
                        }
                    )

                contador += 1

            messages.success(request, f'¡Excelente! {contador} registros procesados correctamente.')

        except Exception as e:
            print(f"Error detallado: {e}")
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
        ranking_data_raw = request.POST.get('ranking_data')

        if not ranking_data_raw or not category_code:
            messages.error(request, "El ranking está vacío o no es válido.")
            return redirect('categorias')

        try:
            tier_dict = json.loads(ranking_data_raw)

            Ranking.objects.using('mongodb').filter(
                user=request.user.email,
                categoryCode=int(category_code)
            ).delete()

            nuevo_ranking = Ranking(
                user=request.user.email,
                rankingDate=timezone.now(),
                categoryCode=int(category_code),
                rankingList=tier_dict
            )
            nuevo_ranking.save(using='mongodb')

            messages.success(request, "¡Yuju! Tu Tier List se ha guardado correctamente.")

        except Exception as e:
            messages.error(request, f"Hubo un error al guardar: {e}")

    return redirect('categorias')


from django.db.models import Avg


def dashboard_admin(request):
    if not (request.user.is_authenticated and request.user.rol == 'admin'):
        return redirect('inicio')

    total_usuarios = Usuario.objects.count()
    total_personajes = Character.objects.using('mongodb').count()
    total_rankings = Ranking.objects.using('mongodb').count()
    total_reviews = Review.objects.using('mongodb').count()

    characters = Character.objects.using('mongodb').all()
    ranking_stats = []
    for c in characters:
        votos = Review.objects.using('mongodb').filter(comment__startswith=f"Voto para: {c.name}")
        promedio = votos.aggregate(Avg('rating'))['rating__avg'] or 0
        if votos.count() > 0:
            ranking_stats.append({
                'name': c.name,
                'media': round(promedio, 1),
                'votos': votos.count()
            })

    top_5 = sorted(ranking_stats, key=lambda x: x['media'], reverse=True)[:5]

    categorias_stats = []
    todas_cats = Category.objects.using('mongodb').all()

    for cat in todas_cats:
        num_rankings = Ranking.objects.using('mongodb').filter(categoryCode=cat.code).count()
        if num_rankings > 0:
            categorias_stats.append({
                'name': cat.name,
                'total': num_rankings
            })

    top_categorias = sorted(categorias_stats, key=lambda x: x['total'], reverse=True)[:3]

    context = {
        'total_usuarios': total_usuarios,
        'total_personajes': total_personajes,
        'total_rankings': total_rankings,
        'total_reviews': total_reviews,
        'top_5': top_5,
        'top_categorias': top_categorias
    }

    return render(request, 'admin_resumen.html', context)
