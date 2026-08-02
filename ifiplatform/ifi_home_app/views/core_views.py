"""Views for IFI home page."""

from django.shortcuts import render
from ifi_home_app.models.article_models import CategoryPage

from ..dummydata import (
    dummy_news_objects,
    dummy_studentunions_objects,
    dummy_tools_objects,
)
from ..models.home_models import HomeBoardMessage, IfiTool, NewsItem, StudentUnion


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
    unions = StudentUnion.objects.all()
    tools = IfiTool.objects.all()
    board_messages = HomeBoardMessage.objects.filter(is_active=True)

    context = {
        "news_items": news_items,
        "unions": unions,
        "tools": tools,
        "board_messages": board_messages,
        "categories": CategoryPage.objects.live(),
    }

    return render(
        request=request,
        template_name="core/home_index.html",
        context=context,
    )
