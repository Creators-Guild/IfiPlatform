"""Seeds a fresh local-dev database with a minimal, representative Wagtail
page tree, so contributors don't have to hand-build the site structure
(index pages, categories, a student union, a tool, ...) every time they
start on a new checkout.

Safe to re-run: every page is looked up by (parent, slug, locale) before
creation, so running this twice does not create duplicates.
"""

from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.images import ImageFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from wagtail.images.models import Image
from wagtail.models import Locale, Page, Site
from wagtail.rich_text import RichText
from wagtail_localize.models import LocaleSynchronization

from ifi_home_app.models import (
    ArticleIndexPage,
    ArticlePage,
    HeaderMessage,
    HomeBoardMessage,
)
from ifi_home_app.models.article_models import (
    CategoryPage,
    StudentUnionCategoryPage,
    ToolPage,
    UnionPage,
)

SEED_IMAGE_PATH = (
    Path(settings.BASE_DIR) / "static" / "images" / "studentunions" / "IfiPitbullsLogo.jpg"
)
SEED_IMAGE_TITLE = "Dev seed placeholder image"

CATEGORY_SPECS = [
    ("Praktisk", "turq"),
    ("Akademisk", "pink"),
    ("Sosialt", "purple"),
    ("Hjelp", "turq"),
    ("IfiPlattform", "pink"),
]

NEWS_ARTICLE_TITLES = [
    "Nyhetsartikkel 1",
    "Nyhetsartikkel 2",
    "Nyhetsartikkel 3",
    "Nyhetsartikkel 4",
]

BANNER_TEXT = "Welcome to your local dev server"

LOREM_IPSUM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim "
    "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea "
    "commodo consequat."
)


class Command(BaseCommand):
    help = (
        "Populates the local dev database with a dummy nb article tree "
        "(index pages, categories, a test article per category, a student "
        "union category with two unions, and a tool page), then syncs an "
        "English locale alias of the whole tree. Re-running is a no-op for "
        "anything that already exists."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow running even when DEBUG is off (e.g. against a real Postgres db).",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "DEBUG is off -- refusing to seed dummy data into what looks like a "
                "non-local database. Pass --force if you really mean it."
            )

        self.created_count = 0
        self.skipped_count = 0

        with transaction.atomic():
            nb_locale, _ = Locale.objects.get_or_create(language_code="nb")
            en_locale, _ = Locale.objects.get_or_create(language_code="en")

            seed_image = self._get_or_create_seed_image()

            root = Page.get_first_root_node()

            artikkler = self._get_or_create_page(
                root, ArticleIndexPage, "Artikkler", nb_locale,
                section="hub",
            )
            self._set_default_site_root(artikkler)

            nyheter = self._get_or_create_page(
                artikkler, ArticleIndexPage, "Nyheter", nb_locale,
                section="news",
            )
            self._seed_news_articles(nyheter, nb_locale)

            info_articles = self._get_or_create_page(
                artikkler, ArticleIndexPage, "Informasjonsartikkler", nb_locale,
                section="info_articles",
            )

            for title, color in CATEGORY_SPECS:
                category = self._get_or_create_page(
                    info_articles, CategoryPage, title, nb_locale,
                    color=color, show_in_menu=True,
                )
                self._get_or_create_page(
                    category, ArticlePage, "Testartikkel", nb_locale,
                    intro="En test-artikkel generert av seed-scriptet.",
                    published_date=timezone.now().date(),
                    body=self._build_article_body(title),
                )

                if title == "Sosialt":
                    self._seed_student_unions(category, nb_locale, seed_image)
                elif title == "Praktisk":
                    self._seed_tool(category, nb_locale, seed_image)

            self._sync_english_locale(nb_locale, en_locale)

            self._seed_header_message(nb_locale, en_locale)
            self._seed_home_board_message(nb_locale, en_locale)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {self.created_count} page(s) created, "
                f"{self.skipped_count} already existed."
            )
        )

    # -- tree pieces -----------------------------------------------------

    def _seed_student_unions(self, sosialt_category, nb_locale, seed_image):
        union_category = self._get_or_create_page(
            sosialt_category, StudentUnionCategoryPage, "Studentforeninger", nb_locale,
        )
        for name in ["Testforening 1", "Testforening 2"]:
            self._get_or_create_page(
                union_category, UnionPage, name, nb_locale,
                email="testforening@example.com",
                logo=seed_image,
                purpose="Test-formål generert av seed-scriptet.",
                activities="Test-aktiviteter generert av seed-scriptet.",
                union_type="general",
                website_url="https://example.com",
                social_links=[
                    ("social_link", {
                        "platform": "instagram",
                        "url": "https://instagram.com/example",
                    }),
                ],
                member_count_sitting=1,
                member_count_intern=0,
                sitting_members=[
                    ("member", {
                        "name": "Test Testesen",
                        "role": "Leder",
                        "school_email": "test@ifi.uio.no",
                        "picture": seed_image,
                    }),
                ],
            )

    def _seed_news_articles(self, nyheter, nb_locale):
        # ArticlePage.parent_page_types only allows a CategoryPage parent, so
        # the news articles need a category under Nyheter to live in.
        news_category = self._get_or_create_page(
            nyheter, CategoryPage, "Siste nytt", nb_locale,
            color="pink", show_in_menu=True,
        )
        today = timezone.now().date()
        for i, title in enumerate(NEWS_ARTICLE_TITLES, start=1):
            self._get_or_create_page(
                news_category, ArticlePage, title, nb_locale,
                intro="En test-nyhetsartikkel generert av seed-scriptet.",
                published_date=today - timedelta(days=i),
                body=self._build_article_body(title),
            )

    def _seed_tool(self, praktisk_category, nb_locale, seed_image):
        # core_views.main_view looks this category up by the hardcoded slug
        # "ifi-verktøy" -- plain slugify() would strip the "ø", so it's
        # pinned explicitly here to keep the homepage's tools section working.
        tool_category = self._get_or_create_page(
            praktisk_category, CategoryPage, "Ifi verktøy", nb_locale,
            color="turq", show_in_menu=True, slug="ifi-verktøy",
        )
        self._get_or_create_page(
            tool_category, ToolPage, "Test-verktøy", nb_locale,
            description="Et test-verktøy generert av seed-scriptet.",
            image=seed_image,
            image_overlay=True,
            link="https://example.com",
            made_by="Ifi Platform",
            preview_images=[("image", seed_image)],
        )

    def _build_article_body(self, category_title):
        return [
            ("heading", {"text": "Om denne testartikkelen", "level": "h2"}),
            ("paragraph", RichText(
                f"<p>Dette er en automatisk generert test-artikkel for kategorien "
                f"<b>{category_title}</b>, laget av seed-scriptet for lokal "
                f"utvikling. Innholdet er kun til testformål.</p>"
            )),
        ]

    def _seed_header_message(self, nb_locale, en_locale):
        text = f"<p>{BANNER_TEXT}</p>"
        message = HeaderMessage.objects.filter(text=text, locale=nb_locale).first()
        if message is None:
            message = HeaderMessage.objects.create(
                text=RichText(text), is_active=True, locale=nb_locale,
            )
            self.created_count += 1
            self.stdout.write(f"  created HeaderMessage: {BANNER_TEXT}")
        else:
            self.skipped_count += 1

        if not message.has_translation(en_locale):
            translation = message.copy_for_translation(en_locale)
            translation.save()
            self.created_count += 1
            self.stdout.write(f"  created HeaderMessage (en): {BANNER_TEXT}")
        else:
            self.skipped_count += 1

    def _seed_home_board_message(self, nb_locale, en_locale):
        title = "Lorem Ipsum"
        message = HomeBoardMessage.objects.filter(
            title=title, locale=nb_locale
        ).first()
        if message is None:
            message = HomeBoardMessage(
                title=title,
                date=timezone.now().date(),
                body=RichText(f"<p>{LOREM_IPSUM}</p>"),
                sender_name="Lorem Ipsum",
                sender_role="Seed script",
                order=0,
                locale=nb_locale,
            )
            message.save()
            self.created_count += 1
            self.stdout.write(f"  created HomeBoardMessage: {title}")
        else:
            self.skipped_count += 1

        if not message.has_translation(en_locale):
            translation = message.copy_for_translation(en_locale)
            translation.save()
            self.created_count += 1
            self.stdout.write(f"  created HomeBoardMessage (en): {title}")
        else:
            self.skipped_count += 1

    # -- generic helpers ---------------------------------------------------

    def _get_or_create_page(self, parent, model, title, locale, slug=None, **field_kwargs):
        slug = slug or slugify(title)
        existing = model.objects.child_of(parent).filter(
            slug=slug, locale_id=locale.id
        ).first()
        if existing:
            self.skipped_count += 1
            return existing

        page = model(title=title, slug=slug, locale=locale, **field_kwargs)
        parent.add_child(instance=page)
        page.save_revision().publish()
        self.created_count += 1
        self.stdout.write(f"  created {model.__name__}: {title}")
        return page

    def _get_or_create_seed_image(self):
        existing = Image.objects.filter(title=SEED_IMAGE_TITLE).first()
        if existing:
            return existing

        if not SEED_IMAGE_PATH.exists():
            raise CommandError(f"Seed image not found at {SEED_IMAGE_PATH}")

        with open(SEED_IMAGE_PATH, "rb") as f:
            image = Image(
                title=SEED_IMAGE_TITLE,
                file=ImageFile(f, name=SEED_IMAGE_PATH.name),
            )
            image.save()
        return image

    def _set_default_site_root(self, root_page):
        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            Site.objects.get_or_create(
                hostname="localhost",
                defaults={
                    "port": 80,
                    "root_page": root_page,
                    "is_default_site": True,
                },
            )
        elif site.root_page_id != root_page.id:
            site.root_page = root_page
            site.save()

    def _sync_english_locale(self, nb_locale, en_locale):
        LocaleSynchronization.objects.get_or_create(
            locale=en_locale, defaults={"sync_from": nb_locale}
        )
        call_command("sync_locale_trees")
