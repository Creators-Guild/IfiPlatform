from django.db import models


class NewsItem(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image_name = models.CharField(max_length=100, blank=True)  # path to image in static
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
