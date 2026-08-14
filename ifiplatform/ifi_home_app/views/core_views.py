"""Views for IFI home page."""

from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from wagtail.models import Locale
from ifi_home_app.models.article_models import (
    ArticlePage,
    CategoryPage,
    StudentUnionCategoryPage,
    UnionPage,
    get_section_index,
)
from ifi_home_app.models.event_models import EventIndexPage, EventPage

from ..dummydata import (
    dummy_news_objects,
    dummy_studentunions_objects,
    dummy_tools_objects,
)
from ..models.home_models import HomeBoardMessage, IfiTool, NewsItem, StudentUnion


def _get_localized_category(slug, language_code, model=CategoryPage):
    """Look up a `model` page by a fixed slug/locale, then resolve it to the
    visitor's active locale (falling back to the anchor locale if untranslated)."""
    category = (
        model.objects.live()
        .filter(slug=slug, locale=Locale.objects.get(language_code=language_code))
        .first()
    )
    return category.localized if category else None


def main_view(request):
    """Display the main IFI home page with news, unions and tools."""
    # (development) if no news in database, use dummydata
    if not NewsItem.objects.exists():
        dummy_news_objects.create(fresh_on_page_load=True)
    if not StudentUnion.objects.exists():
        dummy_studentunions_objects.create(fresh_on_page_load=True)
    if not IfiTool.objects.exists():
        dummy_tools_objects.create(fresh_on_page_load=True)

    # create context
    news_items = NewsItem.objects.order_by("-created_at")[:4]
    news_index_page = get_section_index("news")
    news_articles = (
        ArticlePage.objects.descendant_of(news_index_page)
        .live()
        .filter(locale=Locale.get_active(), show_on_homepage=True)
        .order_by("-published_date")[:12]
        if news_index_page
        else ArticlePage.objects.none()
    )
    info_articles_index_page = get_section_index("info_articles")
    suggested_articles = (
        ArticlePage.objects.descendant_of(info_articles_index_page)
        .live()
        .filter(locale=Locale.get_active(), show_on_homepage=True)
        .order_by("-published_date")[:12]
        if info_articles_index_page
        else ArticlePage.objects.none()
    )
    # Both columns share the same grid (newsbar_layout.css) at the same
    # column width, so matching their card *counts* here is what keeps
    # them the same number of rows tall in the browser -- whichever
    # category happens to have fewer live articles caps the other one too,
    # rather than one column trailing on shorter than its neighbour.
    news_articles = list(news_articles)
    suggested_articles = list(suggested_articles)
    shared_article_count = min(len(news_articles), len(suggested_articles))
    news_articles = news_articles[:shared_article_count]
    suggested_articles = suggested_articles[:shared_article_count]

    unions = StudentUnion.objects.all()
    tools = IfiTool.objects.all()
    board_messages = HomeBoardMessage.objects.filter(
        is_active=True, locale=Locale.get_active()
    )
    categories = CategoryPage.objects.live().filter(locale=Locale.get_active(), show_in_menu=True) 
    
    student_union_category = _get_localized_category(
        "studentforeninger", "nb", model=StudentUnionCategoryPage
    )
    student_union_children = (
        UnionPage.objects.child_of(student_union_category).live().filter(show_in_menu=True)
        if student_union_category
        else []
    )

    ifi_tools_category = _get_localized_category("ifi-verktøy", "nb")
    ifi_tools_children = (
        ifi_tools_category.get_children().live().specific()
        if ifi_tools_category
        else []
    )

    new_student_category = _get_localized_category("ny-ifi-student", "nb")
    new_student_children = (
        new_student_category.get_children().live().specific()
        if new_student_category
        else []
    )

    today = timezone.localdate()
    event_index = (
        EventIndexPage.objects.live().filter(locale=Locale.get_active()).first()
    )
    upcoming_events = (
        EventPage.objects.child_of(event_index)
        .live()
        .filter(locale=Locale.get_active(), show_on_homepage=True)
        .filter(Q(end_date__gte=today) | Q(end_date__isnull=True, event_date__gte=today))
        .order_by("event_date", "event_time")[:6]
        if event_index
        else EventPage.objects.none()
    )
    # Top-level events actually in progress today, e.g. day 3 of Fadderuke
    # -- a subset of upcoming_events (already includes ongoing multi-day
    # events via the end_date filter above), surfaced separately so the
    # homepage box can call them out at the top instead of leaving them to
    # blend into the rest of the list.
    happening_now_events = [event for event in upcoming_events if event.is_happening_now]

    context = {
        "news_items": news_items,
        "news_articles": news_articles,
        "suggested_articles": suggested_articles,
        "unions": unions,
        "tools": tools,
        "board_messages": board_messages,
        "categories": categories,
        "student_union_cat": student_union_category,
        "student_union_children": student_union_children,
        "ifi_tools_cat": ifi_tools_category,
        "ifi_tools_children": ifi_tools_children,
        "new_student_cat": new_student_category,
        "new_student_children": new_student_children,
        "upcoming_events": upcoming_events,
        "happening_now_events": happening_now_events,
    }

    return render(
        request=request,
        template_name="core/home_index.html",
        context=context,
    )
