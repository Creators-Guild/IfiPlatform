"""Seeds a fresh local-dev database with a minimal, representative Wagtail
page tree, so contributors don't have to hand-build the site structure
(index pages, categories, a student union, a tool, ...) every time they
start on a new checkout. Every nb page gets a real English translation,
submitted and imported through wagtail_localize's own PO pipeline rather
than a hand-written second copy of every field (see _translate_page).

Safe to re-run: every page is looked up by (parent, slug, locale) before
creation, so running this twice does not create duplicates.
"""

from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.images import ImageFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from wagtail.coreutils import find_available_slug
from wagtail.images.models import Image
from wagtail.models import Locale, Page, Site
from wagtail.rich_text import RichText
from wagtail_localize.models import LocaleSynchronization, Translation, TranslationSource

from ifi_home_app.models import (
    ArticleIndexPage,
    ArticlePage,
    EventIndexPage,
    EventPage,
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

# (title, event_type, days-from-today for event_date, event_time or None,
# days-from-event_date for end_date or None) -- mirrors the "This month at
# Ifi" mockup: a week-long event with no fixed time (Fadderuke), a dated
# social with a time (Bar til bar), a deadline (Frist for funk-oppmelding),
# and a company presentation (DNB).
EVENT_SPECS = [
    ("Fadderuke", "social", 3, None, 4),
    ("Bar til bar", "social", 8, "17:00", None),
    ("Frist for funk-oppmelding for Dagen@IFI", "deadline", 12, None, None),
    ("DNB Bedriftspresentasjon med Navet", "company", 20, "16:00", None),
]

# Fadderuke's own week-calendar color legend (see EventPage.calendar_legend's
# docstring) -- one entry per calendar_color actually used in
# FADDERUKE_SUB_EVENT_SPECS below.
FADDERUKE_LEGEND = [
    ("blue", "Relevant for studiet"),
    ("yellow", "Mat"),
    ("orange", "Alkoholfritt"),
    ("pink", "Med eller uten alkohol"),
    ("green", "Felles for hele MatNat"),
]

# (days-from-Fadderuke's-own-event_date, title, event_type, start "HH:MM",
# end "HH:MM", calendar_color) -- a full Mon-Fri Fadderuke programme, so
# EventPage.calendar_days has a realistic week to lay out instead of just
# the lone parent event. Titles that would otherwise repeat under the same
# parent (Lunsj, Forkurs, Grill n' chill) get a day/time qualifier purely to
# stay unique per (parent, slug, locale) -- see _get_or_create_page.
FADDERUKE_SUB_EVENT_SPECS = [
    (0, "Oppmøteregistrering", "academic", "09:00", "10:00", "blue"),
    (0, "Programvis opplegg (formiddag)", "academic", "10:00", "12:00", "blue"),
    (0, "Lunsj med fadderne", "social", "12:00", "13:00", "yellow"),
    (0, "Programvis opplegg (ettermiddag)", "academic", "13:00", "15:00", "blue"),
    (0, "Tale på universitetsplassen", "academic", "15:00", "16:00", "blue"),
    (0, "Grill n' chill (mandag)", "social", "16:00", "17:00", "yellow"),
    (0, "Quiz m/CYB", "social", "18:00", "19:00", "pink"),
    (0, "Brettspillkveld m/FUI", "social", "18:00", "21:00", "orange"),
    (1, "Forkurs (tirsdag)", "academic", "09:00", "12:30", "blue"),
    (1, "Lunsj (tirsdag)", "social", "12:00", "13:00", "yellow"),
    (1, "IFI-Olympiaden", "social", "13:00", "16:00", "orange"),
    (1, "Grill n' chill + Kåring av Olympiadevinner", "social", "16:00", "17:00", "yellow"),
    (1, "Kickoff m/ Navet", "social", "17:30", "19:30", "pink"),
    (1, "Spillkveld m/Progsys", "social", "18:00", "21:00", "pink"),
    (1, "Musikkbingo m/MAKI", "social", "18:00", "21:00", "orange"),
    (2, "Forkurs (onsdag)", "academic", "09:00", "12:30", "blue"),
    (2, "Lunsj (onsdag)", "social", "12:00", "13:00", "yellow"),
    (2, "How to IFI m/FUI", "academic", "13:00", "14:00", "orange"),
    (2, "Introduksjon til foreningslivet m/FU", "social", "14:00", "15:00", "orange"),
    (2, "Foreningstorg", "social", "14:00", "16:00", "orange"),
    (2, "Grill n' chill (onsdag)", "social", "16:00", "17:00", "yellow"),
    (2, "Temafest m/Dagen@ifi", "social", "18:00", "21:00", "pink"),
    (3, "Lunsj + Speedfriending m/Fadderstyret", "social", "12:00", "13:00", "yellow"),
    (3, "Gaffaregatt m/Mikro", "social", "13:00", "16:00", "orange"),
    (3, "Volleyballturnering m/VIFI", "social", "13:00", "16:00", "orange"),
    (3, "Kaffesmaking m/CYB & kaffeforeningen", "social", "14:00", "16:00", "orange"),
    (3, "Grill n' chill (torsdag)", "social", "16:00", "17:00", "yellow"),
    (3, "Paint & Sip m/Defi", "social", "18:00", "21:00", "pink"),
    (3, "Realstart! Felles kveld for hele MatNat!", "social", "19:00", "22:00", "green"),
    (4, "Lunsj (fredag)", "social", "12:00", "13:00", "yellow"),
    (4, "Shitty cars m/Sonen", "social", "13:00", "15:00", "orange"),
    (4, "Fotballturnering m/FIFI", "social", "13:00", "16:00", "orange"),
    (4, "2000-Meter m/Digitus", "social", "15:00", "16:00", "pink"),
    (4, "Grill n' chill + Kakefredag m/Progsys", "social", "16:00", "17:00", "yellow"),
    (4, "CTRL+ALT+DEL m/CYB", "social", "18:00", "21:00", "pink"),
]

# Shown in Fadderuke's own homepage dropdown (see
# EventPage.highlighted_sub_events) -- just the one event common to all of
# MatNat, not every sub-event.
FADDERUKE_HIGHLIGHTED_TITLES = {"Realstart! Felles kveld for hele MatNat!"}

# Student unions referenced by the "m/XXX" abbreviations in
# FADDERUKE_SUB_EVENT_SPECS's titles above -- created as minimal UnionPage
# children of the same Studentforeninger category as Testforening 1/2, with
# just enough fields filled in to be a real page (see _seed_fadderuke_unions).
FADDERUKE_UNION_SPECS = [
    "CYB", "FUI", "Progsys", "MAKI", "VIFI", "FU", "Mikro", "Defi",
    "Sonen", "FIFI", "Digitus", "Navet", "Fadderstyret", "Dagen@ifi",
]

# Sub-event title -> [(union title, role), ...] for EventPage.related_unions
# -- "host" for the union directly named in the sub-event's own title,
# "contributor"/"collaborator" used on a couple of entries (Foreningstorg,
# Realstart!) to also demo those roles and multi-union entries. Sub-events
# not listed here (Lunsj, Grill n' chill, ...) are deliberately left
# union-less -- nobody specific "hosts" the cafeteria lunch.
FADDERUKE_SUB_EVENT_UNIONS = {
    "Oppmøteregistrering": [("Fadderstyret", "host")],
    "Programvis opplegg (formiddag)": [("Fadderstyret", "host")],
    "Programvis opplegg (ettermiddag)": [("Fadderstyret", "host")],
    "Tale på universitetsplassen": [("Fadderstyret", "host")],
    "Quiz m/CYB": [("CYB", "host")],
    "Brettspillkveld m/FUI": [("FUI", "host")],
    "Forkurs (tirsdag)": [("Fadderstyret", "host")],
    "IFI-Olympiaden": [("Fadderstyret", "host")],
    "Kickoff m/ Navet": [("Navet", "host")],
    "Spillkveld m/Progsys": [("Progsys", "host")],
    "Musikkbingo m/MAKI": [("MAKI", "host")],
    "Forkurs (onsdag)": [("Fadderstyret", "host")],
    "How to IFI m/FUI": [("FUI", "host")],
    "Introduksjon til foreningslivet m/FU": [("FU", "host")],
    "Foreningstorg": [
        ("CYB", "contributor"), ("FUI", "contributor"),
        ("Progsys", "contributor"), ("VIFI", "contributor"),
    ],
    "Temafest m/Dagen@ifi": [("Dagen@ifi", "host")],
    "Lunsj + Speedfriending m/Fadderstyret": [("Fadderstyret", "host")],
    "Gaffaregatt m/Mikro": [("Mikro", "host")],
    "Volleyballturnering m/VIFI": [("VIFI", "host")],
    "Kaffesmaking m/CYB & kaffeforeningen": [("CYB", "host")],
    "Paint & Sip m/Defi": [("Defi", "host")],
    "Realstart! Felles kveld for hele MatNat!": [
        ("Fadderstyret", "host"),
        ("CYB", "collaborator"),
        ("Progsys", "collaborator"),
    ],
    "Shitty cars m/Sonen": [("Sonen", "host")],
    "Fotballturnering m/FIFI": [("FIFI", "host")],
    "2000-Meter m/Digitus": [("Digitus", "host")],
    "Grill n' chill + Kakefredag m/Progsys": [("Progsys", "host")],
    "CTRL+ALT+DEL m/CYB": [("CYB", "host")],
}

# (title, intro, body heading, body paragraph) -- demo content for the
# "Ny Ifi Student?" category (see _seed_new_student_articles), so the
# homepage's "New Student?" dropdown (home_navbar.html) has real
# articles/thumbnails to show instead of its "No articles yet" fallback.
NEW_STUDENT_ARTICLE_SPECS = [
    (
        "Adgangskort",
        "Alt du trenger å vite om å skaffe adgangskort til Ifi.",
        "Hvordan skaffe adgangskort",
        "I teorien går det an å være student uten adgangskort. Men det blir "
        "fort veldig upraktisk og du bør skaffe deg et så fort som mulig.",
    ),
    (
        "Sjekkliste for nye Ifi-studenter",
        "En sjekkliste over det aller viktigste du bør ordne som ny student.",
        "Sjekkliste",
        "Som ny student er det en del å gjøre, men heldigvis trenger du "
        "bare å gjøre de fleste av disse tingene én gang.",
    ),
    (
        "Nyttige verktøy det er skjekt å vite om",
        "En oversikt over verktøy og tjenester som gjør studiehverdagen enklere.",
        "Verktøy",
        "Det finnes mange nyttige verktøy og tjenester som Ifi-studenter "
        "bruker i studiehverdagen. Her er noen av de mest brukte.",
    ),
]

BANNER_TEXT = "Welcome to your local dev server"

LOREM_IPSUM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim "
    "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea "
    "commodo consequat."
)

# nb -> en for every translatable string this script writes. Fed through
# wagtail_localize's real PO import/export pipeline (see _translate_page)
# rather than just hand-writing a second copy of every field. Anything not
# listed here (image files, choice fields, urls, the placeholder name/email)
# falls back to the source-language value untouched.
TRANSLATIONS = {
    "Artikkler": "Articles",
    "Nyheter": "News",
    "Informasjonsartikkler": "Info Articles",
    "Praktisk": "Practical",
    "Akademisk": "Academic",
    "Sosialt": "Social",
    "Hjelp": "Help",
    "IfiPlattform": "IfiPlatform",
    "Testartikkel": "Test Article",
    "Ifi verktøy": "Ifi Tools",
    "Test-verktøy": "Test Tool",
    "UiO verktøy": "UiO Tools",
    "Nøstet test-verktøy": "Nested test tool",
    "Et nøstet test-verktøy generert av seed-scriptet, for å vise Ifi verktøy sin \"vis nøstede verktøy\"-innstilling.": "A nested test tool generated by the seed script, to demonstrate Ifi Tools' \"show nested tools\" setting.",
    "Studentforeninger": "Student Unions",
    "Testforening 1": "Test Union 1",
    "Testforening 2": "Test Union 2",
    "Siste nytt": "Latest News",
    "Nyhetsartikkel 1": "News Article 1",
    "Nyhetsartikkel 2": "News Article 2",
    "Nyhetsartikkel 3": "News Article 3",
    "Nyhetsartikkel 4": "News Article 4",
    "Om denne testartikkelen": "About this test article",
    "En test-artikkel generert av seed-scriptet.": "A test article generated by the seed script.",
    "En test-nyhetsartikkel generert av seed-scriptet.": "A test news article generated by the seed script.",
    "Dette er en automatisk generert test-artikkel laget av seed-scriptet for lokal utvikling. Innholdet er kun til testformål.": "This is an automatically generated test article created by the seed script for local development. The content is for testing purposes only.",
    "Test-formål generert av seed-scriptet.": "Test purpose generated by the seed script.",
    "Test-aktiviteter generert av seed-scriptet.": "Test activities generated by the seed script.",
    "Leder": "Chair",
    "Et test-verktøy generert av seed-scriptet.": "A test tool generated by the seed script.",
    "Arrangementer": "Events",
    "Fadderuke": "Fadderuke",
    "Bar til bar": "Bar crawl",
    "Frist for funk-oppmelding for Dagen@IFI": "Deadline: Dagen@IFI committee signup",
    "DNB Bedriftspresentasjon med Navet": "DNB company presentation with Navet",
    # Fadderuke's own calendar-color legend (FADDERUKE_LEGEND).
    "Relevant for studiet": "Relevant to Studies",
    "Mat": "Food",
    "Alkoholfritt": "Non-alcoholic",
    "Med eller uten alkohol": "With or without alcohol",
    "Felles for hele MatNat": "Common to the entire MatNat",
    # Fadderuke sub-events (FADDERUKE_SUB_EVENT_SPECS).
    "Oppmøteregistrering": "Check-in",
    "Programvis opplegg (formiddag)": "Programme-specific session (morning)",
    "Lunsj med fadderne": "Lunch with the mentors",
    "Programvis opplegg (ettermiddag)": "Programme-specific session (afternoon)",
    "Tale på universitetsplassen": "Speech at the University Square",
    "Grill n' chill (mandag)": "Grill n' chill (Monday)",
    "Quiz m/CYB": "Quiz w/CYB",
    "Brettspillkveld m/FUI": "Board game night w/FUI",
    "Forkurs (tirsdag)": "Pre-course (Tuesday)",
    "Lunsj (tirsdag)": "Lunch (Tuesday)",
    "IFI-Olympiaden": "The IFI Olympics",
    "Grill n' chill + Kåring av Olympiadevinner": "Grill n' chill + Olympics winner announcement",
    "Kickoff m/ Navet": "Kickoff w/ Navet",
    "Spillkveld m/Progsys": "Games night w/Progsys",
    "Musikkbingo m/MAKI": "Music bingo w/MAKI",
    "Forkurs (onsdag)": "Pre-course (Wednesday)",
    "Lunsj (onsdag)": "Lunch (Wednesday)",
    "How to IFI m/FUI": "How to IFI w/FUI",
    "Introduksjon til foreningslivet m/FU": "Intro to student union life w/FU",
    "Foreningstorg": "Student union fair",
    "Grill n' chill (onsdag)": "Grill n' chill (Wednesday)",
    "Temafest m/Dagen@ifi": "Theme party w/Dagen@ifi",
    "Lunsj + Speedfriending m/Fadderstyret": "Lunch + Speedfriending w/the Mentor Committee",
    "Gaffaregatt m/Mikro": "Gaffaregatt w/Mikro",
    "Volleyballturnering m/VIFI": "Volleyball tournament w/VIFI",
    "Kaffesmaking m/CYB & kaffeforeningen": "Coffee tasting w/CYB & the coffee student union",
    "Grill n' chill (torsdag)": "Grill n' chill (Thursday)",
    "Paint & Sip m/Defi": "Paint & Sip w/Defi",
    "Realstart! Felles kveld for hele MatNat!": "Realstart! Joint evening for all of MatNat!",
    "Lunsj (fredag)": "Lunch (Friday)",
    "Shitty cars m/Sonen": "Shitty cars w/Sonen",
    "Fotballturnering m/FIFI": "Football tournament w/FIFI",
    "2000-Meter m/Digitus": "2000m race w/Digitus",
    "Grill n' chill + Kakefredag m/Progsys": "Grill n' chill + Cake Friday w/Progsys",
    "CTRL+ALT+DEL m/CYB": "CTRL+ALT+DEL w/CYB",
    # Fadderuke-hosting unions (FADDERUKE_UNION_SPECS) -- most are
    # abbreviations/proper names left as-is; only Fadderstyret has a real
    # English equivalent worth translating.
    "Fadderstyret": "The Mentor Committee",
    "En studentforening ved Ifi generert av seed-scriptet.": "A student union at Ifi generated by the seed script.",
    # "Ny Ifi Student?" category + its demo articles (NEW_STUDENT_ARTICLE_SPECS).
    "Ny Ifi Student?": "New Student?",
    "Her er alt du skulle trenge som en ny Ifi Student!": "Here's everything you should need as a new Ifi student!",
    "Adgangskort": "Access card",
    "Alt du trenger å vite om å skaffe adgangskort til Ifi.": "Everything you need to know about getting an access card for Ifi.",
    "Hvordan skaffe adgangskort": "How to get an access card",
    "I teorien går det an å være student uten adgangskort. Men det blir fort veldig upraktisk og du bør skaffe deg et så fort som mulig.": "In theory it's possible to be a student without an access card. But it quickly gets very impractical, so you should get one as soon as possible.",
    "Sjekkliste for nye Ifi-studenter": "Checklist for new Ifi students",
    "En sjekkliste over det aller viktigste du bør ordne som ny student.": "A checklist of the most important things to sort out as a new student.",
    "Sjekkliste": "Checklist",
    "Som ny student er det en del å gjøre, men heldigvis trenger du bare å gjøre de fleste av disse tingene én gang.": "As a new student there's quite a bit to do, but luckily you only need to do most of these things once.",
    "Nyttige verktøy det er skjekt å vite om": "Useful tools worth knowing about",
    "En oversikt over verktøy og tjenester som gjør studiehverdagen enklere.": "An overview of tools and services that make everyday student life easier.",
    "Verktøy": "Tools",
    "Det finnes mange nyttige verktøy og tjenester som Ifi-studenter bruker i studiehverdagen. Her er noen av de mest brukte.": "There are many useful tools and services Ifi students use day to day. Here are some of the most commonly used ones.",
}

ARTICLE_BODY = [
    ("heading", {"text": "Om denne testartikkelen", "level": "h2"}),
    ("paragraph", {"text": RichText(
        "<p>Dette er en automatisk generert test-artikkel laget av "
        "seed-scriptet for lokal utvikling. Innholdet er kun til "
        "testformål.</p>"
    )}),
]

BOARD_MESSAGE_SPECS = [
    {
        "title": "Lorem Ipsum 1",
        "sender_name": "Lorem Ipsum",
        "display_seconds": 30,
        # short enough that the message body shouldn't need to scroll
        "body": "<p>Lorem ipsum dolor sit amet.</p>",
    },
    {
        "title": "Lorem Ipsum 2",
        "sender_name": "Dolor Sit",
        "display_seconds": 45,
        # long enough to just overflow the fixed-height card, so scrolling kicks in
        "body": "".join(f"<p>{LOREM_IPSUM}</p>" for _ in range(2)),
    },
    {
        "title": "Lorem Ipsum 3",
        "sender_name": "Amet Consectetur",
        "display_seconds": 60,
        # several paragraphs, clearly needs a lot of scrolling
        "body": "".join(f"<p>{LOREM_IPSUM}</p>" for _ in range(5)),
    },
]


class Command(BaseCommand):
    help = (
        "Populates the local dev database with a dummy nb article tree "
        "(index pages, categories, a test article per category, a student "
        "union category with two unions, and a tool page), each translated "
        "into a real en counterpart via wagtail_localize's PO pipeline. "
        "Re-running is a no-op for anything that already exists."
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

        # Deliberately not wrapped in transaction.atomic(): Translation.save_target()
        # defers its actual page-content publish via transaction.on_commit(), which
        # only fires when the OUTERMOST transaction commits. Wrapping this whole
        # method in one atomic() block would queue up every page's deferred publish
        # until the very end, where each one re-applies its (pre-slug-fix) frozen
        # revision and silently reverts the slug rewrite in _translate_page below.
        # Without an enclosing transaction, each on_commit fires immediately.
        nb_locale, _ = Locale.objects.get_or_create(language_code="nb")
        en_locale, _ = Locale.objects.get_or_create(language_code="en")

        seed_image = self._get_or_create_seed_image()

        root = Page.get_first_root_node()

        artikkler = self._get_or_create_page(
            root, ArticleIndexPage, "Artikkler", nb_locale,
            section="hub",
        )
        self._set_default_site_root(artikkler)
        self._translate_page(artikkler, en_locale)

        nyheter = self._get_or_create_page(
            artikkler, ArticleIndexPage, "Nyheter", nb_locale,
            section="news",
        )
        self._translate_page(nyheter, en_locale)
        self._seed_news_articles(nyheter, nb_locale, en_locale)

        info_articles = self._get_or_create_page(
            artikkler, ArticleIndexPage, "Informasjonsartikkler", nb_locale,
            section="info_articles",
        )
        self._translate_page(info_articles, en_locale)

        for title, color in CATEGORY_SPECS:
            category = self._get_or_create_page(
                info_articles, CategoryPage, title, nb_locale,
                color=color, show_in_menu=True,
            )
            self._translate_page(category, en_locale)

            article = self._get_or_create_page(
                category, ArticlePage, "Testartikkel", nb_locale,
                intro="En test-artikkel generert av seed-scriptet.",
                published_date=timezone.now().date(),
                body=self._build_article_body(),
            )
            self._translate_page(article, en_locale)

            if title == "Sosialt":
                self._seed_student_unions(category, nb_locale, en_locale, seed_image)
            elif title == "Praktisk":
                self._seed_tool(category, nb_locale, en_locale, seed_image)
                self._seed_new_student_articles(category, nb_locale, en_locale, seed_image)

        self._seed_events(artikkler, nb_locale, en_locale, seed_image)

        self._sync_english_locale(nb_locale, en_locale)

        self._seed_header_message(nb_locale, en_locale)
        self._seed_home_board_message(nb_locale, en_locale)

        # wagtail_localize's copy-for-translation path doesn't keep the
        # translated parent's `numchild` counter in sync, which makes
        # Wagtail's tree-walking router treat every en page as childless
        # (silent 404s below the site root). fix_tree() recalculates it.
        Page.fix_tree()

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {self.created_count} page(s) created, "
                f"{self.skipped_count} already existed."
            )
        )

    # -- tree pieces -----------------------------------------------------

    def _seed_student_unions(self, sosialt_category, nb_locale, en_locale, seed_image):
        union_category = self._get_or_create_page(
            sosialt_category, StudentUnionCategoryPage, "Studentforeninger", nb_locale,
        )
        self._translate_page(union_category, en_locale)

        for name in ["Testforening 1", "Testforening 2"]:
            union = self._get_or_create_page(
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
            self._translate_page(union, en_locale)

    def _seed_news_articles(self, nyheter, nb_locale, en_locale):
        # ArticlePage.parent_page_types only allows a CategoryPage parent, so
        # the news articles need a category under Nyheter to live in.
        news_category = self._get_or_create_page(
            nyheter, CategoryPage, "Siste nytt", nb_locale,
            color="pink", show_in_menu=True,
        )
        self._translate_page(news_category, en_locale)

        today = timezone.now().date()
        for i, title in enumerate(NEWS_ARTICLE_TITLES, start=1):
            article = self._get_or_create_page(
                news_category, ArticlePage, title, nb_locale,
                intro="En test-nyhetsartikkel generert av seed-scriptet.",
                published_date=today - timedelta(days=i),
                body=self._build_article_body(),
            )
            self._translate_page(article, en_locale)

    def _seed_events(self, artikkler, nb_locale, en_locale, seed_image):
        event_index = self._get_or_create_page(
            artikkler, EventIndexPage, "Arrangementer", nb_locale,
        )
        self._translate_page(event_index, en_locale)

        today = timezone.now().date()
        fadderuke = None
        for title, event_type, offset_days, time_str, end_offset_days in EVENT_SPECS:
            # Fadderuke's sub-events (FADDERUKE_SUB_EVENT_SPECS) are a Mon-Fri
            # programme, so Fadderuke itself always starts on the next Monday
            # rather than EVENT_SPECS's plain offset -- otherwise its week
            # would land on arbitrary weekdays depending on when this command
            # happens to run.
            if title == "Fadderuke":
                event_date = today + timedelta(days=(7 - today.weekday()) % 7)
            else:
                event_date = today + timedelta(days=offset_days)
            event = self._get_or_create_page(
                event_index, EventPage, title, nb_locale,
                event_type=event_type,
                event_date=event_date,
                event_time=(
                    datetime.strptime(time_str, "%H:%M").time() if time_str else None
                ),
                end_date=(
                    event_date + timedelta(days=end_offset_days)
                    if end_offset_days else None
                ),
            )
            if title == "Fadderuke":
                # Not translated yet -- _seed_fadderuke_sub_events (below)
                # sets calendar_legend/related_unions on this nb page and
                # translates it itself, before creating any sub-event (see
                # that method's own comment for why the ordering matters).
                fadderuke = event
            else:
                self._translate_page(event, en_locale)

        self._seed_fadderuke_sub_events(fadderuke, nb_locale, en_locale, seed_image)

    def _seed_fadderuke_unions(self, nb_locale, en_locale, seed_image):
        """Creates the minimal UnionPage per name in FADDERUKE_UNION_SPECS
        (as children of the same Studentforeninger category Testforening
        1/2 live under), for FADDERUKE_SUB_EVENT_UNIONS to link sub-events
        to via EventPage.related_unions. Returns {title: nb UnionPage}."""
        union_category = StudentUnionCategoryPage.objects.get(
            slug="studentforeninger", locale=nb_locale
        )
        unions = {}
        for title in FADDERUKE_UNION_SPECS:
            union = self._get_or_create_page(
                union_category, UnionPage, title, nb_locale,
                logo=seed_image,
                purpose="En studentforening ved Ifi generert av seed-scriptet.",
                union_type="general",
            )
            self._translate_page(union, en_locale)
            unions[title] = union
        return unions

    def _seed_fadderuke_sub_events(self, fadderuke, nb_locale, en_locale, seed_image):
        """Fills Fadderuke with a full Mon-Fri programme (see
        FADDERUKE_SUB_EVENT_SPECS) and its own calendar-color legend, so
        EventPage.calendar_days has a realistic week to lay out instead of
        just the lone parent event."""
        if not fadderuke.calendar_legend:
            fadderuke.calendar_legend = [
                ("entry", {"color": color, "label": label})
                for color, label in FADDERUKE_LEGEND
            ]
            fadderuke.save_revision().publish()

        unions = self._seed_fadderuke_unions(nb_locale, en_locale, seed_image)

        # Fadderstyret hosts the whole week, not just one sub-event -- set
        # directly on Fadderuke itself so EventPage.all_related_unions has
        # a real "host" to show at the top level (every other union only
        # ever hosts one specific sub-event, which all_related_unions caps
        # down to "collaborator" once rolled up to the parent).
        if not fadderuke.related_unions:
            fadderuke.related_unions = [
                ("union", {"union": unions["Fadderstyret"], "role": "host"}),
            ]
            fadderuke.save_revision().publish()

        # Must happen before any sub-event below is translated, not after --
        # wagtail-localize's Translation.save_target(copy_parent_pages=True)
        # auto-creates a bare, untranslated copy of a page's parent the
        # moment a CHILD gets translated and the parent doesn't have a
        # translation yet (so the child has somewhere to live in the target
        # locale tree). If that fired first, has_translation(en_locale)
        # would already be True by the time _translate_page(fadderuke, ...)
        # ran, and it would skip -- silently leaving Fadderuke's own en
        # translation as that untranslated auto-copy forever (calendar_legend/
        # related_unions structurally present, but never actually translated).
        self._translate_page(fadderuke, en_locale)

        for day_offset, title, event_type, start, end, color in FADDERUKE_SUB_EVENT_SPECS:
            event_date = fadderuke.event_date + timedelta(days=day_offset)
            sub_event = self._get_or_create_page(
                fadderuke, EventPage, title, nb_locale,
                event_type=event_type,
                event_date=event_date,
                event_time=datetime.strptime(start, "%H:%M").time(),
                event_end_time=datetime.strptime(end, "%H:%M").time(),
                calendar_color=color,
                show_on_homepage=False,
                is_highlighted=title in FADDERUKE_HIGHLIGHTED_TITLES,
            )

            union_roles = FADDERUKE_SUB_EVENT_UNIONS.get(title)
            if union_roles and not sub_event.related_unions:
                sub_event.related_unions = [
                    ("union", {"union": unions[union_title], "role": role})
                    for union_title, role in union_roles
                ]
                sub_event.save_revision().publish()

            self._translate_page(sub_event, en_locale)

    def _seed_tool(self, praktisk_category, nb_locale, en_locale, seed_image):
        # core_views.main_view looks this category up by the hardcoded slug
        # "ifi-verktøy" -- plain slugify() would strip the "ø", so it's
        # pinned explicitly here to keep the homepage's tools section working.
        # show_nested_tools=True so this category's own page also
        # demonstrates CategoryPage.show_nested_tools (article_models.py):
        # the tool below (nested_tool_category's own direct child, i.e. this
        # category's *grandchild*) shows up here alongside Test-verktøy,
        # not just on nested_tool_category's own page.
        tool_category = self._get_or_create_page(
            praktisk_category, CategoryPage, "Ifi verktøy", nb_locale,
            color="turq", show_in_menu=True, slug="ifi-verktøy",
            show_nested_tools=True,
        )
        self._translate_page(tool_category, en_locale)

        tool = self._get_or_create_page(
            tool_category, ToolPage, "Test-verktøy", nb_locale,
            description="Et test-verktøy generert av seed-scriptet.",
            image=seed_image,
            image_overlay=True,
            link="https://example.com",
            made_by="Ifi Platform",
            preview_images=[("image", seed_image)],
        )
        self._translate_page(tool, en_locale)

        nested_tool_category = self._get_or_create_page(
            tool_category, CategoryPage, "UiO verktøy", nb_locale,
            color="pink", show_in_menu=False, slug="uio-verktoy",
        )
        self._translate_page(nested_tool_category, en_locale)

        nested_tool = self._get_or_create_page(
            nested_tool_category, ToolPage, "Nøstet test-verktøy", nb_locale,
            description=(
                "Et nøstet test-verktøy generert av seed-scriptet, for å "
                "vise Ifi verktøy sin \"vis nøstede verktøy\"-innstilling."
            ),
            image=seed_image,
            link="https://example.com",
            made_by="Ifi Platform",
        )
        self._translate_page(nested_tool, en_locale)

    def _seed_new_student_articles(self, praktisk_category, nb_locale, en_locale, seed_image):
        # core_views.main_view looks this category up by the hardcoded slug
        # "ny-ifi-student" to power the homepage's "New Student?" dropdown
        # (mirrors _seed_tool's pinned "ifi-verktøy" slug above).
        new_student_category = self._get_or_create_page(
            praktisk_category, CategoryPage, "Ny Ifi Student?", nb_locale,
            slug="ny-ifi-student", color="turq", show_in_menu=False,
            intro="Her er alt du skulle trenge som en ny Ifi Student!",
        )
        self._translate_page(new_student_category, en_locale)

        today = timezone.now().date()
        for title, intro, heading, text in NEW_STUDENT_ARTICLE_SPECS:
            article = self._get_or_create_page(
                new_student_category, ArticlePage, title, nb_locale,
                intro=intro,
                published_date=today,
                hero_image=seed_image,
                body=self._build_article_body(heading, text),
            )
            self._translate_page(article, en_locale)

    def _build_article_body(self, heading=None, text=None):
        if heading is None and text is None:
            return [item for item in ARTICLE_BODY]
        return [
            ("heading", {"text": heading, "level": "h2"}),
            ("paragraph", {"text": RichText(f"<p>{text}</p>")}),
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
        for i, spec in enumerate(BOARD_MESSAGE_SPECS):
            title = spec["title"]
            message = HomeBoardMessage.objects.filter(
                title=title, locale=nb_locale
            ).first()
            if message is None:
                message = HomeBoardMessage(
                    title=title,
                    date=timezone.now().date(),
                    body=RichText(spec["body"]),
                    sender_name=spec["sender_name"],
                    sender_role="Seed script",
                    order=i,
                    display_seconds=spec["display_seconds"],
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

    def _translate_page(self, nb_page, en_locale):
        """Produce a real English translation of `nb_page` via wagtail_localize's
        actual PO import/export pipeline (submit for translation -> export PO ->
        fill in msgstr from TRANSLATIONS -> import PO -> publish), rather than
        hand-writing a second copy of every field. Strings with no entry in
        TRANSLATIONS are left untranslated and fall back to the nb text."""
        if nb_page.has_translation(en_locale):
            self.skipped_count += 1
            return nb_page.get_translation(en_locale)

        source, _ = TranslationSource.get_or_create_from_instance(nb_page)
        translation, _ = Translation.objects.get_or_create(
            source=source, target_locale=en_locale
        )

        po = translation.export_po()
        for entry in po:
            text = TRANSLATIONS.get(entry.msgid)
            if text:
                entry.msgstr = text
        translation.import_po(po, translation_type="machine", tool_name="Seed script")
        translation.save_target(publish=True)

        # wagtail_localize doesn't translate slugs (they're excluded from the
        # PO segments), so the target page keeps the nb slug by default --
        # re-slugify from the now-translated title instead. Must be a plain,
        # unrestricted .save(): publish() doesn't write slug back to the live
        # row at all, and save(update_fields=["slug"]) recomputes url_path in
        # memory but then drops it since it's not in update_fields, breaking
        # descendant URLs silently.
        en_page = translation.get_target_instance()
        new_slug = slugify(en_page.title)
        if new_slug and new_slug != en_page.slug:
            en_page.slug = find_available_slug(en_page.get_parent(), new_slug)
            en_page.save()

        self.created_count += 1
        self.stdout.write(
            f"  translated {type(nb_page).__name__} (en): {nb_page.title}"
        )
        return en_page

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
