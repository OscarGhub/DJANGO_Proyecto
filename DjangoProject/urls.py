"""
URL configuration for DjangoProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.inicio, name='inicio'),
    path('actualizar-api/', views.actualizar_desde_api, name='actualizar_api'),
    path('user_panel/', views.user_panel, name='user_panel'),
    path('characters/', views.characters, name='characters'),
    path('registro/', views.registrar_usuario, name='registro'),
    path('login/', views.login_usuario, name='login'),
    path('logout/', views.logout_usuario, name='logout'),
    path('ranking/', views.ranking, name='ranking'),
    path('ver_rankings/', views.mejores_ranking, name='ver_rankings'),
    path('gestion/', views.gestion, name='gestion'),
    path('categorias/', views.categorias, name='categorias'),
    path('mas_personajes/', views.mas_personajes, name='mas_personajes'),
    path('mas_categorias/', views.mas_categorias, name='mas_categorias'),
    path('insertar_csv/', views.insertar_csv, name='insertar_csv'),
    path('descargar_csv/', views.descargar_plantilla_csv, name='descargar_csv'),
    path('valorar_personaje/', views.valorar_personaje, name='valorar_personaje'),
    path('borrar_personaje/<int:code>/', views.borrar_personaje, name='borrar_personaje'),
    path('borrar_categoria/<int:code>/', views.borrar_categoria, name='borrar_categoria'),
    path('editar_categoria/<int:code>/', views.editar_categoria, name='editar_categoria'),
    path('guardar_ranking/', views.guardar_ranking, name='guardar_ranking'),
    path('admin_resumen/', views.dashboard_admin, name='admin_resumen'),
]
