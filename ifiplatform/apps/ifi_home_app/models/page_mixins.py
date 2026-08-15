"""Mixins shared across page model types -- named `page_mixins`, not
`article_mixins`: TranslationWarningMixin is used by event_models.py's
EventPage/EventIndexPage too, not just the article/union/tool page types.

EditorModeMixin is the shared authorization rule for on-page editor-mode
tooling (style panels, Publish/Unpublish), mixed into every page type that
exposes any of it.

Design rationale/history: docs/claude_context/article_style_and_page_mixins.md"""

from account_app.permissions import is_pending_editor
from django.utils.functional import cached_property
from wagtail_localize.models import TranslationSource

from django.db import models

from .article.constants import HEX_COLOR_VALIDATOR
from ..translation.sync import SOURCE_LANGUAGE_CODE


def _get_translation_progress(page):
    """Returns (total, translated) string-segment counts for the wagtail-localize
    Translation of `page` into its own locale, or None if there's no such record
    (e.g. it was never submitted for translation via wagtail-localize)."""
    try:
        from wagtail_localize.models import Translation
    except ImportError:
        return None
    translation = (
        Translation.objects.filter(
            source__object_id=page.translation_key,
            target_locale_id=page.locale_id,
            enabled=True,
        )
        .order_by("-created_at")
        .first()
    )
    if translation is None:
        return None
    return translation.get_progress()


def _page_needs_translation(page):
    """True if `page` itself is untranslated: either it's still an untouched
    alias auto-created by locale synchronisation (mirroring another locale's
    content rather than having its own), or a real translation that
    wagtail-localize considers incomplete. `alias_of` is unambiguous about
    which side of a locale pair is the placeholder, unlike comparing text
    between the two pages."""
    if page.alias_of_id is not None:
        return True
    progress = _get_translation_progress(page)
    return progress is not None and progress[1] < progress[0]


class TranslationWarningMixin:
    """Adds `needs_translation` to context: True if this specific page is
    untranslated (an alias placeholder, or an incomplete translation)."""

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["needs_translation"] = _page_needs_translation(self)
        return context


def editor_mode_allowed(target, user, action):
    """Wagtail's own permission for `action` against `target` (an already
    alias/locale-resolved page), AND that `user` isn't a pending editor.
    Exported (not private) so ArticlePage's publish/unpublish methods can
    reuse this against publish_target instead of duplicating it."""
    permissions = target.permissions_for_user(user)
    wagtail_allowed = getattr(permissions, f"can_{action}")()
    return wagtail_allowed and not is_pending_editor(user)


class EditorModeMixin:
    """Mixed into any Page subtype that exposes on-page editor-mode
    tooling. See docs/claude_context/article_style_and_page_mixins.md."""

    @property
    def style_target(self):
        """The page revisions/saves should actually apply to -- an alias
        page can't take its own revisions, so edits go to its source."""
        return self.alias_of.specific if self.alias_of_id else self

    def can_edit_in_editor_mode(self, user):
        return editor_mode_allowed(self.style_target, user, "edit")

    def can_sync_mirrored_page(self, user):
        """Whether `user` may push this page's synchronized fields to its
        translations right now: needs edit permission, this page must be
        the nb ("OG") copy, and it needs an existing translation to push to."""
        target = self.style_target
        if target.locale.language_code != SOURCE_LANGUAGE_CODE:
            return False
        if not editor_mode_allowed(target, user, "edit"):
            return False
        source = TranslationSource.objects.get_for_instance_or_none(target)
        return source is not None and source.translations.filter(enabled=True).exists()


class PageBannerStyle(models.Model):
    """Optional decorative banner behind a page's title. Used by
    CategoryPage and ArticleIndexPage (see BannerStyleMixin), edited
    on-page via editor mode (banner_style.js), outside Wagtail's
    revision/publish system. See
    docs/claude_context/article_style_and_page_mixins.md."""

    translation_key = models.UUIDField(unique=True)

    show_banner = models.BooleanField(default=False)
    banner_color = models.CharField(max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR])
    banner_dot_color = models.CharField(max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR])
    banner_text_color = models.CharField(max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR])

    # blank falls back to a fixed default (60/14rem in the templates) --
    # no meaningful "auto" here, unlike ArticleBlockStyle.width_rem/height_rem.
    banner_width_rem = models.FloatField(null=True, blank=True)
    banner_height_rem = models.FloatField(null=True, blank=True)
    banner_font_size = models.FloatField(null=True, blank=True)


class BannerStyleMixin:
    """Adds .banner_style (get-or-create PageBannerStyle row, keyed by this
    page's translation_key) to any Page subclass that mixes this in.
    Currently CategoryPage and ArticleIndexPage."""

    @cached_property
    def banner_style(self):
        return PageBannerStyle.objects.get_or_create(translation_key=self.translation_key)[0]
