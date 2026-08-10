"""Site-wide wagtail hooks for ifi_home_app.

Currently just the nb -> en synchronized-field auto-sync (see the function
docstring below) -- add further hooks here rather than starting new files,
unless a hook is specific enough to a single feature area to warrant its own
module."""

from wagtail import hooks

from .translation_sync import SOURCE_LANGUAGE_CODE, sync_synchronized_fields


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
