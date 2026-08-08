"""API endpoints backing the on-page style panels on article pages
(padding/alignment/font size) -- see article_quick_style.js/
article_block_style.js and ArticlePage.get_context()'s can_edit_style in
article_models.py."""

import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ifi_home_app.models.article_models import (
    COLOR_CHOICES,
    HEX_COLOR_VALIDATOR,
    ArticleBlockStyle,
    ArticlePage,
)

# box styling (see BLOCK_STYLE_DEFAULTS["box"]/_effective_box_style() in
# article_models.py) is available on every block type below, plus "column"
# -- a multi_column sub-column, which has no style of its own besides box.
BOX_FIELDS = {
    "box_enabled",
    "box_border_width",
    "box_border_color",
    "box_border_custom_color",
    "box_border_visible",
    "box_radius",
    "box_bg_color",
    "box_bg_custom_color",
    "box_padding",
    "box_margin",
}

# not box_* -- applies independent of whether a block's box is enabled (see
# _effective_heading_style() in article_models.py), available wherever
# font_size is (or, for title/meta/intro, wherever their own box is).
TEXT_COLOR_FIELDS = {"text_color", "text_custom_color"}

BLOCK_STYLE_FIELDS = {
    "heading": {"side_padding", "alignment", "font_size"} | BOX_FIELDS | TEXT_COLOR_FIELDS,
    "paragraph": {"side_padding", "alignment", "font_size"} | BOX_FIELDS | TEXT_COLOR_FIELDS,
    "image": {"alignment", "width_rem", "side_padding"} | BOX_FIELDS,
    # article/category/union/tool cards -- width/height, plus (article_card
    # only) list_style/fixed_ratio (see ArticleBlockStyle's own docstrings).
    "article_card": {"width_rem", "height_rem", "list_style", "fixed_ratio"},
    "category_card": {"width_rem", "height_rem"},
    "union_card": {"width_rem", "height_rem"},
    "tool_card": {"width_rem", "height_rem"},
    # an image's own title (alt_text)/caption, boxed together as one unit
    # (its own <figcaption>) independent of the image's own box above --
    # keyed by a synthesized "<image-block-id>-caption" id, same pattern as
    # a multi_column column's own title.
    "image_caption": {"side_padding"} | BOX_FIELDS,
    # the title/caption text's own alignment/font-size/side-padding/color,
    # independent of each other and of the figcaption's own box above --
    # keyed by "<image-block-id>-cap-title"/"-cap-body".
    "image_title": {"side_padding", "alignment", "font_size"} | TEXT_COLOR_FIELDS,
    "image_caption_body": {"side_padding", "alignment", "font_size"} | TEXT_COLOR_FIELDS,
    "multi_column": {"side_padding", "gap", "column_weights"} | BOX_FIELDS,
    "column": {"side_padding"} | BOX_FIELDS,
    # a multi_column column's own title -- alignment/font-size/text-color
    # only (no box or side padding of its own -- it's edited from the same
    # trigger/panel as its column, see FIELDS_BY_TYPE.column in
    # article_block_style.js, which sends this as a second, independent
    # save request alongside the column's own box fields), keyed by a
    # synthesized "<column-uuid>-title" id (see _effective_block_styles()
    # in article_models.py).
    "column_title": {"alignment", "font_size"} | TEXT_COLOR_FIELDS,
    # title/meta/intro (the article-header group), keyed by fixed pseudo
    # ids ("article-title"/"article-meta"/"article-intro", see
    # ArticlePage.get_context()). Alignment/font-size for these three
    # already live on dedicated ArticlePage fields, edited via
    # save_header_style instead -- side padding/box/text color are saved as
    # ArticleBlockStyle rows for them (side padding and box from their own
    # individual trigger, text color from the shared article_header one).
    "title": {"side_padding"} | BOX_FIELDS | TEXT_COLOR_FIELDS,
    "meta": {"side_padding"} | BOX_FIELDS | TEXT_COLOR_FIELDS,
    "intro": {"side_padding"} | BOX_FIELDS | TEXT_COLOR_FIELDS,
    # the title/meta/intro group as a whole, keyed by the fixed pseudo id
    # "article-header" -- box only (alignment/font-size are plain
    # ArticlePage fields, saved via save_header_style instead; side padding
    # is too, see ArticlePage.get_context()'s own comment on this row).
    "article_header": set(BOX_FIELDS),
}


@require_POST
def save_quick_style(request, page_id):
    """Save content_side_padding/content_alignment/content_font_size/
    content_bg_enabled/content_bg_color/content_bg_custom_color for one
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
        bg_enabled = bool(data["content_bg_enabled"])
        bg_color = data["content_bg_color"]
        bg_custom_color = data.get("content_bg_custom_color") or ""
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    if alignment not in dict(ArticlePage.CONTENT_ALIGNMENT_CHOICES):
        return JsonResponse({"error": "Invalid alignment."}, status=400)

    if bg_color not in dict(COLOR_CHOICES):
        return JsonResponse({"error": "Invalid content_bg_color."}, status=400)

    if bg_custom_color:
        try:
            HEX_COLOR_VALIDATOR(bg_custom_color)
        except ValidationError:
            return JsonResponse({"error": "Invalid content_bg_custom_color."}, status=400)

    page.content_side_padding = side_padding
    page.content_alignment = alignment
    page.content_font_size = font_size
    page.content_bg_enabled = bg_enabled
    page.content_bg_color = bg_color
    page.content_bg_custom_color = bg_custom_color
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
        if "height_rem" in allowed_fields and data.get("height_rem") is not None:
            defaults["height_rem"] = float(data["height_rem"])
        if "gap" in allowed_fields and data.get("gap") is not None:
            defaults["gap"] = float(data["gap"])
        if "column_weights" in allowed_fields and data.get("column_weights") is not None:
            defaults["column_weights"] = [float(w) for w in data["column_weights"]]
        if "box_border_width" in allowed_fields and data.get("box_border_width") is not None:
            defaults["box_border_width"] = float(data["box_border_width"])
        if "box_radius" in allowed_fields and data.get("box_radius") is not None:
            defaults["box_radius"] = float(data["box_radius"])
        if "box_padding" in allowed_fields and data.get("box_padding") is not None:
            defaults["box_padding"] = float(data["box_padding"])
        if "box_margin" in allowed_fields and data.get("box_margin") is not None:
            defaults["box_margin"] = float(data["box_margin"])
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    if "alignment" in allowed_fields and data.get("alignment") is not None:
        alignment = data["alignment"]
        if alignment not in dict(ArticlePage.CONTENT_ALIGNMENT_CHOICES):
            return JsonResponse({"error": "Invalid alignment."}, status=400)
        defaults["alignment"] = alignment

    if "box_enabled" in allowed_fields and data.get("box_enabled") is not None:
        defaults["box_enabled"] = bool(data["box_enabled"])
    if "box_border_visible" in allowed_fields and data.get("box_border_visible") is not None:
        defaults["box_border_visible"] = bool(data["box_border_visible"])
    if "list_style" in allowed_fields and data.get("list_style") is not None:
        defaults["list_style"] = bool(data["list_style"])
    if "fixed_ratio" in allowed_fields and data.get("fixed_ratio") is not None:
        defaults["fixed_ratio"] = bool(data["fixed_ratio"])

    for color_field, custom_field in (
        ("box_border_color", "box_border_custom_color"),
        ("box_bg_color", "box_bg_custom_color"),
        # unlike border/bg, "" is a real value here -- text color has no
        # fallback color of its own, "" means "leave the text color alone"
        # (see BLOCK_STYLE_DEFAULTS["heading"]["text_color"]).
        ("text_color", "text_custom_color"),
    ):
        if color_field in allowed_fields and data.get(color_field) is not None:
            color = data[color_field]
            if color and color not in dict(COLOR_CHOICES):
                return JsonResponse({"error": f"Invalid {color_field}."}, status=400)
            defaults[color_field] = color
        if custom_field in allowed_fields and data.get(custom_field) is not None:
            custom_color = data[custom_field]
            if custom_color:
                try:
                    HEX_COLOR_VALIDATOR(custom_color)
                except ValidationError:
                    return JsonResponse({"error": f"Invalid {custom_field}."}, status=400)
            defaults[custom_field] = custom_color

    ArticleBlockStyle.objects.update_or_create(
        article=page, block_id=block_id, defaults=defaults
    )

    return JsonResponse({"ok": True})


@require_POST
def save_header_style(request, page_id):
    """Save title_alignment/intro_alignment/meta_alignment/header_side_padding/
    title_font_size/intro_font_size/meta_font_size for one ArticlePage and
    publish immediately. Unlike save_block_style, these are plain ArticlePage
    fields (not StreamField content), so this is the same
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
        header_side_padding = float(data["header_side_padding"])
        title_font_size = float(data["title_font_size"])
        intro_font_size = float(data["intro_font_size"])
        meta_font_size = float(data["meta_font_size"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    valid_alignments = dict(ArticlePage.CONTENT_ALIGNMENT_CHOICES)
    for value in (title_alignment, intro_alignment, meta_alignment):
        if value not in valid_alignments:
            return JsonResponse({"error": "Invalid alignment."}, status=400)

    page.title_alignment = title_alignment
    page.intro_alignment = intro_alignment
    page.meta_alignment = meta_alignment
    page.header_side_padding = header_side_padding
    page.title_font_size = title_font_size
    page.intro_font_size = intro_font_size
    page.meta_font_size = meta_font_size
    revision = page.save_revision(user=request.user)
    revision.publish(user=request.user)

    return JsonResponse({"ok": True})


@require_POST
def save_hero_image_style(request, page_id):
    """Save hero_image_position/hero_image_width_rem/hero_image_side_padding
    for one ArticlePage and publish immediately. Same pattern as
    save_header_style -- plain ArticlePage fields, not StreamField content,
    since the hero image is a single fixed slot on the page rather than a
    body block."""
    page = get_object_or_404(ArticlePage, pk=page_id).style_target

    if not page.permissions_for_user(request.user).can_edit():
        return JsonResponse({"error": "You don't have permission to edit this page."}, status=403)

    try:
        data = json.loads(request.body)
        alignment = data["alignment"]
        width_rem = float(data["width_rem"])
        side_padding = float(data["side_padding"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    if alignment not in dict(ArticlePage.HERO_POSITION_CHOICES):
        return JsonResponse({"error": "Invalid alignment."}, status=400)

    page.hero_image_position = alignment
    page.hero_image_width_rem = width_rem
    page.hero_image_side_padding = side_padding
    revision = page.save_revision(user=request.user)
    revision.publish(user=request.user)

    return JsonResponse({"ok": True})


@require_POST
def save_toc_icon_style(request, page_id):
    """Save toc_icon_size for one ArticlePage and publish immediately. Same
    pattern as save_header_style/save_hero_image_style -- a plain
    ArticlePage field, not StreamField content or a per-block
    ArticleBlockStyle override, since there's only ever one table-of-
    contents icon on the page. Edited via its own trigger next to the icon
    itself (article_block_style.js's "toc_icon" pseudo block-type), not the
    global quick-style panel -- it used to live there, but it's specific to
    one element on the page, not a whole-article default."""
    page = get_object_or_404(ArticlePage, pk=page_id).style_target

    if not page.permissions_for_user(request.user).can_edit():
        return JsonResponse({"error": "You don't have permission to edit this page."}, status=403)

    try:
        data = json.loads(request.body)
        toc_icon_size = float(data["toc_icon_size"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    page.toc_icon_size = toc_icon_size
    revision = page.save_revision(user=request.user)
    revision.publish(user=request.user)

    return JsonResponse({"ok": True})


@require_POST
def publish_page(request, page_id):
    """Publish the latest draft revision of one ArticlePage -- lets an
    editor push a page live (or push pending draft edits live) straight
    from its own front-end URL/global style panel, instead of going
    through the Wagtail admin. Requires can_publish specifically, stricter
    than the can_edit_style/can_edit every other endpoint in this file
    checks -- Wagtail keeps edit and publish as separate permissions (see
    ArticlePage.get_context()'s can_publish_page, which gates whether the
    Publish button even renders)."""
    page = get_object_or_404(ArticlePage, pk=page_id).style_target

    if not page.permissions_for_user(request.user).can_publish():
        return JsonResponse({"error": "You don't have permission to publish this page."}, status=403)

    revision = page.get_latest_revision()
    if revision is None:
        return JsonResponse({"error": "This page has no draft to publish."}, status=400)

    revision.publish(user=request.user)

    return JsonResponse({"ok": True})
