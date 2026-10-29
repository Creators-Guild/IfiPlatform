# Research data handling

Last updated: 2026-10-29

How the data for the master's thesis is kept safe: where it is, who can
reach it, and what to do at each step. The thesis asks how a student-run
platform turns passive users into contributors.

This repo is public. Write roles and where to check, never names,
passwords or keys. "The student" is the master's student doing the
research. The project lead in the Sikt application (the supervisor) has
no access to the research data.

Parts marked **Not decided** point to the questions near the end.

## What the Sikt application promises

A summary of the platform part (Utvalg 1), as in the change notice of
2026-10-29. The application has the exact wording.

1. Data is collected automatically from IfiPlatform's database and from
   the GitHub API (only the platform's own repo, and only from the time
   someone consents), and stored under a pseudonym (an internal ID).
2. Everything is hosted on NREC, including the link between pseudonym,
   site account and GitHub account. Only pseudonymised copies for
   analysis and the backup keys are kept on UiO's OneDrive (Microsoft 365
   for UiO).
3. The link is stored **encrypted**, in its own database, apart from the
   data used for analysis. The same database holds the exact time of
   each event and the consent records. The analysis data only gets year,
   month and time of day.
4. Only a **service account** for the automated jobs uses the link. The
   student has separate access by hand, **only when needed**, for
   example when a participant asks to see or delete their data. The
   project lead (supervisor) has no access to it.
5. Consent (time ticked, text version, time withdrawn) is stored in the
   link database, tied to the pseudonym. The site database only stores
   whether someone takes part, with no pseudonym.
6. The databases are backed up daily, encrypted, on NREC, and each
   backup is deleted after 14 days.
7. In June 2027 the data is made coarser and tested against public
   GitHub. Then the link key, the backups of the link database and the
   keys on OneDrive are deleted for good. After that, all remaining data
   must be **fully anonymous**. Anonymous data may be kept.
8. Results are reported for groups. Groups under five are merged, and no
   single person's path is described so that they can be recognised.

Everything below is there to keep these promises.

## Where the data is

| Place | What's in it | Who can reach it |
| --- | --- | --- |
| Site database | Accounts, the GitHub ID of everyone who connects GitHub, and a short queue of events from people who consented (deleted once the research job has read them, and left out of the site database's backup) | The site, root |
| Link database | Pseudonym ↔ user ↔ GitHub ID, and the exact time of each event, encrypted | The research job, the student by hand when needed, root |
| Research database | Pseudonyms, and events with year, month, time of day, type and size | Written only by the research job. Read by the student (read-only), root |
| Keys (encryption and lookup) | A file only the research job's Linux user can read. The backup private key and a copy of the link database's key are on the student's UiO OneDrive | The research job, root; the student (OneDrive) |
| Backups | Encrypted dumps on the backup volume `/mnt/backups`, kept 14 days | Root can see the files; only the private key, kept off the server, opens them (question 4) |
| Copies for analysis | Pseudonymised exports on the student's UiO OneDrive, never the link (question 5) | The student |

**Root** means anyone who can log in to the server as `ubuntu`, or who
holds the deploy key. Root can read every database and `.env`. Only the
student has root, and nobody else gets it before June 2027: the devops
person only gets a limited user (question 1).

## How the website is kept away from the data

The website never opens the link or research database. Its database user
is refused if it tries.

1. When someone who consented does something (publishes a page, for
   example), the website writes a row to a small queue in the site
   database: "user 42 published page X at 14:22".
2. Every few minutes, the **research job** reads the queue. It runs as
   its own Linux user, with its own database user and the encryption key
   in a file only it can read. This is the service account from promise 4.
3. It looks up the pseudonym, writes the exact time to the link database
   and a coarse row to the research database, and deletes the queue row.

Consent and withdrawal work the same way: the button in account settings
sets a flag, and the job creates or deletes the data within minutes.

## Why exact times are only in the link database

GitHub is public and shows the exact time of every PR, issue and review.
A row like "PR merged 2026-11-03 14:22, 120 lines" can be matched to the
one public PR made at that minute, and so to its author, without the link
database.

So the research database only gets year, month and a time-of-day block.
That is much harder to match, but not impossible: an exact size or a
rare kind of contribution can still point to one PR (question 10).

Anything new needed from the exact times later is worked out by a job
that writes a new coarse field. The student doesn't read exact times
for analysis, since the link database is opened by hand only when needed
(promise 4).

## Decided

- Taking part is opt-in, and separate from contributing. It never affects
  roles or access.
- Without consent, nothing is recorded about a person (except in the
  totals for the whole site).
- Withdrawing consent deletes the participant's research data. This is
  possible until June 2027.
- Deleting an account asks: delete my research data too, or keep it.
  Keeping it deletes everything about that pseudonym in the link
  database (the link row, the consent record, the GitHub ID copy, the
  lookup values and all exact times), so the person can't withdraw
  later. Only the coarse rows in the research database stay.
- Exact times are stored only in the link database. The research
  database gets year, month and a time-of-day block.
- The website never opens the link or research database. A research job
  with its own Linux user, database user and key does that work (see
  above).
- Three database users: the website's (site database only), the research
  job's (link and research databases), and the student's own (the
  link database by hand when needed, the research database read-only).
- Numbers about everyone are totals only, per month or term, and 1–4 is
  shown as "fewer than 5".
- Umami's visitor statistics are not personal data: no cookies, no
  stored IP addresses, nothing linked to an account. They're used for the
  research as numbers about the whole site, and the privacy policy says
  so (decided 2026-10-28).
- Only what the analysis needs is kept. June 2027 deletes only the link
  database; the research database stays. When the research data is
  deleted later, only the results and the proof of them remain.
- The student takes part as a test participant, marked and left out
  of the analysis.
- Nobody but the student gets root before June 2027. The devops person
  only gets a limited user (question 1).
- Free text (commit messages, issue text, article text) is only read in
  memory, to count words and find fixed markers such as `Made-with: ifi`.
  It is never stored or logged.
- Results are reported for groups. Groups under five are merged, and no
  single participant's path is told as a story (question 12).
- In June 2027 the data is made coarser and tested. Then the link
  database, its backups, the keys (also the copies on OneDrive) and the
  GitHub App are deleted.

## Risks

1. **Someone with root reads data they shouldn't.** (question 1)
2. **New code reads or leaks research data.** Code that gets into `main`
   is deployed, and the research job's code can read everything.
   (question 3)
3. **Data ends up somewhere nobody thought of:** logs, error messages,
   the admin pages, backups, laptops, dev machines. (questions 4–7)
4. **Pseudonyms can be turned back into users.** If a pseudonym is made
   from the user ID (for example a hash of it), anyone can try every ID.
   (question 8)
5. **The consent record holds the link in plain text.** If the consent
   row in the site database has both the user and the pseudonym, the link
   exists unencrypted. (question 9)
6. **The data isn't really anonymous after June 2027.** With 10–15 people,
   a public repo and a small community, even coarse data can point to one
   person, for example "the only maintainer". (questions 10–11)
7. **The thesis text points to a person.** A story about one person's
   path can be recognised by people who know the project. (question 12)

## Questions

1. **The devops person.** Decided 2026-10-29: no root before June 2027,
   since the Sikt application says only the student can reach the
   research data, and root can read the key file. They get only the
   limited user on the [to-fix list](../to_fix.md) under Server, and no
   server login until it exists.
2. **Database users.** Decided, see above.
3. **Code review.** Decided and done: `research_app` is in
   `.github/CODEOWNERS`, so research code needs the student's approval.
4. **Backups.** Decided: yes, the link and research databases are backed
   up, since losing the data would be serious. The consent text must say
   that withdrawn data stays in the backups for up to 14 days. Decided:
   the backups are encrypted with a public key (for example with the tool
   `age`). The server only has the public key, so it can lock backups but
   not open them. The private key, and a copy of the link database's
   encryption key, are kept off the server, on Microsoft 365 for UiO
   (OneDrive), which UiO approves for yellow data. The backups stay on
   the server's backup volume (`/mnt/backups`), so losing the whole NREC
   project would lose them too.
   Write down *where* the keys are (never the keys themselves), so they
   can be found when a backup is needed: _(fill in: OneDrive folder)_.
   Decided 2026-10-29: deletions are not re-applied after a restore. A
   restore from the last 14 days can bring back data that was withdrawn
   in that time, so avoid restoring the link and research databases
   unless the data is lost.
   In June 2027 all backups of the link database are deleted the same
   day as the database, not left to expire.
   Decided 2026-10-28: the site database's backup leaves out the rows of
   the research queue. They hold a user ID and the exact time of an
   event, which belong only in the link database. A row lives a few
   minutes, so a restore loses at most a few minutes of events.
5. **Copies for analysis.** Decided by the Sikt application: only
   pseudonymised exports, kept on the student's UiO OneDrive (Microsoft
   365 for UiO, approved for yellow data), never the link. Whatever the
   computer saves while working (notebooks, charts, CSV files) counts as
   a copy too. **Not decided:** how to work with the data without making
   more copies than needed.
6. **Logs and admin pages.** Decided: never log GitHub usernames, GitHub
   IDs, user IDs or pseudonyms, keep research data out of the Django and
   Wagtail admin, and check both with automatic tests:
   - a test fails if anything from the research app is registered in the
     Django or Wagtail admin
   - a test runs the research job with made-up data and fails if any of
     those made-up values shows up in the log output, including a
     made-up commit message and issue text
   - the job logs only the kind of an error, never its message, since
     database errors include the values involved
7. **Dev machines.** Decided: never copy research data from the server to
   a dev machine. Tests use made-up data.
8. **Pseudonyms.** Decided: random. A pseudonym made from the user ID (a
   hash of it, for example) could be worked out again by trying every
   user ID, even after the link database is deleted. A random one can't.
9. **The consent record.** Decided: it lives in the link database
   (pseudonym, time the box was ticked, consent text version, time of
   withdrawal). The site database only stores "takes part: yes/no" on the
   profile, with no pseudonym. Withdrawing deletes the consent record
   along with the data. No record of the consent is kept after
   withdrawal.
10. **How coarse.** Decided for now: nothing more than the coarse times.
    Sizes stay exact and roles aren't merged. Change it if needed, for
    example if the test in question 11 finds people.
11. **A test before deleting the key.** Decided, done in June 2027: a
    script that plays an outsider with only the research data and public
    GitHub. For each row it counts how many public PRs, issues, reviews
    or articles have the same month, time block, type and size. If only
    one matches, or all of a participant's rows point to the same GitHub
    user, that person can be found: make the data coarser (question 10).
12. **The thesis text.** Decided: no stories about individual platform
    participants; their data is reported for groups, groups under five
    are merged, and rare roles aren't described one by one. Quotes from
    the Halloween interviews are anonymised.
13. **A log of access by hand.** Decided, in two parts:
    - automatic: PostgreSQL logs every query from the student's
      research user (`log_statement = 'all'` on that user). This log
      holds personal data too, so it's deleted in June 2027.
    - by hand: one line per opening: when, why, and which request.
14. **Halloween data on this server.** The Sikt application also covers
    the Halloween event's participants and helpers. Their GitHub data and
    link (research ID ↔ GitHub username or email) are stored on NREC,
    encrypted and apart from the analysis data, and deleted when the
    analysis is done, by 30.06.2027 at the latest. **Not decided:** where
    on the server, how it's kept apart from the platform's research data,
    and whether it's backed up.

## Later

- **TSD** (UiO's service for sensitive data) for the backup keys, the
  backups themselves (sent there through TSD's upload API, with an
  upload-only key) and the analysis. The Sikt application says all data
  is on NREC, so this needs a change notice to Sikt first.

## Checklists

### Before the first participant

- [ ] Sikt has approved the change notice of 2026-10-29.
- [ ] All questions above decided, and this doc updated.
- [ ] Consent text and privacy policy updated.
- [ ] The link database is encrypted and only the research job uses it.
- [ ] The website's database user is refused by the link and research
      databases (try it).
- [ ] The research job runs as its own Linux user, and only that user can
      read its key file.
- [ ] Withdrawing and account deletion tested with made-up data.
- [ ] Encrypted backups of the link and research databases work, a
      restore has been tested, and where the keys are is written down.
- [x] The research code's folder is in `.github/CODEOWNERS`.
- [ ] The automatic tests for logs and admin pages pass.

### When someone withdraws

- [ ] Check that their research rows, link rows (with the exact times) and
      queue rows are gone.
- [ ] Backups: nothing to do. The data is gone from them within 14 days.

### When someone gets or loses root

- [ ] Follow [access_and_handover.md](../operations/access_and_handover.md).
- [ ] Nobody but the student gets root before June 2027 (question 1).

### June 2027

In this order:

- [ ] Make the data coarser (question 10).
- [ ] Run the matching test (question 11), and make the data coarser
      again if it finds people.
- [ ] Delete the link database, all its backups, the encryption and
      lookup keys, the PostgreSQL log of manual access, and the GitHub
      App. The research database stays.
- [ ] Delete the key copies on OneDrive, then empty the recycle bin and
      the second-stage recycle bin (OneDrive keeps deleted files for up
      to 93 days), and check that no old versions are left.
- [ ] Make the analysis copies on OneDrive coarser too, or delete them.
- [ ] Clear "takes part" on every profile and turn off collection.
- [ ] Update this doc.
