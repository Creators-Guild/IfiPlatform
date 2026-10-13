# pylint: disable=C0114,C0115,C0116
"""The one-time switch from two page trees to one Norwegian tree with
stored English -- see docs/claude_references/translation_redesign.md
("Migration") and docs/claude_context/translation_overlay.md."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Locale, Page, Site
from wagtail_localize.models import StringTranslation
from wagtail_localize.operations import TranslationCreator

from ifi_home_app.models import (
    ArticleIndexPage,
    ArticlePage,
    EnglishSlug,
    HeaderMessage,
    MenuGroup,
    SegmentTranslation,
)
from ifi_home_app.translation.english_overlay import english


def _translate_tree(page, locale, user):
    """The old two-tree setup: a published English copy of page and its
    descendants, every piece "machine-translated" as "[EN] <Norwegian>"."""
    creator = TranslationCreator(user, [locale])
    for p in [page, *page.get_descendants()]:
        creator.create_translations(p)
    for source, translations in creator.mappings.items():
        for segment in source.stringsegment_set.select_related("string"):
            StringTranslation.objects.get_or_create(
                translation_of=segment.string,
                locale=locale,
                context_id=segment.context_id,
                defaults={
                    "data": f"[EN] {segment.string.data}",
                    "translation_type": StringTranslation.TRANSLATION_TYPE_MACHINE,
                },
            )
        for translation in translations:
            translation.save_target(
                user=user, publish=source.get_source_instance().live
            )


class SwitchTests(TestCase):
    def setUp(self):
        self.nb, _ = Locale.objects.get_or_create(language_code="nb")
        self.en, _ = Locale.objects.get_or_create(language_code="en")
        self.user = get_user_model().objects.create_superuser(
            "kari", "k@test.com", "pw"
        )
        root = Page.get_first_root_node()
        self.index = ArticleIndexPage(
            locale=self.nb, title="Artikler", slug="artikler", section="info_articles"
        )
        root.add_child(instance=self.index)
        self.index.save_revision().publish()
        site = Site.objects.get(is_default_site=True)
        site.root_page = self.index
        site.save()
        self.article = self._article("Fadderuke", "fadderuke")
        _translate_tree(self.index, self.en, self.user)
        self.en_index = self.index.get_translation(self.en)
        self.en_article = self.article.get_translation(self.en)

    def _article(self, title, slug, parent=None, locale=None):
        page = ArticlePage(
            locale=locale or self.nb,
            title=title,
            slug=slug,
            published_date=timezone.now().date(),
            intro="<p>Velkommen.</p>",
            body=[("heading", {"text": "Program", "level": "h2"})],
        )
        (parent or self.index).add_child(instance=page)
        page.save_revision().publish()
        return page

    def run_switch(self, *args):
        out = StringIO()
        call_command("switch_to_english_overlay", *args, stdout=out)
        return out.getvalue()


class DryRunTests(SwitchTests):
    def test_dry_run_changes_nothing(self):
        report = self.run_switch()
        self.assertIn("Dry run: nothing was changed", report)
        self.assertTrue(Locale.objects.filter(language_code="en").exists())
        self.assertTrue(Page.objects.filter(pk=self.en_article.pk).exists())
        self.assertFalse(SegmentTranslation.objects.exists())


class ApplyTests(SwitchTests):
    def test_copies_english_and_removes_the_english_tree(self):
        nb_pages = Page.objects.filter(locale=self.nb, depth__gt=1).count()
        report = self.run_switch("--apply")
        self.assertIn("Switched", report)
        self.assertFalse(Locale.objects.filter(language_code="en").exists())
        self.assertFalse(Page.objects.filter(pk=self.en_article.pk).exists())
        self.assertEqual(Page.objects.filter(depth__gt=1).count(), nb_pages)
        row = SegmentTranslation.objects.get(
            segment_path="title", norwegian_text="Fadderuke"
        )
        self.assertEqual((row.english_text, row.source), ("[EN] Fadderuke", "deepl"))
        with english():
            self.assertEqual(
                ArticlePage.objects.get(pk=self.article.pk).title, "[EN] Fadderuke"
            )
        self.assertIn("Already switched", self.run_switch("--apply"))

    def test_a_persons_fix_stays_a_persons_fix(self):
        StringTranslation.objects.filter(
            locale=self.en, context__path="title", translation_of__data="Fadderuke"
        ).update(
            data="Buddy week",
            translation_type=StringTranslation.TRANSLATION_TYPE_MANUAL,
            last_translated_by=self.user,
        )
        self.run_switch("--apply")
        row = SegmentTranslation.objects.get(
            segment_path="title", norwegian_text="Fadderuke"
        )
        self.assertEqual(
            (row.english_text, row.source, row.translated_by),
            ("Buddy week", "human", self.user),
        )

    def test_english_slug_kept_and_redirect_when_address_changes(self):
        Page.objects.filter(pk=self.en_article.pk).update(slug="freshers-week")
        moved = self._article("Flyttet", "flyttet")
        self._article("Under", "under", parent=moved)
        self.run_switch("--apply")
        self.assertEqual(
            EnglishSlug.objects.get(page=self.article).slug, "freshers-week"
        )

    def test_english_only_page_deleted_and_redirected(self):
        lonely = self._article(
            "Only English", "only-english", parent=self.en_index, locale=self.en
        )
        report = self.run_switch("--apply")
        self.assertIn("English-only pages deleted: 1", report)
        self.assertFalse(Page.objects.filter(pk=lonely.pk).exists())
        self.assertTrue(Redirect.objects.filter(old_path="/en/only-english").exists())

    def test_alias_has_no_english_and_is_removed(self):
        untranslated = self._article("Uoversatt", "uoversatt")
        alias = untranslated.copy_for_translation(self.en, alias=True)
        self.run_switch("--apply")
        self.assertFalse(Page.objects.filter(pk=alias.pk).exists())
        self.assertFalse(
            SegmentTranslation.objects.filter(norwegian_text="Uoversatt").exists()
        )

    def test_menu_typed_into_english_copy_is_kept(self):
        group = MenuGroup(locale=self.nb, title="Studentliv")
        group.save()
        copy = group.copy_for_translation(self.en)
        copy.title = "Student life"
        copy.save()
        report = self.run_switch("--apply")
        self.assertIn("typed directly", report)
        row = SegmentTranslation.objects.get(norwegian_text="Studentliv")
        self.assertEqual((row.english_text, row.source), ("Student life", "human"))
        self.assertFalse(MenuGroup.objects.filter(pk=copy.pk).exists())

    def test_norwegian_link_to_english_page_is_repointed(self):
        message = HeaderMessage.objects.create(
            locale=self.nb,
            text=f'<p>Se <a linktype="page" id="{self.en_article.pk}">her</a></p>',
        )
        self.run_switch("--apply")
        message.refresh_from_db()
        self.assertIn(f'id="{self.article.pk}"', message.text)
