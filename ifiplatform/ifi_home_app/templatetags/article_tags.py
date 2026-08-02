# ifi_home_app/templatetags/blog_tags.py
from django import template
from ifi_home_app.models import ArticleIndexPage

register = template.Library()

@register.simple_tag
def get_article_index():
    return ArticleIndexPage.objects.live().first()