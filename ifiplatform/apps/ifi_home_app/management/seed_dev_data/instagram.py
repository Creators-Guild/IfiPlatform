"""InstagramPost seeding: a few example posts, added "by hand" with
generated images, so the homepage's Instagram feed shows locally without a
Meta token. The accounts themselves come from migration 0164."""

import io
from datetime import timedelta

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageDraw

from ifi_home_app.models import InstagramAccount, InstagramPost

# (username, hours ago, caption, colour, picture text)
EXAMPLE_POSTS = [
    (
        "unioslo_ifi",
        2,
        "Ett enkelt Google-søk så har du svaret 😅",
        "#a3b0fa",
        "1",
    ),
    ("digok.memes", 5, "når obligen er innlevert 23:59:58", "#ffe27a", "2"),
    (
        "ifinavet",
        26,
        "Bedriftspresentasjon med pizza på onsdag. Påmelding i bio!",
        "#8de9a8",
        "3",
    ),
    (
        "cybernetisk",
        50,
        "Fredagsbar i Escape fra 18:00. Ta med venner!",
        "#ffb15c",
        "4",
    ),
    ("gangen_i_tredje", 60, "mandag morgen i tredje etasje", "#cbaaff", "5"),
    (
        "outputifi",
        72,
        "Ny utgave av >OUTPUT er ute! Hent ditt eksemplar i Escape.",
        "#ffb15c",
        "6",
    ),
    ("quizifi", 80, "Quiz på tirsdag kl. 19. Lag på maks fire.", "#ff9fd0", "7"),
    (
        "fui_ifi",
        100,
        "Husk å svare på emneevalueringen! Det tar fem minutter.",
        "#C8FEFF",
        "8",
    ),
    ("digok.memes", 120, "git push --force på fredag kl. 16", "#ff9fd0", "9"),
    (
        "ifirastlos",
        150,
        "Fotballtrening torsdag. Alle nivåer er velkomne.",
        "#8de9a8",
        "10",
    ),
    (
        "pitch_ifi",
        170,
        "Pitch-kveld: tre minutter, én idé. Søk innen fredag.",
        "#a3b0fa",
        "11",
    ),
    (
        "ifimikro",
        200,
        "Lodding for nybegynnere i Mikro-rommet på lørdag.",
        "#ffe27a",
        "12",
    ),
]


def _example_image(colour, text):
    image = Image.new("RGB", (1080, 1080), colour)
    draw = ImageDraw.Draw(image)
    draw.ellipse((-200, -200, 600, 600), fill="#ffffff")
    # Pillow's built-in font has no æøå, so the picture text stays ASCII.
    draw.text((80, 900), f"Example post {text}", fill="#120e0e", font_size=72)
    out = io.BytesIO()
    image.save(out, "JPEG", quality=80)
    return ContentFile(out.getvalue())


class InstagramSeedMixin:  # pylint: disable=too-few-public-methods
    """Adds EXAMPLE_POSTS. Mixed into seed_dev_data's Command, which sets
    created_count/skipped_count."""

    created_count = 0
    skipped_count = 0

    def _seed_instagram_posts(self):
        now = timezone.now()
        for username, hours, caption, colour, text in EXAMPLE_POSTS:
            account = InstagramAccount.objects.filter(username=username).first()
            permalink = f"https://www.instagram.com/{username}/"
            if account is None or account.posts.filter(caption=caption).exists():
                self.skipped_count += 1
                continue
            post = InstagramPost(
                account=account,
                permalink=permalink,
                caption=caption,
                posted_at=now - timedelta(hours=hours),
            )
            post.image.save(
                f"example-{username}.jpg", _example_image(colour, text), save=False
            )
            post.save()
            self.created_count += 1
            self.stdout.write(f"  created InstagramPost: @{username}")
