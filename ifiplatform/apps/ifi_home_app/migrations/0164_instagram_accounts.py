"""Adds the first curated Instagram accounts for the homepage feed (the
accounts Ifi Creators' Guild follows, Nov 2026). After this, admins manage
the list in the "Instagram accounts" snippet."""

from django.db import migrations

# (username, display name, kind)
ACCOUNTS = [
    ("ificreatorsguild", "IFI Creators' Guild", "official"),
    ("mapsuio", "MAPS", "official"),
    ("sp_uio", "Studentparlamentet ved UiO", "official"),
    ("unioslo_ifi", "UiO - Institutt for Informatikk", "official"),
    ("outputifi", ">OUTPUT IFI Avis", "official"),
    ("quizifi", "QUIZIFI", "official"),
    ("_realitifi", "RealitIFI", "official"),
    ("ifimikro", "MIKRO", "official"),
    ("cybernetisk", "Cybernetisk Selskab", "official"),
    ("ifidefi", "Defi", "official"),
    ("fifivedifi", "FIFI", "official"),
    ("ukas_pils", "UkasPils", "official"),
    ("ifisonen", "Sonen for Eksperimentell Informatikk", "official"),
    ("ifipitbulls", "ifi Pitbulls", "official"),
    ("digitus_uio", "Digitus UiO", "official"),
    ("unioslo", "Universitetet i Oslo", "official"),
    ("gangen_i_tredje", "Gangen i tredje", "meme"),
    ("unioslo_mn", "UiO – Realfag og teknologi", "official"),
    ("ifinavet", "Navet", "official"),
    ("pitch_ifi", "PiTCH", "official"),
    ("sikkerhetifi", "SIFI: Sikkerhet på IFI", "official"),
    ("ifi_ordenen", "IFI-ordenen", "official"),
    ("foreninger", "SiO Foreninger", "official"),
    ("makigramifi", "MA:KI", "official"),
    ("fui_ifi", "Fagutvalget ved IFI", "official"),
    ("toastjaern", "Toastens Organisasjon", "official"),
    ("ifi_readline", "The real readLine", "official"),
    ("pgaifi", "Programmers Golf Association", "official"),
    ("ifirastlos", "IFI RASTLØS", "official"),
    ("ifiprogsys", "ProgSys", "official"),
    ("runtimeifi", "Runtime IFI", "official"),
    ("digok.memes", "Eulers president", "meme"),
]


def add_accounts(apps, schema_editor):
    account_model = apps.get_model("ifi_home_app", "InstagramAccount")
    for order, (username, name, kind) in enumerate(ACCOUNTS):
        account_model.objects.get_or_create(
            username=username,
            defaults={"display_name": name, "kind": kind, "sort_order": order},
        )


def remove_accounts(apps, schema_editor):
    account_model = apps.get_model("ifi_home_app", "InstagramAccount")
    account_model.objects.filter(
        username__in=[username for username, _name, _kind in ACCOUNTS],
        posts__isnull=True,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("ifi_home_app", "0163_instagram")]

    operations = [migrations.RunPython(add_accounts, remove_accounts)]
