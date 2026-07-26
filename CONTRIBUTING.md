# Contributing to IfiPlatform
 
Thanks for wanting to contribute! This project is built by IFI-Creators' Guild — contributions of any size are welcome, whether it's fixing a typo, reporting a bug, or building a new feature.
 
If you've never contributed to an open source project before, don't worry — this guide walks through everything you need.

## Main Roles in this Repository
1. **Committer** - Trusted developer (and part of core team) with the rights to commit and merge code directly to the main repository
2. **Collaborator** - Developer with write access to the repo itself (e.g. teammates who aren't yet trusted to merge unreviewed, but can push branches and manage issues directly)
3. **Contributor (You)** - The open, public-facing role — anyone can be this without any special access. You fork the repo, open issues, and submit pull requests for review.

**These roles aren't fixed** — As long as you are a member of IFI-Creators' Guild, contributors who show consistent, quality work may be invited to become Collaborators, and Collaborators who build up trust over time may be invited to become Committers.

## Getting Started
 
1. **Fork the repository** to your own GitHub account.
2. **Clone your fork** locally (unlkess you are a collaborator):
```bash
git clone https://github.com/<your-username>/IfiPlatform.git
cd IfiPlatform
```
3. **Set up your dev environment** — see the [Setup section in the README](README.md#setup) for creating a virtual environment and installing dependencies.
4. **Create a branch** for your change:
```bash
git checkout -b <issue-type>/<short-description>
```
   e.g. `feature/mobile-nav`, `bug/login-redirect`, `task/setup-instructions`
 
## Reporting Issues
 
Before opening a new issue, please **search existing issues** to check it hasn't already been reported.
 
### Issue Type
 
We use GitHub's native **Issue Type** field with three options:
 
| Type | Use for |
|---|---|
| **Bug** | Something is broken or not working as expected |
| **Feature** | New functionality or user-facing improvement |
| **Task** | Maintenance, chores, cleanup, tooling, dependency updates, sub-tasks, tests, and documentation |
 
### Labels
 
On top of Type, we use labels to add detail:
 
- `test` — issue is specifically about writing or improving test coverage
- `docs` — issue is specifically about documentation
- `area: mobile`, `area: ui`, `area: backend`, etc. — which part of the platform it touches
- `good first issue` — a good entry point if you're new to the project
- `help wanted` — we'd especially appreciate outside help on this one
**Example:** an issue about adding tests for the login page would be **Type: Task** + labels `test`, `area: backend`.
 
### Example issue templates
 
We keep worked examples of how to write a good issue for each type — check the pinned/labeled `example` issues in the [Issues tab](../../issues) for a Bug, Feature, and Task example you can copy the structure from. Take what's relevant to your issue and leave out what isn't; not every field applies to every issue. 

There are no rules you have to follow regarding the templates, but it is **highly recommended**. This is to ensure that issues are well documented, easy to understand and pick up by others. Don't assume something is obvious — you already know the context behind this issue, but someone picking it up might not. **When in doubt, overexplain rather than underexplain.**
 
## Submitting a Pull Request
 
1. Make sure your branch is up to date with `main` before opening a PR:
```bash
git fetch origin
git rebase origin/main
```
2. Keep PRs **small and focused** — one bug fix or one feature per PR is much easier to review than a large bundle of unrelated changes.
3. Write a clear PR description: what you changed, why, and which issue it relates to (e.g. `Closes #12`).
4. If your change isn't finished yet but you want early feedback, open it as a **draft PR**.
5. Be responsive to review comments — feedback is about the code, not about you. Everyone's PRs get review comments; it's a normal part of the process, not a sign something went wrong.

## Code Style
 
- Follow existing formatting/naming conventions in the codebase.
- Keep functions and views focused — one responsibility per function where reasonable.
- Comment non-obvious logic, but don't over-comment self-explanatory code.

**Formatting:** We use [Black](https://black.readthedocs.io/) to auto-format code. It's included in `requirements.txt`, so it's installed automatically as part of your setup. Run it locally before committing:
```bash
black .
```
 
**Linting:** Pylint runs automatically in CI on every push (via GitHub Actions) and must score **7/10 or higher** to pass. You can run it locally first to catch issues early:
```bash
pylint --load-plugins pylint_django --django-settings-module=ifiplatform_project.settings --ignore-paths=ifiplatform/.*/migrations $(git ls-files '*.py')
```

 
## Questions?
 
If anything here is unclear, open an issue with **Type: Task** and label `docs` — improving this guide for the next contributor is a contribution too.

Else, send a mail to one of the core team:
- (coming) E-mail to contactperson

When in doubt, ask Claude