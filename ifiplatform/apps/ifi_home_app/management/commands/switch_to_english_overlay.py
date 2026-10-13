"""One-time switch from wagtail-localize's two page trees to one Norwegian
tree with English stored as text pieces. Forward-only.

Dry run by default: does everything inside a transaction, prints the
report, then rolls back. `--apply` keeps it. Does nothing once the English
locale is gone. The steps and why: docs/claude_references/translation_redesign.md
("Migration"); design notes: docs/claude_context/translation_overlay.md."""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from modelcluster.models import get_all_child_relations
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Locale, Page, ReferenceIndex, Site, TranslatableMixin
from wagtail_localize import models as localize
from wagtail_localize.segments import StringSegmentValue
from wagtail_localize.segments.extract import extract_segments as localize_segments

from ...translation import english_urls, page_segments, stored_translations
from ...translation.page_segments import Segment

# wagtail-localize's tables, emptied in this order (segments PROTECT their
# context, so they go before it).
LOCALIZE_MODELS = [
    localize.StringTranslation,
    localize.SegmentOverride,
    localize.StringSegment,
    localize.TemplateSegment,
    localize.RelatedObjectSegment,
    localize.OverridableSegment,
    localize.TranslationLog,
    localize.Translation,
    localize.TranslationSource,
    localize.TranslationContext,
    localize.String,
    localize.Template,
    localize.LocaleSynchronization,
    localize.TranslatableObject,
]
_PAGE_LINK = re.compile(r"<a\b[^>]*>")


class _DryRun(Exception):
    pass


@dataclass
class Report:
    copied: dict = field(default_factory=lambda: defaultdict(int))
    skipped_technical: Counter = field(default_factory=Counter)
    no_twin: list = field(default_factory=list)
    typed_directly: list = field(default_factory=list)
    format_mismatches: list = field(default_factory=list)
    slugs: int = 0
    slug_clashes: list = field(default_factory=list)
    repointed: list = field(default_factory=list)
    unsupported_references: list = field(default_factory=list)
    redirects: list = field(default_factory=list)
    english_only_deleted: list = field(default_factory=list)
    deleted: dict = field(default_factory=dict)
    lost: list = field(default_factory=list)
    before_after: dict = field(default_factory=dict)

    def lines(self):
        copied = self.copied
        yield "English pieces copied:"
        yield f"  from wagtail-localize: {copied['human']} by people, {copied['deepl']} DeepL"
        yield f"  written in English first (snippets): {copied['english first']}"
        yield f"  typed straight into English copies (paired by place): {copied['typed']}"
        yield (
            "  not copied (not a translated place, e.g. IDs): "
            f"{sum(self.skipped_technical.values())}"
        )
        for place, count in self.skipped_technical.most_common():
            yield f"    {count:4} {place}"
        for label in self.typed_directly:
            yield f"    typed directly: {label}"
        for label in self.no_twin:
            yield f"  no Norwegian object to attach to: {label}"
        yield f"English slugs kept: {self.slugs}"
        for clash in self.slug_clashes:
            yield f"  changed to stay unique: {clash}"
        yield f"References to English objects repointed to Norwegian: {len(self.repointed)}"
        for item in self.repointed:
            yield f"  {item}"
        yield f"Redirects for English addresses that change: {len(self.redirects)}"
        for old, new in self.redirects:
            yield f"  {old} -> {new}"
        yield f"English-only pages deleted: {len(self.english_only_deleted)}"
        for label in self.english_only_deleted:
            yield f"  {label}"
        yield "English copies deleted: " + ", ".join(
            f"{n} {what}" for what, n in self.deleted.items()
        )
        for label in self.lost:
            yield f"  lost (English copy without Norwegian twin): {label}"
        before, after = self.before_after.get("before", 0), self.before_after.get(
            "after", 0
        )
        total = self.before_after.get("total", 0)
        yield f"Pieces with English: {before} shown before -> {after} stored now, of {total}"
        yield f"  missing after (DeepL fills them): {total - after}"


def _label(obj):
    name = getattr(obj, "title", None) or getattr(obj, "label", None) or str(obj)
    return f"{type(obj).__name__} {obj.pk} “{str(name)[:50]}”"


def _translatable_models():
    """Project page types and snippets that wagtail-localize translated."""
    return [
        model
        for model in apps.get_models()
        if issubclass(model, TranslatableMixin)
        and (model is Page or model._meta.app_label == "ifi_home_app")
        and not model._meta.abstract
    ]


def _objects(locale):
    """{translation_key: object} for every page (specific) and translated
    snippet in `locale`."""
    found = {}
    for page in Page.objects.filter(locale=locale, depth__gt=1).specific():
        found[page.translation_key] = page
    for model in _translatable_models():
        if not issubclass(model, Page):
            for obj in model._default_manager.filter(locale=locale):
                found.setdefault(obj.translation_key, obj)
    return found


class Command(BaseCommand):
    help = (
        "Switches from two page trees to one Norwegian tree with stored English. "
        "Dry run unless --apply."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Keep the changes.")

    def handle(self, *args, **options):
        english = Locale.objects.filter(language_code="en").first()
        if english is None:
            self.stdout.write("Already switched: there is no English locale.")
            return
        norwegian = Locale.objects.get(language_code="nb")
        report = Report()
        try:
            with transaction.atomic():
                failure = _switch(english, norwegian, report)
                for line in report.lines():
                    self.stdout.write(line)
                if failure:
                    raise CommandError(failure + " Nothing was changed.")
                if not options["apply"]:
                    raise _DryRun
        except _DryRun:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run: nothing was changed. Run with --apply to switch."
                )
            )
            return
        self.stdout.write(
            self.style.SUCCESS("Switched to one Norwegian tree with stored English.")
        )


def _switch(english, norwegian, report):
    """All steps; returns a failure message, or None."""
    nb_objects, en_objects = _objects(norwegian), _objects(english)
    nb_counts = _counts(norwegian)

    mismatches = _check_format(nb_objects.values())
    if mismatches:
        report.format_mismatches = mismatches
        return (
            "Our text pieces differ from wagtail-localize's on: "
            + "; ".join(mismatches[:10])
            + ". Copied English would not match."
        )
    rows, before = _rows_from_localize(english, norwegian, nb_objects, report)
    before += _rows_typed_directly(nb_objects, en_objects, rows, report)
    for target, target_rows in rows.items():
        stored_translations.import_rows(target, target_rows)

    _copy_slugs(nb_objects, en_objects, report)
    problem = _repoint_references(english, nb_objects, en_objects, report)
    if problem:
        return problem
    _add_redirects(english, nb_objects, en_objects, report)
    _delete_english(english, norwegian, nb_objects, report)

    after = total = 0
    for obj in _objects(norwegian).values():
        stored = stored_translations.lookup(obj)
        for segment in page_segments.extract_segments(obj):
            total += 1
            after += (segment.path, segment.norwegian_hash) in stored
    report.before_after = {"before": before, "after": after, "total": total}
    if _counts(norwegian) != nb_counts:
        return (
            "Norwegian objects changed while deleting the English copies: "
            f"{nb_counts} before, {_counts(norwegian)} after."
        )
    if after < before:
        return f"Fewer pieces have English after ({after}) than before ({before})."
    return None


def _counts(locale):
    counts = {"pages": Page.objects.filter(locale=locale, depth__gt=1).count()}
    for model in _translatable_models():
        if not issubclass(model, Page):
            counts[model.__name__] = model._default_manager.filter(
                locale=locale
            ).count()
    return counts


def _check_format(objects):
    """Every piece we extract must be one wagtail-localize extracted too,
    same place and same text: otherwise copied English wouldn't match."""
    mismatches = []
    for obj in objects:
        theirs = {
            (value.path, value.string.data)
            for value in localize_segments(obj)
            if isinstance(value, StringSegmentValue)
        }
        ours = {(s.path, s.norwegian_text) for s in page_segments.extract_segments(obj)}
        if ours - theirs:
            mismatches.append(f"{_label(obj)}: {sorted(ours - theirs)[:2]}")
    return mismatches


# Fields renamed since wagtail-localize recorded their pieces: (model name,
# old place) -> new place.
RENAMED_PLACES = {("MenuGroupLink", "prefix"): "label_prefix"}


def _resolve_child(obj, path):
    """wagtail-localize stores a child object's pieces under its parent
    ("links.<link key>.label"); we store them on the child itself."""
    parts = path.split(".")
    if len(parts) >= 3:
        for relation in get_all_child_relations(obj):
            if relation.get_accessor_name() == parts[0]:
                child = (
                    getattr(obj, parts[0])
                    .filter(translation_key=parts[1], locale_id=obj.locale_id)
                    .first()
                )
                return child, ".".join(parts[2:])
    return obj, path


def _rows_from_localize(english, norwegian, nb_objects, report):
    """Rows from wagtail-localize's records, which say which Norwegian each
    English translates. Returns ({target: rows}, pieces shown in English
    before: current Norwegian pieces that had a record)."""
    rows = defaultdict(list)
    translations = localize.StringTranslation.objects.select_related(
        "translation_of", "context__object", "last_translated_by"
    )
    for record in translations:
        obj = nb_objects.get(record.context.object.translation_key)
        if record.locale_id == english.pk:
            norwegian_text, english_text = record.translation_of.data, record.data
            manual = (
                record.translation_type
                == localize.StringTranslation.TRANSLATION_TYPE_MANUAL
            )
            source, user = (
                ("human", record.last_translated_by) if manual else ("deepl", None)
            )
            kind = source
        elif record.locale_id == norwegian.pk:  # written in English first
            norwegian_text, english_text = record.data, record.translation_of.data
            source, user, kind = "human", None, "english first"
        else:
            continue
        if obj is None:
            report.no_twin.append(
                f"{record.context.object.content_type.model} piece {record.context.path}"
            )
            continue
        target, path = _resolve_child(obj, record.context.path)
        if target is not None:
            path = RENAMED_PLACES.get((type(target).__name__, path), path)
        if target is None or not page_segments.is_translated_place(type(target), path):
            report.skipped_technical[
                f"{record.context.object.content_type.model}: "
                + page_segments.place_of(record.context.path)
            ] += 1
            continue
        rows[target].append(
            (
                Segment(path, norwegian_text),
                english_text,
                source,
                user,
                record.has_error,
                record.field_error or "",
            )
        )
        report.copied[kind] += 1

    before = 0
    for target, target_rows in rows.items():
        known = {
            (row[0].path, row[0].norwegian_text) for row in target_rows if not row[4]
        }
        before += sum(
            (s.path, s.norwegian_text) in known
            for s in page_segments.extract_segments(target)
        )
    return rows, before


def _rows_typed_directly(nb_objects, en_objects, rows, report):
    """English typed straight into an English copy (no wagtail-localize
    record, e.g. menu groups): paired with the Norwegian twin by place.
    Not provably current, so listed in the report. Returns the number of
    pieces paired (they were shown in English before)."""
    total = 0
    for key, nb_obj in nb_objects.items():
        en_obj = en_objects.get(key)
        if en_obj is None or nb_obj in rows or getattr(en_obj, "alias_of_id", None):
            continue
        by_place = defaultdict(list)
        for segment in page_segments.extract_segments(en_obj):
            by_place[segment.path].append(segment.norwegian_text)
        paired = []
        norwegian_by_place = defaultdict(list)
        for segment in page_segments.extract_segments(nb_obj):
            norwegian_by_place[segment.path].append(segment)
        for path, norwegian in norwegian_by_place.items():
            english_texts = by_place.get(path, [])
            if len(english_texts) != len(norwegian):
                continue
            for segment, text in zip(norwegian, english_texts):
                if text != segment.norwegian_text:
                    paired.append((segment, text, "human", None, False, ""))
        if paired:
            rows[nb_obj] = paired
            total += len(paired)
            report.copied["typed"] += len(paired)
            report.typed_directly.append(f"{_label(nb_obj)}: {len(paired)} piece(s)")
    return total


def _copy_slugs(nb_objects, en_objects, report):
    """Keeps today's English slugs, so most English links don't change. A
    slug equal to the Norwegian one isn't stored: the page falls back to it
    and gets a real English slug from DeepL later (with a redirect)."""
    for key, nb_obj in nb_objects.items():
        en_obj = en_objects.get(key)
        if not isinstance(nb_obj, Page) or en_obj is None or nb_obj.depth <= 2:
            continue
        if en_obj.slug != nb_obj.slug:
            saved = english_urls.set_english_slug(
                nb_obj, en_obj.slug, "human", redirect=False
            )
            report.slugs += 1
            if saved != en_obj.slug:
                report.slug_clashes.append(
                    f"{_label(nb_obj)}: {en_obj.slug} -> {saved}"
                )


def _repoint_references(english, nb_objects, en_objects, report):
    """Norwegian and shared objects that point at an English page or
    snippet are pointed at its Norwegian twin. Supports foreign keys and
    rich text links on snippets; anything else stops the switch-over."""
    en_by_id = {
        (type(obj)._meta.concrete_model, str(obj.pk)): nb_objects[key]
        for key, obj in en_objects.items()
        if key in nb_objects
    }
    english_page_ids = {
        str(obj.pk) for obj in en_objects.values() if isinstance(obj, Page)
    }

    holders = list(nb_objects.values())
    for model in apps.get_models():
        if (
            model._meta.app_label == "ifi_home_app"
            and not issubclass(model, TranslatableMixin)
            and model.__module__ != "ifi_home_app.models.translation"
        ):
            holders += list(model._default_manager.all())

    for holder in holders:
        references = ReferenceIndex._extract_references_from_object(holder)
        for to_content_type_id, to_id, model_path, content_path in references:
            target_model = ContentType.objects.get_for_id(
                to_content_type_id
            ).model_class()
            if target_model is None:
                continue
            is_page = issubclass(target_model, Page)
            if is_page and str(to_id) not in english_page_ids:
                continue
            twin = None
            if is_page:
                english_page = next(
                    (
                        o
                        for o in en_objects.values()
                        if isinstance(o, Page) and str(o.pk) == str(to_id)
                    ),
                    None,
                )
                twin = (
                    nb_objects.get(english_page.translation_key)
                    if english_page
                    else None
                )
            elif issubclass(target_model, TranslatableMixin):
                twin = en_by_id.get((target_model._meta.concrete_model, str(to_id)))
                if twin is None:
                    continue
            else:
                continue
            field_name = model_path.split(".")[0]
            label = (
                f"{_label(holder)} {content_path} -> {type(twin).__name__} {twin.pk}"
            )
            if twin is None or isinstance(holder, Page):
                report.unsupported_references.append(label)
                continue
            model_field = holder._meta.get_field(field_name)
            if model_field.is_relation:
                type(holder)._default_manager.filter(pk=holder.pk).update(
                    **{model_field.attname: twin.pk}
                )
            elif model_field.get_internal_type() in ("TextField",) or hasattr(
                model_field, "features"
            ):
                html = getattr(holder, field_name)
                fixed = _PAGE_LINK.sub(
                    lambda tag: _relink(tag.group(0), to_id, twin.pk), html
                )
                type(holder)._default_manager.filter(pk=holder.pk).update(
                    **{field_name: fixed}
                )
            else:
                report.unsupported_references.append(label)
                continue
            report.repointed.append(label)
    if report.unsupported_references:
        return (
            "Some objects point at English pages in ways this command can't fix "
            "(pages or StreamFields): "
            + "; ".join(report.unsupported_references)
            + ". Point them at the Norwegian page by hand first."
        )
    return None


def _relink(tag, old_id, new_id):
    if 'linktype="page"' not in tag:
        return tag
    return re.sub(rf'\bid="{old_id}"', f'id="{new_id}"', tag)


def _english_root(english):
    site = Site.objects.get(is_default_site=True)
    return (
        site.root_page,
        Page.objects.filter(
            locale=english, translation_key=site.root_page.translation_key
        ).first(),
    )


def _add_redirects(english, nb_objects, en_objects, report):
    """Old /en/ address -> new English address, for every live English page
    whose address changes, and for English-only pages (to the Norwegian
    twin: same Peoply organization for union duplicates, else the nearest
    ancestor with a twin)."""
    nb_root, en_root = _english_root(english)
    if en_root is None:
        return

    def new_path(page):
        return "/en/" + english_urls.english_url_path(page, nb_root.depth)

    peoply_twins = {
        obj.peoply_organization_id: obj
        for obj in nb_objects.values()
        if getattr(obj, "peoply_organization_id", "")
    }
    for en_page in (
        Page.objects.filter(locale=english, live=True, depth__gt=en_root.depth)
        .descendant_of(en_root)
        .specific()
    ):
        old = "/en/" + en_page.url_path[len(en_root.url_path) :]
        twin = nb_objects.get(en_page.translation_key)
        if twin is None:
            twin = peoply_twins.get(
                getattr(en_page, "peoply_organization_id", "") or None
            )
        if twin is None:
            ancestor = next(
                (
                    nb_objects[a.translation_key]
                    for a in reversed(en_page.get_ancestors())
                    if a.translation_key in nb_objects and a.depth > en_root.depth
                ),
                nb_root,
            )
            twin = ancestor
        new = new_path(twin) if twin.pk != nb_root.pk else "/en/"
        if old != new:
            Redirect.add_redirect(
                Redirect.normalise_path(old), redirect_to=new, is_permanent=True
            )
            report.redirects.append((old, new))


def _delete_english(english, norwegian, nb_objects, report):
    for key, obj in _objects(english).items():
        if key not in nb_objects:
            if isinstance(obj, Page):
                report.english_only_deleted.append(f"{_label(obj)} live={obj.live}")
            else:
                report.lost.append(_label(obj))
    pages = Page.objects.filter(locale=english, depth__gt=1)
    report.deleted["pages"] = pages.count()
    report.deleted["aliases"] = pages.exclude(alias_of=None).count()
    snippet_models = [m for m in _translatable_models() if not issubclass(m, Page)]
    for model in snippet_models:
        report.deleted[model._meta.verbose_name_plural] = model._default_manager.filter(
            locale=english
        ).count()

    for model in LOCALIZE_MODELS:
        model.objects.all().delete()
    for page in pages.order_by("depth"):
        if Page.objects.filter(pk=page.pk).exists():
            page.delete()
    for model in snippet_models:
        model._default_manager.filter(locale=english).delete()

    Page.objects.filter(depth=1, locale=english).update(locale=norwegian)
    english.delete()
