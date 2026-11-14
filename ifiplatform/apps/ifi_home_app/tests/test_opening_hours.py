# pylint: disable=C0114,C0115,C0116
from datetime import date, datetime, time
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import translation

from ifi_home_app.management.seed_dev_data.opening_hours import (
    LOCATION_SPECS,
    build_location,
)
from ifi_home_app.models import Location, LocationClosure
from ifi_home_app.models.event.constants import SITE_TIMEZONE
from ifi_home_app.models.opening_hours import location_status, opening_hours_now

# Week of Mon 9 – Sun 15 November 2026.
TUE, THU, FRI, SAT, SUN = (date(2026, 11, d) for d in (10, 12, 13, 14, 15))


def _at(day, hour, minute=0):
    return datetime.combine(day, time(hour, minute), tzinfo=SITE_TIMEZONE)


def _location(name):
    """An unsaved Location built from the seed specs."""
    return build_location(next(s for s in LOCATION_SPECS if s[0] == name))


def _event(day, hour, end=None, title="Pubkveld"):
    return SimpleNamespace(
        event_date=day, event_time=time(hour), event_end_time=end, title=title
    )


class LocationStatusTests(SimpleTestCase):
    def setUp(self):
        self.enterContext(translation.override("en"))

    def status(self, name, moment, events=()):
        return location_status(_location(name), moment, events)

    def test_building_open_then_card_then_closed(self):
        self.assertEqual(self.status("Ole-Johan Dahls hus", _at(TUE, 10)).state, "open")
        self.assertEqual(
            self.status("Ole-Johan Dahls hus", _at(TUE, 10)).next_text,
            "card needed from 18:00",
        )
        evening = self.status("Ole-Johan Dahls hus", _at(TUE, 18, 20))
        self.assertEqual((evening.state, evening.next_text), ("card", "until 24:00"))
        night = self.status("Ole-Johan Dahls hus", _at(SUN, 4))
        self.assertEqual(
            (night.state, night.next_text), ("closed", "card access from 05:00")
        )

    def test_exact_boundaries(self):
        self.assertEqual(self.status("Ole-Johan Dahls hus", _at(TUE, 7)).state, "open")
        self.assertEqual(
            self.status("Ole-Johan Dahls hus", _at(TUE, 17, 59)).state, "open"
        )
        self.assertEqual(self.status("Ole-Johan Dahls hus", _at(TUE, 18)).state, "card")

    def test_next_opening_on_another_day_names_the_day(self):
        status = self.status("Ole-Johan Spiseri", _at(SAT, 12))
        self.assertEqual(
            (status.state, status.next_text), ("closed", "opens Mon 08:00")
        )

    def test_friday_bar_runs_past_midnight(self):
        friday = self.status("Escape", _at(FRI, 19, 30))
        self.assertEqual((friday.state, friday.next_text), ("open", "until 01:00"))
        self.assertEqual([p["label"] for p in friday.parts if p["active"]], ["Bar"])
        saturday_night = self.status("Escape", _at(SAT, 0, 30))
        self.assertEqual(saturday_night.state, "open")
        self.assertEqual(self.status("Escape", _at(SAT, 1, 0)).state, "closed")

    def test_event_without_end_time_counts_as_open_until_one(self):
        status = self.status("Escape", _at(TUE, 22), [_event(TUE, 19)])
        self.assertEqual((status.state, status.next_text), ("open", "until 01:00"))
        self.assertTrue(status.event_running)
        self.assertEqual([p["label"] for p in status.parts if p["active"]], ["Event"])

    def test_event_later_today_is_announced(self):
        event = _event(TUE, 19, end=time(23))
        status = self.status("Escape", _at(TUE, 17), [event])
        self.assertEqual((status.state, status.next_text), ("closed", "opens 19:00"))
        self.assertFalse(status.event_running)
        self.assertIs(status.event, event)

    def test_half_price_soon_and_now(self):
        soon = self.status("Ole-Johan Spiseri", _at(THU, 15, 10))
        self.assertEqual(soon.half_price, "soon")
        self.assertEqual(soon.half_price_from.time(), time(15, 30))
        self.assertEqual(
            self.status("Ole-Johan Spiseri", _at(THU, 15, 45)).half_price, "now"
        )
        self.assertEqual(
            self.status("Ole-Johan Spiseri", _at(FRI, 14, 10)).half_price, "soon"
        )
        self.assertEqual(self.status("Ole-Johan Spiseri", _at(THU, 12)).half_price, "")

    def test_closure_overrides_the_week(self):
        location = _location("Ole-Johan Spiseri")
        location.closures.add(  # pylint: disable=no-member
            LocationClosure(start_date=TUE, end_date=THU, reason="Inventory")
        )
        status = location_status(location, _at(TUE, 10))
        self.assertEqual(
            (status.state, status.next_text), ("closed", "Closed: Inventory")
        )
        self.assertEqual(location_status(location, _at(FRI, 10)).state, "open")

    def test_hours_lines_mark_today(self):
        lines = self.status("Ole-Johan Dahls hus", _at(SAT, 12)).hours
        self.assertEqual(
            [(l["days"], l["times"], l["today"]) for l in lines],
            [("Mon–Fri", "07:00–18:00", False), ("Every day", "05:00–24:00", True)],
        )


class OpeningHoursBoxTests(TestCase):
    def test_renders_statuses_and_warning(self):
        Location.objects.all().delete()  # the ones migration 0162 adds
        for order, name in enumerate(["Ole-Johan Dahls hus", "Escape"]):
            location = _location(name)
            location.sort_order = order
            location.save()
        statuses = opening_hours_now(_at(FRI, 19, 30))
        request = RequestFactory().get("/")
        with translation.override("en"):
            html = render_to_string(
                "home/partials/openinghours/openinghours.html",
                {"opening_hours": statuses, "request": request},
                request=request,
            )
        self.assertEqual(
            [s.location.name for s in statuses], ["Ole-Johan Dahls hus", "Escape"]
        )
        self.assertIn("Card needed", html)
        self.assertIn('class="is-on">Bar<', html)
        self.assertIn("frivillige studenter", html)

    def test_renders_nothing_without_places(self):
        html = render_to_string(
            "home/partials/openinghours/openinghours.html", {"opening_hours": []}
        )
        self.assertEqual(html.strip(), "")


class InitialPlacesMigrationTests(TestCase):
    def test_fresh_database_has_the_four_places(self):
        self.assertEqual(
            list(Location.objects.values_list("name", flat=True)),
            ["Ole-Johan Dahls hus", "Ifi-biblioteket", "Ole-Johan Spiseri", "Escape"],
        )
        escape = Location.objects.get(name="Escape")
        self.assertEqual(escape.event_location, "Escape")
        self.assertEqual(
            [(p.label, p.friday) for p in escape.periods.all()],
            [("Kafé", True), ("Bar", True)],
        )
