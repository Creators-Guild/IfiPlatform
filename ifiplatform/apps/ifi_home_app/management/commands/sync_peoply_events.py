"""Creates real EventPages from Peoply, one per UnionPage that has a
peoply_organization_id set (see that field's own help text).

Create-only: an event already synced (matched by external_source="peoply" +
external_uid, see EventPage's own comment on those fields) is left alone on
every later run, even if it changed on Peoply or an editor edited it here --
sync only ever adds, it never overwrites or removes. A later resync won't
pick up a changed venue/time on Peoply's side either; re-running this isn't
a way to keep an event's details live-updated, just to catch new ones.

Run manually, or wire into a schedule later (ci-deploy.yml already has a
nightly cron for deploys as a precedent) once that's actually wanted."""

from datetime import datetime, time, timedelta, timezone as dt_timezone
from html import escape

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from wagtail.coreutils import find_available_slug
from wagtail.models import Locale

from ifi_home_app.integrations.peoply_api import get_events
from ifi_home_app.models.article.unions import UnionPage
from ifi_home_app.models.event_models import EventIndexPage, EventPage, PeoplySyncState, SITE_TIMEZONE


def _plain_text_to_html(text):
    """Peoply's description is plain text with \\r\\n line breaks, not HTML
    -- RichTextField expects HTML. A blank line becomes a paragraph break, a
    single line break becomes <br>."""
    paragraphs = text.replace("\r\n", "\n").split("\n\n")
    return "".join(
        f"<p>{escape(paragraph).replace(chr(10), '<br>')}</p>"
        for paragraph in paragraphs
        if paragraph.strip()
    )


def _to_local(iso_string):
    """Peoply timestamps are ISO-8601 UTC -- convert to the site's own
    timezone so event_date/event_time land on the right local day/hour."""
    parsed = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return parsed.astimezone(SITE_TIMEZONE)


def _infer_event_type(title):
    """Peoply events are overwhelmingly social (pub crawls, parties,
    workshops, ...), but "Bedriftspresentasjon" ("company presentation") in
    the title is a reliable enough signal to tag those as EventPage's
    "company" type instead -- common for unions like Navet that host a lot
    of them. Editors can always correct this by hand either way."""
    if "bedriftspresentasjon" in title.lower():
        return "company"
    return "social"


class Command(BaseCommand):
    help = (
        "Creates EventPages from Peoply for every UnionPage with a "
        "peoply_organization_id set. Create-only -- never updates or "
        "removes an already-synced event, even if it changed on Peoply."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--after",
            help="YYYY-MM-DD -- only sync events starting on/after this date. Defaults to today.",
        )

    def handle(self, *args, **options):
        after_date = (
            datetime.strptime(options["after"], "%Y-%m-%d").replace(tzinfo=dt_timezone.utc)
            if options["after"] else timezone.now()
        )

        try:
            nb_locale = Locale.objects.get(language_code="nb")
        except Locale.DoesNotExist as exc:
            raise CommandError("No nb Locale found -- run migrate first.") from exc

        event_index = EventIndexPage.objects.live().filter(locale=nb_locale).first()
        if event_index is None:
            raise CommandError("No live nb EventIndexPage found to create synced events under.")

        unions = UnionPage.objects.live().exclude(peoply_organization_id="")
        # A union's nb/en translations share the same peoply_organization_id
        # -- sync once per union, not once per locale.
        seen_translation_keys = set()
        created_count = 0
        skipped_count = 0

        for union in unions:
            if union.translation_key in seen_translation_keys:
                continue
            seen_translation_keys.add(union.translation_key)

            for event in get_events(union.peoply_organization_id, after_date):
                if EventPage.objects.filter(
                    external_source="peoply", external_uid=event["id"]
                ).exists():
                    skipped_count += 1
                    continue

                start = _to_local(event["startDate"])
                end = _to_local(event["endDate"]) if event.get("endDate") else None

                page_kwargs = {
                    "title": event["title"],
                    "slug": find_available_slug(event_index, slugify(event["title"])),
                    "locale": nb_locale,
                    "event_type": _infer_event_type(event["title"]),
                    "event_date": start.date(),
                    "event_time": start.time(),
                    "location": (event.get("freeformAddress") or event.get("locationName") or "")[:200],
                    "intro": _plain_text_to_html(event.get("description") or ""),
                    "external_source": "peoply",
                    "external_uid": event["id"],
                    "peoply_url": f"https://peoply.app/events/{event['urlId']}",
                    # Only ever set when Peoply's own registrationMode is
                    # "EXTERNAL" -- confirmed empirically (99 real events
                    # sampled) that "PEOPLY"-mode events always have a null
                    # externalUrl, and every "EXTERNAL"-mode one has a real
                    # one. Left blank for "PEOPLY" mode -- event_page.html
                    # uses that (blank signup_url on a peoply-sourced event)
                    # to tell "sign up on Peoply itself" apart from "sign up
                    # somewhere else", rather than needing a separate field.
                    "signup_url": event.get("externalUrl") or "",
                    "related_unions": [("union", {"union": union, "role": "host"})],
                }
                if end is not None:
                    # end_date means "still happening" for every hour of
                    # that whole day too (EventPage.is_happening_now checks
                    # calendar dates, not clock time) -- correct for a
                    # genuine multi-day event, but wrong for a normal party
                    # that just runs past local midnight: Peoply's own UTC
                    # timestamps are same-day (e.g. 16:00-23:00 UTC), and
                    # only *look* cross-day after converting to Oslo time
                    # (CEST is UTC+2, so 23:00 UTC becomes 01:00 the next
                    # local day). Confirmed against real synced data -- a
                    # CYB event stored this way showed as "happening now"
                    # for nearly 24h after it had actually ended. A
                    # same-day end before this cutoff is assumed to be that
                    # kind of overflow, not a real multi-day event; treated
                    # as ending within the start day for is_happening_now's
                    # purposes, even though the clock time is technically
                    # past midnight.
                    next_day_early_morning = (
                        end.date() == start.date() + timedelta(days=1)
                        and end.time() < time(6, 0)
                    )
                    if end.date() == start.date() or next_day_early_morning:
                        page_kwargs["event_end_time"] = end.time()
                    else:
                        page_kwargs["end_date"] = end.date()

                page = EventPage(**page_kwargs)
                event_index.add_child(instance=page)
                page.save_revision().publish()
                created_count += 1
                self.stdout.write(f"  created EventPage: {event['title']}")

        PeoplySyncState.touch()
        self.stdout.write(self.style.SUCCESS(
            f"Done: {created_count} event(s) created, {skipped_count} already existed."
        ))
