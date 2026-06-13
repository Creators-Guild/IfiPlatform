"""Models for IFI home page: StudentUnion and IfiTool."""
from django.db import models

# Create your models here.


class StudentUnion(models.Model):
    """Represents a student union or organization at IFI."""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image_name = models.CharField(max_length=100, blank=True)  # path to image in static
    programme_union = models.BooleanField(
        default=False, verbose_name="Is_programme_union"
    )
    homepage = models.URLField(blank=True)


class IfiTool(models.Model):
    """Represents a tool or resource created by IFI students/staff."""
    title = models.CharField(max_length=200)
    creators = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=200, blank=True)
    image_name = models.CharField(max_length=100, blank=True)  # path to image in static
    link = models.URLField(blank=True)
