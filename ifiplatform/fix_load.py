from django.db.models.signals import post_save
from wagtail_localize.models import LocaleSynchronization, sync_trees_on_locale_sync_save
post_save.disconnect(sync_trees_on_locale_sync_save, sender=LocaleSynchronization)

from django.core.management import call_command
call_command('loaddata', 'sqlite_export.json')
