"""Admin registration for ifi_home_app models."""
from django.contrib import admin
from .models import NewsItem, StudentUnion

admin.site.register(NewsItem)
admin.site.register(StudentUnion)
