# account_app management commands

## cleanup_unverified_accounts

```bash
py manage.py cleanup_unverified_accounts [--dry-run]
```

Deletes signups that never confirmed their email address
(`is_active=False` until `verify_email_view` flips it — see
`account_app.views.login_views`) once they're older than
`settings.UNVERIFIED_ACCOUNT_RETENTION_DAYS` (7 days by default). Exists
for GDPR storage-limitation (Art. 5(1)(e)) — no reason to keep a
name/email on file for an account nobody ever actually claimed. A plain
delete is safe here (unlike `account_app.views.account_views.
delete_account_view`) since an unverified account can never have authored
content or hold permissions.

No task scheduler exists in this project (no Celery/django-crontab) — this
is meant to be invoked periodically from *outside* Django entirely (host
cron, or your platform's own scheduled-job feature). Nothing runs it for
you automatically. Safe to re-run. `--dry-run` lists matching accounts
without deleting them.
