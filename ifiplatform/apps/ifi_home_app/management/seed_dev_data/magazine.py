"""MagazineIssue seeding -- a few real >OUTPUT issues for the homepage's
magazine box, so it shows without running sync_output_magazine. They use
the issues' real Sanity IDs, so a later sync updates them instead of adding
duplicates. The covers load from Sanity's CDN, so they need internet."""

from datetime import date

from django.utils import timezone

from ifi_home_app.models import MagazineIssue

_CDN = "https://cdn.sanity.io/images/z7zut3cm/production/"

MAGAZINE_ISSUE_SPECS = [
    (
        "1d38a6b9-e1bd-47bf-9c8f-cee80f99ca8a",
        ">Output utg. 15",
        "output-utg-15",
        "1b43de77fc5f59843b43624f1f6162599760d632-623x802.jpg?rect=11,0,602,802",
        date(2026, 4, 1),
    ),
    (
        "964734a6-085c-4d56-be81-4a8d239762e1",
        ">Output utg. 14",
        "rytme",
        "d8480f6993746eb83a0cb85293ed7ba3bcc867ff-2620x3370.jpg?rect=46,0,2528,3370",
        date(2025, 11, 1),
    ),
    (
        "13a3b023-a00a-47fb-9f12-2b7de13d1467",
        ">Output utg. 13",
        "output",
        "b39a4b7c3eb010733658220ba41b7db9140ca2bb-2620x3370.jpg?rect=46,0,2528,3370",
        date(2025, 4, 1),
    ),
]


class MagazineSeedMixin:  # pylint: disable=too-few-public-methods
    """Adds MAGAZINE_ISSUE_SPECS. Mixed into seed_dev_data's Command,
    which sets created_count/skipped_count."""

    created_count = 0
    skipped_count = 0

    def _seed_magazine_issues(self):
        for sanity_id, title, slug, cover, issue_date in MAGAZINE_ISSUE_SPECS:
            _issue, created = MagazineIssue.objects.get_or_create(
                sanity_id=sanity_id,
                defaults={
                    "title": title,
                    "url": f"https://www.ifiavis.no/utgaver/{slug}",
                    "cover_url": _CDN + cover,
                    "issue_date": issue_date,
                    "last_seen_at": timezone.now(),
                },
            )
            if created:
                self.created_count += 1
                self.stdout.write(f"  created MagazineIssue: {title}")
            else:
                self.skipped_count += 1
