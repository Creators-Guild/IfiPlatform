"""Views for IFI news feature."""
from django.shortcuts import render


def news_main(request):
    """Display the main news page."""
    return render(request=request, template_name="ifi_news/news_main.html")


def news_article(request):
    """Display a specific news article."""
    return render(request=request, template_name="ifi_news/news_article.html")
