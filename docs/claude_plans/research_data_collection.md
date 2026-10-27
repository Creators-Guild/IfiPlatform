# Plan: research data collection for the master's thesis

Last updated: 2026-10-27

Hanna's thesis asks how a student-run open-source platform turns passive
users into contributors. The data collection is approved by Sikt. This plan
covers the code only (no interviews). Delete this plan when the build is
done.

## Approach

A rough, exploratory first round: build a small proof of concept in layers,
look at the data after each layer, and open more research later. With about
10–15 participants, their data is read as individual paths (an exploratory
case study), not statistics. The whole-site totals give the big picture.

Real qualitative data (people's own words) is not in the current design:
no interviews, no stored text. Adding two or three open questions (for
example after a first contribution: "What made you try?") needs a change
notice to Sikt first. Otherwise, keep it for a later study.

## Focus

Onboarding and organisation: how people go from having an account, to a
first contribution, to contributing regularly or taking a bigger role, and
which ways in work best.

Collected:

- **The way in:** when someone joined, when they first contributed, and the
  path: site editor, GitHub website, `ifi`, a good-first-issue, an issue
  form, a footer link.
- **What came after:** how often and how much they contributed.
- **Role steps:** for example reader → content contributor → developer →
  maintainer.
- **Who helps whom:** who reviewed a newcomer's work. Experience is worked
  out later from earlier events.
- **Totals for the whole site,** with no names.
- **A feature timeline** from git history, for before/after comparisons.

Dropped (quality control): CI results, review rounds, reverts and follow-up
bug fixes, AI help, the list of QA structures. Collecting less than Sikt
approved is fine. Because of this, a contribution is recorded once, when it
is finished, and never looked up again later.

Example of one stored row:

```
participant 7f3a…   type: article   way in: site editor   day 12 after signup   640 words
```

## Decided

- Contributing and taking part in the research are separate. Consent is
  opt-in in account settings and never affects roles or access.
- Withdrawing consent **deletes** the participant's research data. The
  consent text says withdrawal is only possible until the link database is
  deleted in June 2027.
- Deleting the account does **not** withdraw consent automatically. The
  delete form (`AccountDeleteForm`, next to its study-tools and articles
  choices) asks: delete my research data too, or keep it. Nothing is
  ticked in advance.
  - **Delete:** the same as withdrawing.
  - **Keep:** the research rows stay. The link row is deleted, so
    collection stops and nothing points back to the person any more. The
    form says that this also means they can't withdraw later, because
    nobody can find their data again.
  - The consent text mentions this choice too.
- **Connect GitHub is for everyone**, not just participants. It feeds a
  later gamification/leaderboard feature (idea from the Halloween mock
  site). The numeric GitHub ID is stored with the account. For participants,
  the link database keeps its own copy, so research lookups never go
  through the main database's `Profile`/`User`.
- **`ifi` use** is measured by a `Made-with: ifi` line in commit messages
  (see below).
- Data can only be used for what the consent text says. If follow-up
  research is likely, say so in the consent text now (as far as Sikt
  allows).
- Moderation: check on prod whether pages go through Wagtail's default
  "Moderators approval" workflow:
  `python manage.py shell -c "from wagtail.models import WorkflowPage; print(list(WorkflowPage.objects.values_list('page__title','workflow__name','workflow__active')))"`

## Numbers about everyone (not personal data)

Three rules: only totals (nothing per person), per month or term (not per
day), and numbers 1–4 are reported as "fewer than 5". Only the totals are
saved. The privacy policy says the site counts usage in totals.

| Source | Examples |
| --- | --- |
| Site database | new accounts, first contributions, published articles, drafts never published |
| GitHub (public repo, full history) | issues opened by template, PRs opened/merged, good-first-issues picked up |
| Git history | commits made with `ifi` (`Made-with: ifi`) |
| Umami (already on the site) | footer link clicks (`data-umami-event="footer-…"`), visits to the contribution guide |

The most useful number is probably how far people get, for example
"opened the editor 20 → saved a draft 8 → published 3".

## Knowing when `ifi` is used

- **Done (2026-10-27, not yet merged):** `ifi save` and `ifi undo-file` end
  the commit message with a `Made-with: ifi` line (`commit_marked` in
  `tools/ifi/common.sh`, a second `-m` so it works on any Git version). The
  recap shows the plain `git commit -m` and says ifi added the line.
  `CONTRIBUTING.md` mentions it. It counts commits, not `ifi check`/`ifi test`.
- Getting the data, from any clone after `git fetch upstream`:
  - commits per month:
    `git log upstream/main --grep="Made-with: ifi" --date=format:%Y-%m --format=%ad | sort | uniq -c`
  - people per month, no names printed:
    `git log upstream/main --grep="Made-with: ifi" --date=format:%Y-%m --format='%ad|%ae' | sort -u | cut -d'|' -f1 | uniq -c`
  - for participants, the daily job saves "way in: ifi" when a finished PR
    has a commit with the line.
- Rejected for now: a hidden mark in the PR text (`ifi pull-request` only
  prints a link, so it would need a second PR template), and a usage
  counter that sends each command to the site (most friction: network,
  IP addresses in logs, a note to Sikt).

## Limits

- GitHub Desktop and the command line look the same in GitHub's data.
- Django keeps no history of group changes. For earlier roles, only what a
  person has at consent time can be recorded.
- GitHub activity from before someone made a site account gets a negative
  day number.
- Encrypted fields can't be searched. Store a keyed HMAC of the GitHub ID
  and user_id for lookups, and delete that key in June 2027 too.

## Repo facts this builds on

- `account_app` has `Profile`, and the export (`export_data_view`) and
  delete (`delete_account_view`) views in `views/account_views.py`.
- Nothing in the Django code talks to GitHub yet.
- There is one database. Prod runs Ubuntu's PostgreSQL 16 on the NREC VM,
  so a second database and role is `createuser` + `createdb`.
  `compose.prod.yml` will need an init script for the extra databases.
- Scheduled jobs are systemd timers in `deploy/systemd/` (deploy 01:00,
  translation catch-up 03:30, backup 05:00). `backup_db.sh` dumps only the
  default database.
- `page_published` is already used in
  `ifi_home_app/translation/auto_translate.py`.
- New packages needed: `cryptography` (field encryption), `PyJWT` (GitHub
  App login).

## Done so far (2026-10-27, not yet merged)

- **Footer links** in `templates/partials/footer.html`: Contribution Guide,
  GitHub, Report a bug, Request a feature, with Umami click events. The bug
  link prefills the form's "Related" field with the page path (skipped on
  `/account/` pages, whose paths can hold one-time codes). An issue whose
  text contains that line came from the site. The four link texts still
  need Norwegian translations (`makemessages`).
- **`CONTRIBUTING.md`** links to the README near the top, since the footer
  sends people there first.
- **`Made-with: ifi`** commit line (above).
- The deploy date of each of these goes in the feature timeline.

## Layers

### Layer 1: totals (no consent, no new database)

A `manage.py` command that prints monthly totals as CSV from the site
database, the GitHub API (public repo, so the "before" months come for
free) and git history. Umami clicks are read in Umami itself. Start
exploring as soon as this works.

### Layer 2: a few participants' paths

Needed before the first participant (Sikt approved these):

1. **Databases.** A link database (pseudonym ↔ user ↔ GitHub ID, encrypted
   fields, deleted June 2027) and a research database (pseudonyms and
   numbers only), with a database router. All "who is this?" lookups go
   through one file: no consent means "nobody", and the event is dropped.
2. **GitHub App.** One read-only App owned by Creators-Guild. Connect GitHub
   in account settings for everyone (keep the numeric ID, throw away the
   token). Add the App to `docs/operations/access_and_handover.md`.
3. **Consent.** A research section in account settings: consent text
   (versioned template), study year, earlier project experience. When
   someone consents, copy their GitHub ID into the link database and fetch
   what they did before. Withdraw, the export addition, the research choice
   in the delete form, and the privacy policy update ship together with it.
4. **Recording.** Published pages (type, day, word count) and drafts never
   published, via `page_published` and the page history. Group changes via
   `m2m_changed` on `User.groups.through` (both directions, plus
   `pre_clear`). One daily job (a systemd timer) for GitHub: finished PRs
   and issues (type, way in, day, size) and reviews (who helped whom).
5. **Export.** A command that writes CSV from the research database only.
   Write down what each column means.

### Layer 3: explore

A timeline per person, and the "how far did people get" chains. That's
where the questions for later research come from.

### June 2027

Make the data coarser: study year in two groups (years 1–2, year 3+),
experience yes/no, months instead of days. Then delete the link database and
both keys, and delete the GitHub App. Backups roll off after 14 days.
Copies made by hand outside NREC need handling too.

## Later (not in the first round)

- Webhooks instead of only the daily job (signature checked, payload never
  logged or stored).
- A daily check of GitHub repo roles (save a row only on change).
- The feature-timeline script from git history.
- A report form on the site itself, so no GitHub account is needed. The
  GitHub App files the issue, the site knows who reported it, and the form
  says the text becomes public.
- A "How to contribute" page on the site with both paths (writing on the
  site, code on GitHub). `CONTRIBUTING.md` is written for coders.
- The leaderboard (its own plan: nicknames, opt-in to be shown).
- A usage counter for all `ifi` commands, if commit counts aren't enough.
