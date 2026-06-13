from ..models.wiki_models import *
from . import dummy_users_objects

def create(fresh_on_page_load:bool = False):
    if fresh_on_page_load:
        WikiAuthor.objects.all().delete()
        WikiArticle_Meta.objects.all().delete()
        WikiArticle.objects.all().delete()
    
    dummy_user = dummy_users_objects.get_dummy_user()
    author, _ = WikiAuthor.objects.get_or_create(
        user=dummy_user,
        defaults={"name": "Dummy"},
    )
    
    for i in range(4):
        article = WikiArticle.objects.create(
            title = f"Dummy Wiki Article {i}",
            intro_text = "intro intro",
            body = "Lorem ipsum dummy content" * 100
        )
        meta = WikiArticle_Meta.objects.create(
            description = "description: Lorem ipsum dummy content",
            article = article
        )
        meta.authors.add(author)
        
        