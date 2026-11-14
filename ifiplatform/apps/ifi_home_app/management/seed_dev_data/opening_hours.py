"""Location seeding for the homepage's opening hours box: the four IFI
places with the hours from UiO's pages (Nov 2026). Escape's bar is usually
only open on Fridays; other bar nights are Peoply events at Escape."""

from datetime import time

from ifi_home_app.models import Location, OpeningPeriod

from .constants import ESCAPE_WARNING

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")
EVERY_DAY = WEEKDAYS + ("saturday", "sunday")

# (name, extra Location fields, [(label, days, opens, closes, access)])
LOCATION_SPECS = [
    (
        "Ole-Johan Dahls hus",
        {},
        [
            ("", WEEKDAYS, time(7), time(18), "open"),
            ("Kort + PIN", EVERY_DAY, time(5), time(0), "card"),
        ],
    ),
    (
        "Ifi-biblioteket",
        {},
        [
            ("Betjent", WEEKDAYS, time(10), time(14), "open"),
            ("Kort + kode", EVERY_DAY, time(5), time(0), "card"),
        ],
    ),
    (
        "Ole-Johan Spiseri",
        {"note": "Halvpris siste 30 min", "half_price_minutes": 30},
        [
            (
                "",
                ("monday", "tuesday", "wednesday", "thursday"),
                time(8),
                time(16),
                "open",
            ),
            ("", ("friday",), time(8), time(15), "open"),
        ],
    ),
    (
        "Escape",
        {
            "hours_unconfirmed": True,
            "warning": ESCAPE_WARNING,
            "show_parts": True,
            "event_location": "Escape",
        },
        [
            ("Kafé", WEEKDAYS, time(8), time(16), "open"),
            ("Bar", ("friday",), time(18), time(1), "open"),
        ],
    ),
]


def build_location(spec, sort_order=0):
    """An unsaved Location with its time slots, from one LOCATION_SPECS row."""
    name, extra, periods = spec
    location = Location(name=name, sort_order=sort_order, **extra)
    for slot, (label, days, opens, closes, access) in enumerate(periods):
        location.periods.add(  # pylint: disable=no-member
            OpeningPeriod(
                label=label,
                opens=opens,
                closes=closes,
                access=access,
                sort_order=slot,
                **{day: True for day in days},
            )
        )
    return location


class OpeningHoursSeedMixin:  # pylint: disable=too-few-public-methods
    """Adds LOCATION_SPECS. Mixed into seed_dev_data's Command, which sets
    created_count/skipped_count."""

    created_count = 0
    skipped_count = 0

    def _seed_opening_hours(self):
        # Migration 0162 already adds these places to a fresh database; then
        # only their English is stored here.
        for order, spec in enumerate(LOCATION_SPECS):
            location = Location.objects.filter(name=spec[0]).first()
            if location is not None:
                self.skipped_count += 1
            else:
                location = build_location(spec, order)
                location.save()
                self.created_count += 1
                self.stdout.write(f"  created Location: {location.name}")
            self._translate_page(location)
            for period in location.periods.all():
                self._translate_page(period)
