"""Site-wide wagtail hooks for ifi_home_app.

The nb -> en synchronized-field auto-sync (see the function docstring below)
plus the "Machine-translate subtree" admin button/URL (see
translation/views.py) -- add further hooks here rather than starting new
files, unless a hook is specific enough to a single feature area to warrant
its own module."""

from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.widgets.button import Button
from wagtail_localize.machine_translators import get_machine_translator

from .translation import views as translation_views
from .translation.sync import SOURCE_LANGUAGE_CODE, sync_synchronized_fields


@hooks.register("register_admin_urls")
def register_admin_urls():
    return [
        path(
            "machine-translate-subtree/<int:page_id>/",
            translation_views.machine_translate_subtree,
            name="machine_translate_subtree",
        ),
    ]


def _machine_translate_subtree_button(page, user, view_name=None, next_url=None):
    """Shown on nb pages with descendants -- see translation/views.py."""
    if (
        page.is_root()
        or page.locale.language_code != SOURCE_LANGUAGE_CODE
        or not page.get_descendants().exists()
        or not user.has_perm("wagtail_localize.submit_translation")
    ):
        return

    if get_machine_translator() is None:
        return

    yield Button(
        "Machine-translate subtree",
        reverse("machine_translate_subtree", args=[page.id]),
        priority=61,
        icon_name="doc-empty-inverse",
    )


hooks.register("register_page_header_buttons", _machine_translate_subtree_button)
hooks.register(
    "register_page_listing_more_buttons", _machine_translate_subtree_button
)


@hooks.register("after_publish_page")
def sync_synchronized_fields_to_translations(request, page):
    """On every nb page publish through wagtail-admin, push its
    wagtail-localize SynchronizedFields (show_in_menu, status, etc.) out to
    every enabled translation, so they don't silently drift (see
    translation/sync.py). Doesn't cover publishes that bypass wagtail-admin
    (article_views.publish_page, sync_mirrored_page) -- those call
    sync_synchronized_fields directly instead, since this hook only fires
    from wagtail-admin's own edit view."""
    page = page.specific
    if page.locale.language_code != SOURCE_LANGUAGE_CODE:
        return
    sync_synchronized_fields(page, user=request.user)
