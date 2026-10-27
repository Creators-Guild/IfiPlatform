# Plan: manual run of ifi after the October 2026 changes

Last updated: 2026-10-27

The ifi commands were changed a lot on 2026-10-26/27: new behaviour,
removed commands (start, hide, unhide, review, save --only, auto-stash) and
many bug fixes. `tools/ifi/tests/run` passes, but it runs against a fake
GitHub. This run checks what the sandbox can't fake: real logins, real
GitHub, real Django, VS Code, Windows. Do it, write down anything odd, then
delete this plan.

Use `tools/ifi/tests/manual_checklist.md` for the exact steps. Do these rows
first, in this order; the rest changed little and can wait.

## 1. The everyday loop
Container, a second GitHub account that is not a collaborator, its fork.
- First terminal after the container starts, then `ifi check`.
- `ifi fix-issue` → change a file and make `notes.txt` → `ifi save`, answer
  n → only the changed file is committed.
- `ifi pull-request` → the link opens GitHub's page; the terminal lists
  `notes.txt` as not in the pull request.

## 2. Conflicts
- A commit on main that changes the same line → `ifi check` warns →
  `ifi update`, answer y to help.
- While it waits: `ifi save` refuses ("ifi update stopped at a conflict").
- VS Code's merge editor with one `<<<<<<<` left, **Complete Merge** →
  `ifi update` refuses ("still have conflict markers").
- Fix it → `ifi update` (mentions VS Code's Sync button) →
  `ifi pull-request` replaces the branch on GitHub.

## 3. Real Django and GitHub
- Translation clash → ifi joins the `.po` files, `compilemessages` runs.
- **Update branch** on GitHub → `ifi pull-request` lists only that merge
  commit, not main's commits.
- Merge the pull request → `ifi cleanup`. Also as a collaborator: your
  branch is deleted in the main repo, a teammate's merged branch stays.

## 4. Paths and Windows
- `ifi undo-file` from inside `ifiplatform/`, with the path as `git status`
  shows it there.
- Git Bash without Python: `./ifi fix-issue`, `save`, `pull-request`,
  `check` all work; pull-request shows the link.
- Windows: `ifi account switch <other>` opens a login window.

## 5. Accounts, if you use gh
- The three gh rows: no password pop-up, the right account on the commit.

## Afterwards
- Bugs → fix them (root cause first). Confusing wording counts too
  (manual_checklist.md, "Write down").
- Then let one or two beginners do a real issue with ifi, and note where
  they hesitate.
- Delete this plan.
