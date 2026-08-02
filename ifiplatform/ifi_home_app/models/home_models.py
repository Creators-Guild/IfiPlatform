"""Models for IFI home page: StudentUnion and IfiTool."""

from django.db import models


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


# temp item
class NewsItem(models.Model):
    """A temporary news item shown on the homepage, until a real news system exists."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image_name = models.CharField(max_length=100, blank=True)  # path to image in static
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
