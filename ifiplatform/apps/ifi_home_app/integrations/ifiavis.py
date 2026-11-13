"""Reads the >OUTPUT magazine's issue list from ifiavis.no/utgaver. The site
has no API or feed we can use (see docs/to_fix.md), so this parses the data
Next.js embeds in the page. Consumed by sync_output_magazine.

Design rationale: docs/claude_context/home_magazinebox.md"""

import json
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests

BASE_URL = "https://www.ifiavis.no"
LISTING_URL = BASE_URL + "/utgaver"

NORWEGIAN_MONTHS = {
    "januar": 1,
    "februar": 2,
    "mars": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}

_CHUNK_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', re.S)
_DATE_RE = re.compile(r"^\s*([a-zæøå]+)\s+(\d{4})\s*$", re.I)
_REF_RE = re.compile(r"^\$L?([0-9a-f]+)$")


class IfiavisParseError(Exception):
    """The page didn't look the way we expect -- most likely a redesign."""


@dataclass(frozen=True)
class Issue:
    sanity_id: str
    title: str
    url: str
    cover_url: str
    issue_date: date


def parse_issue_date(text):
    """'november 2025' -> date(2025, 11, 1)."""
    match = _DATE_RE.match(text)
    month = NORWEGIAN_MONTHS.get(match.group(1).lower()) if match else None
    if not month:
        raise IfiavisParseError(f"Unknown issue date: {text!r}")
    return date(int(match.group(2)), month, 1)


def _cover_base(src):
    """Sanity image URL without ifiavis's own size settings, keeping their
    crop (rect=), so we can ask for our own size."""
    parts = urlsplit(src)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k == "rect"]
    return urlunsplit(parts._replace(query=urlencode(query, safe=",")))


def _payload_rows(html):
    """The page's React data as {row id: decoded JSON}. Rows that aren't
    JSON (text and module rows) are skipped."""
    payload = "".join(json.loads(chunk) for chunk in _CHUNK_RE.findall(html))
    rows = {}
    for line in payload.split("\n"):
        row_id, sep, body = line.partition(":")
        if not sep:
            continue
        try:
            rows[row_id] = json.loads(body)
        except ValueError:
            continue
    return rows


class _Tree:
    """Walks the React tree, following "$L<row id>" references: Next.js
    moves parts of the tree (such as some issue dates) into later rows."""

    def __init__(self, rows):
        self.rows = rows

    def _resolve(self, node, seen):
        if isinstance(node, str):
            match = _REF_RE.match(node)
            if match and match.group(1) in self.rows and match.group(1) not in seen:
                return self.rows[match.group(1)], seen | {match.group(1)}
        return node, seen

    def elements(self, node, seen=frozenset()):
        """Every React element (["$", type, key, props]) inside node."""
        node, seen = self._resolve(node, seen)
        if isinstance(node, list):
            if _is_element(node):
                yield node
                yield from self.elements(node[3].get("children"), seen)
            else:
                for child in node:
                    yield from self.elements(child, seen)

    def texts(self, node, seen=frozenset()):
        """Every plain string child inside node, in order."""
        node, seen = self._resolve(node, seen)
        if isinstance(node, str):
            if not node.startswith("$"):
                yield node
        elif isinstance(node, list):
            if _is_element(node):
                yield from self.texts(node[3].get("children"), seen)
            else:
                for child in node:
                    yield from self.texts(child, seen)


def _is_element(node):
    return len(node) == 4 and node[0] == "$" and isinstance(node[3], dict)


def _issue_from_card(tree, key, props):
    children = props.get("children")
    image = next(
        (el[3] for el in tree.elements(children) if "cdn.sanity.io" in str(el[3].get("src", ""))),
        None,
    )
    texts = [t.strip() for t in tree.texts(children) if t.strip()]
    date_text = next((t for t in texts if _DATE_RE.match(t)), None)
    if image is None or date_text is None:
        raise IfiavisParseError(f"Issue card {props['href']!r} has no cover or no date")
    title = next((t for t in texts if t != date_text), None) or image.get("alt", "")
    return Issue(
        sanity_id=key,
        title=title,
        url=urljoin(BASE_URL, props["href"]),
        cover_url=_cover_base(image["src"]),
        issue_date=parse_issue_date(date_text),
    )


def parse_issues(html):
    """All issues on the /utgaver page, newest first. Raises
    IfiavisParseError if none are found, so a redesign fails loudly instead
    of looking like an empty archive."""
    rows = _payload_rows(html)
    tree = _Tree(rows)
    issues = {}
    for row in rows.values():
        for _dollar, _type, key, props in tree.elements(row):
            href = props.get("href")
            if (
                isinstance(href, str)
                and href.startswith("/utgaver/")
                and isinstance(key, str)
                and key not in issues
            ):
                issues[key] = _issue_from_card(tree, key, props)
    if not issues:
        raise IfiavisParseError("No issues found on the /utgaver page")
    return sorted(issues.values(), key=lambda issue: issue.issue_date, reverse=True)


def get_issues():
    response = requests.get(LISTING_URL, timeout=10)
    response.raise_for_status()
    return parse_issues(response.text)
