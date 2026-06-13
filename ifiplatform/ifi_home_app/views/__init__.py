"""Views module for IFI home app."""
from . import core_views as home_views
from . import ifi_news_views as news_views
from . import ifi_wiki_views as wiki_views

__all__ = ["home_views", "news_views", "wiki_views"]
