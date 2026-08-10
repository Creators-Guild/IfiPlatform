"""Models for the Events section: a plain index/leaf pair (EventIndexPage ->
EventPage), same shape as StudentUnionCategoryPage -> UnionPage. No editor-
mode on-page tooling (EditorModeMixin/BannerStyleMixin) on either page yet --
unlike ArticlePage/CategoryPage, there's no on-page style panel for events to
plug into; add it later if that changes. TranslationWarningMixin is kept
since it's free and these pages need nb/en translations like everything else
on this bilingual site."""

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

from ifi_home_app.models.article_models import TranslationWarningMixin


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
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional -- for events spanning more than one day.",
    )
    location = models.CharField(max_length=200, blank=True)
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

    signup_url = models.URLField(
        blank=True,
        help_text="Optional -- link to a signup/registration form for this event.",
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
        FieldPanel("end_date"),
        FieldPanel("location"),
        FieldPanel("intro"),
        FieldPanel("show_on_homepage"),
        FieldPanel("is_highlighted"),
        FieldPanel("related_unions"),
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
    def sub_events(self):
        """This event's own live sub-events (if any), in date order --
        shown on its own page (event_page.html) and counted (not listed)
        in the homepage box (home_eventsbox.html)."""
        return EventPage.objects.child_of(self).live().order_by("event_date", "event_time")

    @property
    def highlighted_sub_events(self):
        """The subset of sub_events explicitly marked is_highlighted --
        these are the only ones actually named in the homepage box's
        dropdown (home_eventsbox.html); the rest stay count-only there,
        still fully listed on this event's own page regardless."""
        return self.sub_events.filter(is_highlighted=True)


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
