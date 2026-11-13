"""Models module for IFI home app."""

__all__ = [
    "StudentUnion",
    "ArticlePage",
    "ArticleIndexPage",
    "HeaderMessage",
    "HomeBoardMessage",
    "EventIndexPage",
    "EventPage",
    "GlossarySyncState",
    "MagazineIssue",
    "Location",
    "OpeningPeriod",
    "LocationClosure",
    "Menu",
    "MenuGroup",
    "MenuGroupLink",
    "MenuSlot",
    "EnglishSlug",
    "SegmentTranslation",
    "TranslationSettings",
    "WaitingForEnglish",
]

from .home_models import *
from .article_models import ArticlePage, ArticleIndexPage
from .site_models import HeaderMessage
from .event.pages import EventIndexPage, EventPage
from .event import peoply  # noqa: F401 -- imported so Django registers its models
from .glossary_models import GlossarySyncState
from .magazine import MagazineIssue
from .opening_hours import Location, LocationClosure, OpeningPeriod
from .menus import Menu, MenuGroup, MenuGroupLink, MenuSlot
from .translation import (
    EnglishSlug,
    SegmentTranslation,
    TranslationSettings,
    WaitingForEnglish,
)
