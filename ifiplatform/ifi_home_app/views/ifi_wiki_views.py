from django.shortcuts import render, get_object_or_404
from ..models.wiki_models import *
from ..dummydata import dummy_wiki_articles

def wiki_main(request):
    if not WikiArticle.objects.exists():
        dummy_wiki_articles.create(fresh_on_page_load=True)
    
    article_metas = WikiArticle_Meta.objects.all()
    context = {
        "article_metas" : article_metas
    }
    return render(
        request=request, 
        template_name='ifi_wiki/wiki_main.html', 
        context=context
        )



def wiki_article(request, pk):
    article = get_object_or_404(WikiArticle, pk=pk)
    # "meta_data" cause related names in WikiArticle_Meta
    meta = getattr(article, "meta_data", None)

    context = {
        "article" : article,
        "meta" : meta
    }

    return render(
        request=request, 
        template_name='ifi_wiki/wiki_article.html',
        context=context
        )