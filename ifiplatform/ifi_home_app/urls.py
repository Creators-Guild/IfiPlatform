"""URL configuration for the ifi_home app."""

from django.urls import path, include
from wagtail import urls as wagtail_urls

from .views import home_views
from .views import article_views

ifi_home_urlpatterns = [path("", home_views.main_view, name="ifi_home")]

ifi_api_urlpatterns = [
    path(
        "api/articles/<int:page_id>/quick-style/",
        article_views.save_quick_style,
        name="article_quick_style",
    ),
]

ifi_article_urlpatterns = [
    path("", include(wagtail_urls)),
]

urlpatterns = ifi_home_urlpatterns + ifi_api_urlpatterns + ifi_article_urlpatterns
