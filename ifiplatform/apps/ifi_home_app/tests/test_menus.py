# pylint: disable=C0114,C0115,C0116
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone, translation
from wagtail.models import Locale, Page

from ifi_home_app.models import ArticleIndexPage
from ifi_home_app.models.article_models import CategoryPage
from ifi_home_app.models.menus import Menu, MenuGroup, MenuGroupLink, MenuSlot, get_menu
from ifi_home_app.templatetags.article_tags import get_shortcut_columns


class MenuTests(TestCase):
    """models/menus.py -- see docs/claude_context/menus.md."""

    def setUp(self):
        self.nb, _ = Locale.objects.get_or_create(language_code="nb")
        self.en, _ = Locale.objects.get_or_create(language_code="en")
        self.index = ArticleIndexPage(locale=self.nb, title="Artikler", slug="artikler", section="info_articles")
        Page.get_first_root_node().add_child(instance=self.index)
        self.index.save_revision().publish()

    def _category(self, title, **kwargs):
        category = CategoryPage(locale=self.nb, title=title, slug=title.lower(), **kwargs)
        self.index.add_child(instance=category)
        category.save_revision().publish()
        return category

    def _group(self, title="Gruppe", links=(), **kwargs):
        group = MenuGroup(locale=self.nb, title=title, **kwargs)
        for order, link in enumerate(links):
            group.links.add(MenuGroupLink(sort_order=order, **link))
        group.save()
        return group

    def _menu(self, key, *slots):
        menu = Menu(key=key)
        for order, slot in enumerate(slots):
            slot = slot if isinstance(slot, dict) else {"group": slot}
            menu.slots.add(MenuSlot(sort_order=order, **slot))
        menu.save()
        return menu

    def _nb(self, key):
        with translation.override("nb"):
            return get_menu(key)

    def test_missing_menu_is_empty(self):
        self.assertEqual(self._nb("sidemenu"), [])

    def test_keeps_editor_order(self):
        first, second = self._category("Første"), self._category("Andre")
        group = self._group(links=[{"page": second}, {"page": first}])
        self._menu("sidemenu", self._group("B"), group)

        menu = self._nb("sidemenu")
        self.assertEqual([g["title"] for g in menu], ["B", "Gruppe"])
        self.assertEqual([link["label"] for link in menu[1]["links"]], ["Andre", "Første"])

    def test_skips_unpublished_and_off_season_pages(self):
        visible = self._category("Synlig")
        unpublished = self._category("Upublisert")
        unpublished.unpublish()
        off_season = self._category("Sesong", active_until=timezone.now().date() - timedelta(days=1))
        self._menu("sidemenu", self._group(links=[{"page": visible}, {"page": unpublished}, {"page": off_season}]))

        self.assertEqual([link["label"] for link in self._nb("sidemenu")[0]["links"]], ["Synlig"])

    def test_external_links_are_flagged(self):
        self._menu("sidemenu", self._group(
            link_url="https://example.com/heading",
            links=[{"url": "https://example.com", "label": "Eksempel"}],
        ))

        group = self._nb("sidemenu")[0]
        self.assertTrue(group["external"])
        self.assertEqual(group["url"], "https://example.com/heading")
        self.assertTrue(group["links"][0]["external"])

    def test_heading_page_link_is_internal(self):
        self._menu("sidemenu", self._group(link_page=self.index))

        group = self._nb("sidemenu")[0]
        self.assertFalse(group["external"])
        self.assertEqual(group["url"], self.index.url)

    def test_group_rejects_both_heading_links(self):
        group = MenuGroup(locale=self.nb, title="Begge", link_page=self.index, link_url="https://example.com")
        with self.assertRaises(ValidationError):
            group.clean()

    def test_link_needs_exactly_one_target(self):
        with self.assertRaises(ValidationError):
            MenuGroupLink(label="Ingen").clean()
        with self.assertRaises(ValidationError):
            MenuGroupLink(page=self.index, url="https://example.com").clean()

    def test_blank_label_uses_localized_page_title(self):
        category = self._category("Akademisk")
        en_category = category.copy_for_translation(self.en, copy_parents=True)
        en_category.title = "Academic"
        en_category.save_revision().publish()
        self._menu("sidemenu", self._group(links=[{"page": category}]))

        with translation.override("en"):
            link = get_menu("sidemenu")[0]["links"][0]
        self.assertEqual(link["label"], "Academic")
        self.assertEqual(link["url"], en_category.url)

    def test_en_falls_back_to_untranslated_nb_group(self):
        self._menu("sidemenu", self._group("Bare norsk"))

        with translation.override("en"):
            self.assertEqual(get_menu("sidemenu")[0]["title"], "Bare norsk")

    def test_en_uses_translated_group(self):
        group = self._group("Nyheter")
        en_group = group.copy_for_translation(self.en)
        en_group.title = "News"
        en_group.save()
        self._menu("sidemenu", group)

        with translation.override("en"):
            self.assertEqual(get_menu("sidemenu")[0]["title"], "News")

    def test_shortcuts_are_grouped_by_column(self):
        self._menu(
            "shortcuts",
            {"group": self._group("A"), "column": 2},
            {"group": self._group("B"), "column": 1},
            {"group": self._group("C"), "column": 2},
        )

        with translation.override("nb"):
            columns = get_shortcut_columns()
        self.assertEqual([[g["title"] for g in column] for column in columns], [["B"], ["A", "C"]])
