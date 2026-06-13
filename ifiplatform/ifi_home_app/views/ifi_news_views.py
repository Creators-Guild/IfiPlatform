from django.shortcuts import render


def news_main(request):
    return render(request=request, template_name="ifi_news/news_main.html")


def news_article(request):
    return render(request=request, template_name="ifi_news/news_article.html")
