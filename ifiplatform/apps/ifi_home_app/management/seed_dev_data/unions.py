"""Student-union seeding: the two demo unions under Sosialt, and the
Fadderuke-hosting union roster used by events.py's sub-event seeding."""

from ifi_home_app.models.article_models import StudentUnionCategoryPage, UnionPage

from .constants import FADDERUKE_UNION_SPECS


class UnionSeedMixin:
    def _seed_student_unions(self, sosialt_category, nb_locale, en_locale, seed_image):
        union_category = self._get_or_create_page(
            sosialt_category, StudentUnionCategoryPage, "Studentforeninger", nb_locale,
        )
        self._translate_page(union_category, en_locale)

        for name in ["Testforening 1", "Testforening 2"]:
            union = self._get_or_create_page(
                union_category, UnionPage, name, nb_locale,
                email="testforening@example.com",
                logo=seed_image,
                purpose="Test-formål generert av seed-scriptet.",
                activities="Test-aktiviteter generert av seed-scriptet.",
                union_type="general",
                website_url="https://example.com",
                social_links=[
                    ("social_link", {
                        "platform": "instagram",
                        "url": "https://instagram.com/example",
                    }),
                ],
                member_count_sitting=1,
                member_count_intern=0,
                sitting_members=[
                    ("member", {
                        "name": "Test Testesen",
                        "role": "Leder",
                        "school_email": "test@ifi.uio.no",
                        "picture": seed_image,
                    }),
                ],
            )
            self._translate_page(union, en_locale)

    def _seed_fadderuke_unions(self, nb_locale, en_locale, seed_image):
        """Creates the minimal UnionPage per name in FADDERUKE_UNION_SPECS
        (as children of the same Studentforeninger category Testforening
        1/2 live under), for FADDERUKE_SUB_EVENT_UNIONS to link sub-events
        to via EventPage.related_unions. Returns {title: nb UnionPage}."""
        union_category = StudentUnionCategoryPage.objects.get(
            slug="studentforeninger", locale=nb_locale
        )
        unions = {}
        for title in FADDERUKE_UNION_SPECS:
            union = self._get_or_create_page(
                union_category, UnionPage, title, nb_locale,
                logo=seed_image,
                purpose="En studentforening ved Ifi generert av seed-scriptet.",
                union_type="general",
            )
            self._translate_page(union, en_locale)
            unions[title] = union
        return unions
