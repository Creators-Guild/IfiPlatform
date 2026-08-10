"""One-off seeder for Fadderuka 2026's day-by-day schedule (10.-14. august),
transcribed from the printed program, as sub-events under the "Fadderuke"
EventPage. Meant to be run once against the real (nb) database -- production
included -- not just local dev, so unlike seed_dev_data.py this has no
DEBUG/--force guard.

Safe to re-run: every sub-event is looked up by its own (parent, slug,
locale) before creation, same idempotency pattern as seed_dev_data.py's
_get_or_create_page, so running this twice does not create duplicates.

Usage:
    py manage.py seed_fadderuka_2026_subevents --dry-run   # preview only
    py manage.py seed_fadderuka_2026_subevents              # actually write

This file is a one-off, not meant to stay in the codebase -- once the data
is confirmed live, delete it manually (it does not delete itself).
"""

from datetime import date, time

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from wagtail.coreutils import find_available_slug
from wagtail.models import Locale

from ifi_home_app.models.article_models import UnionPage
from ifi_home_app.models.event_models import EventIndexPage, EventPage

PARENT_EVENT = {
    "title": "Fadderuke",
    "slug": "fadderuke",
    "event_type": "social",
    "event_date": date(2026, 8, 10),
    "end_date": date(2026, 8, 14),
    "intro": (
        "<p>Fadderuka 2026, 10.– 14. august. Se dagsprogrammet under.</p>"
        "<p>Escape kafé har åpent kl. 12–15 torsdag og fredag.</p>"
    ),
    # Matches the printed program's own color legend verbatim -- "green"
    # is the one addition (Realstart, the one cell the printed legend
    # itself never assigned a color to).
    "calendar_legend": [
        ("entry", {"color": "blue", "label": "Studierelevant"}),
        ("entry", {"color": "yellow", "label": "Mat"}),
        ("entry", {"color": "orange", "label": "Alkoholfritt"}),
        ("entry", {"color": "pink", "label": "Både med og uten alkohol"}),
        ("entry", {"color": "green", "label": "Felles for hele MatNat"}),
    ],
}

# (date, start HH:MM, end HH:MM or None, title, event_type, calendar_color,
# intro) -- one row per cell in the printed schedule, including every
# parallel/alternative track in a shared time slot as its own sibling
# sub-event (the model has no notion of a "track", so overlapping sessions
# just share a date/time -- the week-calendar view on the parent event's
# page fans them out side by side). Every explicit end time below matches
# the printed schedule; open-ended "fra kl. X" evening slots (no end
# printed) get a nominal 3-hour block instead of a bare start time, so they
# still render as a real block in that calendar rather than a 1-hour
# default sized for a short meeting. calendar_color reproduces the printed
# schedule's own legend (blue=studierelevant, yellow=mat,
# orange=alkoholfritt, pink=med/uten alkohol) rather than event_type's own
# 4 categories, which can't distinguish e.g. "food" from "alcohol-free
# social" -- "green" is the one cell the printed legend itself didn't
# define (Realstart), kept as its own color rather than folded into pink.
SUBEVENTS = [
    # -- Mandag 10.08 -----------------------------------------------------
    (date(2026, 8, 10), "09:00", "10:00", "Oppmøteregistrering", "academic", "blue",
     "Oppmøteregistrering for nye studenter."),
    (date(2026, 8, 10), "10:00", "12:00", "Programvis opplegg", "academic", "blue",
     "Programvis opplegg, kl. 10:00–12:00."),
    (date(2026, 8, 10), "12:00", "13:00", "Lunsj med fadderne", "social", "yellow",
     "Lunsj med fadderne."),
    (date(2026, 8, 10), "13:00", "15:00", "Programvis opplegg", "academic", "blue",
     "Programvis opplegg, kl. 13:00–15:00."),
    (date(2026, 8, 10), "15:00", "16:00", "Tale på universitetsplassen", "academic", "blue",
     "Tale på universitetsplassen, kl. 15:00–16:00."),
    (date(2026, 8, 10), "16:00", "17:00", "Grill n' chill", "social", "yellow",
     "Grill n' chill, kl. 16:00–17:00."),
    (date(2026, 8, 10), "18:00", "19:00", "Quiz m/CYB", "social", "pink",
     "Quiz, i regi av CYB. Kl. 18:00–19:00."),
    (date(2026, 8, 10), "18:00", "21:00", "Brettspillkveld m/FUI", "social", "orange",
     "Brettspillkveld, i regi av FUI. Fra kl. 18:00."),

    # -- Tirsdag 11.08 ------------------------------------------------------
    (date(2026, 8, 11), "09:00", "12:30", "Forkurs", "academic", "blue",
     "Forkurs, kl. 09:00–12:30."),
    (date(2026, 8, 11), "12:00", "13:00", "Lunsj", "social", "yellow", "Lunsj."),
    (date(2026, 8, 11), "13:00", "16:00", "IFI-Olympiaden", "social", "orange",
     "IFI-Olympiaden, kl. 13:00–16:00."),
    (date(2026, 8, 11), "16:00", "17:00", "Grill n' chill + Kåring av Olympiade vinner", "social", "yellow",
     "Grill n' chill og kåring av Olympiade-vinner, kl. 16:00–17:00."),
    (date(2026, 8, 11), "18:00", "21:00", "Kickoff m/Navet", "social", "pink",
     "Kickoff, i regi av Navet. Fra kl. 18:00."),
    (date(2026, 8, 11), "18:00", "21:00", "Spillkveld m/Progsys", "social", "pink",
     "Spillkveld, i regi av Progsys. Fra kl. 18:00."),
    (date(2026, 8, 11), "18:00", "21:00", "Musikkbingo m/MAKI", "social", "orange",
     "Musikkbingo, i regi av MAKI. Fra kl. 18:00."),

    # -- Onsdag 12.08 ---------------------------------------------------
    (date(2026, 8, 12), "09:00", "12:30", "Forkurs", "academic", "blue",
     "Forkurs, kl. 09:00–12:30."),
    (date(2026, 8, 12), "12:00", "13:00", "Lunsj", "social", "yellow", "Lunsj."),
    (date(2026, 8, 12), "13:00", "14:00", "How to IFI m/FUI", "academic", "blue",
     "How to IFI, i regi av FUI. Kl. 13:00–14:00."),
    (date(2026, 8, 12), "14:00", "16:00", "Foreningstorg", "social", "orange",
     "Foreningstorg, kl. 14:00–16:00."),
    (date(2026, 8, 12), "14:00", "15:00", "Introduksjon til foreningslivet m/FU", "academic", "orange",
     "Introduksjon til foreningslivet, i regi av FU. Kl. 14:00–15:00."),
    (date(2026, 8, 12), "16:00", "17:00", "Grill n' chill", "social", "yellow",
     "Grill n' chill, kl. 16:00–17:00."),
    (date(2026, 8, 12), "18:00", "21:00", "Temafest m/Dagen@ifi", "social", "pink",
     "Temafest, i regi av Dagen@IFI. Fra kl. 18:00."),

    # -- Torsdag 13.08 --------------------------------------------------
    (date(2026, 8, 13), "12:00", "13:00", "Lunsj + Speedfriending m/Fadderstyret", "social", "yellow",
     "Lunsj og Speedfriending, i regi av Fadderstyret."),
    (date(2026, 8, 13), "13:00", "16:00", "Gaffaregatta m/Mikro", "social", "orange",
     "Gaffaregatta, i regi av Mikro. Kl. 13:00–16:00."),
    (date(2026, 8, 13), "13:00", "16:00", "Volleyball-turnering m/VIFI", "social", "orange",
     "Volleyballturnering, i regi av VIFI. Kl. 13:00–16:00."),
    (date(2026, 8, 13), "14:00", "16:00", "Kaffe-smaking m/CYB & kaffeforeningen", "social", "orange",
     "Kaffesmaking, i regi av CYB og kaffeforeningen. Kl. 14:00–16:00."),
    (date(2026, 8, 13), "16:00", "17:00", "Grill n' chill", "social", "yellow",
     "Grill n' chill, kl. 16:00–17:00."),
    (date(2026, 8, 13), "18:00", "21:00", "Paint & Sip m/Defi", "social", "pink",
     "Paint & Sip, i regi av Defi. Fra kl. 18:00."),
    (date(2026, 8, 13), "19:00", "22:00", "Realstart! Felles kveld for hele MatNat!", "social", "green",
     "Felles kveldsarrangement for hele MatNat. Fra kl. 19:00."),

    # -- Fredag 14.08 -----------------------------------------------------
    (date(2026, 8, 14), "12:00", "13:00", "Lunsj", "social", "yellow", "Lunsj."),
    (date(2026, 8, 14), "13:00", "15:00", "Shitty cars m/Sonen", "social", "orange",
     "Shitty cars, i regi av Sonen. Kl. 13:00–15:00."),
    (date(2026, 8, 14), "13:00", "16:00", "Fotball-turnering m/FIFI", "social", "orange",
     "Fotballturnering, i regi av FIFI. Kl. 13:00–16:00."),
    (date(2026, 8, 14), "15:00", "16:00", "2000-Meter m/Digitus", "social", "pink",
     "2000-Meter, i regi av Digitus. Kl. 15:00–16:00."),
    (date(2026, 8, 14), "16:00", "17:00", "Grill n' chill + Kakefredag m/Progsys", "social", "yellow",
     "Grill n' chill og Kakefredag, i regi av Progsys. Kl. 16:00–17:00."),
    (date(2026, 8, 14), "18:00", "21:00", "CTRL+ALT+DEL m/CYB", "social", "pink",
     "CTRL+ALT+DEL, i regi av CYB. Fra kl. 18:00."),
]

DAY_ABBR = {
    date(2026, 8, 10): "man",
    date(2026, 8, 11): "tir",
    date(2026, 8, 12): "ons",
    date(2026, 8, 13): "tor",
    date(2026, 8, 14): "fre",
}

# (date, start HH:MM, title) -> the union credited in that title's own
# "m/X" text -- kept as a lookup separate from SUBEVENTS rather than an
# extra column on every one of them, so this doesn't need to touch every
# existing row's shape. Only the events that actually credit a union are
# listed here; anything absent just means "no union in the title" (most
# meals/breaks/plenary sessions). Looked up as a real UnionPage by title
# at runtime (_find_union) -- deliberately not resolved to a page id here,
# since the correct page (if it even exists yet) can only be found against
# whatever database this actually runs against, not this dev checkout.
SUBEVENT_UNIONS = {
    (date(2026, 8, 10), "18:00", "Quiz m/CYB"): "CYB",
    (date(2026, 8, 10), "18:00", "Brettspillkveld m/FUI"): "FUI",
    (date(2026, 8, 11), "18:00", "Kickoff m/Navet"): "Navet",
    (date(2026, 8, 11), "18:00", "Spillkveld m/Progsys"): "Progsys",
    (date(2026, 8, 11), "18:00", "Musikkbingo m/MAKI"): "MA:KI",  # real UnionPage title has the colon
    (date(2026, 8, 12), "13:00", "How to IFI m/FUI"): "FUI",
    (date(2026, 8, 12), "14:00", "Introduksjon til foreningslivet m/FU"): "FU",
    # Both credited on the real Peoply listing (co-hosted with Fadderstyret)
    # -- see SUBEVENT_PEOPLY_INFO's own note on this event's real title.
    (date(2026, 8, 12), "18:00", "Temafest m/Dagen@ifi"): ["Dagen@ifi", "Fadderstyret"],
    (date(2026, 8, 13), "12:00", "Lunsj + Speedfriending m/Fadderstyret"): "Fadderstyret",
    (date(2026, 8, 13), "13:00", "Gaffaregatta m/Mikro"): "Mikro",
    (date(2026, 8, 13), "13:00", "Volleyball-turnering m/VIFI"): "VIFI",
    (date(2026, 8, 13), "14:00", "Kaffe-smaking m/CYB & kaffeforeningen"): "CYB",
    (date(2026, 8, 13), "18:00", "Paint & Sip m/Defi"): "Defi",
    (date(2026, 8, 14), "13:00", "Shitty cars m/Sonen"): "Sonen",
    (date(2026, 8, 14), "13:00", "Fotball-turnering m/FIFI"): "FIFI",
    (date(2026, 8, 14), "15:00", "2000-Meter m/Digitus"): "Digitus",
    (date(2026, 8, 14), "16:00", "Grill n' chill + Kakefredag m/Progsys"): "Progsys",
    (date(2026, 8, 14), "18:00", "CTRL+ALT+DEL m/CYB"): "CYB",
}

# (date, start HH:MM, title) -> confirmed details from that event's real
# Peoply listing (peoply.app) -- location and a fuller description, plus a
# corrected start/end time wherever the printed schedule's own time turned
# out to differ from what's actually published. Sparse and manually
# checked, not scraped: Peoply is a client-rendered SPA with nothing
# usable in its raw HTML (confirmed -- WebFetch against it returns an
# empty shell/"0 treff", even on org and listing pages), so this can only
# ever cover whichever events someone has actually opened in a real
# browser and reported back, not the full 35. Every intro here ends with
# an explicit "hentet fra Peoply" attribution line, per instruction --
# applied on top of (not replacing) SUBEVENTS' own event_type/
# calendar_color classification for that row.
SUBEVENT_PEOPLY_INFO = {
    (date(2026, 8, 11), "13:00", "IFI-Olympiaden"): {
        "location": "Ole Johan Dahls-hus, Gaustadalléen 23B, Oslo",
        "intro": (
            "<p>Vi i Fadderstyret ønsker å invitere dere til IFI-Olympiaden 2026! "
            "Det vil vare fra 13 til 16 i Ole-Johan Dahls hus den 11. august.</p>"
            "<p>Olympiade er et konkuranse-konsept hvor alle foreningene våre har "
            "egne poster på huset, hvor faddergruppene skal konkurrere i hvor mange "
            "poeng de kan score, samt gi en smakebit på de ulike arrangementene som "
            "finnes på IFI.</p>"
            "<p>Vinnerlaget (faddergruppe) vil få heder og ære, samt premie fra oss "
            "under grill n' chill ved IFI-dammen, tirsdag klokka 16-17 ish.</p>"
            "<p><em>Informasjon hentet fra Peoply.</em></p>"
        ),
    },
    (date(2026, 8, 11), "18:00", "Kickoff m/Navet"): {
        # Real event/start-end time differs from the printed schedule's own
        # 18:00 (no end given there) -- Peoply's own event card says 17:30-19:30.
        "event_time": "17:30",
        "event_end_time": "19:30",
        "location": "Ingensteds, Brenneriveien 9",
        "intro": (
            "<p><strong>Offisiell tittel på Peoply: Fadderuke-kickoff | Navet x "
            "Bekk</strong></p>"
            "<p>Gratis pizza, både faglige og underholdende innslag og DJ til langt "
            "på natt. Første ordentlige fest for nye informatikkstudenter!</p>"
            "<p>Arrangør: Navet x Bekk<br>Servering: Pizza fra Stykk<br>"
            "Språk: Norsk<br>Aldersgrense: 18+ (Husk ID!)</p>"
            "<p>Vi i Navet og Bekk ønsker deg hjertelig velkommen til IFI, og til "
            "årets Fadderuke-kickoff!</p>"
            "<p>Du har akkurat startet på informatikk, og vi vil gi deg en skikkelig "
            "start på studietiden. Det blir kort og godt program på scenen, gratis "
            "pizza fra Stykke, underhodning og DJ ut kvelden. Ta med faddergruppa, "
            "eller kom alene det er nok folk å mingle med!</p>"
            "<p>Slik blir kvelden:<br>"
            "17:30 &ndash; Dørene åpner. Navet står klare i døra og registrerer deg.<br>"
            "18:15 &ndash; Programmet starter (velkommen, intro til Bekk, "
            "studievalg-innslag, hvordan vinne IFI, sommerjobb i Bekk)<br>"
            "19:20 &ndash; Gratis pizza fra Stykke<br>"
            "20:30 &ndash; Underholdning<br>"
            "21:30 &ndash; DJ<br>"
            "23:30 &ndash; Takk for i kveld!</p>"
            "<p>Påmelding og mer info: "
            "<a href=\"https://ifinavet.no/events/h26-kickoff-med-bekk-1F7A\">"
            "ifinavet.no</a></p>"
            "<p><em>Informasjon hentet fra Peoply.</em></p>"
        ),
    },
    (date(2026, 8, 12), "14:00", "Introduksjon til foreningslivet m/FU"): {
        "location": "Store Auditorium, Kristen Nygaards hus, Gaustadalléen 23A, Oslo",
        "intro": (
            "<p>Nysgjerrig på hvilke foreninger vi har på IFI? Lyst til å bli med, "
            "men vet ikke helt hvordan? Vi svarer på store og små spørsmål i denne "
            "presentasjonen, før dere slippes fri til foreningstorget!</p>"
            "<p>NB: Det blir servert Pizza i starten, mellom How 2 IFI og "
            "Introduksjon til foreningslivet.</p>"
            "<p><em>Informasjon hentet fra Peoply.</em></p>"
        ),
    },
    (date(2026, 8, 12), "14:00", "Foreningstorg"): {
        "location": "Foajeen, Ole Johan Dahls-hus, Gaustadalléen 23B, Oslo",
        "intro": (
            "<p>Vi i Fadderstyret inviterer dere til Foreningstorget 2026. Dette vil "
            "foregå i fojaeen og vestibylen (innenfor hovedinngangen til OJD) den "
            "12. august fra ca. 14:00 til 16:00.</p>"
            "<p>På IFI har vi et kjempestort og lukrativt forenings-miljø, som består "
            "blant annet av linjeforeninger, quiz-mestere, idretts-entusiaster, "
            "bedriftskontakter, vår helt egen studentbar, og masse mer!</p>"
            "<p>Under foreningstorget har du og dine med-faddere/fadderbarn "
            "muligheten å utforske foreningslivet på IFI &ndash; hvem vet, kanskje "
            "du finner din forening? :)</p>"
            "<p>Vi ses!</p>"
            "<p><em>Informasjon hentet fra Peoply.</em></p>"
        ),
    },
    (date(2026, 8, 12), "18:00", "Temafest m/Dagen@ifi"): {
        "location": "Escape, Gaustadalléen 23B, Oslo",
        "intro": (
            "<p><strong>Offisiell tittel på Peoply: World Cup Party</strong> "
            "(co-arrangert av Dagen@ifi og Fadderstyret ved IFI)</p>"
            "<p>Dagen@ifi inviterer til temafest!! Årets tema er WORLD CUP. "
            "Vel møtt!!</p>"
            "<p>PS: Du finner dresscode inspo og mer info på Instagram "
            "@dagenatifi</p>"
            "<p><em>Informasjon hentet fra Peoply.</em></p>"
        ),
    },
    (date(2026, 8, 14), "16:00", "Grill n' chill + Kakefredag m/Progsys"): {
        "location": "Bliss",
        "intro": (
            "<p>Fredagen i fadderuken holdes Kakefredag! Kom innom for gode "
            "samtaler og gratis kake.</p>"
            "<p><em>Informasjon hentet fra Peoply (arrangementet er der oppført "
            "separat, i regi av ProgSys, uten grill n' chill).</em></p>"
        ),
    },
}

# calendar_color -> info_tag label -- calendar_color already encodes the
# printed schedule's own food/alcohol/study-relevant legend per event (see
# SUBEVENTS/PARENT_EVENT's calendar_legend above), so this reuses that
# same classification rather than a second, separately-judged tagging
# pass. info_tags is freeform (EventPage.info_tags's own docstring already
# names "Food served"/"Alcohol-free" as example values), so these labels
# aren't a fixed system, just what's actually known about each event.
TAG_BY_CALENDAR_COLOR = {
    "blue": "Studierelevant",
    "yellow": "Mat serveres",
    "orange": "Alkoholfritt",
    "pink": "Alkohol kan serveres",
    "green": "Felles for MatNat",
}


def _find_union(union_name, nb_locale):
    """The live UnionPage matching `union_name` in the nb locale, or None --
    tries an exact title match first (e.g. a union page literally titled
    "CYB"), then falls back to a substring match (e.g. "CYB" inside
    "CYB -- Cybernetisk Fagutvalg") for whichever unions have a longer
    official page title than the short credit line in the schedule. Never
    fabricates a match: if neither finds anything, the sub-event is just
    left without a related_unions entry rather than guessing wrong."""
    match = UnionPage.objects.live().filter(locale=nb_locale, title__iexact=union_name).first()
    if match is None:
        match = UnionPage.objects.live().filter(locale=nb_locale, title__icontains=union_name).first()
    return match


class Command(BaseCommand):
    help = (
        "Seeds Fadderuka 2026's printed day-by-day schedule as sub-events "
        "under the 'Fadderuke' EventPage (nb locale). Creates the parent "
        "event too if it doesn't already exist. Re-running is a no-op for "
        "anything that already exists."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created/skipped without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        nb_locale = Locale.objects.filter(language_code="nb").first()
        if nb_locale is None:
            raise CommandError("No 'nb' Locale found -- is this the right database?")

        event_index = EventIndexPage.objects.live().filter(locale=nb_locale).first()
        if event_index is None:
            raise CommandError(
                "No live EventIndexPage found in the nb locale -- create the "
                "Events section first."
            )

        fadderuke = EventPage.objects.child_of(event_index).filter(
            slug=PARENT_EVENT["slug"], locale=nb_locale
        ).first()

        if fadderuke is None:
            self.stdout.write(
                f"Would create parent event: {PARENT_EVENT['title']}"
                if dry_run else f"Creating parent event: {PARENT_EVENT['title']}"
            )
            if not dry_run:
                fadderuke = EventPage(
                    title=PARENT_EVENT["title"],
                    slug=PARENT_EVENT["slug"],
                    locale=nb_locale,
                    event_type=PARENT_EVENT["event_type"],
                    event_date=PARENT_EVENT["event_date"],
                    end_date=PARENT_EVENT["end_date"],
                    intro=PARENT_EVENT["intro"],
                    calendar_legend=PARENT_EVENT["calendar_legend"],
                )
                event_index.add_child(instance=fadderuke)
                fadderuke.save_revision().publish()
        else:
            self.stdout.write(
                f"Parent event already exists, reusing: {fadderuke.title} "
                f"(id={fadderuke.id})"
            )
            # A page with this exact slug can already exist without having
            # gone through PARENT_EVENT at all -- e.g. seed_dev_data.py's
            # own "Fadderuke" EVENT_SPECS entry, whose dates are relative to
            # whatever "today" was when it ran (today+3/+4 days), not the
            # real 10.-14. august. Only correcting the two date fields
            # specifically (not title/intro/etc.) -- narrow enough that it
            # can't clobber real editorial content, but still fixes exactly
            # this kind of stale-placeholder-date drift on re-run.
            date_fixed = (
                fadderuke.event_date != PARENT_EVENT["event_date"]
                or fadderuke.end_date != PARENT_EVENT["end_date"]
            )
            if date_fixed and not dry_run:
                fadderuke.event_date = PARENT_EVENT["event_date"]
                fadderuke.end_date = PARENT_EVENT["end_date"]
                fadderuke.save_revision().publish()
                self.stdout.write(
                    f"  corrected dates to {PARENT_EVENT['event_date']}"
                    f"–{PARENT_EVENT['end_date']}"
                )
            elif date_fixed:
                self.stdout.write(
                    f"  would correct dates to {PARENT_EVENT['event_date']}"
                    f"–{PARENT_EVENT['end_date']} "
                    f"(currently {fadderuke.event_date}–{fadderuke.end_date})"
                )

        created = 0
        skipped = 0
        union_linked = 0
        union_unmatched = set()
        tags_added = 0
        # Every distinct UnionPage credited on any sub-event, keyed by id --
        # rolled up onto the *parent* event's own related_unions afterward
        # (as "collaborator", see below) so Fadderuke's own page shows
        # everyone involved across the whole week, not just whichever union
        # an editor happened to add there by hand.
        sub_event_unions = {}

        peoply_updated = 0

        for event_date, time_str, end_time_str, title, event_type, calendar_color, intro in SUBEVENTS:
            slug_base = f"{DAY_ABBR[event_date]}-{time_str.replace(':', '')}-{slugify(title)}"

            # A credit can be one union or (rarely, e.g. a co-hosted party)
            # several -- SUBEVENT_UNIONS holds either a bare string or a
            # list, normalized to a list here so the rest of this loop
            # doesn't need to care which.
            union_names = SUBEVENT_UNIONS.get((event_date, time_str, title))
            if isinstance(union_names, str):
                union_names = [union_names]
            union_pages = []
            for union_name in union_names or []:
                union_page = _find_union(union_name, nb_locale)
                if union_page:
                    union_pages.append(union_page)
                    sub_event_unions[union_page.id] = union_page
                else:
                    union_unmatched.add(union_name)

            peoply_info = SUBEVENT_PEOPLY_INFO.get((event_date, time_str, title))

            if dry_run:
                existing = (
                    fadderuke is not None
                    and EventPage.objects.child_of(fadderuke)
                    .filter(slug=slug_base, locale=nb_locale)
                    .first()
                )
                union_note = ""
                if union_names:
                    match_summary = ", ".join(
                        f"{n}->{'OK' if _find_union(n, nb_locale) else 'NOT FOUND'}" for n in union_names
                    )
                    union_note = f" [union: {match_summary}"
                    if existing and existing.related_unions:
                        union_note += ", already linked, would leave as-is"
                    union_note += "]"
                tag_label = TAG_BY_CALENDAR_COLOR.get(calendar_color)
                tag_note = ""
                if tag_label:
                    has_tag = existing and tag_label in {t.name for t in existing.info_tags.all()}
                    tag_note = f" [tag: {tag_label}{', already present' if has_tag else ''}]"
                    tags_added += not has_tag
                peoply_note = ""
                if peoply_info:
                    peoply_note = " [peoply info available]"
                    peoply_updated += 1
                self.stdout.write(
                    f"  {'skip (exists)' if existing else 'create'}: "
                    f"{event_date} {time_str}–{end_time_str} {title}{union_note}{tag_note}{peoply_note}"
                )
                skipped += bool(existing)
                created += not existing
                continue

            existing = EventPage.objects.child_of(fadderuke).filter(
                slug=slug_base, locale=nb_locale
            ).first()

            changed = False
            if existing:
                sub_event = existing
                skipped += 1
            else:
                slug = find_available_slug(fadderuke, slug_base)
                sub_event = EventPage(
                    title=title,
                    slug=slug,
                    locale=nb_locale,
                    event_type=event_type,
                    event_date=event_date,
                    event_time=time.fromisoformat(time_str),
                    event_end_time=time.fromisoformat(end_time_str),
                    calendar_color=calendar_color,
                    intro=f"<p>{intro}</p>",
                )
                fadderuke.add_child(instance=sub_event)
                created += 1
                changed = True

            # Adds whichever credited unions aren't on this sub-event yet --
            # matched by page id, same "only ever add, never touch what's
            # already there" rule as the parent-level roll-up below, rather
            # than an all-or-nothing "only if completely empty" check: a
            # sub-event that already got a first host linked on an earlier
            # run (or by hand) can still pick up a second one a later
            # SUBEVENT_UNIONS update adds (e.g. Temafest turning out to be
            # co-hosted), without disturbing the host(s) already there.
            existing_sub_union_ids = {
                entry.value["union"].id for entry in sub_event.related_unions
                if entry.value["union"] is not None
            }
            missing_on_sub_event = [p for p in union_pages if p.id not in existing_sub_union_ids]
            if missing_on_sub_event:
                sub_event.related_unions = [
                    ("union", {"union": entry.value["union"], "role": entry.value["role"]})
                    for entry in sub_event.related_unions
                ] + [
                    ("union", {"union": p, "role": "host"}) for p in missing_on_sub_event
                ]
                union_linked += len(missing_on_sub_event)
                changed = True

            # Same "only ever adds, never overwrites" rule as related_unions
            # above -- an editor's own tags (or a previous run's) are left
            # alone, this only ever adds the one derived tag if it isn't
            # already present.
            tag_label = TAG_BY_CALENDAR_COLOR.get(calendar_color)
            if tag_label and tag_label not in {t.name for t in sub_event.info_tags.all()}:
                sub_event.info_tags.add(tag_label)
                tags_added += 1
                changed = True

            # Unlike related_unions/tags above, this *does* overwrite
            # location/intro/time -- SUBEVENT_PEOPLY_INFO is a short,
            # manually-checked allowlist of confirmed corrections (see its
            # own docstring), not something an editor could have touched
            # yet on a page this script only just created, so there's
            # nothing here to accidentally clobber.
            if peoply_info:
                peoply_changed = False
                new_location = peoply_info.get("location")
                if new_location and sub_event.location != new_location:
                    sub_event.location = new_location
                    peoply_changed = True
                new_intro = peoply_info.get("intro")
                if new_intro and sub_event.intro != new_intro:
                    sub_event.intro = new_intro
                    peoply_changed = True
                new_time = peoply_info.get("event_time")
                if new_time:
                    parsed = time.fromisoformat(new_time)
                    if sub_event.event_time != parsed:
                        sub_event.event_time = parsed
                        peoply_changed = True
                new_end_time = peoply_info.get("event_end_time")
                if new_end_time:
                    parsed = time.fromisoformat(new_end_time)
                    if sub_event.event_end_time != parsed:
                        sub_event.event_end_time = parsed
                        peoply_changed = True
                if peoply_changed:
                    peoply_updated += 1
                    changed = True

            if changed:
                sub_event.save_revision().publish()
                verb = "created" if not existing else "updated"
                self.stdout.write(f"  {verb}: {event_date} {time_str}–{end_time_str} {title}")

        # Roll every sub-event's credited union up onto the parent event
        # itself, as "collaborator" -- only ever *adding* missing ones
        # (matched by page id), never touching an entry already there
        # (e.g. Fadderstyret as "host", added by hand in the admin), so
        # this can't demote/duplicate anything an editor already set up.
        collaborators_added = 0
        if fadderuke is not None:
            existing_union_ids = {
                entry.value["union"].id
                for entry in fadderuke.related_unions
                if entry.value["union"] is not None
            }
            missing = [
                union_page for uid, union_page in sub_event_unions.items()
                if uid not in existing_union_ids
            ]
            if missing:
                collaborators_added = len(missing)
                if dry_run:
                    self.stdout.write(
                        "Would add as collaborator on Fadderuke: "
                        + ", ".join(sorted(u.title for u in missing))
                    )
                else:
                    new_entries = [
                        ("union", {"union": entry.value["union"], "role": entry.value["role"]})
                        for entry in fadderuke.related_unions
                    ]
                    new_entries += [
                        ("union", {"union": union_page, "role": "collaborator"})
                        for union_page in missing
                    ]
                    fadderuke.related_unions = new_entries
                    fadderuke.save_revision().publish()
                    self.stdout.write(
                        "Added as collaborator on Fadderuke: "
                        + ", ".join(sorted(u.title for u in missing))
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[dry run] ' if dry_run else ''}"
                f"Done: {created} sub-event(s) {'to create' if dry_run else 'created'}, "
                f"{skipped} already existed, {union_linked} host union(s) linked, "
                f"{tags_added} tag(s) added, {collaborators_added} parent-level "
                f"collaborator(s) added, {peoply_updated} sub-event(s) enriched with "
                "confirmed Peoply info."
            )
        )
        if union_unmatched:
            self.stdout.write(
                self.style.WARNING(
                    "No matching UnionPage found (left unlinked) for: "
                    + ", ".join(sorted(union_unmatched))
                )
            )
