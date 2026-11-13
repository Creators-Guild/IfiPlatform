# Plan: research numbers from the Halloween mock site

Last updated: 2026-10-29

The mock site (halloween.ifiplattform.no) must be deleted on
**2 November 2026**, as its privacy policy promises. Before that, Hanna
takes a few **anonymous totals** from it for her master's thesis. The
Sikt application (change notice of 2026-10-29) and the information letter
for the event's participants promise exactly this, and nothing more:

> From the mock site, only anonymous, aggregated numbers are taken
> before the site is deleted on 2 November 2026; no data about
> individuals.

Totals are not personal data, so this may be done before Sikt has
approved the change notice. Delete this plan when the site is deleted.

## What to count

Exactly these four numbers (from the Sikt variable list for the event),
nothing else:

1. Registered accounts in total.
2. Accounts that connected a GitHub account.
3. Accounts that solved at least one task.
4. Accounts that were created without doing anything more (no GitHub
   connection and no task attempted).

**Check in the code first** and write the answers into this plan:

- Which model and field means "connected GitHub"?
- What counts as "solved a task" (a completed task row, a merged PR, a
  score)? Use what the site itself showed as solved.
- What counts as "doing something" for number 4?
- Which accounts to leave out: superusers, staff, Hanna's and the
  helpers' accounts, test accounts. Decide the rule, and count how many
  were left out (only the number).

## How

1. Add a small read-only management command in the mock site repo, for
   example `halloween_totals`, that prints the four numbers and how many
   accounts were left out. It must never print or log names, usernames,
   emails, GitHub IDs or anything per account. A short test with made-up
   accounts checks the four numbers.
2. Deploy it, then on the mock server run:
   `docker compose exec web python manage.py halloween_totals`
3. Write down, by hand, in one small file (for example
   `halloween_totals.txt`):
   - the four numbers and the number left out
   - the date and time they were taken
   - the commit hash of the code that counted them
   - the definitions from "Check in the code first"
4. Keep that file in Hanna's research folder on UiO OneDrive, with the
   rest of the analysis data. It's not personal data, so it could live
   anywhere, but don't commit the exact numbers to a public repo: the
   thesis reports 1–4 as "fewer than 5".

Also note, while it's still visible: the number of people signed up on
Peoply (a single number, same file).

## Don't

- Don't copy the database, a dump, a backup or any per-account rows off
  the server, not even "just in case". The promise is totals only.
- Don't move any of the mock site's data to IfiPlatform. Only the small
  file of totals is kept.
- Don't fetch per-person GitHub data from the event repo now. That needs
  the participant's consent (UiO Nettskjema) and Sikt's approval first,
  and it happens later on IfiPlatform's server (see "Later").

## Then delete the site (by 2 November 2026)

- [ ] The four totals are written down and checked.
- [ ] Stop the containers and delete the database and media volumes.
- [ ] Delete the mock site's backups, wherever they are kept.
- [ ] Delete the VM (or its disks) and any snapshots in the NREC project.
- [ ] Remove the `halloween` DNS record.
- [ ] Remove the mock site's `.env` (secrets) from wherever it's stored.
- [ ] Write down the date it was deleted (the letter says it was deleted
      on 2 November 2026).

**Keep the event's GitHub repository.** It is not part of the mock site,
and the research needs it later. Archiving it (read-only) is fine;
deleting it is not, at least until the analysis is done (by 30.06.2027).

## Later (after Sikt approves, not part of this plan)

For participants who consent in Nettskjema: fetch their activity in the
event repo (forks, pull requests, tasks solved and difficulty, forked
without solving) to **IfiPlatform's server on NREC**, give each a random
research ID, store the link (ID ↔ GitHub username or email) encrypted
and apart from the analysis data, and delete the link and the Nettskjema
answers by 30.06.2027. How exactly is decided in the IfiPlatform repo
(`docs/research/data_handling.md`, question 14).
