# Custom manage.py commands

This project's own `manage.py` commands, beyond Django's built-in ones
(`migrate`, `createsuperuser`, `test`, `makemessages`/`compilemessages`,
etc. — see the main [README.md](../README.md) for those), live next to
their code rather than in one combined doc:

- [ifi_home_app/management/commands/commands.md](../ifiplatform/apps/ifi_home_app/management/commands/commands.md) — `seed_dev_data`, `sync_deepl_glossary`, `sync_translated_page_fields`, `sync_peoply_events`
- [account_app/management/commands/commands.md](../ifiplatform/apps/account_app/management/commands/commands.md) — `cleanup_unverified_accounts`
- [core_app/management/commands/commands.md](../ifiplatform/core_app/management/commands/commands.md) — `compile_translations`, `announce_deploy`, `clear_cache`
