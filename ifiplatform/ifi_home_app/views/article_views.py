"""API endpoints backing the on-page style panels on article pages
(padding/alignment/font size) -- see article_quick_style.js/
article_block_style.js and ArticlePage.get_context()'s can_edit_style in
article_models.py."""

import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ifi_home_app.models.article_models import ArticleBlockStyle, ArticlePage

BLOCK_STYLE_FIELDS = {
    "styled_text": {"side_padding", "alignment", "font_size"},
    "image": {"alignment", "width_rem"},
    "multi_column": {"side_padding"},
}


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


@require_POST
def save_block_style(request, page_id):
    """Save a single block's style override (ArticleBlockStyle) -- a plain
    upsert, deliberately outside Wagtail's StreamField/revision/publish
    system entirely (see ArticleBlockStyle's docstring in article_models.py
    for why). Live immediately, same as save_quick_style, no draft step."""
    page = get_object_or_404(ArticlePage, pk=page_id).style_target

    if not page.permissions_for_user(request.user).can_edit():
        return JsonResponse({"error": "You don't have permission to edit this page."}, status=403)

    try:
        data = json.loads(request.body)
        block_id = data["block_id"]
        block_type = data["block_type"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    allowed_fields = BLOCK_STYLE_FIELDS.get(block_type)
    if not allowed_fields or not block_id:
        return JsonResponse({"error": "Invalid block type."}, status=400)

    defaults = {}
    try:
        if "side_padding" in allowed_fields and data.get("side_padding") is not None:
            defaults["side_padding"] = float(data["side_padding"])
        if "font_size" in allowed_fields and data.get("font_size") is not None:
            defaults["font_size"] = float(data["font_size"])
        if "width_rem" in allowed_fields and data.get("width_rem") is not None:
            defaults["width_rem"] = float(data["width_rem"])
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    if "alignment" in allowed_fields and data.get("alignment") is not None:
        alignment = data["alignment"]
        if alignment not in dict(ArticlePage.CONTENT_ALIGNMENT_CHOICES):
            return JsonResponse({"error": "Invalid alignment."}, status=400)
        defaults["alignment"] = alignment

    ArticleBlockStyle.objects.update_or_create(
        article=page, block_id=block_id, defaults=defaults
    )

    return JsonResponse({"ok": True})


@require_POST
def save_header_style(request, page_id):
    """Save title_alignment/intro_alignment/meta_alignment for one
    ArticlePage and publish immediately. Unlike save_block_style, these are
    plain ArticlePage fields (not StreamField content), so this is the same
    save_revision()+publish() pattern as save_quick_style -- no
    ArticleBlockStyle side table involved."""
    page = get_object_or_404(ArticlePage, pk=page_id).style_target

    if not page.permissions_for_user(request.user).can_edit():
        return JsonResponse({"error": "You don't have permission to edit this page."}, status=403)

    try:
        data = json.loads(request.body)
        title_alignment = data["title_alignment"]
        intro_alignment = data["intro_alignment"]
        meta_alignment = data["meta_alignment"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    valid_alignments = dict(ArticlePage.CONTENT_ALIGNMENT_CHOICES)
    for value in (title_alignment, intro_alignment, meta_alignment):
        if value not in valid_alignments:
            return JsonResponse({"error": "Invalid alignment."}, status=400)

    page.title_alignment = title_alignment
    page.intro_alignment = intro_alignment
    page.meta_alignment = meta_alignment
    revision = page.save_revision(user=request.user)
    revision.publish(user=request.user)

    return JsonResponse({"ok": True})
