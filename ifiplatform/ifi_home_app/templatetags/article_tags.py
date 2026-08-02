# ifi_home_app/templatetags/blog_tags.py
from django import template
from ifi_home_app.models.article_models import ArticleIndexPage, CategoryPage

register = template.Library()

# to be bale to link to spesific articles
@register.simple_tag
def get_article_index():
    return ArticleIndexPage.objects.live().first()

# to be able to send categorycontext, mainly to sidemenu
@register.simple_tag
def get_categories():
    return [c for c in CategoryPage.objects.live() if c.is_visible]