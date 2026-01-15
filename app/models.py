import datetime

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django_mongodb_backend.fields import ArrayField
from django_mongodb_backend.models import EmbeddedModel

# Create your models here.
class Character(EmbeddedModel):

    code = models.IntegerField(null=False, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=400)
    image = models.CharField(max_length=300)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'character'
        managed = False

class Review(EmbeddedModel):
    user = models.CharField(max_length=100)
    reviewDate = models.DateField(default=datetime.datetime.now())
    rating = models.PositiveIntegerField(null=False, validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()

    def __str__(self):
        return self.user + " " + str(self.rating)

    class Meta:
        db_table = 'review'
        managed = False

class Ranking(EmbeddedModel):
    user = models.CharField(max_length=100)
    rankingDate = models.DateField(default=datetime.datetime.now())
    categoryCode = models.IntegerField(null=False)
    rankingList = ArrayField(models.IntegerField())

    def __str__(self):
        return self.user + " " + str(self.rankingList)

    class Meta:
        db_table = 'ranking'
        managed = False
