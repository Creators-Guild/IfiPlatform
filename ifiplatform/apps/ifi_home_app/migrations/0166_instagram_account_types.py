"""Instagram account types (user, 2026-11-17): official/meme becomes union,
student democracy, university, media or humour, and accounts can link to
their union page. The data step sorts the accounts from 0164 by username;
any other account becomes a union, and meme becomes humour. Reversing maps
humour back to meme and everything else to official."""

import django.db.models.deletion
from django.db import migrations, models

TYPES = {
    "unioslo": "university",
    "unioslo_ifi": "university",
    "unioslo_mn": "university",
    "foreninger": "university",
    "sp_uio": "democracy",
    "outputifi": "media",
}


def new_type(username, old_kind):
    """The type an existing account gets."""
    if old_kind == "meme":
        return "humour"
    return TYPES.get(username, "union")


def sort_accounts(apps, schema_editor):
    InstagramAccount = apps.get_model("ifi_home_app", "InstagramAccount")
    for account in InstagramAccount.objects.all():
        account.kind = new_type(account.username, account.kind)
        account.save(update_fields=["kind"])


def unsort_accounts(apps, schema_editor):
    InstagramAccount = apps.get_model("ifi_home_app", "InstagramAccount")
    InstagramAccount.objects.filter(kind="humour").update(kind="meme")
    InstagramAccount.objects.exclude(kind="meme").update(kind="official")


class Migration(migrations.Migration):

    dependencies = [
        ("ifi_home_app", "0165_instagram_video_and_albums"),
    ]

    operations = [
        migrations.AddField(
            model_name="instagramaccount",
            name="union_page",
            field=models.ForeignKey(
                blank=True,
                help_text="The union's page on this site. Its tag on the posts links there. The sync fills it in when a union page lists this account.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="ifi_home_app.unionpage",
            ),
        ),
        migrations.AlterField(
            model_name="instagramaccount",
            name="kind",
            field=models.CharField(
                choices=[
                    ("union", "Union or association"),
                    ("democracy", "Student democracy"),
                    ("university", "University or department"),
                    ("media", "Media"),
                    ("humour", "Humour"),
                ],
                default="union",
                help_text="Shown as a tag on the account's posts.",
                max_length=12,
                verbose_name="type",
            ),
        ),
        migrations.RunPython(sort_accounts, unsort_accounts),
        migrations.AlterField(
            model_name="instagrampost",
            name="video",
            field=models.FileField(
                blank=True,
                help_text="Empty when Instagram gives no video file; the cover then links to Instagram.",
                upload_to="instagram/videos/",
            ),
        ),
    ]
