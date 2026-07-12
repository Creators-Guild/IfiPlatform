"""URL configuration for yourpage app."""
from django.urls import path
from .views import core_views

urlpatterns = [path("", core_views.main_view, name="yourpage_main")]
