# research_app totals — design notes

Last updated: 2026-10-28
Covers: ifiplatform/apps/research_app/totals.py, ifiplatform/apps/research_app/github_api.py, ifiplatform/apps/research_app/management/commands/research_totals.py

Phase 1 of `docs/claude_plans/research_data_collection.md`: whole-site
monthly totals, no consent, no new database. Data handling rules for the
research are in `docs/research/data_handling.md`.

## Rules the code keeps

- **Counts only.** People are told apart by user ID, GitHub user ID or
  commit email inside `Tally.add_person`, and `Tally.result()` keeps only
  `len()` of each set. Nothing returned or printed names anyone. Don't add
  a column, debug print or log line that does.
- **1–4 are printed as `<5`** (`show()`), from the plan's totals rules.
  0 stays 0. Applied when printing, so the counting functions return real
  numbers (the tests rely on that).
- **Months are in Oslo time** (`SITE_TIMEZONE` from
  `ifi_home_app.models.event.constants`), since `settings.TIME_ZONE` is
  UTC.
- **The default range ends at the last complete month**, so a printed
  month never changes later. `drafts_never_published` is still too low for
  the most recent month: a draft only counts once it's 30 days old
  (`DRAFT_ABANDONED_DAYS`, the plan's "abandoned draft" rule).

## Choices that look odd

- **No user = not a person.** `PageLogEntry` publish rows with
  `user=None` are the Peoply sync (and anything else run from code), so
  they don't count. `pages_first_published` uses each page's very first
  publish row: a synced event that an editor later republishes is still
  not counted.
- **Bots on GitHub:** `type == "Bot"` or a login ending in `[bot]`
  (`github-actions[bot]` has type "Bot", but not every app account does).
- **Commits come from the GitHub API, not `git log`**, so the command
  works where `git` isn't installed (the future Docker image) and always
  reads the default branch on GitHub. A commit whose email GitHub doesn't
  know has `author: null`; `people_using_ifi` then falls back to the
  commit email.
- **Issue kinds come from the labels the issue templates set**
  (`.github/ISSUE_TEMPLATE/*.yml`), checked in order bug, feature, docs,
  task, since a docs issue has both `docs` and `task`. Issues made before
  the templates have none and only count in `issues_opened`.
- **`issues_from_site`** looks for `Found on page:` in the issue body,
  which the footer's "Report a bug" link prefills
  (`templates/partials/footer.html`). Change both together.
- **`first_time_pr_authors_merged`** sorts pull requests by `merged_at`
  first, so each author's earliest merge wins. Unmerged ones sort last
  (`"~"` sorts after any date string).
