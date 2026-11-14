# pylint: disable=C0114,C0115,C0116
import io
import shutil
import tempfile
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone, translation
from PIL import Image
from wagtail.admin.panels import get_edit_handler

from ifi_home_app.integrations import instagram
from ifi_home_app.models import InstagramAccount, InstagramPost, InstagramSyncState
from ifi_home_app.models.instagram import SYNCED, InstagramPostForm

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
                            }
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
            with self.assertRaisesMessage(instagram.InstagramError, "Invalid user id"):
                instagram.get_account("someone_personal")


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
    def test_renders_posts_with_meme_tag_and_video_icon(self):
        meme = InstagramAccount.objects.get(username="digok.memes")
        post = InstagramPost(
            account=meme,
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
        self.assertIn("is-meme", html)
        self.assertIn(">meme<", html)
        self.assertIn('title="Video"', html)
        self.assertIn("3 h", html)
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
