# Plan: make the ifi commands fit everyday work

## Context

The `ifi` commands (tools/ifi/) were built for the Halloween event:
beginners, one issue each, one afternoon. A review found that the basic loop
(`fix-issue → save → pull-request → update → cleanup`) also fits normal work,
but some things break when people work over several days, on several
computers, or with teammates.

- **Already done (commit e6c9cc1):** removed `ifi undo-file --extra`. It
  needed a "Files to change" list in the issue, which only the event issues
  had. The ifi tests passed: 129 passed, 0 failed, 1 skipped.
- **Kept on purpose:** `ifi account`. You and students switch between a
  personal and a school GitHub account.

## Status at a glance

| Item | What | Status |
| --- | --- | --- |
| A1 | Find your branch again on any computer | ✅ Done (3294d7b) |
| A2 | Warn about and fix clashing database changes (migrations) | ✅ Done (5bab3f9) |
| A3 | Put unsaved work aside when switching, with reminders | ✅ Done (3294d7b); wording → "stash", see "Decisions 2026-10-26" |
| A4 | Pull requests without an issue | ✅ Done (38118b6); consequences in docs/to_fix.md |
| B1 | Join clashing translation files | ✅ Done (8271ce1) |
| B2 | `ifi save` asks about new files, and `--only` | ✅ Done (fb56457) |
| B3 | `ifi hide`/`unhide`; undo-file stops hiding | ✅ Done |
| B4 | Rewrote your own commits vs someone else's push | 🟢 Built (not committed) |
| B5 | cleanup deletes your merged branches on origin | ✅ Agreed, details in "Decisions 2026-10-26" |
| C1 | Pull requests into `beta` | ❌ No: `beta` is old and unused, everything goes to `main` |
| C2 | Merge button | ✅ Only "Merge commit" is used, so nothing to build |
| C3 | `ifi review <pr>` | ✅ Agreed: collaborators only (see C3 below) |
| C4 | Branch types | ✅ Done with `ifi start` (A4), CONTRIBUTING.md updated |

The user commits each item themselves: build one, stop, wait for "go on".
Tests ran on a Windows host need tests/lib.sh's `safe.directory` line
(the sandbox drops the container's system config, and /workspace belongs
to root there).

Order of work: A1 → A3 → A2 → A4 → B1–B5 → C3.
A1 and A3 both change `fix-issue`, so they go together. C3 reuses A3's
put-aside code, so it comes after A3.

---

## Group A: agreed

### A1. Find your branch again on any computer

- **Today:** `ifi fix-issue 42` writes "this branch is for issue 42" into a
  settings file that exists only on this computer (`.git/config`).
- **Problem:** on another computer or in a new clone, ifi doesn't know about
  your branch, so it makes a new, empty one.
- **Change:** ifi builds the branch name from the issue title, so it gets the
  same name on every computer. It looks for that name on GitHub, shows who
  made the last change and when, and asks: "Is this your work for issue 42?"
  If you say yes, you continue there.
- **Good to know:** if the issue's title changed, or GitHub can't be reached,
  ifi can't work out the name and acts as it does today.

**For the builder:**
- tools/ifi/fix-issue: after `slugify` gives `name="$kind/$slug"`, also fetch
  origin. Look for `origin/$name-$nr`, then `origin/$name`. If there's a
  match, show its last commit (`git log -1 --format='%s, by %an, %ar'`) and
  ask y/n. On yes: `switch_or_explain ... -c "$name" --track "origin/$name"`
  and set `branch.$name.ifi-issue`.
- Do the same when a *local* branch has that name but no `ifi-issue` link
  (one made with plain git). Today it adds `-$nr` and starts a new branch.
- Move the "you already have a branch" part (switch, then check whether main
  moved on) into a function, so both paths use it. A3 hooks in there too.
- Collaborators: origin is the main repo, so other people's branches are
  there too. The "by <author>" line is what stops you taking someone else's.
- Tests in tools/ifi/tests/test_fix_issue.sh: continue a branch from a second
  clone; answering no makes a new branch; offline works like today.
  tests/lib.sh may need a helper for a second clone.

### A2. Clashing database changes (migrations)

- **Today:** changing a model makes a numbered file, like `0007_...py`. If you
  and a teammate both add one in the same app, Git sees no conflict, because
  the names differ. Django then refuses to run: "Conflicting migrations".
- **Change:**
  1. `ifi update` and `ifi check` warn: "You and main both added a database
     change in apps/x. Run ifi migrate after the update."
  2. `ifi migrate` finds the clash and offers Django's own fix
     (`makemigrations --merge`). Django shows what it will merge and asks
     before writing anything. Then `ifi save` as usual.

**For the builder:**
- New helper in tools/ifi/common.sh: the migration folders where *both* sides
  added files since the fork point. Use
  `git diff --name-only --diff-filter=A <fork> <side> -- '*/migrations/[0-9]*.py'`,
  take the folder of each file, then `comm -12`. Git only, no Django needed.
- tools/ifi/update: work out the clash *before* the rebase or merge, and save
  it as `branch.<b>.ifi-migration-clash`, since a conflict can pause the
  update. Show the warning when the update finishes, then unset it.
- tools/ifi/check step 9: it already has `fork_point`, so add a ⚠️ line there.
- tools/ifi/migrate: first ask Django which apps clash:
  `manage.py shell -c` with
  `MigrationLoader(connection).detect_conflicts()` (prints app labels). If any
  clash, explain it and run `makemigrations --merge` (interactive). Then
  makemigrations + migrate as today, and end with "Your turn: ifi save".
- `verb_form` (common.sh) only knows certain verbs. Add any new first word,
  e.g. "Merge" (tests/test_output.sh checks this).
- CLAUDE.md rule: read docs/claude_context/migrations.md before touching
  migrations. A merge migration only lists both files as dependencies, so the
  raw-SQL rules don't apply. Check anyway.
- Tests: test_update.sh and test_check.sh with fake migration files (the
  sandbox has no Django). The Django part is a new row in
  tools/ifi/tests/manual_checklist.md.

### A3. Put unsaved work aside when switching branches

- **Today:** with uncommitted changes, `ifi fix-issue <other issue>` stops
  and says "commit them first".
- **Change:** ifi lists your changed files and asks: "Put these aside for
  <branch>? You get them back when you come back to it." Git calls this a
  *stash*, like putting papers in a drawer. When you go back with
  `ifi fix-issue <nr>`, ifi takes them out again by itself.
- **Your question: how does a beginner remember?** ifi reminds you in four
  places:
  1. **Every new terminal** (the startup check): "⚠️ You have changes put
     aside for bug/orange-cards. Get them back: ifi fix-issue 42"
  2. **`ifi check`**: the same line, with the date they were put aside.
  3. **`ifi pull-request`**: "This branch has changes put aside that aren't
     in your pull request. Send without them? (y/n)", so nothing is
     forgotten.
  4. **`ifi cleanup`**: if a branch it deletes has put-aside changes, it says
     so and keeps them.
- **Good to know:** put-aside changes are **only on this computer, not on
  GitHub**. ifi says so every time it puts something aside.
- **Maybe later:** a mark in the terminal prompt, like `(1 put aside)`.

**For the builder:**
- tools/ifi/fix-issue: where it stops today for changes on a non-main branch,
  ask instead if there's a terminal (`-t 0`). Without a terminal, or on "n",
  keep today's message. On "y":
  `run "Put your unsaved changes aside for $current" git stash push --include-untracked -m "ifi: $current"`.
- New helper in common.sh, `stash_for <branch>`: the `stash@{n}` whose
  subject ends in `ifi: <branch>`. Read it from
  `git stash list --format='%gd%x09%gs'`. Compare as plain text, not a regex,
  because branch names contain `/`.
- After switching to a branch (the A1 function, plus the "already on it"
  case): if `stash_for` finds one, run
  `run "Take back the changes you put aside" git stash pop --quiet <ref>`.
  If the pop conflicts, Git keeps the stash, so explain that and show
  `git stash list`.
- tools/ifi/check: a new step that lists every `ifi:` stash. Use
  `quiet=false warn` so the startup check shows it too (like "main has new
  commits"). Find the issue number from `branch.<b>.ifi-issue`.
- tools/ifi/pull-request: before `push_branch`, if `stash_for` finds one,
  warn and ask y/n.
- tools/ifi/cleanup: name the stash of each branch it deletes, and keep it.
- Bash 3.2 (Mac): no `mapfile`, no `${x,,}`.
- Tests: test_fix_issue.sh (put aside and take back, new files come along,
  without a terminal it stops like today), test_check.sh (reminder, also
  with `--quiet`), test_pull_request.sh, test_cleanup.sh.

### A4. Pull requests without an issue

- **Today:** `ifi pull-request` won't go on without an issue number.
- **Change:**
  - `ifi pull-request` asks "Which issue does this fix? (Enter if none)".
  - New `ifi start <type> <few words>` starts a branch without an issue, from
    the newest main, named like the others (`task/fix-typo`).
- **⚠️ Consequences, for you to think about later:**
  - The pull request closes no issue. Nothing on GitHub links the work to a
    task.
  - **Trello:** cards are made from issues (.github/workflows/trello_sync.yml).
    No issue means no card, so the work doesn't show on the board.
  - Students might skip step 1 of CONTRIBUTING.md ("Pick an issue, comment
    that you're taking it"), so two people could do the same work.
  - These are also listed in docs/to_fix.md (ifi commands), for later.
  - Ways to soften it later: only allow "no issue" for some types (task,
    docs, ci); add "Most changes should have an issue. Sure? (y/n)"; or leave
    `ifi start` out of the beginners' help page.

**For the builder:**
- tools/ifi/pull-request: an empty answer saves `branch.<b>.ifi-issue none`,
  so it doesn't ask again. With `none`, the "Your turn" text says to explain
  in the description why there's no issue, instead of the `Closes #` line.
- New tools/ifi/start: reuse fix-issue's branch-making part (`slugify`,
  `find_base`, `fetch_base`, `switch_or_explain -c ... --no-track`), moved
  into a shared function. Allowed types: bug, feature, task, docs, ci (C4).
- Add `start` everywhere commands are listed: tools/ifi/ifi (dispatcher),
  shell-setup.sh (Tab completion), pages/ifi.txt. The test
  `t_commands_lists_agree` checks they match.
- tools/ifi/check step 7: no "not linked to an issue" warning for `none`.
- Tests: test_pull_request.sh (Enter means no issue, isn't asked again), new
  test_start.sh.

---

## Group B: agreed

| # | Today | Change |
| --- | --- | --- |
| B1 | Translation files (`.po`) conflict often, and they're big to fix by hand | If only translation files conflict, ifi combines both versions (`msgcat --use-first`; where the same text has two translations, yours wins), then rebuilds the `.mo` files with `compilemessages`. gettext is in the container (Dockerfile.dev). Where it's missing, the normal conflict help is shown. |
| B2 | `ifi save` adds every file, even new ones you didn't mean to | When there are new files, list them and ask "Add these too? (y/n)". Maybe also `ifi save "msg" --only <files>`. Not `ifi save "msg" file1`, because today `ifi save Fixed the cards` without quotes works, and that would break. |
| B3 | Undoing a file you added makes Git ignore it for good, with no warning | Say it clearly, mark the line in `.git/info/exclude` with a comment, and have `ifi check` list those files and how to un-hide them. Review it after building (docs/to_fix.md). |
| B4 | One message for two cases when GitHub has commits you don't | Separate "someone else pushed to your branch" from "you rewrote your history yourself". Tell them apart with `git cherry` (same changes = you rewrote them). |
| B5 | `ifi cleanup` doesn't delete collaborators' merged branches on GitHub | Also delete them on origin when origin is the main repo. It's safe: only branches already merged into main. |

## Decisions 2026-10-26

Asked and answered before building B1–C3:

- **B1:** when only translation files clash, ifi joins them and goes on
  with the update by itself (also at each commit of a rebase), then lists
  the joined files. Translation files plus other files: the usual conflict
  help, as planned. `.mo` files are rebuilt with
  `compilemessages -l <lang>`, only for the languages that clashed.
- **B2:** `ifi save` asks only about *untracked* files ("Add these too?").
  Changes to files Git knows are always included. y: added, and never asked
  again (Git tracks them now). n: left out of the commit, kept on disk, and
  asked again next time, like `git status` keeps listing them.
  Build `ifi save "msg" --only <files>` now (like `git commit --only`).
- **B3:** `ifi undo-file` stops hiding files. It takes an added file out of
  Git and ends with the tip `ifi hide <file>`. New commands:
  - `ifi hide <file>`: adds `/<file>` to `.git/info/exclude` (this computer
    only; `.gitignore` is for everyone and is edited like any other file).
    Refuses files Git tracks: "Take it out first: ifi undo-file <file>".
  - `ifi unhide <file>`: removes that line.
  - `ifi check` lists hidden files, with "Show them to Git again:
    ifi unhide <file>".
  This replaces the "mark the line with a comment" idea, and answers the
  undo-file item in docs/to_fix.md.
- **B4:** "you rewrote your own commits" (git cherry: all of GitHub's extra
  commits have the same changes as yours) → ask "Replace your branch on
  GitHub with this version? (y/n)", pushed with a lease. Someone else's
  commits → today's message, plus a list of GitHub's extra commits
  ("subject", by author, when). An --amend that changed content counts as
  "someone else's" (cherry sees different changes), which is the safe side.
- **B5:** on origin, delete only the branches cleanup also deletes on your
  computer. Not every merged branch on GitHub (that would hit `beta`,
  `skeleton`, ...). GitHub does *not* auto-delete merged branches in this
  repo, so fix cleanup's comment that says it does.
- **C3:** unsaved changes when starting `ifi review`, also on main: ask to
  stash them, given back at `ifi review --done`.
- **Wording:** say "stash" wherever ifi puts changes aside (fix-issue,
  check, pull-request, cleanup, review), to teach Git's words. E.g. "Stash
  your changes (put them aside)? (y/n)".

## Group C: answers

- **C1. Pull requests into `beta`: no.** `beta` hasn't changed since
  2026-08-15 and has nothing that isn't in main. ifi keeps using `main`.
- **C2. Merge button: only "Merge commit".** ifi already sees those branches
  as merged. If squash or rebase merging is ever turned on, `ifi cleanup`
  stops seeing merged branches; then it needs to ask GitHub instead.
- **C3. `ifi review <pr>`: collaborators only.**
  - **What it does:** `ifi review 57` downloads pull request #57 into a
    branch `review/57` and switches to it, so your local site runs their
    code and you can click around and run the tests.
    `ifi review --done` takes you back to your own branch.
  - **Why only collaborators:** their code runs on your computer. It can
    change your project files and your local database, and while you run
    their tests or migrations it can ask VS Code for your GitHub login.
    Collaborators are trusted, and reviewing is part of their job.
  - **Safety step:** before downloading, ifi shows who wrote the pull
    request and its title, and asks "Run code from <name>? (y/n)".

  **For the builder:**
  - New tools/ifi/review. Collaborator = may push to the main repo: a
    dry-run push to `$base`, like `try_login` (tools/ifi/account) and
    `ifi check` step 6. Denied → "Only collaborators can use ifi review.
    Read the pull request on GitHub: <link>".
  - Author and title from `GET /repos/$MAIN_REPO/pulls/<nr>` (the `$PY` +
    urllib + `IFI_GITHUB_API` pattern from fix-issue). Offline → the last
    commit's author from Git.
  - `git fetch $base +pull/<nr>/head:review/<nr>`, then switch. Running it
    again updates the branch (switch away first if you're on it).
  - Unsaved work on the branch you leave: put aside with A3's code;
    remember the branch in `ifi.review-return`.
  - `ifi review --done`: switch back, take back put-aside work, delete
    `review/<nr>`. If the pull request added migrations, say: "Their
    database changes are still in your local database. If the site acts
    strange: ifi reset-database".
  - On `review/*`, `ifi save` and `ifi pull-request` refuse: "This is
    someone else's pull request. Leave comments on GitHub instead."
  - Register `review` in tools/ifi/ifi, shell-setup.sh (with `--done`) and
    pages/ifi.txt. Document it in docs/contributing/collaborators.md.
  - Tests: new test_review.sh; the fake GitHub in tests/lib.sh needs a
    `pulls/<nr>` answer and a `refs/pull/<nr>/head` ref.
- **C4. Branch types: `bug/ feature/ task/ docs/ ci/`.** `ifi fix-issue`
  still takes the type from the issue (bug, feature or task). `ifi start`
  (A4) also accepts docs and ci. Update CONTRIBUTING.md's branch-name line
  when building.

---

## Rules while building (from CLAUDE.md)

- Before editing a file, look for a `docs/claude_context/...` pointer at the
  top and read that note. docs/claude_context/ifi_account.md covers
  common.sh and check: run its stale check, and bump its date when those
  change.
- Update the human docs that show ifi commands in the same step: README.md,
  CONTRIBUTING.md, docs/contributing/get_the_code.md, docker_guide.md and
  setup_without_docker.md, plus tools/ifi/pages/*.txt. Bump each doc's
  `Last updated:` date.
- Keep ifi's style: steps through `run` / `git_or_explain` so they show up
  under "Done for you" and in the plain-Git recap, plain words, and
  "Your turn:" with `choices`.

## How to check it works

1. `tools/ifi/tests/run`: all pass, including the new tests for each item.
2. `tools/ifi/tests/playground`: try each item by hand on the fake GitHub.
   - A1: second clone, then `ifi fix-issue 5`.
   - A3: change a file, `ifi fix-issue 6`, then `ifi check`, then
     `ifi fix-issue 5`.
   - A4: `ifi start task fix typo`, then `ifi pull-request` and press Enter.
3. By hand in the real container (add rows to manual_checklist.md):
   - A2: two branches that each add a migration in the same app.
     `ifi update`, then `ifi migrate` merges them, then `ifi test`.
   - A3: open a new VS Code terminal and check the reminder shows.
