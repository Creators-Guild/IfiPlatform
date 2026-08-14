"""Models for the Events section: a plain index/leaf pair (EventIndexPage ->
EventPage), same shape as StudentUnionCategoryPage -> UnionPage. No editor-
mode on-page tooling (EditorModeMixin/BannerStyleMixin) on either page yet --
unlike ArticlePage/CategoryPage, there's no on-page style panel for events to
plug into; add it later if that changes. TranslationWarningMixin is kept
since it's free and these pages need nb/en translations like everything else
on this bilingual site."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

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

# event_time/event_end_time are plain (non-tz-aware) TimeFields, entered and
# displayed as-is with no conversion -- editors enter them as Oslo wall-clock
# (this is a Ifi/UiO site; that's where the events actually happen), same as
# every other clock time already shown on the site (event_page.html etc).
# settings.TIME_ZONE is "UTC" though (storage/bookkeeping convention, not a
# site-content one), and nothing activates a per-request timezone -- so
# timezone.localtime() on its own returns UTC wall-clock, not Oslo's. Needed
# only where a clock *time* is compared against event_time (EventPage.
# live_sub_events below) -- the plain calendar-day comparisons elsewhere
# (is_happening_now, timezone.localdate()) don't need it: UTC and Oslo only
# ever disagree on which *day* it is within an hour or two of midnight,
# already an existing, pre-existing-elsewhere edge case, not one this
# introduces.
SITE_TIMEZONE = ZoneInfo("Europe/Oslo")

# Same "fixed palette + custom hex fallback" pattern as article_models.py's
# COLOR_CHOICES (reusing HEX_COLOR_VALIDATOR from there directly), but its
# own list rather than that one: these name a pastel set matched to a
# printed program's own color-coded legend (see calendar_color's own
# comment below), not article_models.py's box/border palette, and "" here
# means "derive one from event_type" rather than a fixed default color.
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
    """Through-model for EventPage.info_tags -- Wagtail's standard tagging
    recipe (ClusterTaggableManager + a TaggedItemBase subclass), not a
    second/parallel tagging mechanism. Free-text tags with autocomplete
    from previously-used ones (e.g. "Bachelor", "MN students", "Food
    served", "Alcohol-free") -- deliberately not a fixed choices list, so a
    brand-new tag never needs a code change."""

    content_object = ParentalKey(
        "EventPage", on_delete=models.CASCADE, related_name="tagged_items"
    )


def event_union_block():
    """A student union involved in an event, plus the role they played
    (host/contributor/collaborator). Reuses UnionPage via PageChooserBlock,
    same pattern as article_models.py's union_card_block() (ArticlePage's
    own "Student Union Card" body block) -- not a second, parallel way of
    picking a UnionPage. A function (not a shared instance) since Wagtail
    block instances carry per-use bookkeeping and aren't safe to reuse
    across multiple StreamField definitions."""
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
    """One row of a parent event's own color legend (calendar_legend below)
    -- a color (this event's calendar_color palette, minus "Auto" and
    "Custom": a legend entry has to name one specific, fixed color) plus
    freeform label text explaining what that color means for *this*
    event's sub-events (e.g. "Blue = Study-relevant"), since that meaning
    is specific to whatever schedule is being recreated, not a fixed
    sitewide convention. A function (not a shared instance) for the same
    reason as event_union_block above -- Wagtail block instances aren't
    safe to reuse across StreamField definitions."""
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
    """One titled link to a map for one of the event's locations (e.g.
    "Google Maps" -> a Google Maps URL) -- StructBlock rather than a plain
    URLBlock so an event spanning several locations can add one of these
    per location, each with its own clickable label, instead of a single
    generic "View on map" link. title is optional: event_page.html falls
    back to a generic "View on map" label when left blank, same as most
    other optional label-ish fields in this file."""
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


class EventIndexPage(TranslationWarningMixin, Page):
    """Landing page listing all events -- what "Events" in the nav links to
    (see home_sidemenu.html/article_tags.get_event_index)."""

    template = "events/event_index_page.html"

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["ifi_home_app.EventPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["events"] = (
            EventPage.objects.child_of(self)
            .live()
            .filter(locale=Locale.get_active())
            .order_by("event_date", "event_time")
        )
        return context


EVENT_TYPE_CHOICES = [
    ("social", _("Social")),
    ("deadline", _("Deadline")),
    ("academic", _("Academic")),
    ("company", _("Company presentation")),
    ("other", _("Other")),
]


class EventPage(TranslationWarningMixin, Page):
    """A single event -- covers dated events (Bar til bar), date ranges/
    week-long events (Fadderuke, via end_date), and deadlines (Frist for
    funk-oppmelding) through the same shape rather than separate models,
    since they only differ in which fields are filled in."""

    template = "events/event_page.html"

    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default="other")
    # blank event_time means "no specific time" (e.g. a week-long event like
    # Fadderuke, shown as "Uke 33" rather than a clock time -- see
    # home_eventsbox.html).
    event_date = models.DateField()
    event_time = models.TimeField(null=True, blank=True)
    # Optional -- only used to size/position this event's block in a parent
    # event's week-calendar view (calendar_days below). Left blank, a sub-
    # event just gets a fixed-length block there instead of a clipped one.
    event_end_time = models.TimeField(null=True, blank=True)
    # Optional -- lets an editor color-code a sub-event's week-calendar
    # block directly (e.g. to recreate a printed program's own color
    # legend, like "yellow = food, orange = alcohol-free"), instead of only
    # ever getting the automatic event_type-based color (see
    # _resolve_calendar_color below). Blank means "auto".
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
    # One or more titled map links (e.g. "Google Maps", "MazeMap") -- a
    # StreamField rather than a single URLField since an event can span
    # more than one location, each wanting its own map link.
    location_map_links = StreamField(
        [("map_link", location_map_link_block())],
        use_json_field=True,
        blank=True,
        help_text="Optional -- one or more titled links to a map (e.g. Google Maps) for this event's location(s).",
    )
    # Links to existing ArticlePages describing the location(s) in more
    # detail (e.g. an info page about a specific building) -- reuses
    # article_card_block() as-is (article_models.py) rather than a new
    # event-specific block, same "StreamField of a single-PageChooserBlock
    # StructBlock" shape already used for related_unions below via
    # event_union_block(). A StreamField (not a single FK) since more than
    # one location article can apply to one event.
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
    # Only meaningful on a sub-event -- surfaces it in its parent's homepage
    # dropdown (see highlighted_sub_events below/home_eventsbox.html).
    # Harmless if checked on a top-level event, just has no effect there.
    is_highlighted = models.BooleanField(
        default=False,
        help_text="For a sub-event: show it in its parent event's homepage dropdown.",
    )

    # Groundwork for a future automatic sync (e.g. Peoply/UiO ICS feeds) --
    # unused until that exists, kept here so adding it later doesn't need a
    # schema change. "" means manually created.
    external_source = models.CharField(max_length=20, blank=True)
    external_uid = models.CharField(max_length=200, blank=True)

    # Which student unions are involved, and how (hosting/contributing/
    # collaborating) -- shown on the event's own page (see event_page.html),
    # not the compact homepage box, which has no room for it.
    related_unions = StreamField(
        [("union", event_union_block())],
        use_json_field=True,
        blank=True,
        help_text="Optional -- student unions involved in this event, and their role.",
    )

    # Only meaningful on a *parent* event (one with sub_events) -- explains
    # what each calendar_color actually means for this specific schedule
    # (event_page.html renders it as a row above the week-calendar, only
    # when non-empty -- there's no separate on/off toggle, having any
    # entries at all *is* "on"). Harmless if left empty or set on an event
    # with no sub-events, same as is_highlighted above being a no-op
    # outside its own intended context.
    calendar_legend = StreamField(
        [("entry", calendar_legend_entry_block())],
        use_json_field=True,
        blank=True,
        help_text="Optional -- explains what each sub-event calendar color means (e.g. \"Blue = Study-relevant\"), shown above the week-calendar.",
    )

    # The event's Peoply page -- almost every event links here, so it's the
    # primary/expected field (was called signup_url before Peoply became
    # the norm; see signup_url below for the now-secondary, genuinely
    # optional case).
    peoply_url = models.URLField(
        blank=True,
        help_text="Optional -- link to this event's page on Peoply.",
    )
    # A separate signup/registration link, only for the rare event that
    # doesn't use Peoply for signup (e.g. an external form). Most events
    # should use Peoply link above instead.
    signup_url = models.URLField(
        blank=True,
        help_text="Optional -- link to a signup/registration form for this event, if not using Peoply.",
    )
    # See EventPageTag above for why this is a real ClusterTaggableManager
    # rather than a StreamField of freeform text blocks (like related_unions
    # above) -- shown on the event's own page, same scoping as related_unions.
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

    # An EventPage may itself hold sub-events (e.g. Fadderuke's individual
    # daily events) -- allowed directly under either the EventIndexPage or
    # a top-level event, but capped at one level of nesting by can_create_at
    # below (parent_page_types/subpage_types alone can only gate by page
    # *type*, not tree depth -- same reasoning/pattern as ArticlePage.
    # can_create_at's own "not a hub index" check).
    parent_page_types = ["ifi_home_app.EventIndexPage", "ifi_home_app.EventPage"]
    subpage_types = ["ifi_home_app.EventPage"]

    @classmethod
    def can_create_at(cls, parent):
        """Same as Page.can_create_at(), plus: sub-events can't have
        sub-events of their own -- only allow creating here when `parent`
        is the EventIndexPage, or a top-level event (one whose own parent
        isn't itself an EventPage)."""
        if not super().can_create_at(parent):
            return False
        if isinstance(parent, EventPage):
            return not isinstance(parent.get_parent().specific, EventPage)
        return True

    @property
    def is_happening_now(self):
        """True on any day this event is actually in progress -- from
        event_date through end_date inclusive for a multi-day event (e.g.
        Fadderuke), just event_date for a single-day one. Powers the
        homepage box's "Happening now" callout (home_eventsbox.html/
        core_views.py), which can list more than one of these at once when
        several top-level events overlap.
        """
        today = timezone.localdate()
        return self.event_date <= today <= (self.end_date or self.event_date)

    @property
    def sub_events(self):
        """This event's own live sub-events (if any), in date order --
        shown on its own page (event_page.html) and counted (not listed)
        in the homepage box (home_eventsbox.html)."""
        return EventPage.objects.child_of(self).live().order_by("event_date", "event_time")

    @property
    def live_sub_events(self):
        """This event's own sub-events actually happening at this exact
        moment -- in progress today (is_happening_now above) AND, for a
        timed sub-event, whose own [event_time, event_end_time] window
        covers the current clock time too (an untimed sub-event has no
        window to check, so it counts as live for its whole day). Shown
        indented under this event in the homepage box's "Happening now"
        callout (home_eventsbox.html) -- much narrower than
        highlighted_sub_events below (today's whole programme, curated
        fallback included), since this is meant to answer "what's on
        *right now*", not "what's on today". SITE_TIMEZONE (Europe/Oslo),
        not the bare timezone.localtime() every other date/time check in
        this file uses -- see that constant's own comment above."""
        current_time = timezone.localtime(timezone=SITE_TIMEZONE).time()

        def is_live(sub_event):
            if not sub_event.is_happening_now:
                return False
            if not sub_event.event_time:
                return True
            start = sub_event.event_time
            end = sub_event.event_end_time
            if end is None or end <= start:
                # No stored end, or one that'd wrap past midnight -- same
                # nominal-1-hour fallback calendar_days below uses, just
                # clamped to the same day rather than replicating its
                # minutes-since-midnight math for what's meant to be a
                # quick "is it live right now" check.
                end = (datetime.combine(date.min, start) + timedelta(hours=1)).time()
                if end < start:
                    end = time(23, 59, 59)
            return start <= current_time <= end

        return [sub_event for sub_event in self.sub_events if is_live(sub_event)]

    @property
    def localized_location_articles(self):
        """The ArticlePages linked in location_articles, already resolved
        to the active locale (.localized.specific already applied) -- so
        templates never need to remember to do that themselves.
        PageChooserBlock references aren't auto-translated by wagtail-
        localize (a deliberate upstream design choice -- see
        handle_related_object_block() in wagtail_localize/segments/
        extract.py -- and it applies the same way to a plain ForeignKey,
        not just StreamField blocks, so there's no simpler field type that
        would sidestep this), so resolving it here once is what keeps every
        future template touching this field from re-discovering that the
        hard way, the way related_unions did."""
        return [
            entry.value["article"].localized.specific
            for entry in self.location_articles
            if entry.value["article"] is not None
        ]

    @property
    def all_related_unions(self):
        """This event's own related_unions plus every sub_event's, deduped
        by union (keeping the highest-priority role seen) -- shown on the
        event's own page (event_page.html) and the homepage box
        (home_eventsbox.html) instead of related_unions directly. Without
        this, a parent event like Fadderuke -- whose own related_unions is
        typically empty, since in practice a union only ever gets tagged on
        the specific sub-event it's actually involved in -- would show no
        involved unions at all despite its sub-events listing plenty.

        "host" is only ever kept for a union tagged as host directly on
        *this* page -- a union hosting one sub-event (e.g. CYB running a
        single quiz night) isn't the host of the whole week, so a sub-
        event's own "host" role is capped down to "collaborator" once
        rolled up here; "collaborator"/"contributor" from a sub-event carry
        over unchanged, since neither implies ownership of the whole event
        the way "host" does.

        Returns plain {"role": ..., "union": ...} dicts rather than raw
        StreamField block values, since these come from two different
        StreamFields (this page's own and each sub_event's) glued
        together, not one real StreamField queryable as-is."""
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
        """Sub-events named in the homepage box's dropdown (home_eventsbox.
        html) -- the rest stay count-only there, still fully listed on this
        event's own page regardless. Today's sub-event(s) win whenever
        there's anything scheduled today (e.g. day 3 of a week-long event
        like Fadderuke), so the homepage always surfaces "what's on today"
        without an editor having to re-flag is_highlighted daily. Falls back
        to the explicitly-curated is_highlighted set otherwise -- before the
        event starts (a "coming up" teaser) or on a day with nothing
        scheduled."""
        today_events = self.sub_events.filter(event_date=timezone.localdate())
        if today_events.exists():
            return today_events
        return self.sub_events.filter(is_highlighted=True)

    @property
    def calendar_days(self):
        """This event's sub_events laid out for a week-calendar view
        (event_page.html), one column per distinct date among them, blocks
        positioned/sized by minutes-since-midnight within a shared hour
        range spanning just the sub_events themselves (not a fixed 00-24)
        -- and fanned out side by side within a day when their times
        overlap, same as a real calendar app does for a scheduling clash
        (see _cluster_overlapping/_assign_columns below).

        Untimed sub-events (event_time blank -- "no specific time", per the
        field's own comment above) can't be placed on a grid at all, so
        they come back separately under "untimed" rather than being
        silently dropped."""
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
            # No stored end -- fall back to a nominal 1-hour block, same as
            # a bare click-to-create event in most calendar apps.
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

        # top_pct per label, same math as each block above -- lets the
        # template position labels by percentage (so they line up with the
        # actual gridlines/blocks) instead of doing arithmetic itself.
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


# event_type -> calendar_color fallback for events that never picked one --
# only a rough default (event_type's own 4 categories can't distinguish
# e.g. "food" from "alcohol-free social" the way calendar_color can), good
# enough for whatever wasn't worth an editor's explicit color choice.
_AUTO_CALENDAR_COLOR_BY_EVENT_TYPE = {
    "academic": "blue",
    "deadline": "pink",
    "company": "purple",
    "social": "orange",
    "other": "orange",
}


def _resolve_calendar_color(event):
    """The (color_key, custom_hex) this event's calendar block should
    render with -- color_key is a CSS class suffix (event-calendar-block--
    {{ color_key }}, event_page.css) for every choice except "custom",
    where custom_hex (calendar_color_custom) is the real color and
    color_key is just the class that applies dark text to it."""
    color = event.calendar_color or _AUTO_CALENDAR_COLOR_BY_EVENT_TYPE.get(event.event_type, "orange")
    if color == "custom" and event.calendar_color_custom:
        return "custom", event.calendar_color_custom
    return color, None


def _pct(numerator, denominator):
    """A percentage pre-formatted as a plain '12.34' string, not a float --
    these values only ever land in an inline `style="...%"` attribute
    (event_page.html), and Django's own {{ }} number rendering is locale-
    aware (USE_L10N): the active nb locale would render e.g. 7.69 as
    "7,69", a comma decimal separator that's simply invalid inside CSS and
    silently drops the whole declaration, breaking every block's
    positioning. Plain str formatting here is never locale-aware, unlike
    the template's own filters."""
    return f"{numerator / denominator * 100:.4f}"


def _cluster_overlapping(events, start_minutes, end_minutes):
    """Partition start-time-sorted `events` into clusters of transitively
    overlapping events -- two events overlap directly if their time ranges
    intersect; two clusters merge if any pair across them does. A single
    sweep is enough: a new event only starts a fresh cluster once every
    event in the current cluster has already ended by the time this one
    starts (current_max_end tracks that "already ended" point)."""
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
    events: walking in start-time order, each event gets the lowest-
    numbered column whose most recent occupant has already ended by this
    event's own start -- the same side-by-side fan-out a real calendar app
    uses for a scheduling clash, rather than stacking overlapping events on
    top of each other. column_count is per cluster, not global, so an
    event with no clash of its own still gets the full day-column width
    even if some other, unrelated cluster later that day needed several."""
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
    """Live, still-upcoming events that tag `union` in their related_unions
    field, regardless of role -- for UnionPage.get_context()'s own "Upcoming
    Events" section (see article_models.py; imported there via a
    function-local import to avoid a circular import, since this module
    already imports TranslationWarningMixin from article_models).

    related_unions is a StreamField, not a real relation, so this can't be
    a plain .filter() the way a ForeignKey/M2M would allow -- filtered in
    Python instead, comparing by translation_key (not raw page id) so a
    union tagged on an nb event still matches when viewing the en
    translation of that same union, and vice versa. Fine at this site's
    scale; avoids DB-specific JSON-lookup SQL that'd behave differently
    between SQLite (dev) and whatever runs in production."""
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
