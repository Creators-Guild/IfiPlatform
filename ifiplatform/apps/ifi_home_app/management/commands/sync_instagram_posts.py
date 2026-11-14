"""Copies the newest posts of every active InstagramAccount from Meta's
Graph API (Business Discovery) into InstagramPost rows, downloading each
image once (Meta's image links expire). Synced posts get their caption and
link updated; `hidden` is never touched; only the newest 12 synced posts per
account are kept (older ones and their images are deleted). Posts added by
hand are never changed. The 12 posts the feed shows (shown_posts()) also
get their video file and every album picture; posts that leave the feed
lose them again. One account failing (e.g. a personal account) is
recorded on the account and doesn't stop the others. Without a token in
.env it does nothing. Runs hourly 07-23 from the sync-instagram-posts
systemd timer.

Design rationale: docs/claude_context/home_instagram.md"""

import io

from django.core.files import File
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from ifi_home_app.integrations import instagram
from ifi_home_app.models.instagram import (
    ALBUM,
    POSTS_KEPT_PER_ACCOUNT,
    SYNCED,
    VIDEO,
    InstagramAccount,
    InstagramPost,
    InstagramPostImage,
    InstagramSyncState,
    shown_posts,
)

POST_IMAGE_SIZE = 1080
AVATAR_SIZE = 150


def _jpeg(data, size):
    """`data` as a JPEG no larger than size x size."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            image = image.convert("RGB")
            image.thumbnail((size, size))
            out = io.BytesIO()
            image.save(out, "JPEG", quality=85, optimize=True)
    except (UnidentifiedImageError, OSError) as error:
        raise instagram.InstagramError(f"Not an image: {error}") from error
    return ContentFile(out.getvalue())


class Command(BaseCommand):
    """See the module docstring."""

    help = "Sync the newest posts of the Instagram accounts in the feed."
    # instagram_id -> integrations.instagram.Post fetched this run
    remote = None

    def handle(self, *args, **options):
        if not instagram.is_configured():
            self.stdout.write("No INSTAGRAM_ACCESS_TOKEN in .env: nothing to sync.")
            return
        self._check_token()
        self.remote = {}
        failed = []
        for account in InstagramAccount.objects.filter(is_active=True):
            try:
                created = self._sync_account(account)
            except instagram.InstagramError as error:
                account.last_error = str(error)[:300]
                account.save(update_fields=["last_error"])
                failed.append(f"@{account.username}: {error}")
                continue
            self.stdout.write(f"@{account.username}: {created} new")
        self._sync_shown_media()
        if failed:
            raise CommandError(
                f"{len(failed)} account(s) failed:\n" + "\n".join(failed)
            )
        self.stdout.write(self.style.SUCCESS("Instagram sync done."))

    def _check_token(self):
        try:
            expires_at = instagram.token_expires_at()
        except instagram.InstagramError as error:
            self.stderr.write(f"Could not check the token: {error}")
            return
        state = InstagramSyncState.record_token_expiry(expires_at)
        if state.expires_soon():
            self.stderr.write(
                f"WARNING: the Instagram token expires {expires_at:%Y-%m-%d}. "
                "Renew it (docs/operations/instagram_setup.md)."
            )

    def _sync_account(self, account):
        found = instagram.get_account(account.username, limit=POSTS_KEPT_PER_ACCOUNT)
        if found.name and not account.display_name:
            account.display_name = found.name
        if found.profile_picture_url and not account.profile_picture:
            picture = _jpeg(instagram.download(found.profile_picture_url), AVATAR_SIZE)
            account.profile_picture.save(f"{account.username}.jpg", picture, save=False)
        account.last_synced_at = timezone.now()
        account.last_error = ""
        account.save()

        existing = {
            post.instagram_id: post for post in account.posts.filter(source=SYNCED)
        }
        created = 0
        for post in found.posts:
            self.remote[post.instagram_id] = post
            row = existing.get(post.instagram_id)
            if row is not None:
                row.caption, row.permalink = post.caption, post.permalink
                row.media_type, row.posted_at = post.media_type, post.posted_at
                row.save(
                    update_fields=["caption", "permalink", "media_type", "posted_at"]
                )
                continue
            row = InstagramPost(
                account=account,
                instagram_id=post.instagram_id,
                permalink=post.permalink,
                caption=post.caption,
                posted_at=post.posted_at,
                media_type=post.media_type,
                source=SYNCED,
            )
            image = _jpeg(instagram.download(post.image_url), POST_IMAGE_SIZE)
            row.image.save(f"{post.instagram_id}.jpg", image, save=False)
            row.save()
            created += 1

        keep = account.posts.filter(source=SYNCED).values_list("pk", flat=True)[
            :POSTS_KEPT_PER_ACCOUNT
        ]
        for old in account.posts.filter(source=SYNCED).exclude(pk__in=list(keep)):
            old.delete()
        return created

    def _sync_shown_media(self):
        """Videos and album pictures, only for the posts the feed shows.
        Posts that left the feed lose theirs, to save disk."""
        shown = list(shown_posts())
        for post in InstagramPost.objects.filter(source=SYNCED).exclude(
            pk__in=[p.pk for p in shown]
        ):
            if post.video:
                post.video.delete(save=True)
            post.album_images.all().delete()
        for post in shown:
            remote = self.remote.get(post.instagram_id)
            if post.source != SYNCED or remote is None:
                continue
            try:
                self._fetch_media(post, remote)
            except instagram.InstagramError as error:
                self.stderr.write(f"{post}: {error}")

    def _fetch_media(self, post, remote):
        if post.media_type == VIDEO and not post.video and remote.video_url:
            with instagram.download_video(remote.video_url) as video:
                post.video.save(f"{post.instagram_id}.mp4", File(video), save=True)
        if post.media_type == ALBUM and not post.album_images.all():
            added = []
            try:
                # The cover (the album's 1st picture) is post.image already.
                for order, url in enumerate(remote.album_urls[1:], start=1):
                    extra = InstagramPostImage(post=post, sort_order=order)
                    picture = _jpeg(instagram.download(url), POST_IMAGE_SIZE)
                    extra.image.save(f"{post.instagram_id}-{order}.jpg", picture)
                    added.append(extra)
            except instagram.InstagramError:
                for extra in added:
                    extra.delete()
                raise
