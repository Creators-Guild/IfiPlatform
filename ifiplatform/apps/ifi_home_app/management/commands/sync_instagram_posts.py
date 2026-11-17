"""Copies the newest posts of every active InstagramAccount from Meta's
Graph API (Business Discovery) into InstagramPost rows, downloading each
image once (Meta's image links expire). Synced posts get their caption and
link updated; `hidden` is never touched; only the newest 12 synced posts per
account, and only from the last year (POST_MAX_AGE), are kept; older ones
and their images are deleted. Posts added by hand are never changed.
Every stored synced post also gets its video file and every album picture;
they go when the post is deleted. One account failing (e.g. a personal
account) is recorded on the account and doesn't stop the others. Accounts
without a union page are linked to the union page that lists them, and
account requests decided over six months ago are deleted.
Without a token in .env it does nothing more. Runs hourly 07-23 from the sync-instagram-posts
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
    POST_MAX_AGE,
    POSTS_KEPT_PER_ACCOUNT,
    FAILED_RUNS_BEFORE_PAUSE,
    SYNCED,
    VIDEO,
    InstagramAccount,
    InstagramPost,
    InstagramPostImage,
    InstagramSyncState,
    match_union_pages,
)
from ifi_home_app.models.instagram_request import delete_old_requests

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
        linked = match_union_pages()
        if linked:
            self.stdout.write(f"Linked {linked} account(s) to their union page.")
        deleted = delete_old_requests()
        if deleted:
            self.stdout.write(f"Deleted {deleted} old account request(s).")
        if not instagram.is_configured():
            self.stdout.write("No INSTAGRAM_ACCESS_TOKEN in .env: nothing to sync.")
            return
        self._check_token()
        self.remote = {}
        failed = []
        for account in InstagramAccount.objects.filter(
            is_active=True, sync_paused=False
        ):
            try:
                created = self._sync_account(account)
            except instagram.AccountNotReadable as error:
                if self._count_unreadable(account, error):
                    self.stdout.write(
                        f"@{account.username}: paused, Meta can't read it "
                        f"({FAILED_RUNS_BEFORE_PAUSE} runs in a row)"
                    )
                else:
                    failed.append(f"@{account.username}: {error}")
                continue
            except instagram.InstagramError as error:
                account.last_error = str(error)[:300]
                account.save(update_fields=["last_error"])
                failed.append(f"@{account.username}: {error}")
                continue
            self.stdout.write(f"@{account.username}: {created} new")
        self._sync_media()
        if failed:
            raise CommandError(
                f"{len(failed)} account(s) failed:\n" + "\n".join(failed)
            )
        self.stdout.write(self.style.SUCCESS("Instagram sync done."))

    def _count_unreadable(self, account, error):
        """Counts a run where Meta can't read the account; pauses it after
        FAILED_RUNS_BEFORE_PAUSE in a row. Returns True when it paused."""
        account.last_error = str(error)[:300]
        account.failed_runs += 1
        account.sync_paused = account.failed_runs >= FAILED_RUNS_BEFORE_PAUSE
        account.save(update_fields=["last_error", "failed_runs", "sync_paused"])
        return account.sync_paused

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
        account.failed_runs = 0
        account.save()

        existing = {
            post.instagram_id: post for post in account.posts.filter(source=SYNCED)
        }
        created = 0
        cutoff = timezone.now() - POST_MAX_AGE
        for post in found.posts:
            if post.posted_at < cutoff:
                continue
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

        synced = account.posts.filter(source=SYNCED)
        keep = synced.filter(posted_at__gte=cutoff).values_list("pk", flat=True)[
            :POSTS_KEPT_PER_ACCOUNT
        ]
        for old in synced.exclude(pk__in=list(keep)):
            old.delete()
        return created

    def _sync_media(self):
        """Videos and album pictures for every stored synced post that's
        missing them, using the links Meta gave this run (a post whose
        account failed waits for the next run)."""
        posts = InstagramPost.objects.filter(
            source=SYNCED, instagram_id__in=list(self.remote)
        ).prefetch_related("album_images")
        for post in posts:
            remote = self.remote[post.instagram_id]
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
