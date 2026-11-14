"""Adds the four places of the homepage's opening hours box, with the hours
from UiO's pages (Nov 2026), so production isn't empty after deploy. Only
runs on a database without any places, so it never overwrites what admins
have entered. After this, the hours are edited in the "Opening hours"
snippet. English is filled in by the nightly translate_english run."""

from datetime import time

from django.db import migrations

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")
EVERY_DAY = WEEKDAYS + ("saturday", "sunday")
ESCAPE_WARNING = (
    "Escape drives av frivillige studenter. Dette er de planlagte tidene, "
    "og det kan åpne senere eller stenge tidligere."
)

# (name, extra Location fields, [(label, days, opens, closes, access)])
PLACES = [
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


def add_places(apps, schema_editor):
    location_model = apps.get_model("ifi_home_app", "Location")
    period_model = apps.get_model("ifi_home_app", "OpeningPeriod")
    if location_model.objects.exists():
        return
    for order, (name, extra, periods) in enumerate(PLACES):
        location = location_model.objects.create(name=name, sort_order=order, **extra)
        for slot, (label, days, opens, closes, access) in enumerate(periods):
            period_model.objects.create(
                location=location,
                label=label,
                opens=opens,
                closes=closes,
                access=access,
                sort_order=slot,
                **{day: True for day in days},
            )


def remove_places(apps, schema_editor):
    location_model = apps.get_model("ifi_home_app", "Location")
    location_model.objects.filter(
        name__in=[name for name, _extra, _periods in PLACES]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("ifi_home_app", "0161_opening_hours")]

    operations = [migrations.RunPython(add_places, remove_places)]
