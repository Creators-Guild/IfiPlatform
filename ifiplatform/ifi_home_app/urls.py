"""URL configuration for the ifi_home app."""
from django.urls import path
from .views import home_views


# ifi_wiki_urlpatterns = [
#     path("wiki/", wiki_views.wiki_main, name="ifi_wiki"),
#     # using django path converter (<converter:name>)
#     path("wiki/<int:pk>/", wiki_views.wiki_article, name="ifi_wiki_article"),
# ]


ifi_home_urlpatterns = [path("", home_views.main_view, name="ifi_home")]

urlpatterns = ifi_home_urlpatterns
