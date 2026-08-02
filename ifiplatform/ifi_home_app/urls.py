"""URL configuration for the ifi_home app."""

from django.urls import path, include
from wagtail import urls as wagtail_urls

from .views import home_views

ifi_home_urlpatterns = [path("", home_views.main_view, name="ifi_home")]

ifi_article_urlpatterns = [
    path("articles/", include(wagtail_urls)),
]

urlpatterns = ifi_home_urlpatterns + ifi_article_urlpatterns
