"""Opening hours for the homepage box: places (Location) with weekly time
slots (OpeningPeriod) and closed date ranges (LocationClosure), plus
location_status(), which works out whether a place is open right now.
opening_hours_now() is what the homepage view calls; a live source (the
planned Escape API) would plug in there.

Design rationale: docs/claude_context/home_openinghours.md"""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable

from .event.constants import SITE_TIMEZONE

WEEKDAY_FIELDS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
SHORT_DAYS = [
    gettext_lazy("Mon"),
    gettext_lazy("Tue"),
    gettext_lazy("Wed"),
    gettext_lazy("Thu"),
    gettext_lazy("Fri"),
    gettext_lazy("Sat"),
    gettext_lazy("Sun"),
]
# An event without an end time counts as running until this time the next
# night (the bar's usual closing time).
EVENT_DEFAULT_END = time(1, 0)
# A change before this time on the next day is still "tonight" and is
# shown without a weekday ("until 01:00", not "until Sat 01:00").
NIGHT_ENDS = time(5, 0)

OPEN = "open"
CARD = "card"
CLOSED = "closed"


class Location(ClusterableModel):
    """A place shown in the homepage's opening hours box."""

    translated_fields = ["name", "note", "warning"]

    name = models.CharField(max_length=100)
    note = models.CharField(
        max_length=200,
        blank=True,
        help_text="Short note under the hours, e.g. 'Halvpris siste 30 min'.",
    )
    hours_unconfirmed = models.BooleanField(
        default=False,
        help_text="The hours are planned, not guaranteed. Adds a * and the warning below.",
    )
    warning = models.CharField(
        max_length=300,
        blank=True,
        help_text="Shown at the bottom of the box when the hours are not guaranteed.",
    )
    show_parts = models.BooleanField(
        default=False,
        help_text="Show the time slots' labels as parts, e.g. 'Kafé | Bar | Event'.",
    )
    event_location = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Events whose location is exactly this (e.g. 'Escape') count as "
            "open while they run. Leave blank for none."
        ),
    )
    half_price_minutes = models.PositiveSmallIntegerField(
        default=0,
        help_text="Half price this many minutes before closing. 0 for never.",
    )
    sort_order = models.IntegerField(default=0, help_text="Lower comes first.")
    is_active = models.BooleanField(
        default=True, help_text="Uncheck to hide this place."
    )

    panels = [
        FieldPanel("name"),
        FieldRowPanel([FieldPanel("sort_order"), FieldPanel("is_active")]),
        InlinePanel("periods", label="Time slots"),
        InlinePanel("closures", label="Closed days"),
        FieldPanel("note"),
        MultiFieldPanel(
            [FieldPanel("hours_unconfirmed"), FieldPanel("warning")],
            heading="Not guaranteed",
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_parts"),
                FieldPanel("event_location"),
                FieldPanel("half_price_minutes"),
            ],
            heading="Extras",
        ),
    ]

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "opening hours place"

    def __str__(self):
        return self.name


class OpeningPeriod(Orderable):
    """One weekly time slot of a Location."""

    translated_fields = ["label"]

    ACCESS_CHOICES = [(OPEN, "Open to everyone"), (CARD, "UiO card needed")]

    location = ParentalKey(Location, on_delete=models.CASCADE, related_name="periods")
    label = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional, e.g. 'Kafé', 'Bar', 'Betjent', 'Kort + PIN'.",
    )
    monday = models.BooleanField(default=False)
    tuesday = models.BooleanField(default=False)
    wednesday = models.BooleanField(default=False)
    thursday = models.BooleanField(default=False)
    friday = models.BooleanField(default=False)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)
    opens = models.TimeField()
    closes = models.TimeField(
        help_text="Earlier than the opening time means after midnight; 00:00 is midnight."
    )
    access = models.CharField(max_length=10, choices=ACCESS_CHOICES, default=OPEN)

    panels = [
        FieldPanel("label"),
        FieldRowPanel([FieldPanel(day) for day in WEEKDAY_FIELDS], heading="Days"),
        FieldRowPanel(
            [FieldPanel("opens"), FieldPanel("closes"), FieldPanel("access")]
        ),
    ]

    def __str__(self):
        return f"{self.label or self.location} {self.opens:%H:%M}-{self.closes:%H:%M}"

    @property
    def weekdays(self):
        """0 = Monday ... 6 = Sunday."""
        return [i for i, name in enumerate(WEEKDAY_FIELDS) if getattr(self, name)]

    def clean(self):
        super().clean()
        if not self.weekdays:
            raise ValidationError("Pick at least one day.")
        if self.opens == self.closes and self.opens != time(0):
            raise ValidationError("Opening and closing time can't be the same.")


class LocationClosure(Orderable):
    """Days a Location is closed whatever its time slots say."""

    translated_fields = ["reason"]

    location = ParentalKey(Location, on_delete=models.CASCADE, related_name="closures")
    start_date = models.DateField()
    end_date = models.DateField(help_text="Last closed day.")
    reason = models.CharField(
        max_length=100, blank=True, help_text="Shown in the box, e.g. 'Juleferie'."
    )

    panels = [
        FieldRowPanel([FieldPanel("start_date"), FieldPanel("end_date")]),
        FieldPanel("reason"),
    ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("The last closed day is before the first.")


@dataclass
class _Window:
    start: datetime
    end: datetime
    access: str
    label: str = ""
    event: object = None


@dataclass
class LocationStatus:  # pylint: disable=too-many-instance-attributes
    """What the box shows for one Location at one moment."""

    location: Location
    state: str
    next_text: str = ""
    parts: list = field(default_factory=list)
    hours: list = field(default_factory=list)
    event: object = None
    event_start: datetime = None
    event_running: bool = False
    half_price: str = ""
    half_price_from: datetime = None


def _at(day, clock):
    return datetime.combine(day, clock, tzinfo=SITE_TIMEZONE)


def _end_after(start, day, clock):
    end = _at(day, clock)
    return end if end > start else end + timedelta(days=1)


def _event_window(event):
    if event.event_time is None:
        return None
    start = _at(event.event_date, event.event_time)
    if event.event_end_time is not None:
        end = _end_after(start, event.event_date, event.event_end_time)
    else:
        end = _at(event.event_date + timedelta(days=1), EVENT_DEFAULT_END)
    return _Window(start, end, OPEN, _("Event"), event)


def _windows(periods, events, first_day, days):
    windows = []
    for offset in range(days):
        day = first_day + timedelta(days=offset)
        for period in periods:
            if day.weekday() in period.weekdays:
                start = _at(day, period.opens)
                end = _end_after(start, day, period.closes)
                windows.append(_Window(start, end, period.access, period.label))
    for event in events:
        window = _event_window(event)
        if window is not None:
            windows.append(window)
    return windows


def _closure_on(closures, day):
    return next((c for c in closures if c.start_date <= day <= c.end_date), None)


def _state_at(windows, closures, moment):
    if _closure_on(closures, moment.date()):
        return CLOSED, []
    active = [w for w in windows if w.start <= moment < w.end]
    if any(w.access == OPEN for w in active):
        return OPEN, active
    if active:
        return CARD, active
    return CLOSED, []


def _when(moment, now):
    tonight = (
        moment.date() == now.date() + timedelta(days=1) and moment.time() < NIGHT_ENDS
    )
    clock = (
        "24:00" if tonight and moment.time() == time(0) else moment.strftime("%H:%M")
    )
    if moment.date() == now.date() or tonight:
        return clock
    return _("%(day)s %(time)s") % {"day": SHORT_DAYS[moment.weekday()], "time": clock}


def _next_text(state, next_state, when):
    texts = {
        (OPEN, CARD): _("card needed from %(when)s"),
        (OPEN, CLOSED): _("until %(when)s"),
        (CARD, OPEN): _("open without card from %(when)s"),
        (CARD, CLOSED): _("until %(when)s"),
        (CLOSED, OPEN): _("opens %(when)s"),
        (CLOSED, CARD): _("card access from %(when)s"),
    }
    return texts[(state, next_state)] % {"when": when}


def _day_range(weekdays):
    if len(weekdays) == 7:
        return _("Every day")
    names = [str(SHORT_DAYS[d]) for d in weekdays]
    consecutive = all(b == a + 1 for a, b in zip(weekdays, weekdays[1:]))
    if len(weekdays) > 2 and consecutive:
        return f"{names[0]}–{names[-1]}"
    return ", ".join(names)


def _hours_lines(periods, today):
    return [
        {
            "days": _day_range(period.weekdays),
            "label": period.label,
            "times": f"{period.opens:%H:%M}–"
            + ("24:00" if period.closes == time(0) else f"{period.closes:%H:%M}"),
            "today": today.weekday() in period.weekdays,
        }
        for period in periods
    ]


def _next_change(windows, closures, state, now):
    """(state, moment) of the first change after `now`, or None."""
    candidates = {w.start for w in windows} | {w.end for w in windows}
    candidates |= {_at(c.end_date + timedelta(days=1), time(0)) for c in closures}
    for moment in sorted(c for c in candidates if c > now):
        next_state, _active = _state_at(windows, closures, moment)
        if next_state != state:
            return next_state, moment
    return None


def _parts(location, periods, active):
    labels = list(dict.fromkeys(p.label for p in periods if p.label))
    if location.event_location:
        labels.append(_("Event"))
    on = {w.label for w in active}
    return [{"label": label, "active": label in on} for label in labels]


def _shown_event(windows, active, now):
    """The running event window, else the next one later today, else None."""
    running = next((w for w in active if w.event is not None), None)
    if running is not None:
        return running, True
    upcoming = sorted(
        (w for w in windows if w.event is not None and w.start > now),
        key=lambda w: w.start,
    )
    if upcoming and upcoming[0].start.date() == now.date():
        return upcoming[0], False
    return None, False


def _half_price(minutes, state, next_change, now):
    """("now" | "soon" | "", half price start) for a place that's open."""
    if not minutes or state != OPEN or not next_change or next_change[0] == OPEN:
        return "", None
    closing = next_change[1]
    starts = closing - timedelta(minutes=minutes)
    if now >= starts:
        return "now", starts
    if now >= starts - timedelta(minutes=minutes):
        return "soon", starts
    return "", starts


def location_status(location, now, events=()):
    """The LocationStatus of `location` at `now` (an aware datetime).
    `events` are the EventPages at this location around today."""
    now = timezone.localtime(now, SITE_TIMEZONE)
    periods = list(location.periods.all())
    closures = list(location.closures.all())
    windows = _windows(periods, events, now.date() - timedelta(days=1), 9)
    state, active = _state_at(windows, closures, now)
    status = LocationStatus(location, state, hours=_hours_lines(periods, now.date()))
    next_change = _next_change(windows, closures, state, now)

    closure = _closure_on(closures, now.date())
    if closure is not None:
        if closure.reason:
            status.next_text = _("Closed: %(reason)s") % {"reason": closure.reason}
    else:
        if next_change is not None:
            status.next_text = _next_text(
                state, next_change[0], _when(next_change[1], now)
            )
        window, status.event_running = _shown_event(windows, active, now)
        if window is not None:
            status.event, status.event_start = window.event, window.start

    if location.show_parts:
        status.parts = _parts(location, periods, active)
    status.half_price, status.half_price_from = _half_price(
        location.half_price_minutes, state, next_change, now
    )
    return status


def opening_hours_now(now=None):
    """The status of every active Location, in box order. Events come from
    the synced EventPages whose location matches a place's event_location."""
    from .event.pages import EventPage  # pylint: disable=import-outside-toplevel

    now = timezone.localtime(now or timezone.now(), SITE_TIMEZONE)
    locations = list(
        Location.objects.filter(is_active=True).prefetch_related("periods", "closures")
    )
    names = {loc.event_location.lower() for loc in locations if loc.event_location}
    events_by_name = {}
    if names:
        query = Q()
        for name in names:
            query |= Q(location__iexact=name)
        today = now.date()
        events = (
            EventPage.objects.live()
            .filter(
                is_archived=False, event_date__range=(today - timedelta(days=1), today)
            )
            .filter(query)
        )
        for event in events:
            events_by_name.setdefault(event.location.lower(), []).append(event)
    return [
        location_status(loc, now, events_by_name.get(loc.event_location.lower(), []))
        for loc in locations
    ]
