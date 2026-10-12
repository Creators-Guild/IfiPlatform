"""Site-wide wagtail hooks for ifi_home_app.

The English editor (its URL, the "English" buttons on pages and snippets,
the read-only "Stored English" list -- see translation/english_editor.py),
the translate-now nudges (see translation/nudge.py), the translated
snippets' registration, and hiding what's left of wagtail-localize's admin
-- add further hooks here rather than starting new files, unless a hook is
specific enough to a single feature area to warrant its own module."""

from django.urls import path
from wagtail import hooks
from wagtail.snippets.models import register_snippet

from .models import HeaderMessage, HomeBoardMessage, MenuGroup
from .translation import english_editor, nudge


@hooks.register("register_admin_urls")
def register_admin_urls():
    return [
        path(
            "english/<int:content_type_id>/<int:object_id>/",
            english_editor.edit,
            name="english_editor",
        ),
        path(
            "english/subtree/<int:page_id>/",
            english_editor.machine_translate_subtree,
            name="english_machine_translate_subtree",
        ),
        path(
            "english/menu/<int:menu_id>/",
            english_editor.machine_translate_menu,
            name="english_machine_translate_menu",
        ),
    ]


@hooks.register("register_admin_viewset")
def register_stored_english_viewset():
    return english_editor.StoredEnglishViewSet("stored_english")


hooks.register("register_page_header_buttons", english_editor.page_button)
hooks.register("register_page_listing_more_buttons", english_editor.page_button)
hooks.register("register_page_header_buttons", english_editor.subtree_button)
hooks.register("register_page_listing_more_buttons", english_editor.subtree_button)
hooks.register("register_snippet_listing_buttons", english_editor.snippet_button)

for _snippet_model in (HeaderMessage, HomeBoardMessage, MenuGroup):
    register_snippet(_snippet_model)

hooks.register("after_publish_page", nudge.warn_after_publish)
hooks.register("before_edit_page", nudge.warn_on_edit)
hooks.register("construct_homepage_panels", nudge.add_dashboard_panel)
hooks.register("register_page_listing_buttons", nudge.listing_status_button)


@hooks.register("construct_reports_menu")
def hide_wagtail_localize_report(request, menu_items):
    """wagtail-localize stays installed only for translation/page_segments.py;
    its "Translations" report has nothing to show. Its other buttons hide
    themselves: they need a second locale or translation records, and the
    switch-over removed both."""
    menu_items[:] = [item for item in menu_items if item.name != "translations"]
