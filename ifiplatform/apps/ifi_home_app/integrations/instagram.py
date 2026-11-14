"""Thin client for Meta's Graph API, used to read the newest public posts of
other Instagram accounts through Business Discovery, as the Ifi Creators'
Guild business account (settings.INSTAGRAM_*). Consumed by
sync_instagram_posts.

Design rationale: docs/claude_context/home_instagram.md"""

from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from django.conf import settings

GRAPH_URL = "https://graph.facebook.com"
MAX_IMAGE_BYTES = 15 * 1024 * 1024

IMAGE, VIDEO, ALBUM = "image", "video", "album"
_MEDIA_TYPES = {"IMAGE": IMAGE, "VIDEO": VIDEO, "CAROUSEL_ALBUM": ALBUM}


class InstagramError(Exception):
    """Meta refused the request or answered with something we can't use."""


@dataclass(frozen=True)
class Post:
    """One post as Business Discovery returns it."""

    instagram_id: str
    permalink: str
    caption: str
    posted_at: datetime
    media_type: str
    image_url: str


@dataclass(frozen=True)
class Account:
    """An account's profile and newest posts."""

    username: str
    name: str
    profile_picture_url: str
    posts: list


def is_configured():
    """Whether .env has what the sync needs to call Meta."""
    return bool(
        settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_BUSINESS_ACCOUNT_ID
    )


def _get(path, params):
    url = f"{GRAPH_URL}/{settings.INSTAGRAM_GRAPH_VERSION}/{path}"
    params = {**params, "access_token": settings.INSTAGRAM_ACCESS_TOKEN}
    try:
        response = requests.get(url, params=params, timeout=15)
    except requests.RequestException as error:
        raise InstagramError(f"Could not reach Meta: {error}") from error
    try:
        data = response.json()
    except ValueError as error:
        raise InstagramError(
            f"Meta answered {response.status_code} without JSON"
        ) from error
    if "error" in data:
        message = data["error"].get("message", "unknown error")
        raise InstagramError(f"Meta refused: {message}")
    if response.status_code >= 400:
        raise InstagramError(f"Meta answered {response.status_code}")
    return data


def _image_url(media):
    """The picture to show: the image itself, a video's thumbnail, or an
    album's first picture."""
    kind = media.get("media_type")
    if kind == "CAROUSEL_ALBUM":
        children = (media.get("children") or {}).get("data") or []
        first = children[0] if children else {}
        return (
            media.get("media_url")
            or first.get("media_url")
            or first.get("thumbnail_url", "")
        )
    if kind == "VIDEO":
        return media.get("thumbnail_url", "")
    return media.get("media_url", "")


def parse_account(data):
    """An Account from a Business Discovery response. Posts without a
    picture we may download (e.g. a video Meta gives no thumbnail for) are
    left out."""
    found = data.get("business_discovery")
    if not found:
        raise InstagramError("Meta's answer has no business_discovery")
    posts = []
    for media in (found.get("media") or {}).get("data") or []:
        image_url = _image_url(media)
        if not image_url or not media.get("permalink"):
            continue
        posts.append(
            Post(
                instagram_id=media["id"],
                permalink=media["permalink"],
                caption=media.get("caption", ""),
                posted_at=datetime.fromisoformat(
                    media["timestamp"].replace("+0000", "+00:00")
                ),
                media_type=_MEDIA_TYPES.get(media.get("media_type"), IMAGE),
                image_url=image_url,
            )
        )
    return Account(
        username=found.get("username", ""),
        name=found.get("name", ""),
        profile_picture_url=found.get("profile_picture_url", ""),
        posts=posts,
    )


def get_account(username, limit=12):
    """The newest `limit` posts of a public business/creator account.
    Raises InstagramError for personal or missing accounts too."""
    fields = (
        f"business_discovery.username({username}){{username,name,profile_picture_url,"
        f"media.limit({limit}){{id,caption,media_type,media_url,thumbnail_url,"
        "permalink,timestamp,children{media_type,media_url,thumbnail_url}}}"
    )
    return parse_account(
        _get(settings.INSTAGRAM_BUSINESS_ACCOUNT_ID, {"fields": fields})
    )


def token_expires_at():
    """When the access token stops working, or None if it never expires."""
    data = _get("debug_token", {"input_token": settings.INSTAGRAM_ACCESS_TOKEN})
    expires = (data.get("data") or {}).get("expires_at") or 0
    return datetime.fromtimestamp(expires, tz=timezone.utc) if expires else None


def download(url):
    """The bytes behind an image URL Meta gave us (they expire after a while,
    so we keep our own copy)."""
    try:
        response = requests.get(url, timeout=20, stream=True)
        response.raise_for_status()
        chunks, size = [], 0
        for chunk in response.iter_content(64 * 1024):
            size += len(chunk)
            if size > MAX_IMAGE_BYTES:
                raise InstagramError("Image is larger than 15 MB")
            chunks.append(chunk)
    except requests.RequestException as error:
        raise InstagramError(f"Could not download image: {error}") from error
    return b"".join(chunks)
