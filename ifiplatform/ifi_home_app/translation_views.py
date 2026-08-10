"""wagtail-admin view for machine-translating an entire nb page subtree into
English in one action -- unlike wagtail-localize's own "Translate" button
(creates empty translations, one page or one subtree at a time, with no
content) and "Machine Translate" button (fills in DeepL content, but only for
whichever single page's translation editor you're currently in), this walks
`page` and every descendant, creates/updates each one's English translation,
fills it in via DeepL, and publishes it -- all from one confirm screen.

Registered as a wagtail-admin URL (see wagtail_hooks.py's register_admin_urls
hook) rather than under ifi_home_app/urls.py, so it inherits wagtail-admin's
own login/session handling the same way wagtail_localize's own views do."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from wagtail.models import Locale, Page

from wagtail_localize.machine_translators import get_machine_translator
from wagtail_localize.models import StringTranslation
from wagtail_localize.operations import TranslationCreator
from wagtail_localize.views.edit_translation import apply_machine_translation

from .deepl_glossary_terms import GLOSSARY_TERMS
from .models import GlossarySyncState
from .translation_sync import SOURCE_LANGUAGE_CODE

# The only other locale this bilingual site has -- see translation_sync.py's
# own SOURCE_LANGUAGE_CODE comment for why nb is the anchor.
TARGET_LANGUAGE_CODE = "en"


@login_required
@require_http_methods(["GET", "POST"])
def machine_translate_subtree(request, page_id):
    """GET shows a confirm screen (page + descendant count); POST runs the
    translation and redirects back to the page's edit view."""
    if not request.user.has_perms(["wagtail_localize.submit_translation"]):
        raise PermissionDenied

    page = get_object_or_404(Page, id=page_id).specific
    if page.locale.language_code != SOURCE_LANGUAGE_CODE:
        raise PermissionDenied(
            f"Only pages in the anchor locale ({SOURCE_LANGUAGE_CODE}) can be "
            "mass machine-translated."
        )

    target_locale = get_object_or_404(Locale, language_code=TARGET_LANGUAGE_CODE)
    machine_translator = get_machine_translator()
    if machine_translator is None:
        messages.error(request, "No machine translator is configured.")
        return redirect(reverse("wagtailadmin_pages:edit", args=[page.id]))

    pages = [page, *page.get_descendants()]

    if request.method == "POST":
        translated_count = _translate_and_publish_subtree(
            pages, target_locale, machine_translator, request.user
        )
        messages.success(
            request,
            f"Machine-translated and published {translated_count} page(s) into English.",
        )
        return redirect(reverse("wagtailadmin_pages:edit", args=[page.id]))

    return render(
        request,
        "translation/machine_translate_subtree_confirm.html",
        {"page": page, "descendant_count": len(pages) - 1},
    )


@transaction.atomic
def _translate_and_publish_subtree(pages, target_locale, machine_translator, user):
    """Creates/updates an English translation for every page in `pages`,
    fills each one in via `machine_translator`, and publishes it -- matching
    the live status of its nb source page, same as
    WAGTAILLOCALIZE_SYNC_LIVE_STATUS_ON_TRANSLATE's own default behaviour."""
    creator = TranslationCreator(user, [target_locale])
    for page in pages:
        creator.create_translations(page)

    translated_count = 0
    for source, translations in creator.mappings.items():
        publish = source.get_source_instance().live
        for translation in translations:
            _clear_stale_glossary_translations(translation)
            apply_machine_translation(translation.id, user, machine_translator)
            translation.save_target(user=user, publish=publish)
            translated_count += 1
    return translated_count


def _clear_stale_glossary_translations(translation):
    """apply_machine_translation() skips any segment that already has a
    StringTranslation, which is normally right -- an unchanged nb sentence
    keeps its existing machine translation instead of burning DeepL quota
    re-translating something that would come back identical (segments are
    content-addressed by wagtail-localize, so a sentence that DID change on
    the nb side already gets a fresh segment and isn't affected by any of
    this).

    The one case that skip is wrong for: a sentence containing a glossary
    term (see deepl_glossary_terms.py), translated *before* the glossary
    last changed -- DeepL would now translate it differently. Delete just
    those specific, still-stale, machine-made translations so
    apply_machine_translation() re-does them; everything else (including
    any human-corrected translation, regardless of glossary terms) is left
    untouched."""
    synced_at = GlossarySyncState.last_synced_at()
    if synced_at is None or not GLOSSARY_TERMS:
        return

    # Case-insensitive to match DeepL's own glossary matching (confirmed
    # empirically: "Fadderuke"/"fadderuke"/"FADDERUKE" in source text all
    # get matched and normalised to the glossary's defined casing).
    lower_terms = [term.lower() for term in GLOSSARY_TERMS]
    affected = [
        (segment.string_id, segment.context_id)
        for segment in translation.source.stringsegment_set.select_related("string")
        if any(term in segment.string.data.lower() for term in lower_terms)
    ]
    if not affected:
        return

    pair_filter = Q()
    for string_id, context_id in affected:
        pair_filter |= Q(translation_of_id=string_id, context_id=context_id)

    StringTranslation.objects.filter(
        pair_filter,
        locale=translation.target_locale,
        translation_type=StringTranslation.TRANSLATION_TYPE_MACHINE,
        updated_at__lt=synced_at,
    ).delete()
