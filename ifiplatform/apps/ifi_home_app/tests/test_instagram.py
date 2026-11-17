# pylint: disable=C0114,C0115,C0116
import importlib
import io
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone, translation
from PIL import Image
from wagtail.admin.panels import get_edit_handler
from wagtail.models import Locale, Site

from ifi_home_app.integrations import instagram
from ifi_home_app.models import InstagramAccount, InstagramPost, InstagramSyncState
from ifi_home_app.models.article.unions import UnionPage
from ifi_home_app.models.instagram import (
    DEMOCRACY,
    HUMOUR,
    SYNCED,
    UNIVERSITY,
    InstagramPostForm,
    match_union_pages,
    with_union_links,
)

BUSINESS_DISCOVERY = {
    "business_discovery": {
        "username": "unioslo_ifi",
        "name": "UiO - Institutt for Informatikk",
        "profile_picture_url": "https://cdn.example/avatar.jpg",
        "media": {
            "data": [
                {
                    "id": "1",
                    "caption": "Søkekurs torsdag",
                    "media_type": "IMAGE",
                    "media_url": "https://cdn.example/1.jpg",
                    "permalink": "https://www.instagram.com/p/AAA/",
                    "timestamp": "2026-11-12T10:00:00+0000",
                },
                {
                    "id": "2",
                    "media_type": "VIDEO",
                    "thumbnail_url": "https://cdn.example/2-thumb.jpg",
                    "media_url": "https://cdn.example/2.mp4",
                    "permalink": "https://www.instagram.com/reel/BBB/",
                    "timestamp": "2026-11-11T10:00:00+0000",
                },
                {
                    "id": "3",
                    "media_type": "VIDEO",
                    "permalink": "https://www.instagram.com/reel/CCC/",
                    "timestamp": "2026-11-10T10:00:00+0000",
                },
                {
                    "id": "4",
                    "media_type": "CAROUSEL_ALBUM",
                    "permalink": "https://www.instagram.com/p/DDD/",
                    "timestamp": "2026-11-09T10:00:00+0000",
                    "children": {
                        "data": [
                            {
                                "media_type": "IMAGE",
                                "media_url": "https://cdn.example/4a.jpg",
                            },
                            {
                                "media_type": "VIDEO",
                                "thumbnail_url": "https://cdn.example/4b.jpg",
                            },
                        ]
                    },
                },
            ]
        },
    }
}


def _jpeg_bytes():
    out = io.BytesIO()
    Image.new("RGB", (40, 40), "#a3b0fa").save(out, "JPEG")
    return out.getvalue()


class ParseAccountTests(SimpleTestCase):
    def test_reads_images_video_thumbnails_and_album_covers(self):
        account = instagram.parse_account(BUSINESS_DISCOVERY)
        self.assertEqual(account.name, "UiO - Institutt for Informatikk")
        self.assertEqual(
            [(p.instagram_id, p.media_type, p.image_url) for p in account.posts],
            [
                ("1", "image", "https://cdn.example/1.jpg"),
                ("2", "video", "https://cdn.example/2-thumb.jpg"),
                ("4", "album", "https://cdn.example/4a.jpg"),
            ],
        )
        self.assertEqual(
            account.posts[0].posted_at,
            datetime(2026, 11, 12, 10, tzinfo=dt_timezone.utc),
        )

    @override_settings(INSTAGRAM_ACCESS_TOKEN="t", INSTAGRAM_BUSINESS_ACCOUNT_ID="1")
    def test_meta_error_becomes_instagram_error(self):
        response = Mock(status_code=400)
        response.json.return_value = {"error": {"message": "Invalid user id"}}
        with patch(
            "ifi_home_app.integrations.instagram.requests.get", return_value=response
        ):
            with self.assertRaisesMessage(
                instagram.AccountNotReadable, "Invalid user id"
            ):
                instagram.get_account("someone_personal")

    @override_settings(INSTAGRAM_ACCESS_TOKEN="t", INSTAGRAM_BUSINESS_ACCOUNT_ID="1")
    def test_token_errors_are_not_unreadable_accounts(self):
        response = Mock(status_code=400)
        response.json.return_value = {
            "error": {"message": "Error validating access token", "code": 190}
        }
        with patch(
            "ifi_home_app.integrations.instagram.requests.get", return_value=response
        ):
            with self.assertRaises(instagram.InstagramError) as caught:
                instagram.get_account("unioslo_ifi")
        self.assertNotIsInstance(caught.exception, instagram.AccountNotReadable)


def _found(posts, username="unioslo_ifi"):
    return instagram.Account(username, "Name", "", posts)


def _post(n, caption="Hei", hours_ago=None):
    posted = timezone.now() - timedelta(hours=hours_ago if hours_ago is not None else n)
    return instagram.Post(
        str(n),
        f"https://www.instagram.com/p/{n}/",
        caption,
        posted,
        "image",
        f"https://cdn.example/{n}.jpg",
    )


class SyncTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media)
        self.enterContext(
            override_settings(
                MEDIA_ROOT=self.media,
                INSTAGRAM_ACCESS_TOKEN="t",
                INSTAGRAM_BUSINESS_ACCOUNT_ID="1",
            )
        )
        InstagramAccount.objects.update(is_active=False)
        self.account = InstagramAccount.objects.get(username="unioslo_ifi")
        self.account.is_active = True
        self.account.save()
        self.enterContext(
            patch.object(instagram, "download", return_value=_jpeg_bytes())
        )
        self.enterContext(
            patch.object(instagram, "token_expires_at", return_value=None)
        )

    def sync(self, posts):
        with patch.object(instagram, "get_account", return_value=_found(posts)):
            call_command(
                "sync_instagram_posts", stdout=io.StringIO(), stderr=io.StringIO()
            )

    def run_failing(self, error):
        """One sync run where Meta raises `error`; True if the run failed."""
        with patch.object(instagram, "get_account", side_effect=error) as fake:
            try:
                call_command(
                    "sync_instagram_posts", stdout=io.StringIO(), stderr=io.StringIO()
                )
            except CommandError:
                return True, fake.called
        return False, fake.called

    def test_unreadable_account_is_paused_after_three_runs(self):
        error = instagram.AccountNotReadable("Meta refused: Invalid user id")
        self.assertEqual(self.run_failing(error), (True, True))
        self.assertEqual(self.run_failing(error), (True, True))
        self.assertEqual(self.run_failing(error), (False, True))
        self.account.refresh_from_db()
        self.assertTrue(self.account.sync_paused)
        self.assertEqual(self.run_failing(error), (False, False))

    def test_other_errors_never_pause(self):
        error = instagram.InstagramError("Could not reach Meta: timeout")
        for _ in range(4):
            self.run_failing(error)
        self.account.refresh_from_db()
        self.assertFalse(self.account.sync_paused)
        self.assertEqual(self.account.failed_runs, 0)

    def test_a_run_where_every_account_fails_is_not_counted(self):
        other = InstagramAccount.objects.get(username="ifinavet")
        other.is_active = True
        other.save()
        error = instagram.AccountNotReadable("Meta refused: Invalid user id")
        for _ in range(4):
            self.run_failing(error)
        self.account.refresh_from_db()
        self.assertFalse(self.account.sync_paused)
        self.assertEqual(self.account.failed_runs, 0)

    def test_a_collab_post_stays_under_the_first_account(self):
        other = InstagramAccount.objects.get(username="ifinavet")
        other.is_active = True
        other.save()

        def fake(username, **_kwargs):
            return _found([_post(1)], username=username)

        with patch.object(instagram, "get_account", side_effect=fake):
            call_command(
                "sync_instagram_posts", stdout=io.StringIO(), stderr=io.StringIO()
            )
            call_command(
                "sync_instagram_posts", stdout=io.StringIO(), stderr=io.StringIO()
            )
        self.assertEqual(InstagramPost.objects.filter(instagram_id="1").count(), 1)
        self.assertEqual(
            len(os.listdir(os.path.join(self.media, "instagram/posts"))), 1
        )

    def test_old_posts_of_paused_accounts_are_deleted(self):
        self.sync([_post(1)])
        post = self.account.posts.get()
        InstagramPost.objects.filter(pk=post.pk).update(
            posted_at=timezone.now() - timedelta(days=400)
        )
        InstagramAccount.objects.filter(pk=self.account.pk).update(sync_paused=True)
        self.sync([])
        self.assertFalse(InstagramPost.objects.filter(pk=post.pk).exists())
        self.assertFalse(default_storage.exists(post.image.name))

    def test_deleting_an_account_deletes_its_profile_picture(self):
        self.account.profile_picture.save("x.jpg", ContentFile(_jpeg_bytes()))
        name = self.account.profile_picture.name
        self.assertTrue(default_storage.exists(name))
        self.account.delete()
        self.assertFalse(default_storage.exists(name))

    def test_a_good_run_resets_the_count(self):
        InstagramAccount.objects.filter(pk=self.account.pk).update(failed_runs=2)
        self.sync([_post(1)])
        self.account.refresh_from_db()
        self.assertEqual(self.account.failed_runs, 0)

    def test_unticking_paused_tries_again(self):
        self.account.sync_paused = True
        self.account.failed_runs = 3
        self.account.save()
        self.account.sync_paused = False
        self.account.save()
        self.assertEqual(self.account.failed_runs, 0)
        self.sync([_post(1)])
        self.assertTrue(self.account.posts.exists())

    def test_creates_posts_with_their_images(self):
        self.sync([_post(1), _post(2)])
        posts = list(self.account.posts.all())
        self.assertEqual([p.instagram_id for p in posts], ["1", "2"])
        self.assertTrue(all(p.source == SYNCED and p.image for p in posts))
        self.assertEqual(posts[0].image_width, 40)

    def test_updates_caption_but_keeps_hidden(self):
        self.sync([_post(1)])
        self.account.posts.update(hidden=True)
        self.sync([_post(1, caption="Ny tekst")])
        post = self.account.posts.get()
        self.assertEqual((post.caption, post.hidden), ("Ny tekst", True))

    def test_keeps_newest_twelve_synced_and_never_touches_manual(self):
        manual = InstagramPost.objects.create(
            account=self.account,
            permalink="https://www.instagram.com/p/manual/",
            posted_at=timezone.now() - timedelta(days=60),
            image=ContentFile(_jpeg_bytes(), name="manual.jpg"),
        )
        self.sync([_post(n) for n in range(1, 15)])
        synced = self.account.posts.filter(source=SYNCED)
        self.assertEqual(synced.count(), 12)
        self.assertNotIn("14", list(synced.values_list("instagram_id", flat=True)))
        self.assertTrue(InstagramPost.objects.filter(pk=manual.pk).exists())

    def test_posts_older_than_a_year_are_not_kept(self):
        old = _post(1, hours_ago=24 * 400)
        self.sync([_post(2), old])
        self.assertEqual(
            list(self.account.posts.values_list("instagram_id", flat=True)), ["2"]
        )
        stale = self.account.posts.get()
        InstagramPost.objects.filter(pk=stale.pk).update(
            posted_at=timezone.now() - timedelta(days=400)
        )
        image = stale.image.name
        self.sync([])
        self.assertFalse(self.account.posts.exists())
        self.assertFalse(stale.image.storage.exists(image))

    def test_one_failing_account_is_recorded_and_others_still_sync(self):
        other = InstagramAccount.objects.get(username="digok.memes")
        other.is_active = True
        other.save()

        def fake(username, **_kwargs):
            if username == "digok.memes":
                raise instagram.InstagramError("Meta refused: not a business account")
            return _found([_post(1)])

        with patch.object(instagram, "get_account", side_effect=fake):
            with self.assertRaises(CommandError):
                call_command(
                    "sync_instagram_posts", stdout=io.StringIO(), stderr=io.StringIO()
                )
        other.refresh_from_db()
        self.assertIn("not a business account", other.last_error)
        self.assertEqual(self.account.posts.count(), 1)

    def test_without_token_nothing_happens(self):
        with override_settings(INSTAGRAM_ACCESS_TOKEN=""):
            with patch.object(instagram, "get_account") as get_account:
                call_command("sync_instagram_posts", stdout=io.StringIO())
        get_account.assert_not_called()

    def test_token_expiry_is_recorded(self):
        soon = timezone.now() + timedelta(days=3)
        with patch.object(instagram, "token_expires_at", return_value=soon):
            self.sync([])
        self.assertTrue(InstagramSyncState.load().expires_soon())


class PostAdminFormTests(TestCase):
    def test_synced_posts_only_allow_hiding(self):
        account = InstagramAccount.objects.get(username="unioslo_ifi")
        post = InstagramPost(account=account, source=SYNCED, posted_at=timezone.now())
        post.pk = 1
        form_class = get_edit_handler(InstagramPost).get_form_class()
        self.assertTrue(issubclass(form_class, InstagramPostForm))
        form = form_class(instance=post)
        self.assertFalse(form.fields["hidden"].disabled)
        self.assertTrue(form.fields["caption"].disabled)


class FeedTemplateTests(TestCase):
    def test_renders_posts_with_humour_tag_and_video_icon(self):
        humour = InstagramAccount.objects.get(username="digok.memes")
        post = InstagramPost(
            account=humour,
            permalink="https://www.instagram.com/p/X/",
            caption="når obligen er innlevert",
            posted_at=timezone.now() - timedelta(hours=3),
            media_type="video",
        )
        post.image.name = "instagram/posts/x.jpg"
        with translation.override("en"):
            html = render_to_string(
                "home/partials/instagram/instagram.html", {"instagram_posts": [post]}
            )
        self.assertIn('<span class="home-instagram-tag is-humour">humour</span>', html)
        self.assertIn('title="Video"', html)
        self.assertIn("3 h", html)
        self.assertIn(
            'class="home-instagram-open" href="https://www.instagram.com/p/X/"', html
        )
        self.assertNotIn('<a class="home-instagram-image"', html)
        self.assertIn("That's the 1 newest posts.", html)

    def test_renders_nothing_without_posts(self):
        html = render_to_string(
            "home/partials/instagram/instagram.html", {"instagram_posts": []}
        )
        self.assertEqual(html.strip(), "")

    def test_age_labels(self):
        now = timezone.now()
        post = InstagramPost(posted_at=now - timedelta(days=10))
        with translation.override("nb"):
            self.assertEqual(post.age(now), "1 u")


class CaptionMoreTests(SimpleTestCase):
    def test_only_long_or_multiline_captions_get_more(self):
        self.assertFalse(InstagramPost(caption="Fredagsbar kl. 18").caption_is_long)
        self.assertTrue(InstagramPost(caption="x" * 71).caption_is_long)
        self.assertTrue(InstagramPost(caption="Linje én\nLinje to").caption_is_long)


class ShowMoreToggleTests(TestCase):
    def _posts(self, n):
        account = InstagramAccount.objects.get(username="unioslo_ifi")
        posts = []
        for i in range(n):
            post = InstagramPost(
                account=account,
                permalink=f"https://www.instagram.com/p/{i}/",
                posted_at=timezone.now(),
            )
            post.image.name = f"instagram/posts/{i}.jpg"
            posts.append(post)
        return posts

    def render(self, n):
        return render_to_string(
            "home/partials/instagram/instagram.html",
            {"instagram_posts": self._posts(n)},
        )

    def test_toggle_only_when_there_is_more_than_one_row_on_phones(self):
        self.assertNotIn("home-instagram-toggle", self.render(2))
        self.assertIn("home-instagram-toggle", self.render(3))


class ParseMediaTests(SimpleTestCase):
    def test_video_file_and_album_pictures(self):
        posts = {
            p.instagram_id: p for p in instagram.parse_account(BUSINESS_DISCOVERY).posts
        }
        self.assertEqual(posts["2"].video_url, "https://cdn.example/2.mp4")
        self.assertEqual(posts["1"].video_url, "")
        self.assertEqual(
            posts["4"].album_urls,
            ("https://cdn.example/4a.jpg", "https://cdn.example/4b.jpg"),
        )


def _video_file():
    # pylint: disable-next=consider-using-with
    out = tempfile.NamedTemporaryFile(suffix=".mp4")
    out.write(b"fake mp4")
    out.flush()
    out.seek(0)
    return out


class ShownMediaSyncTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media)
        self.enterContext(
            override_settings(
                MEDIA_ROOT=self.media,
                INSTAGRAM_ACCESS_TOKEN="t",
                INSTAGRAM_BUSINESS_ACCOUNT_ID="1",
            )
        )
        InstagramAccount.objects.update(is_active=False)
        self.account = InstagramAccount.objects.get(username="unioslo_ifi")
        self.account.is_active = True
        self.account.save()
        self.enterContext(
            patch.object(instagram, "download", return_value=_jpeg_bytes())
        )
        self.enterContext(
            patch.object(instagram, "token_expires_at", return_value=None)
        )
        self.enterContext(
            patch.object(
                instagram, "download_video", side_effect=lambda url: _video_file()
            )
        )
        now = timezone.now()
        self.posts = [
            instagram.Post(
                "v",
                "https://www.instagram.com/p/v/",
                "",
                now,
                "video",
                "https://cdn.example/v.jpg",
                video_url="https://cdn.example/v.mp4",
            ),
            instagram.Post(
                "n",
                "https://www.instagram.com/p/n/",
                "",
                now - timedelta(hours=1),
                "video",
                "https://cdn.example/n.jpg",
            ),
            instagram.Post(
                "a",
                "https://www.instagram.com/p/a/",
                "",
                now - timedelta(hours=2),
                "album",
                "https://cdn.example/a1.jpg",
                album_urls=(
                    "https://cdn.example/a1.jpg",
                    "https://cdn.example/a2.jpg",
                    "https://cdn.example/a3.jpg",
                ),
            ),
        ]

    def sync(self):
        with patch.object(instagram, "get_account", return_value=_found(self.posts)):
            call_command(
                "sync_instagram_posts", stdout=io.StringIO(), stderr=io.StringIO()
            )

    def test_shown_posts_get_video_and_album_pictures(self):
        self.sync()
        video = InstagramPost.objects.get(instagram_id="v")
        self.assertTrue(video.video)
        self.assertFalse(InstagramPost.objects.get(instagram_id="n").video)
        album = InstagramPost.objects.get(instagram_id="a")
        self.assertEqual(album.album_images.count(), 2)
        self.assertEqual(len(album.pictures), 3)

    def test_posts_outside_the_feed_keep_their_media_until_deleted(self):
        self.sync()
        InstagramPost.objects.filter(instagram_id__in=["v", "a"]).update(hidden=True)
        self.sync()
        video = InstagramPost.objects.get(instagram_id="v")
        self.assertTrue(video.video)
        name = video.video.name
        self.assertEqual(
            InstagramPost.objects.get(instagram_id="a").album_images.count(), 2
        )
        video.delete()
        self.assertFalse(default_storage.exists(name))


class MorePostsViewTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media)
        self.enterContext(override_settings(MEDIA_ROOT=self.media))

    def test_returns_every_post_so_the_viewer_can_drop_what_it_has(self):
        account = InstagramAccount.objects.get(username="unioslo_ifi")
        now = timezone.now()
        for i in range(14):
            InstagramPost.objects.create(
                account=account,
                permalink=f"https://www.instagram.com/p/{i}/",
                posted_at=now - timedelta(hours=i),
                image=ContentFile(_jpeg_bytes(), name=f"{i}.jpg"),
            )
        with translation.override("en"):
            html = self.client.get(reverse("instagram_more_posts")).content.decode()
        self.assertEqual(html.count('class="home-instagram-viewer-post"'), 14)
        self.assertIn('aria-label="Post 13 of 14"', html)
        self.assertIn('data-index="12"', html)
        self.assertIn("https://www.instagram.com/p/13/", html)


class ViewerTemplateTests(TestCase):
    def _post(self, **kwargs):
        post = InstagramPost(
            account=InstagramAccount.objects.get(username="unioslo_ifi"),
            permalink="https://www.instagram.com/p/X/",
            caption="Hei",
            posted_at=timezone.now(),
            **kwargs,
        )
        post.image.name = "instagram/posts/x.jpg"
        return post

    def render(self, post, **context):
        with translation.override("en"):
            return render_to_string(
                "home/partials/instagram/instagram.html",
                {"instagram_posts": [post], **context},
            )

    def test_video_with_a_file_plays_on_the_site(self):
        post = self._post(media_type="video")
        post.video.name = "instagram/videos/x.mp4"
        html = self.render(post)
        self.assertIn(
            '<video class="home-instagram-video" controls preload="none"', html
        )
        self.assertNotIn("Watch on Instagram", html)
        self.assertIn('<button class="home-instagram-sound" type="button"', html)
        self.assertIn('<span class="home-instagram-progress"', html)

    def test_video_without_a_file_links_to_instagram(self):
        html = self.render(self._post(media_type="video"))
        self.assertNotIn("<video", html)
        self.assertIn("Watch on Instagram", html)
        self.assertNotIn("home-instagram-sound", html)

    def test_viewer_dialog_has_every_post(self):
        html = self.render(self._post())
        self.assertIn('<dialog class="home-instagram-viewer"', html)
        self.assertIn('data-index="0"', html)
        self.assertIn('data-total="1"', html)
        self.assertNotIn("data-more-url", html)

    def test_viewer_cards_can_hide_seen_posts(self):
        post = self._post()
        post.pk = 41
        html = self.render(post)
        self.assertIn('data-post="41"', html)
        self.assertIn('<p class="home-instagram-viewer-status" hidden>', html)
        self.assertIn('data-hidden-count="{n} seen hidden"', html)
        self.assertIn(
            '<section class="home-instagram-viewer-post home-instagram-viewer-end" hidden>',
            html,
        )
        self.assertIn("Show them anyway", html)
        with translation.override("nb"):
            html = render_to_string(
                "home/partials/instagram/instagram.html", {"instagram_posts": [post]}
            )
        self.assertIn("Skjuler sette", html)
        self.assertIn('data-off="Viser sette"', html)
        self.assertIn('data-hidden-count="{n} sette skjult"', html)

    def test_viewer_counts_every_stored_post_and_loads_the_rest(self):
        html = self.render(self._post(), instagram_total=14)
        self.assertIn('data-total="14"', html)
        self.assertIn('aria-label="Post 1 of 14"', html)
        self.assertIn('data-more-url="/en/api/instagram/posts/"', html)


def _make_union_page(title, instagram_url):
    root = Site.objects.get(is_default_site=True).root_page
    union = UnionPage(
        title=title,
        slug=title.lower(),
        locale=Locale.get_default(),
        social_links=[("social_link", {"platform": "instagram", "url": instagram_url})],
    )
    root.add_child(instance=union)
    union.save_revision().publish()
    return union


class AccountTypeTests(TestCase):
    def test_migration_sorts_the_existing_accounts(self):
        migration = importlib.import_module(
            "ifi_home_app.migrations.0166_instagram_account_types"
        )
        self.assertEqual(migration.new_type("digok.memes", "meme"), "humour")
        self.assertEqual(migration.new_type("unioslo_ifi", "official"), "university")
        self.assertEqual(migration.new_type("sp_uio", "official"), "democracy")
        self.assertEqual(migration.new_type("outputifi", "official"), "media")
        self.assertEqual(migration.new_type("fui_ifi", "official"), "union")
        self.assertEqual(
            InstagramAccount.objects.get(username="gangen_i_tredje").kind, HUMOUR
        )

    def test_tags_are_translated(self):
        account = InstagramAccount(username="x", kind=DEMOCRACY)
        with translation.override("nb"):
            self.assertEqual(account.tag, "studentdemokrati")
        account.kind = UNIVERSITY
        self.assertEqual(account.tag, "UiO")


class UnionLinkTests(TestCase):
    def test_sync_links_accounts_listed_on_a_union_page(self):
        navet = _make_union_page("Navet", "https://www.instagram.com/IfiNavet/?hl=nb")
        _make_union_page("Other", "https://instagram.com/somebody_else")
        self.assertEqual(match_union_pages(), 1)
        account = InstagramAccount.objects.get(username="ifinavet")
        self.assertEqual(account.union_page_id, navet.pk)
        self.assertEqual(match_union_pages(), 0)

    def test_sync_never_replaces_a_link_an_admin_set(self):
        chosen = _make_union_page("Chosen", "https://instagram.com/nobody")
        _make_union_page("Navet", "https://instagram.com/ifinavet")
        account = InstagramAccount.objects.get(username="ifinavet")
        account.union_page = chosen
        account.save()
        match_union_pages()
        account.refresh_from_db()
        self.assertEqual(account.union_page_id, chosen.pk)

    def test_about_line_links_to_the_union_page(self):
        navet = _make_union_page("Navet", "https://instagram.com/ifinavet")
        match_union_pages()
        post = InstagramPost(
            account=InstagramAccount.objects.get(username="ifinavet"),
            permalink="https://www.instagram.com/p/X/",
            posted_at=timezone.now(),
        )
        post.image.name = "instagram/posts/x.jpg"
        [post] = with_union_links([post])
        with translation.override("en"):
            html = render_to_string(
                "home/partials/instagram/post_header.html", {"post": post}
            )
        self.assertIn('<span class="home-instagram-tag is-union">union</span>', html)
        self.assertIn(
            f'<a class="home-instagram-union" href="{navet.localized.url}">'
            "About Navet &rarr;</a>",
            html,
        )
