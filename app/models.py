from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django_mongodb_backend.fields import ArrayField


# python manage.py makemigrations ---> PREPARA SQL SCRIPT
# python manage.py migrate ---> EJECUTA SQL SCRIPT

class UsuarioManager(BaseUserManager):

    def create_user(self, email, nombre, rol, password=None):
        if not email:
            raise ValueError("El usuario debe tener un email")
        email = self.normalize_email(email)
        usuario = self.model(email=email, nombre=nombre, rol=rol)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, nombre, rol='admin', password=None):
        usuario = self.create_user(email, nombre, rol, password)
        usuario.is_superuser = True
        usuario.is_staff = True
        usuario.save(using=self._db)
        return usuario


# MONGO MODELS
class Character(models.Model):
    code = models.IntegerField(null=False, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=400)
    image = models.CharField(max_length=300)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'character'
        managed = False


class Review(models.Model):
    user = models.CharField(max_length=100)
    reviewDate = models.DateField(default=timezone.now)
    rating = models.PositiveIntegerField(null=False, validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()

    def __str__(self):
        return self.user + " " + str(self.rating)

    class Meta:
        db_table = 'review'
        managed = False


class Ranking(models.Model):
    user = models.CharField(max_length=100)
    rankingDate = models.DateTimeField(default=timezone.now)
    categoryCode = models.IntegerField(null=False)
    rankingList = models.JSONField()

    def __str__(self):
        return f"{self.user} - Categoría {self.categoryCode}"

    class Meta:
        db_table = 'ranking'
        managed = False


class Category(models.Model):
    code = models.IntegerField(null=False, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=400)
    characters = ArrayField(models.IntegerField())
    image = models.CharField(max_length=300)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'category'
        managed = False


# SQLITE MODELS
class Usuario(AbstractBaseUser, PermissionsMixin):
    ROLES = (
        ('admin', 'Administrador'),
        ('cliente', 'Cliente'),
    )

    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=100)
    rol = models.CharField(max_length=20, choices=ROLES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'rol']


def __str__(self):
    return self.email
