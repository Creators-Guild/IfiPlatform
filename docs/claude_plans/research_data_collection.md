# Plan: research data collection for the master's thesis

Last updated: 2026-10-29

Hanna's thesis asks how a student-run open-source platform turns passive
users into contributors. The data collection is approved by Sikt. A change
notice (2026-10-29: the platform part widened and described in more
detail, plus the Halloween event's participants and helpers) must be
approved before the first participant. This plan covers the platform's
code only (no interviews). Delete this plan when the build is done.

**Status:** Phase 1 is built (not merged yet). Phase 2 has started; the
Sikt check is done. Build each phase only when Hanna says so.

Security and data handling (who can reach what, risks, open questions):
`docs/research/data_handling.md`. Its open questions are Hanna's to decide.

## Approach

A rough, exploratory first round: build a small proof of concept in layers,
look at the data after each layer, and open more research later. With about
10–15 participants, their data is read as individual paths (an exploratory
case study), not statistics. The whole-site totals give the big picture.

Reading paths one by one is for the analysis only. The thesis reports
groups: groups under five are merged, rare roles aren't described one by
one, and no single participant's path is told as a story (promised to
Sikt and in the information letter).

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
  maintainer. These are not a ladder: one person can hold several roles at
  once (for example content contributor and developer), and can gain or
  lose each one on its own.
- **Who helps whom:** who reviewed a newcomer's work. Experience is worked
  out later from earlier events.
- **Totals for the whole site,** with no names.
- **A feature timeline** from git history, for before/after comparisons.

Dropped (quality control): CI results, review rounds, reverts and follow-up
bug fixes, AI help, the list of QA structures. Collecting less than Sikt
approved is fine. Because of this, a contribution is recorded once, when it
is finished, and never looked up again later.

Example of one row in the research database:

```
participant 7f3a…   #3   contribution: article   way in: site editor   2026-11   evening   weekday   640 words
```

**Times are split between the two databases** (decided 2026-10-27):

- The **link database** keeps the exact time of every event (UTC),
  encrypted, and each participant's signup time. Only the research job
  uses it.
- The **research database** gets only year, month and a time-of-day block
  (in Oslo time). Exact times can be matched to GitHub's public
  timestamps, and so to a person; month and time block are much harder
  to match.
- Anything needed later from the exact times (weekday, comparing with
  event dates) is worked out by an automated job that writes a new coarse
  field to the research database. Hanna doesn't read exact times for
  analysis: the application says the link database is opened by hand
  only when needed, such as access or deletion requests.
- The exact times disappear with the link database in June 2027.

Sizes stay exact for now (640 words, 137 lines), and roles aren't merged.
Decided 2026-10-28: words for articles, issues and comments; lines
added + removed for pull requests.
Hanna changes this if needed.

**Paths** (decided 2026-10-28): every row gets month, time block, weekday
or weekend, and an order number per person (1st, 2nd, 3rd event). Time
blocks, in Oslo time: day 08–16, evening 16–24, night 00–08. Exact day
counts are kept only as a few **milestones** per participant: days from
signup to first mini-contribution, to first contribution, and to each
role change. Days after signup on every row was rejected: together with
the month, it gives away each event's exact date.

**Keep only what the analysis needs.** Once the analysis is clear, Hanna
adjusts what is stored and drops the rest. June 2027 deletes only the
link database; the research database stays. When the research data is
deleted later, only the results and the proof of them remain.

Roles are stored as one row per role change, never as a single "role"
column on the participant:

```
participant 7f3a…   role: content contributor   added     2026-11, evening
participant 7f3a…   role: developer             added     2026-12, morning
participant 7f3a…   role: content contributor   removed   2027-05, afternoon
```

A person's roles at a given time are all roles added and not yet removed by
then, so between December and May this person had two roles.

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
  - **Keep:** the research rows stay. Everything about the pseudonym in
    the link database is deleted: the link row, the consent record, the
    GitHub ID copy, the lookup values and all exact times (exact times
    can be matched to public GitHub timestamps). Collection stops and
    nothing points back to the person any more. The form says that this
    also means they can't withdraw later, because nobody can find their
    data again.
  - The consent text mentions this choice too.
  - The "takes part" flag is deleted with the user, so the website first
    writes a queue row ("user 42 deleted the account: keep / delete
    research data"). The job then deletes the link rows (keep) or
    everything (delete).
- **Access requests for research data are handled by hand by Hanna**, not
  by the data export (`export_data_view`), since the website can't open
  the research databases. The application names access requests as a
  reason for manual access. The export page says how to ask. Each request
  goes in the access log.
- **Connect GitHub is for everyone**, not just participants. It feeds a
  later gamification/leaderboard feature (idea from the Halloween mock
  site). The numeric GitHub ID is stored with the account. For participants,
  the link database keeps its own copy, so research lookups never go
  through the main database's `Profile`/`User`.
- **`ifi` use** is measured by a `Made-with: ifi` line in commit messages
  (see below).
- **The website never touches the link or research database** (decided
  2026-10-27). This is the "separate service account" from the
  application:
  - The website writes a row to a small queue table in the main database
    ("user 42 published page X at 14:22"), only for users who consented.
  - A research job (a systemd timer, every few minutes) runs as its own
    Linux user, with its own database user and the encryption key in a
    file only that Linux user can read. It looks up the pseudonym, writes
    the exact time to the link database and the coarse row to the
    research database, and deletes the queue row.
  - Consent and withdrawal: the button in account settings sets a flag,
    and the job creates or deletes the data within minutes.
  - The daily GitHub job runs the same way.
- **Database users:**
  - `ifiplatform_user` (exists): the website, main database only.
  - `research_service`: the jobs, link and research databases. The only
    one that writes to the research database.
  - Hanna's own research user: the link database by hand, only when
    needed; the research database read-only, for analysis.
- Data can only be used for what the consent text says. Decided
  2026-10-29: no follow-up use is named. The anonymous data left after
  June 2027 can be reused anyway; anything else needs a new application.
- **Nobody but Hanna gets root** before June 2027 (decided 2026-10-29).
  The devops person only gets a limited Linux user, and no login until it
  exists (`docs/to_fix.md`, Server).
- **Free text is read in memory only**, to count words and find fixed
  markers (`Made-with: ifi`, the footer's "Related" line). It is never
  stored or logged.
- **Backups** roll off after 14 days, so withdrawn data is gone from them
  within 14 days. Deletions aren't re-applied after a restore (decided
  2026-10-29).

## Questions

Hanna decides these. Don't build the parts that are still open.

**Data and paths**

1. **Paths.** Decided, see above (milestones plus order number).
2. **Time blocks.** Decided, see above.
3. **Contribution and mini-contribution.** Decided:

   | Contribution | Mini-contribution |
   | --- | --- |
   | A published article or page | An issue opened (bug report, feature request) |
   | A merged pull request | A comment on an issue or pull request |
   | An edit to someone else's page above a low threshold | A review (also stored as "who helps whom") |
   | | A pull request closed without merging |
   | | A small edit to someone else's page |
   | | A draft: finished by someone else, or abandoned |

   Decided: each edit to someone else's page stores the number of words
   added or changed. For now, an edit counts as a contribution from 40
   words. The count itself is stored, so the threshold can change later
   without collecting anything new.
4. **Roles.** Decided: two groups, stored as role rows.
   - **Access roles** (what someone may do): on the site, Wagtail's
     "Editors" and "Moderators"; on GitHub, collaborator (write access)
     and committer (can merge).
   - **Contribution roles** (what someone has done): for example content
     contributor (first published page) and developer (first merged pull
     request).
   Site and GitHub give their own role titles. GitHub roles need the
   daily check, which is now part of Phase 5.
5. **History before consent.** Decided 2026-10-29: only from the day
   someone consents, and only this site and this repo, plus the signup
   time and the roles held at consent. No extra tick for older history;
   going back further needs a new consent and a change notice.
6. **Drafts.** Decided: a mini-contribution, in two cases:
   - finished by someone else: recorded when the page is published; the
     publisher gets a contribution
   - abandoned: after 30 days without being published (a late check)
   Drafts rejected by a moderator are left out (decided 2026-10-28), so
   no moderation check is needed.
7. **Reviewers who aren't participants.** Decided: stored as "reviewed by
   a non-participant".
8. **Event dates.** Decided: not now, on the future agenda.

**The study**

9. **Hanna's influence.** Decided:
   - Hanna takes part as a **test participant**, to check that things
     work. Hanna's pseudonym is marked and left out of the analysis.
   - Hanna's reviews get their own label ("reviewed by the
     researcher/maintainer"), so that influence is visible in the data.
   - Hanna will know roughly who takes part, so not knowing is not an
     option.
   - Already in the plan: only the job writes research data (Hanna's user
     is read-only), and the feature timeline dates every onboarding
     change.
   - Decided 2026-10-28: write down the analysis questions (dated)
     before collection starts, and a reflexivity section in the thesis.
10. **Recruitment.** Decided:
    - a one-time question after signup, or at the next login for existing
      accounts: "Take part in a study? Yes / No / Later"
    - the research section in account settings
    - Hanna advertises in channels, and asks individuals personally only
      when recruiting for the Halloween interviews. There are no
      interviews with platform users.
    - the text says clearly that taking part or not never affects roles,
      access or how someone's work is reviewed
11. **Who can take part.** Decided 2026-10-29: students at UiO, mainly
    bachelor and master students at Ifi, but anyone who says they are a
    UiO student may join. No email check: the site's email goes through
    Resend (USA), which the Sikt application would have to name. The
    student status is part of the one consent tick: «Jeg er student ved
    UiO, har lest informasjonen over og samtykker til at min
    bidragsaktivitet brukes i forskningsprosjektet, som beskrevet.»
12. **What the participant is asked.** Decided 2026-10-29, worded exactly
    as in the questionnaire sent to Sikt (Norwegian is the source):
    1. «Har du tidligere bidratt til programmerings- eller åpen
       kildekode-prosjekter (utenfor dette prosjektet)?» Nei, ingen
       tidligere erfaring / Noe erfaring (skole-/kursprosjekter, mindre
       hobbyprosjekter) / Betydelig erfaring (jobb, praksis, omfattende
       hobbyprosjekter, bidrag til andre åpen kildekode-prosjekter).
       Optional.
    2. «Har du tidligere skrevet eller redigert innhold sammen med andre
       (utenfor emner og utenfor dette prosjektet), f.eks. wiki,
       studentavis eller nettside for en forening?» Nei, ingen tidligere
       erfaring / Noe erfaring (enkelte bidrag, mindre prosjekter) /
       Betydelig erfaring (fast skribent eller redaktør, jobb, omfattende
       prosjekter). Optional.
    3. «Hvilket år begynte du på studieprogrammet du går på nå?» A year.
       Required.
    4. «Hvilket nivå studerer du på?» Bachelor / Master / Annet.
       Required.

    Stored on the participant in the research database as ingen/noe/
    betydelig (or blank), year and level.
13. **Consent text language.** Decided: Norwegian and English; Norwegian
    is the source of truth.

**Data handling** (details in `docs/research/data_handling.md`)

14. **Keys and exports.** Decided: the backup keys are kept on Microsoft
    365 for UiO (OneDrive). Pseudonymised exports for analysis go there
    too (as the Sikt application says), never the link.
15. **Consent records after withdrawal.** Decided: not kept.
16. **Halloween data on this server.** The change notice puts the
    Halloween participants' GitHub data and link on NREC. Not decided:
    where, how it's kept apart, and backups
    (`docs/research/data_handling.md`, question 14).

What the Sikt application lists for the platform (Norwegian, summarised,
as in the change notice): number and type of contributions; the way in;
timing (coarse in the analysis data, plus milestones); roles and role
changes, including roles held at consent; cohort and level; the two
experience questions; quality-control activity (dropped, collecting less
is fine); activity in comments, the size of issues and pull requests, and
the size of each contribution (words, or lines changed); and, for
reviews, the reviewer's experience.

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
- History starts at consent, so milestones are unknown for
  anything that happened before it. Someone who contributed before
  consenting has no "days to first contribution".
- Django keeps no history of group changes. For earlier roles, only what a
  person has at consent time can be recorded: one "had at consent" row per
  role they hold then.
- GitHub activity from before someone made a site account comes before
  their signup time (a negative "days after signup").
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
  default database. Every timer runs as `ubuntu` today (`User=ubuntu`), so
  the research job needs a new Linux user.
- `page_published` is already used in
  `ifi_home_app/translation/auto_translate.py`.
- New packages needed: `cryptography` (field encryption), `PyJWT` (GitHub
  App login).

## Done so far (2026-10-27, not yet merged)

- **Footer links** in `templates/partials/footer.html`: Contribution Guide,
  GitHub, Report a bug, Request a feature, with Umami click events. The bug
  link prefills the form's "Related" field with the page path (skipped on
  `/account/` pages, whose paths can hold one-time codes). An issue whose
  text contains that line came from the site. Norwegian link texts added
  2026-10-28.
- **`CONTRIBUTING.md`** links to the README near the top, since the footer
  sends people there first.
- **`Made-with: ifi`** commit line (above).
- The deploy date of each of these goes in the feature timeline.

## Phases

Each phase is finished, checked and merged before the next one starts.

### Phase 1: totals (no consent, no new database)

**Built 2026-10-28, not merged yet.** Docs: `docs/operations/
management_commands.md#research_totals`; design notes:
`docs/claude_context/research_totals.md`. To try it locally:
`seed_research_data` adds made-up history (and with `--github-file`,
made-up GitHub data) and saves the totals it should give;
`research_totals --output` saves the real ones to compare.

A new `research_app`, where all research code will live, with one
command, `research_totals`. It prints monthly totals as CSV, from the site
database, the GitHub API (public repo, so the "before" months come for
free) and the commit history (through the same API, so it works where
`git` isn't installed). Umami clicks are read in Umami itself.

- Months in Oslo time. Default range: from the first month with data to
  the last complete month.
- The totals rules: nothing per person, nothing printed that names
  anyone, and 1–4 shown as `<5`.
- Bots (`dependabot`, `github-actions[bot]`) and the Peoply sync (which
  publishes with no user) don't count.
- `--no-github` skips the GitHub columns. `GITHUB_TOKEN` is optional, only
  for a higher rate limit.
- Add `research_app` to `.github/CODEOWNERS`, `INSTALLED_APPS`,
  `docs/architecture/overview.md` and
  `docs/operations/management_commands.md`.
- Tests with made-up data, no network.

Start exploring as soon as this works.

### Phase 2: before any participant (mostly outside the code)

Decided 2026-10-28: the Sikt check and the consent text wait until later,
but must be done before Phase 5 (the first participant). The privacy
policy already mentions Umami and the totals (2026-10-28). The research
notice gets its own page, like the content ownership terms
(`/account/content_terms`), not a section in the privacy policy.

- ~~Check the Sikt application and information letter against the
  plan.~~ Done 2026-10-29, see "Sikt check: results" below.
- Wait for Sikt to approve the change notice.
- Write the consent text (Norwegian, the source of truth, and English)
  and the privacy policy update.
- Small decisions, all decided 2026-10-28: sizes per type (see Focus),
  both suggestions in Questions 9, and leaving the queue table's rows out
  of the main database's backup.
- Write down the analysis questions, dated, before the first participant.

**Sikt check: results** (2026-10-29). The application, the information
letter, the variable list and the questionnaire were changed in the
change notice so they match the plan:

1. Consent is stored in the link database (application changed).
2. Level (bachelor, master, other) and cohort, asked at consent.
3. Two optional experience questions for every participant (Questions 12).
4. History before consent: dropped from the plan (Questions 5).
5. "Keep" when deleting the account: described in the letter.
6. Backups (14 days): described.
7. Exact times in the link database, coarse times in the analysis data:
   described.
8. Keys and analysis copies on OneDrive: described.
9. Follow-up research: nothing added (see Decided).
10. UiO email check: dropped (Questions 11).

Also added: UiO students (not only Ifi), the way in, the size of each
contribution, roles as one row per change, milestones, that free text is
read only by machine, group-level reporting, and the June 2027 steps.
The consent text on the site must follow the approved letter.

### Phase 3: research setup, with made-up data only

1. **Databases and the research job.** A link database (pseudonym ↔ user
   ↔ GitHub ID, and exact event times, encrypted fields, deleted June
   2027) and a research database (pseudonyms, coarse times and numbers
   only), with a database router. The three database users, the queue
   table, the research job's Linux user and timer (see Decided). All
   "who is this?" lookups happen in the job, through one file: no consent
   means "nobody", and the event is dropped. Pseudonyms are random, never
   made from the user ID.
2. **Backups** of the link and research databases, encrypted with a
   public key (`age`); the private key and a copy of the link database's
   key are kept by Hanna on Microsoft 365 for UiO (OneDrive).
3. **Access log:** `log_statement = 'all'` on Hanna's research user.
4. **Automatic tests:** no research values in logs, no research models in
   the admin. Tests use made-up data only.

### Phase 4: GitHub App and Connect GitHub

One read-only App owned by Creators-Guild. Connect GitHub in account
settings for everyone (keep the numeric ID, throw away the token). Add
the App to `docs/operations/access_and_handover.md`.

### Phase 5: consent and recording (the first participant)

1. **Consent.** A research section in account settings and the one-time
   question: consent text (versioned template, following the approved
   letter), one tick that also confirms UiO student status, and the four
   questions (see Questions 10–12). Hanna's own test participation is
   marked. The consent record (pseudonym, time, text version, withdrawal
   time) lives in the link database; the profile only gets "takes part:
   yes/no". When someone consents, the job copies their GitHub ID into
   the link database. Withdraw (through the queue), the research choice
   in the delete form (through the queue, see Decided), the export
   page's note on how to ask for research data, and the privacy policy
   update ship together with it.
2. **Recording.** The website only writes queue rows; the job does the
   rest. Published pages (type, time, word count) and drafts (Questions
   6), via `page_published` and the page history. Edits to someone
   else's page store the number of words added or changed (contribution
   from 40 words, see Questions 3). Group changes via `m2m_changed` on
   `User.groups.through` (both directions, plus `pre_clear`), saved as
   one added/removed row per role, so several roles at once just means
   several open rows. A daily check of GitHub repo roles (save a row only
   on change). One daily job (a systemd timer) for GitHub: finished PRs
   and issues (type, way in, time, size) and reviews (who helped whom),
   with GitHub's own timestamps.
3. **Export.** A command that writes CSV from the research database only,
   with Hanna's read-only user. Write down what each column means.

Hanna is the first (test) participant. Then the others.

### Phase 6: explore

A timeline per person, and the "how far did people get" chains. That's
where the questions for later research come from.

### June 2027

The exact times are only in the link database, so they go with it. Before
deleting it: work out anything else still needed from them. Not decided
yet: whether to compare with event dates (workshops, hackathons). If so,
the job writes each row's position relative to events (for example "3
days after an event") to the research database.

In this order (promised to Sikt):

1. Make the research data coarser: study year (from cohort and level) in
   two groups (years 1–2, year 3+, "annet" merged or its own group if
   big enough), each experience question as none / some-or-more, sizes
   in ranges, rare roles merged.
2. Run the matching test (`docs/research/data_handling.md`, question 11)
   and make the data coarser again if it finds people.
3. Delete the link database and all its backups the same day, both keys,
   and the GitHub App. The research database stays.
4. Delete the key copies on OneDrive, empty both recycle bins (OneDrive
   keeps deleted files up to 93 days) and check old versions.
5. Make the analysis copies on OneDrive coarser too, or delete them.
6. Clear "takes part" on every profile and turn off collection.

## Later (not in the first round)

- Webhooks instead of only the daily job (signature checked, payload never
  logged or stored).
- The feature-timeline script from git history.
- A report form on the site itself, so no GitHub account is needed. The
  GitHub App files the issue, the site knows who reported it, and the form
  says the text becomes public.
- A "How to contribute" page on the site with both paths (writing on the
  site, code on GitHub). `CONTRIBUTING.md` is written for coders.
- The leaderboard (its own plan: nicknames, opt-in to be shown).
- A usage counter for all `ifi` commands, if commit counts aren't enough.
- TSD for backups, keys and analysis (Hanna is considering it; needs a
  change notice to Sikt). Plan and build without it for now.
