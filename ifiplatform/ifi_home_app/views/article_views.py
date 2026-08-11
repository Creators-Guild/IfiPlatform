"""API endpoints backing the on-page style panels on article pages
(padding/alignment/font size) -- see article_quick_style.js/
article_block_style.js and ArticlePage.get_context()'s can_edit_style in
article_models.py."""

import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from wagtail.models import Locale, Page

from ifi_home_app.models.article_models import (
    BOX_COLOR_CHOICES,
    COLOR_CHOICES,
    CONTENT_ALIGNMENT_CHOICES,
    HERO_POSITION_CHOICES,
    HEX_COLOR_VALIDATOR,
    ArticleBlockStyle,
    ArticlePage,
    PageBannerStyle,
    alignment_capable_block_ids,
)
from ifi_home_app.translation_sync import sync_synchronized_fields

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
    "box_shadow_enabled",
    "box_shadow_strength",
    "box_shadow_color",
    "box_shadow_custom_color",
}

# not box_* -- applies independent of whether a block's box is enabled (see
# _effective_heading_style() in article_models.py), available wherever
# font_size is (or, for title/meta/intro, wherever their own box is). Text
# shadow rides along in this same set (not its own constant) since it's
# offered everywhere text_color already is, no exceptions -- same reasoning
# as BOX_FIELDS above already mixing box_enabled/box_padding/box_shadow_*
# together instead of splitting shadow out on its own.
TEXT_COLOR_FIELDS = {
    "text_color",
    "text_custom_color",
    "text_shadow_enabled",
    "text_shadow_strength",
    "text_shadow_color",
    "text_shadow_custom_color",
}

# alignment-capable types only -- see ArticleBlockStyle.
# exclude_from_global_alignment and save_quick_style's bulk-overwrite.
EXCLUDE_FROM_GLOBAL_ALIGNMENT_FIELD = {"exclude_from_global_alignment"}

BLOCK_STYLE_FIELDS = {
    "heading": {"side_padding", "alignment", "font_size"}
    | BOX_FIELDS
    | TEXT_COLOR_FIELDS
    | EXCLUDE_FROM_GLOBAL_ALIGNMENT_FIELD,
    "paragraph": {"side_padding", "alignment", "font_size"}
    | BOX_FIELDS
    | TEXT_COLOR_FIELDS
    | EXCLUDE_FROM_GLOBAL_ALIGNMENT_FIELD,
    "image": {"alignment", "width_rem", "side_padding"} | BOX_FIELDS | EXCLUDE_FROM_GLOBAL_ALIGNMENT_FIELD,
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
    "image_title": {"side_padding", "alignment", "font_size"}
    | TEXT_COLOR_FIELDS
    | EXCLUDE_FROM_GLOBAL_ALIGNMENT_FIELD,
    "image_caption_body": {"side_padding", "alignment", "font_size"}
    | TEXT_COLOR_FIELDS
    | EXCLUDE_FROM_GLOBAL_ALIGNMENT_FIELD,
    "multi_column": {"side_padding", "gap", "column_weights"} | BOX_FIELDS,
    "column": {"side_padding"} | BOX_FIELDS,
    # a multi_column column's own title -- alignment/font-size/text-color
    # only (no box or side padding of its own -- it's edited from the same
    # trigger/panel as its column, see FIELDS_BY_TYPE.column in
    # article_block_style.js, which sends this as a second, independent
    # save request alongside the column's own box fields), keyed by a
    # synthesized "<column-uuid>-title" id (see _effective_block_styles()
    # in article_models.py).
    "column_title": {"alignment", "font_size"} | TEXT_COLOR_FIELDS | EXCLUDE_FROM_GLOBAL_ALIGNMENT_FIELD,
    # title/meta/intro (the article-header group), keyed by fixed pseudo
    # ids ("article-title"/"article-meta"/"article-intro", see
    # ArticlePage.get_context()). Alignment/font-size themselves still live
    # on dedicated ArticlePage fields, edited via save_header_style instead
    # (see article_block_style.js's own recordPendingEdit) -- side padding/
    # box/text color/the "lock alignment" opt-out are saved as
    # ArticleBlockStyle rows for them, same as every other alignment-capable
    # block type, so save_quick_style's global-alignment bulk-overwrite can
    # respect it via the exact same exclude_from_global_alignment query.
    "title": {"side_padding"} | BOX_FIELDS | TEXT_COLOR_FIELDS | EXCLUDE_FROM_GLOBAL_ALIGNMENT_FIELD,
    "meta": {"side_padding"} | BOX_FIELDS | TEXT_COLOR_FIELDS | EXCLUDE_FROM_GLOBAL_ALIGNMENT_FIELD,
    "intro": {"side_padding"} | BOX_FIELDS | TEXT_COLOR_FIELDS | EXCLUDE_FROM_GLOBAL_ALIGNMENT_FIELD,
    # the title/meta/intro group as a whole, keyed by the fixed pseudo id
    # "article-header" -- box only (side padding is a plain ArticlePage
    # field like alignment/font-size, saved via save_header_style instead).
    "article_header": set(BOX_FIELDS),
}


@require_POST
def save_quick_style(request, page_id):
    """Save content_side_padding/content_alignment/
    content_font_size_multiplier/content_bg_enabled/content_bg_color/
    content_bg_custom_color -- a plain upsert onto the page's shared
    ArticleStyle row (see ArticlePage.style), same pattern as
    save_block_style. Not Wagtail revision/publish at all any more
    (ArticleStyle isn't a Page field) -- live immediately, same as it
    always was, just without the redundant revision this used to create
    for what's really a styling tweak.

    apply_alignment_to_blocks (optional, default False) is the one
    destructive exception: when true (the JS only ever sends this after
    the editor confirmed a warning dialog, see article_quick_style.js),
    this ALSO overwrites the `alignment` field on every alignment-capable
    ArticleBlockStyle row for this article (creating rows that don't exist
    yet), except any block individually opted out via its own
    exclude_from_global_alignment flag -- see alignment_capable_block_ids()
    in article_models.py -- AND the title/meta/intro header group's own
    title_alignment/meta_alignment/intro_alignment ArticleStyle fields,
    same exclude_from_global_alignment opt-out (checked directly on their
    own "article-title"/"article-meta"/"article-intro" ArticleBlockStyle
    rows, the same rows their own side padding/box/lock-alignment checkbox
    already save to -- see BLOCK_STYLE_FIELDS above), since those three
    aren't part of page.body at all so alignment_capable_block_ids() can
    never see them. content_font_size_multiplier, in contrast, never
    touches ArticleBlockStyle at all -- it's applied purely at render time
    (see _effective_heading_style's display_font_size)."""
    page = get_object_or_404(ArticlePage, pk=page_id).style_target

    if not page.can_edit_in_editor_mode(request.user):
        return JsonResponse({"error": "You don't have permission to edit this page."}, status=403)

    try:
        data = json.loads(request.body)
        side_padding = float(data["content_side_padding"])
        alignment = data["content_alignment"]
        font_size_multiplier = float(data["content_font_size_multiplier"])
        bg_enabled = bool(data["content_bg_enabled"])
        bg_color = data["content_bg_color"]
        bg_custom_color = data.get("content_bg_custom_color") or ""
        apply_alignment_to_blocks = bool(data.get("apply_alignment_to_blocks"))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    if alignment not in dict(CONTENT_ALIGNMENT_CHOICES):
        return JsonResponse({"error": "Invalid alignment."}, status=400)

    if not 0.5 <= font_size_multiplier <= 2:
        return JsonResponse({"error": "Invalid content_font_size_multiplier."}, status=400)

    if bg_color not in dict(COLOR_CHOICES):
        return JsonResponse({"error": "Invalid content_bg_color."}, status=400)

    if bg_custom_color:
        try:
            HEX_COLOR_VALIDATOR(bg_custom_color)
        except ValidationError:
            return JsonResponse({"error": "Invalid content_bg_custom_color."}, status=400)

    style = page.style
    style.content_side_padding = side_padding
    style.content_alignment = alignment
    style.content_font_size_multiplier = font_size_multiplier
    style.content_bg_enabled = bg_enabled
    style.content_bg_color = bg_color
    style.content_bg_custom_color = bg_custom_color
    style.save()

    if apply_alignment_to_blocks:
        excluded_ids = set(
            ArticleBlockStyle.objects.filter(
                translation_key=page.translation_key, exclude_from_global_alignment=True
            ).values_list("block_id", flat=True)
        )
        block_ids = [
            block_id for block_id in alignment_capable_block_ids(page.body) if block_id not in excluded_ids
        ]
        ArticleBlockStyle.objects.bulk_create(
            [
                ArticleBlockStyle(translation_key=page.translation_key, block_id=block_id, alignment=alignment)
                for block_id in block_ids
            ],
            update_conflicts=True,
            unique_fields=["translation_key", "block_id"],
            update_fields=["alignment"],
        )

        header_alignment_fields = {
            "article-title": "title_alignment",
            "article-meta": "meta_alignment",
            "article-intro": "intro_alignment",
        }
        style_changed = False
        for header_block_id, style_field in header_alignment_fields.items():
            if header_block_id not in excluded_ids:
                setattr(style, style_field, alignment)
                style_changed = True
        if style_changed:
            style.save()

    return JsonResponse({"ok": True})


@require_POST
def save_block_style(request, page_id):
    """Save a single block's style override (ArticleBlockStyle) -- a plain
    upsert, deliberately outside Wagtail's StreamField/revision/publish
    system entirely (see ArticleBlockStyle's docstring in article_models.py
    for why). Live immediately, same as save_quick_style, no draft step."""
    page = get_object_or_404(ArticlePage, pk=page_id).style_target

    if not page.can_edit_in_editor_mode(request.user):
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
        if "box_shadow_strength" in allowed_fields and data.get("box_shadow_strength") is not None:
            defaults["box_shadow_strength"] = float(data["box_shadow_strength"])
        if "text_shadow_strength" in allowed_fields and data.get("text_shadow_strength") is not None:
            defaults["text_shadow_strength"] = float(data["text_shadow_strength"])
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    # matches the on-page slider's own range (article_block_style_mini_panel.
    # html, #block-style-width/#block-style-height) -- nothing stops a direct
    # POST to this endpoint from setting an arbitrary value otherwise, and an
    # oversized width/height here is exactly the kind of editor-set value the
    # mobile CSS resets (article_multicolumn.css et al) can't fully undo.
    for field_name, bounds in (
        ("width_rem", (4, 60)),
        ("height_rem", (0, 40)),
        ("box_shadow_strength", (0, 3)),
        ("text_shadow_strength", (0, 3)),
    ):
        value = defaults.get(field_name)
        if value is not None and not bounds[0] <= value <= bounds[1]:
            return JsonResponse({"error": f"Invalid {field_name}."}, status=400)

    if "alignment" in allowed_fields and data.get("alignment") is not None:
        alignment = data["alignment"]
        if alignment not in dict(CONTENT_ALIGNMENT_CHOICES):
            return JsonResponse({"error": "Invalid alignment."}, status=400)
        defaults["alignment"] = alignment

    if "box_enabled" in allowed_fields and data.get("box_enabled") is not None:
        defaults["box_enabled"] = bool(data["box_enabled"])
    if "box_border_visible" in allowed_fields and data.get("box_border_visible") is not None:
        defaults["box_border_visible"] = bool(data["box_border_visible"])
    if "box_shadow_enabled" in allowed_fields and data.get("box_shadow_enabled") is not None:
        defaults["box_shadow_enabled"] = bool(data["box_shadow_enabled"])
    if "text_shadow_enabled" in allowed_fields and data.get("text_shadow_enabled") is not None:
        defaults["text_shadow_enabled"] = bool(data["text_shadow_enabled"])
    if "list_style" in allowed_fields and data.get("list_style") is not None:
        defaults["list_style"] = bool(data["list_style"])
    if "fixed_ratio" in allowed_fields and data.get("fixed_ratio") is not None:
        defaults["fixed_ratio"] = bool(data["fixed_ratio"])
    if "exclude_from_global_alignment" in allowed_fields and data.get("exclude_from_global_alignment") is not None:
        defaults["exclude_from_global_alignment"] = bool(data["exclude_from_global_alignment"])

    for color_field, custom_field in (
        ("box_border_color", "box_border_custom_color"),
        ("box_bg_color", "box_bg_custom_color"),
        # unlike border/bg, "" is a real value here -- text color has no
        # fallback color of its own, "" means "leave the text color alone"
        # (see BLOCK_STYLE_DEFAULTS["heading"]["text_color"]).
        ("text_color", "text_custom_color"),
        # same blank-is-real-state reasoning as text_color above -- "" means
        # "keep using the theme's own shadow color" (see BLOCK_STYLE_
        # DEFAULTS["box"]["shadow_color"]).
        ("box_shadow_color", "box_shadow_custom_color"),
        ("text_shadow_color", "text_shadow_custom_color"),
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
        translation_key=page.translation_key, block_id=block_id, defaults=defaults
    )

    return JsonResponse({"ok": True})


@require_POST
def save_header_style(request, page_id):
    """Save title_alignment/intro_alignment/meta_alignment/header_side_padding/
    title_font_size/intro_font_size/meta_font_size -- a plain upsert onto
    the page's shared ArticleStyle row, same pattern as save_quick_style."""
    page = get_object_or_404(ArticlePage, pk=page_id).style_target

    if not page.can_edit_in_editor_mode(request.user):
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

    valid_alignments = dict(CONTENT_ALIGNMENT_CHOICES)
    for value in (title_alignment, intro_alignment, meta_alignment):
        if value not in valid_alignments:
            return JsonResponse({"error": "Invalid alignment."}, status=400)

    style = page.style
    style.title_alignment = title_alignment
    style.intro_alignment = intro_alignment
    style.meta_alignment = meta_alignment
    style.header_side_padding = header_side_padding
    style.title_font_size = title_font_size
    style.intro_font_size = intro_font_size
    style.meta_font_size = meta_font_size
    style.save()

    return JsonResponse({"ok": True})


@require_POST
def save_hero_image_style(request, page_id):
    """Save hero_image_position/hero_image_width_rem/hero_image_side_padding
    plus the box fields (hero_image_boxed/hero_image_box_color/
    hero_image_box_custom_color/hero_image_box_border_radius/hero_image_box_
    shadow_enabled/hero_image_box_shadow_strength/hero_image_box_shadow_color/
    hero_image_box_shadow_custom_color, formerly Wagtail-admin-only fields,
    now on-page like everything else) -- a plain upsert onto the page's
    shared ArticleStyle row, same pattern as save_quick_style."""
    page = get_object_or_404(ArticlePage, pk=page_id).style_target

    if not page.can_edit_in_editor_mode(request.user):
        return JsonResponse({"error": "You don't have permission to edit this page."}, status=403)

    try:
        data = json.loads(request.body)
        alignment = data["alignment"]
        width_rem = float(data["width_rem"])
        side_padding = float(data["side_padding"])
        boxed = bool(data["boxed"])
        box_color = data["box_color"]
        box_custom_color = data.get("box_custom_color") or ""
        box_border_radius = float(data["box_border_radius"])
        shadow_enabled = bool(data["shadow_enabled"])
        shadow_strength = float(data["shadow_strength"])
        # blank is a real value here, same as box_color/box_custom_color
        # above never being blank vs. text/box-shadow colors elsewhere in
        # this codebase that can be -- see ArticleStyle.hero_image_box_
        # shadow_color's own docstring on why blank means "theme default".
        shadow_color = data.get("shadow_color") or ""
        shadow_custom_color = data.get("shadow_custom_color") or ""
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    if alignment not in dict(HERO_POSITION_CHOICES):
        return JsonResponse({"error": "Invalid alignment."}, status=400)

    if not 4 <= width_rem <= 60:
        return JsonResponse({"error": "Invalid width_rem."}, status=400)

    if box_color not in dict(BOX_COLOR_CHOICES):
        return JsonResponse({"error": "Invalid box_color."}, status=400)

    if box_custom_color:
        try:
            HEX_COLOR_VALIDATOR(box_custom_color)
        except ValidationError:
            return JsonResponse({"error": "Invalid box_custom_color."}, status=400)

    if not 0 <= box_border_radius <= 5:
        return JsonResponse({"error": "Invalid box_border_radius."}, status=400)

    if not 0 <= shadow_strength <= 3:
        return JsonResponse({"error": "Invalid shadow_strength."}, status=400)

    if shadow_color and shadow_color not in dict(BOX_COLOR_CHOICES):
        return JsonResponse({"error": "Invalid shadow_color."}, status=400)

    if shadow_custom_color:
        try:
            HEX_COLOR_VALIDATOR(shadow_custom_color)
        except ValidationError:
            return JsonResponse({"error": "Invalid shadow_custom_color."}, status=400)

    style = page.style
    style.hero_image_position = alignment
    style.hero_image_width_rem = width_rem
    style.hero_image_side_padding = side_padding
    style.hero_image_boxed = boxed
    style.hero_image_box_color = box_color
    style.hero_image_box_custom_color = box_custom_color
    style.hero_image_box_border_radius = box_border_radius
    style.hero_image_box_shadow_enabled = shadow_enabled
    style.hero_image_box_shadow_strength = shadow_strength
    style.hero_image_box_shadow_color = shadow_color
    style.hero_image_box_shadow_custom_color = shadow_custom_color
    style.save()

    return JsonResponse({"ok": True})


@require_POST
def save_toc_icon_style(request, page_id):
    """Save toc_icon_size -- a plain upsert onto the page's shared
    ArticleStyle row, same pattern as save_quick_style. There's only ever
    one table-of-contents icon on the page, edited via its own trigger
    next to the icon itself (article_block_style.js's "toc_icon" pseudo
    block-type), not the global quick-style panel -- it used to live
    there, but it's specific to one element on the page, not a
    whole-article default."""
    page = get_object_or_404(ArticlePage, pk=page_id).style_target

    if not page.can_edit_in_editor_mode(request.user):
        return JsonResponse({"error": "You don't have permission to edit this page."}, status=403)

    try:
        data = json.loads(request.body)
        toc_icon_size = float(data["toc_icon_size"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    style = page.style
    style.toc_icon_size = toc_icon_size
    style.save()

    return JsonResponse({"ok": True})


def _translation_to_sync(nb_page):
    """The real (independently-authored) en translation of nb_page, if one
    exists -- an *alias* translation doesn't need any of this, Wagtail
    already keeps those in sync with their source automatically on both
    publish and unpublish (see PublishPageRevisionAction/UnpublishPageAction
    in wagtail's own source). Only called with nb_page already resolved to
    the nb locale (see ArticlePage.publish_target), so this only ever needs
    to look one direction: nb -> en."""
    if nb_page.locale.language_code != ArticlePage.SOURCE_LANGUAGE_CODE:
        return None
    en_locale = Locale.objects.exclude(
        language_code=ArticlePage.SOURCE_LANGUAGE_CODE
    ).first()
    if en_locale is None:
        return None
    translation = nb_page.get_translation_or_none(en_locale)
    if translation is None or translation.alias_of_id:
        return None
    return translation


@require_POST
def publish_page(request, page_id):
    """Publish the latest draft revision of one ArticlePage -- lets an
    editor push a page live (or push pending draft edits live) straight
    from its own front-end URL/global style panel, instead of going
    through the Wagtail admin. Always acts on the nb ("OG") copy
    regardless of which locale you're actually looking at (see
    ArticlePage.publish_target), then publishes the en translation's own
    latest revision too if one exists, so the two don't drift apart --
    nb is the source of truth, en always follows it. Requires can_publish
    on that nb copy specifically, stricter than the can_edit_style/can_edit
    every other endpoint in this file checks (see ArticlePage.get_context()'s
    can_publish_page, which gates whether the Publish button even renders).

    Also pushes wagtail-localize's synchronized fields (show_in_menu,
    status, etc.) to the translation, same as wagtail_hooks.py's
    after_publish_page hook does for a normal wagtail-admin publish -- this
    view calls Revision.publish() directly rather than going through
    wagtail-admin's edit view, so that hook never fires for it, and synced
    fields would otherwise silently stop propagating for anything published
    this way (see translation_sync.py)."""
    page = get_object_or_404(ArticlePage, pk=page_id).publish_target

    if not page.can_publish_in_editor_mode(request.user):
        return JsonResponse({"error": "You don't have permission to publish this page."}, status=403)

    revision = page.get_latest_revision()
    if revision is None:
        return JsonResponse({"error": "This page has no draft to publish."}, status=400)

    revision.publish(user=request.user)

    translation = _translation_to_sync(page)
    if translation is not None:
        translation_revision = translation.get_latest_revision()
        if translation_revision is not None:
            # skip_permission_checks -- the editor's own permission was
            # already verified above, against the nb copy specifically
            # (see can_publish_page's own docstring for why); this is a
            # system-triggered side effect of that action, not a
            # separate action of its own the editor needs permission for.
            translation_revision.publish(user=request.user, skip_permission_checks=True)

    # Runs last so a freshly-synced field value always wins over whatever
    # the translation_revision.publish() above just put live (that revision
    # is whichever draft a translator was last working on, unrelated to
    # synchronized-field freshness).
    sync_synchronized_fields(page, user=request.user)

    return JsonResponse({"ok": True})


@require_POST
def unpublish_page(request, page_id):
    """Unpublish one ArticlePage -- same nb-first, sync-en-after pattern as
    publish_page above, and the same reasoning for why can_unpublish is
    checked on the nb copy specifically (see ArticlePage.get_context()'s
    can_unpublish_page)."""
    page = get_object_or_404(ArticlePage, pk=page_id).publish_target

    if not page.can_unpublish_in_editor_mode(request.user):
        return JsonResponse({"error": "You don't have permission to unpublish this page."}, status=403)

    page.unpublish(user=request.user)

    translation = _translation_to_sync(page)
    if translation is not None and translation.live:
        # Page.unpublish() has no skip_permission_checks of its own (unlike
        # Revision.publish() above) -- omitting user here is what actually
        # skips the internal permission check (see UnpublishAction.check()
        # in wagtail/actions/unpublish.py: it only checks when self.user is
        # set), same "already verified against nb, this is just a synced
        # side effect" reasoning as the publish side.
        translation.unpublish(log_action=True)

    return JsonResponse({"ok": True})


@require_POST
def sync_mirrored_page(request, page_id):
    """Manually push this page's wagtail-localize synchronized fields
    (show_in_menu, status, etc.) out to its translation right now --
    "Sync mirrored page" in editor mode. Not ArticlePage-specific (unlike
    publish_page/unpublish_page above): CategoryPage/ArticleIndexPage/
    StudentUnionCategoryPage have no publish concept in editor mode at all,
    but they do have synchronized fields (show_in_menu) that can still drift,
    so this is a plain Page lookup resolved through style_target rather than
    ArticlePage's own publish_target. Gated by can_sync_mirrored_page, which
    already confirms the page is the nb ("OG") copy and there's an existing
    translation to sync (see EditorModeMixin.can_sync_mirrored_page)."""
    page = get_object_or_404(Page, pk=page_id).specific.style_target

    if not page.can_sync_mirrored_page(request.user):
        return JsonResponse(
            {"error": "You don't have permission to sync this page, or there's nothing to sync."},
            status=403,
        )

    sync_synchronized_fields(page, user=request.user)

    return JsonResponse({"ok": True})


@require_POST
def save_banner_style(request, page_id):
    """Save show_banner/banner_color/banner_dot_color/banner_text_color/
    banner_width_rem/banner_height_rem/banner_font_size -- a plain upsert
    onto the page's shared PageBannerStyle row (see BannerStyleMixin.
    banner_style in article_models.py), same pattern as save_quick_style.
    Not ArticlePage-specific -- looks up the plain Wagtail Page then
    resolves it to its specific subtype's own style_target (EditorModeMixin
    -- see that module for why this alias-resolution step matters), since
    CategoryPage, ArticleIndexPage and StudentUnionCategoryPage all use
    this same endpoint via BannerStyleMixin."""
    page = get_object_or_404(Page, pk=page_id).specific.style_target

    if not page.can_edit_in_editor_mode(request.user):
        return JsonResponse({"error": "You don't have permission to edit this page."}, status=403)

    try:
        data = json.loads(request.body)
        show_banner = bool(data["show_banner"])
        banner_color = data.get("banner_color") or ""
        banner_dot_color = data.get("banner_dot_color") or ""
        banner_text_color = data.get("banner_text_color") or ""
        # blank/0 both mean "auto" (see PageBannerStyle.banner_width_rem's
        # own comment) -- None is stored either way here, no real field
        # to preserve a distinction between them for.
        width_rem = float(data["banner_width_rem"]) if data.get("banner_width_rem") else None
        height_rem = float(data["banner_height_rem"]) if data.get("banner_height_rem") else None
        font_size = float(data["banner_font_size"]) if data.get("banner_font_size") else None
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data."}, status=400)

    for value, field_name in (
        (banner_color, "banner_color"),
        (banner_dot_color, "banner_dot_color"),
        (banner_text_color, "banner_text_color"),
    ):
        if value:
            try:
                HEX_COLOR_VALIDATOR(value)
            except ValidationError:
                return JsonResponse({"error": f"Invalid {field_name}."}, status=400)

    for value, field_name, bounds in (
        (width_rem, "banner_width_rem", (1, 100)),
        (height_rem, "banner_height_rem", (1, 60)),
        (font_size, "banner_font_size", (0.5, 6)),
    ):
        if value is not None and not bounds[0] <= value <= bounds[1]:
            return JsonResponse({"error": f"Invalid {field_name}."}, status=400)

    style = PageBannerStyle.objects.get_or_create(translation_key=page.translation_key)[0]
    style.show_banner = show_banner
    style.banner_color = banner_color
    style.banner_dot_color = banner_dot_color
    style.banner_text_color = banner_text_color
    style.banner_width_rem = width_rem
    style.banner_height_rem = height_rem
    style.banner_font_size = font_size
    style.save()

    return JsonResponse({"ok": True})
