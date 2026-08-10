"""Site-wide wagtail hooks for ifi_home_app.

The nb -> en synchronized-field auto-sync (see the function docstring below)
plus the "Machine-translate subtree" admin button/URL (see
translation_views.py) -- add further hooks here rather than starting new
files, unless a hook is specific enough to a single feature area to warrant
its own module."""

from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.widgets.button import Button
from wagtail_localize.machine_translators import get_machine_translator

from . import translation_views
from .translation_sync import SOURCE_LANGUAGE_CODE, sync_synchronized_fields


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
    """Shown on nb pages with descendants -- see translation_views.py."""
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
    """Whenever an nb page with existing translations is published, push its
    wagtail-localize SynchronizedFields (show_in_menu, status, and any other
    plain non-text field wagtail-localize auto-classifies as synchronized --
    see get_translatable_fields()) out to every enabled translation, so they
    never silently drift the way UnionPage.show_in_menu did (nb toggled it,
    English never picked it up because nothing triggered wagtail-localize's
    sync outside its own manual "Sync translated pages" admin action).
    See translation_sync.py for the shared implementation (also used by the
    "Sync mirrored page" editor-mode button and publish_page, since both of
    those bypass this hook entirely -- they publish directly via
    Revision.publish() rather than through wagtail-admin's edit view, which
    is the only place after_publish_page actually gets fired from)."""
    page = page.specific
    if page.locale.language_code != SOURCE_LANGUAGE_CODE:
        return
    sync_synchronized_fields(page, user=request.user)
