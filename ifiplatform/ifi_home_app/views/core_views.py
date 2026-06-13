"""Views for IFI home page."""
from django.shortcuts import render
from ..models.home_models import *
from ..models.news_models import NewsItem
from ..dummydata import *


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

    context = {
        "news_items": news_items,
        "unions": unions,
        "tools": tools,
    }

    return render(
        request=request,
        template_name="core/home_main.html",
        context=context,
    )
