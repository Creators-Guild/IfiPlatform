"""Pushes ifi_home_app/deepl_glossary_terms.py's nb -> en term list to DeepL
as a glossary, so DeepL honours those exact translations (or "don't
translate this") on every machine-translation call this project makes --
the single-page "Machine Translate" button, the API, and the
"Machine-translate subtree" bulk action (translation_views.py) all go
through the same wagtail-localize DeepLTranslator, so one glossary covers
all three.

DeepL's v2 glossaries are immutable once created (no "update entries"
endpoint) -- this command deletes any existing glossary with the same name
before creating a fresh one from the current term list, so it's safe to
re-run whenever deepl_glossary_terms.py changes.

One-time manual step after running this: copy the printed glossary_id into
DEEPL_GLOSSARY_ID in .env (same copy-paste flow as DJANGO_SECRET_KEY in
README.md's setup steps) -- settings.py reads it from there into
WAGTAILLOCALIZE_MACHINE_TRANSLATOR's GLOSSARY_IDS option.

Also records the sync time via GlossarySyncState, so translation_views.py
knows which existing machine translations predate this glossary version and
should be redone the next time someone runs a machine translation."""

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ifi_home_app.deepl_glossary_terms import GLOSSARY_TERMS
from ifi_home_app.models import GlossarySyncState

GLOSSARY_NAME = "ifiplatform-nb-en"
SOURCE_LANG = "NB"
TARGET_LANG = "EN"


class Command(BaseCommand):
    help = (
        "Pushes deepl_glossary_terms.py's nb -> en term list to DeepL as a "
        "glossary (deleting and recreating any existing one with the same "
        "name, since DeepL glossaries can't be edited in place). Prints the "
        "resulting glossary_id -- copy it into DEEPL_GLOSSARY_ID in .env."
    )

    def handle(self, *args, **options):
        auth_key = settings.WAGTAILLOCALIZE_MACHINE_TRANSLATOR["OPTIONS"].get(
            "AUTH_KEY"
        )
        if not auth_key:
            raise CommandError("DEEPL_API_KEY is not set in .env.")

        api_base = (
            "https://api-free.deepl.com" if auth_key.endswith(":fx")
            else "https://api.deepl.com"
        )
        headers = {"Authorization": f"DeepL-Auth-Key {auth_key}"}

        existing = requests.get(f"{api_base}/v2/glossaries", headers=headers)
        existing.raise_for_status()
        for glossary in existing.json()["glossaries"]:
            if glossary["name"] == GLOSSARY_NAME:
                requests.delete(
                    f"{api_base}/v2/glossaries/{glossary['glossary_id']}",
                    headers=headers,
                ).raise_for_status()
                self.stdout.write(f"Deleted old glossary {glossary['glossary_id']}")

        entries = "\n".join(f"{nb}\t{en}" for nb, en in GLOSSARY_TERMS.items())
        response = requests.post(
            f"{api_base}/v2/glossaries",
            headers=headers,
            json={
                "name": GLOSSARY_NAME,
                "source_lang": SOURCE_LANG,
                "target_lang": TARGET_LANG,
                "entries": entries,
                "entries_format": "tsv",
            },
        )
        response.raise_for_status()
        glossary_id = response.json()["glossary_id"]
        GlossarySyncState.touch()

        self.stdout.write(self.style.SUCCESS(
            f"Created glossary {glossary_id} with {len(GLOSSARY_TERMS)} term(s)."
        ))
        self.stdout.write(
            f"Now set DEEPL_GLOSSARY_ID={glossary_id} in .env and restart the server."
        )
