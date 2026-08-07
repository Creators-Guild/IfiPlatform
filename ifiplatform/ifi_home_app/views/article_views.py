"""API endpoint backing the on-page "quick style" panel on article pages
(padding/alignment/font size) -- see article_quick_style.js and
ArticlePage.get_context()'s can_edit_style in article_models.py."""

import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ifi_home_app.models.article_models import ArticlePage


@require_POST
def save_quick_style(request, page_id):
    """Save content_side_padding/content_alignment/content_font_size for one
    ArticlePage and publish immediately -- this panel is a quick style tweak,
    not the full editor, so there's no separate draft step."""
    page = get_object_or_404(ArticlePage, pk=page_id).style_target

    if not page.permissions_for_user(request.user).can_edit():
        return JsonResponse({"error": "You don't have permission to edit this page."}, status=403)

    try:
        data = json.loads(request.body)
        side_padding = float(data["content_side_padding"])
        alignment = data["content_alignment"]
        font_size = float(data["content_font_size"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    if alignment not in dict(ArticlePage.CONTENT_ALIGNMENT_CHOICES):
        return JsonResponse({"error": "Invalid alignment."}, status=400)

    page.content_side_padding = side_padding
    page.content_alignment = alignment
    page.content_font_size = font_size
    revision = page.save_revision(user=request.user)
    revision.publish(user=request.user)

    return JsonResponse({"ok": True})
