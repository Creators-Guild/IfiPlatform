"""Models for the Events section: EventIndexPage -> EventPage.

Design rationale/history: docs/claude_context/event_models.md"""

from datetime import date, datetime, time, timedelta
from itertools import groupby
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Locale, Page

from ifi_home_app.models.article_models import HEX_COLOR_VALIDATOR, TranslationWarningMixin, article_card_block

# Needed only where a clock *time* is compared against event_time
# (live_sub_events) -- see docs/claude_context/event_models.md.
SITE_TIMEZONE = ZoneInfo("Europe/Oslo")

EVENT_CALENDAR_COLOR_CHOICES = [
    ("", _("Auto (by event type)")),
    ("blue", _("Blue")),
    ("yellow", _("Yellow")),
    ("orange", _("Orange")),
    ("pink", _("Pink")),
    ("green", _("Green")),
    ("purple", _("Purple")),
    ("custom", _("Custom (hex code)")),
]


class EventPageTag(TaggedItemBase):
    """Through-model for EventPage.info_tags. Free-text tags with
    autocomplete from previously-used ones, not a fixed choices list."""

    content_object = ParentalKey(
        "EventPage", on_delete=models.CASCADE, related_name="tagged_items"
    )


def event_union_block():
    """A student union involved in an event, plus their role."""
    return blocks.StructBlock(
        [
            (
                "union",
                blocks.PageChooserBlock(
                    page_type="ifi_home_app.UnionPage",
                    required=True,
                    help_text="The student union involved.",
                ),
            ),
            (
                "role",
                blocks.ChoiceBlock(
                    choices=[
                        ("host", _("Host")),
                        ("contributor", _("Contributor")),
                        ("collaborator", _("Collaborator")),
                    ],
                    default="host",
                ),
            ),
        ],
        icon="group",
        label="Union",
    )


def calendar_legend_entry_block():
    """One row of a parent event's own color legend (calendar_legend below)."""
    return blocks.StructBlock(
        [
            (
                "color",
                blocks.ChoiceBlock(
                    choices=[
                        (key, label) for key, label in EVENT_CALENDAR_COLOR_CHOICES
                        if key not in ("", "custom")
                    ],
                    default="blue",
                ),
            ),
            ("label", blocks.CharBlock(max_length=60, help_text="What this color means, e.g. \"Study-relevant\".")),
        ],
        icon="tag",
        label="Legend entry",
    )


def location_map_link_block():
    """One titled link to a map for one of the event's locations."""
    return blocks.StructBlock(
        [
            (
                "title",
                blocks.CharBlock(
                    max_length=100,
                    required=False,
                    help_text='Optional -- link text, e.g. "Google Maps". Defaults to "View on map" if left blank.',
                ),
            ),
            (
                "url",
                blocks.URLBlock(
                    required=True,
                    help_text="Link to a map for this location.",
                ),
            ),
        ],
        icon="site",
        label="Map Link",
    )


class PeoplySyncState(models.Model):
    """Singleton row (always pk=1) -- see touch()/last_synced_at(). Mirrors
    GlossarySyncState's own pattern (glossary_models.py)."""

    synced_at = models.DateTimeField(auto_now=True)

    @classmethod
    def touch(cls):
        """Call after a successful sync_peoply_events run."""
        obj, _created = cls.objects.get_or_create(pk=1)
        obj.save()  # bumps synced_at via auto_now even if just created
        return obj.synced_at

    @classmethod
    def last_synced_at(cls):
        """None if sync_peoply_events has never run successfully."""
        obj = cls.objects.filter(pk=1).first()
        return obj.synced_at if obj else None


class PeoplySyncLog(models.Model):
    """One row per click of the "Sync Peoply now" button (events/partials/
    peoply_sync_button.html, event_views.force_sync_peoply_events) -- who
    triggered a manual sync and when, so repeated/spammy use is
    attributable to a specific person. Superuser-only in Django admin, see
    PeoplySyncLogAdmin (admin.py); nothing here creates or edits rows by
    hand."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    triggered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-triggered_at"]

    def __str__(self):
        return f"{self.user} at {self.triggered_at}"


class EventIndexPage(TranslationWarningMixin, Page):
    """Landing page listing all events."""

    template = "events/event_index_page.html"

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["ifi_home_app.EventPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        events = list(
            EventPage.objects.child_of(self)
            .live()
            .filter(locale=Locale.get_active())
            .order_by("event_date", "event_time")
        )
        today = timezone.localdate()
        # Same "still going" rule as is_happening_now: an event only counts
        # as past once its last day (end_date if set, else event_date) is
        # behind us -- a week-long event isn't "past" on day 2.
        upcoming_events = [e for e in events if (e.end_date or e.event_date) >= today]
        past_events = [e for e in events if (e.end_date or e.event_date) < today]

        def month_groups(events_list):
            # groupby only merges *consecutive* equal keys -- safe since
            # events_list stays in whatever sorted-by-event_date order it
            # was given in (ascending for upcoming, reversed for past).
            return [
                {"month": month, "events": list(month_events)}
                for month, month_events in groupby(
                    events_list, key=lambda event: event.event_date.replace(day=1)
                )
            ]

        context["events"] = events
        context["month_groups"] = month_groups(upcoming_events)
        # Most-recently-past month first, since that's the one someone
        # skimming "past events" is most likely looking for.
        context["past_month_groups"] = month_groups(list(reversed(past_events)))
        context["current_semester_year"] = today.year
        context["is_spring_semester"] = today.month <= 6
        return context


EVENT_TYPE_CHOICES = [
    ("social", _("Social")),
    ("deadline", _("Deadline")),
    ("academic", _("Academic")),
    ("company", _("Company presentation")),
    ("other", _("Other")),
]


class EventPage(TranslationWarningMixin, Page):
    """A single event -- covers dated events, week-long events (via
    end_date), and deadlines through the same shape."""

    template = "events/event_page.html"

    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default="other")
    event_date = models.DateField()
    event_time = models.TimeField(null=True, blank=True)  # blank = "no specific time" (e.g. week-long Fadderuke)
    event_end_time = models.TimeField(null=True, blank=True)  # only used to size this event's block in calendar_days
    calendar_color = models.CharField(
        max_length=20, choices=EVENT_CALENDAR_COLOR_CHOICES, blank=True,
        help_text="Optional -- overrides the automatic color of this event's block in a parent event's week-calendar view.",
    )
    calendar_color_custom = models.CharField(
        max_length=7, blank=True, validators=[HEX_COLOR_VALIDATOR],
        help_text="Used only when Calendar color above is set to Custom.",
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional -- for events spanning more than one day.",
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional -- where the event takes place, e.g. a building or room name.",
    )
    location_map_links = StreamField(
        [("map_link", location_map_link_block())],
        use_json_field=True,
        blank=True,
        help_text="Optional -- one or more titled links to a map (e.g. Google Maps) for this event's location(s).",
    )
    location_articles = StreamField(
        [("article", article_card_block())],
        use_json_field=True,
        blank=True,
        help_text="Optional -- links to existing articles with more info about this event's location(s).",
    )
    intro = RichTextField(blank=True)
    show_on_homepage = models.BooleanField(
        default=True,
        help_text="Whether this event can appear in the homepage's upcoming-events box.",
    )
    is_highlighted = models.BooleanField(
        default=False,
        help_text="For a sub-event: show it in its parent event's homepage dropdown.",
    )

    # Groundwork for a future automatic sync (e.g. Peoply/UiO ICS feeds) --
    # unused until that exists. "" means manually created.
    external_source = models.CharField(max_length=20, blank=True)
    external_uid = models.CharField(max_length=200, blank=True)

    related_unions = StreamField(
        [("union", event_union_block())],
        use_json_field=True,
        blank=True,
        help_text="Optional -- student unions involved in this event, and their role.",
    )
    calendar_legend = StreamField(
        [("entry", calendar_legend_entry_block())],
        use_json_field=True,
        blank=True,
        help_text="Optional -- explains what each sub-event calendar color means (e.g. \"Blue = Study-relevant\"), shown above the week-calendar.",
    )
    peoply_url = models.URLField(
        blank=True,
        help_text="Optional -- link to this event's page on Peoply.",
    )
    signup_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Optional -- link to a signup/registration form for this event, if not using Peoply.",
    )
    info_tags = ClusterTaggableManager(
        through=EventPageTag,
        blank=True,
        help_text='Optional -- e.g. "Bachelor", "MN students", "Food served", "Alcohol-free".',
    )

    content_panels = Page.content_panels + [
        FieldPanel("event_type"),
        FieldPanel("event_date"),
        FieldPanel("event_time"),
        FieldPanel("event_end_time"),
        FieldPanel("calendar_color"),
        FieldPanel("calendar_color_custom"),
        FieldPanel("end_date"),
        FieldPanel("location"),
        FieldPanel("location_map_links"),
        FieldPanel("location_articles"),
        FieldPanel("intro"),
        FieldPanel("show_on_homepage"),
        FieldPanel("is_highlighted"),
        FieldPanel("related_unions"),
        FieldPanel("calendar_legend"),
        FieldPanel("peoply_url"),
        FieldPanel("signup_url"),
        FieldPanel("info_tags"),
    ]

    parent_page_types = ["ifi_home_app.EventIndexPage", "ifi_home_app.EventPage"]
    subpage_types = ["ifi_home_app.EventPage"]

    @classmethod
    def can_create_at(cls, parent):
        """Sub-events can't have sub-events of their own."""
        if not super().can_create_at(parent):
            return False
        if isinstance(parent, EventPage):
            return not isinstance(parent.get_parent().specific, EventPage)
        return True

    @property
    def is_happening_now(self):
        """True on any day this event is in progress (event_date through
        end_date inclusive)."""
        today = timezone.localdate()
        return self.event_date <= today <= (self.end_date or self.event_date)

    @property
    def sub_events(self):
        return EventPage.objects.child_of(self).live().order_by("event_date", "event_time")

    @property
    def live_sub_events(self):
        """Sub-events happening at this exact moment (in progress today AND,
        for a timed one, whose [event_time, event_end_time] window covers
        the current clock time). See docs/claude_context/event_models.md
        for why SITE_TIMEZONE, not the bare timezone.localtime(), applies
        here specifically."""
        current_time = timezone.localtime(timezone=SITE_TIMEZONE).time()

        def is_live(sub_event):
            if not sub_event.is_happening_now:
                return False
            if not sub_event.event_time:
                return True
            start = sub_event.event_time
            end = sub_event.event_end_time
            if end is None or end <= start:
                # No stored end, or one that'd wrap past midnight -- nominal
                # 1-hour fallback, clamped to the same day.
                end = (datetime.combine(date.min, start) + timedelta(hours=1)).time()
                if end < start:
                    end = time(23, 59, 59)
            return start <= current_time <= end

        return [sub_event for sub_event in self.sub_events if is_live(sub_event)]

    @property
    def localized_location_articles(self):
        """Linked ArticlePages resolved to the active locale -- see
        docs/claude_context/event_models.md (PageChooserBlock isn't
        auto-translated by wagtail-localize)."""
        return [
            entry.value["article"].localized.specific
            for entry in self.location_articles
            if entry.value["article"] is not None
        ]

    @property
    def all_related_unions(self):
        """This event's related_unions plus every sub_event's, deduped by
        union keeping the highest-priority role. See
        docs/claude_context/event_models.md for the host-capping rule."""
        role_priority = {"host": 0, "collaborator": 1, "contributor": 2}
        best_by_union = {}

        def add_entries(entries, cap_host):
            for entry in entries:
                union = entry.value["union"]
                if union is None:
                    continue
                role = entry.value["role"]
                if cap_host and role == "host":
                    role = "collaborator"
                key = union.translation_key
                if key not in best_by_union or role_priority[role] < role_priority[best_by_union[key][0]]:
                    best_by_union[key] = (role, union)

        add_entries(self.related_unions, cap_host=False)
        for sub_event in self.sub_events:
            add_entries(sub_event.related_unions, cap_host=True)

        return [{"role": role, "union": union} for role, union in best_by_union.values()]

    @property
    def highlighted_sub_events(self):
        """Today's sub-event(s) if any are scheduled today, else the
        curated is_highlighted set."""
        today_events = self.sub_events.filter(event_date=timezone.localdate())
        if today_events.exists():
            return today_events
        return self.sub_events.filter(is_highlighted=True)

    @property
    def calendar_days(self):
        """This event's sub_events laid out for a week-calendar view -- see
        docs/claude_context/event_models.md for the full layout algorithm."""
        timed = [e for e in self.sub_events if e.event_time]
        untimed = [e for e in self.sub_events if not e.event_time]

        if not timed:
            return {
                "hour_start": 0, "hour_end": 0, "hour_marks": [], "hour_count": 0,
                "days": [], "untimed": untimed,
            }

        def start_minutes(event):
            return event.event_time.hour * 60 + event.event_time.minute

        def end_minutes(event):
            if event.event_end_time:
                return event.event_end_time.hour * 60 + event.event_end_time.minute
            return start_minutes(event) + 60

        hour_start = min(start_minutes(e) for e in timed) // 60
        hour_end = max(-(-end_minutes(e) // 60) for e in timed)  # ceil-div
        hour_end = max(hour_end, hour_start + 1)
        total_minutes = (hour_end - hour_start) * 60

        days = []
        for day_date in sorted({e.event_date for e in timed}):
            day_events = sorted(
                (e for e in timed if e.event_date == day_date),
                key=lambda e: (start_minutes(e), end_minutes(e)),
            )
            blocks = []
            for cluster in _cluster_overlapping(day_events, start_minutes, end_minutes):
                columns = _assign_columns(cluster, start_minutes, end_minutes)
                for event in cluster:
                    col, col_count = columns[event]
                    color_key, color_hex = _resolve_calendar_color(event)
                    blocks.append({
                        "event": event,
                        "top_pct": _pct(start_minutes(event) - hour_start * 60, total_minutes),
                        "height_pct": _pct(end_minutes(event) - start_minutes(event), total_minutes),
                        "left_pct": _pct(col, col_count),
                        "width_pct": _pct(1, col_count),
                        "color_key": color_key,
                        "color_hex": color_hex,
                    })
            days.append({"date": day_date, "events": blocks})

        hour_marks = [
            {"hour": h, "top_pct": _pct(h * 60 - hour_start * 60, total_minutes)}
            for h in range(hour_start, hour_end + 1)
        ]

        return {
            "hour_start": hour_start,
            "hour_end": hour_end,
            "hour_marks": hour_marks,
            "hour_count": hour_end - hour_start,
            "days": days,
            "untimed": untimed,
        }


_AUTO_CALENDAR_COLOR_BY_EVENT_TYPE = {
    "academic": "blue",
    "deadline": "pink",
    "company": "purple",
    "social": "orange",
    "other": "orange",
}


def _resolve_calendar_color(event):
    """The (color_key, custom_hex) this event's calendar block renders with."""
    color = event.calendar_color or _AUTO_CALENDAR_COLOR_BY_EVENT_TYPE.get(event.event_type, "orange")
    if color == "custom" and event.calendar_color_custom:
        return "custom", event.calendar_color_custom
    return color, None


def _pct(numerator, denominator):
    # Plain string, not a float -- Django's locale-aware {{ }} rendering
    # would break this inline style="...%" value. See
    # docs/claude_context/event_models.md before changing this.
    return f"{numerator / denominator * 100:.4f}"


def _cluster_overlapping(events, start_minutes, end_minutes):
    """Partitions start-time-sorted `events` into clusters of transitively
    overlapping events. See docs/claude_context/event_models.md."""
    clusters = []
    current = []
    current_max_end = None
    for event in events:
        s = start_minutes(event)
        if current and s >= current_max_end:
            clusters.append(current)
            current = []
            current_max_end = None
        current.append(event)
        e = end_minutes(event)
        current_max_end = e if current_max_end is None else max(current_max_end, e)
    if current:
        clusters.append(current)
    return clusters


def _assign_columns(cluster, start_minutes, end_minutes):
    """Greedy interval-graph coloring within one cluster of overlapping
    events. See docs/claude_context/event_models.md."""
    columns_end = []
    column_of = {}
    for event in cluster:
        s, e = start_minutes(event), end_minutes(event)
        col = next((i for i, end in enumerate(columns_end) if end <= s), len(columns_end))
        if col == len(columns_end):
            columns_end.append(e)
        else:
            columns_end[col] = e
        column_of[event] = col
    column_count = len(columns_end)
    return {event: (col, column_count) for event, col in column_of.items()}


def upcoming_events_for_union(union):
    """Live, still-upcoming events tagging `union` in related_unions,
    regardless of role. See docs/claude_context/event_models.md."""
    today = timezone.localdate()
    candidates = (
        EventPage.objects.live()
        .filter(locale=union.locale_id)
        .filter(
            models.Q(end_date__gte=today)
            | models.Q(end_date__isnull=True, event_date__gte=today)
        )
        .order_by("event_date", "event_time")
    )
    return [
        event
        for event in candidates
        if any(
            entry.value["union"] is not None
            and entry.value["union"].translation_key == union.translation_key
            for entry in event.related_unions
            if entry.block_type == "union"
        )
    ]
