"""Views for IFI home page."""

from django.shortcuts import render
from wagtail.models import Locale
from ifi_home_app.models.article_models import (
    ArticlePage,
    CategoryPage,
    StudentUnionCategoryPage,
    get_section_index,
)

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
    unions = StudentUnion.objects.all()
    tools = IfiTool.objects.all()
    board_messages = HomeBoardMessage.objects.filter(is_active=True)
    categories = CategoryPage.objects.live().filter(locale=Locale.get_active(), show_in_menu=True) 
    
    student_union_category = _get_localized_category(
        "studentforeninger", "nb", model=StudentUnionCategoryPage
    )
    student_union_children = (
        student_union_category.get_children().live().specific()
        if student_union_category
        else []
    )

    ifi_tools_category = _get_localized_category("ifi-verktøy", "nb")
    ifi_tools_children = (
        ifi_tools_category.get_children().live().specific()
        if ifi_tools_category
        else []
    )

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
    }

    return render(
        request=request,
        template_name="core/home_index.html",
        context=context,
    )
