# Access and handover

Last updated: 2026-10-27

Every account and key the project depends on, who controls it, and what
to do when someone joins or leaves. If the only person with access to one
of these leaves without handing it over, that part of the project is lost.

**This repo is public.** Write roles and where to check, never passwords,
keys, tokens or personal contact details.

## Accounts and access

Fill in the blanks. "Owner" is the account that can add and remove other
people. "Who has access" is where to look up the current list, since a
list of names here would go out of date.

| System | Used for | Owner | Who has access: where to check |
| ------ | -------- | ----- | ------------------------------ |
| NREC project | Both VMs, the backup volumes, security groups | Hanna K. K. Niemi (`hkkniemi`) | NREC dashboard → project members |
| SSH, platform VM | Logging in to the server, deploys | Hanna K. K. Niemi (`hkkniemi`) | `~/.ssh/authorized_keys` on the server |
| SSH, analytics VM | Umami server | Hanna K. K. Niemi (`hkkniemi`) | `~/.ssh/authorized_keys` on that server |
| GitHub `Creators-Guild` | Code, issues, Actions, secrets | Hanna K. K. Niemi (`hkkniemi`) | Org → People, repo → Settings → Collaborators |
| Domain `ifiplattform.no` | DNS for the site and `stats.` | Hanna K. K. Niemi (`hkkniemi`), at _(fill in: registrar)_ | _(fill in)_ |
| Email (SMTP) | Account verification emails | Hanna K. K. Niemi (`hkkniemi`), at _(fill in: provider)_ | _(fill in)_ |
| DeepL | Machine translation | Hanna K. K. Niemi (`hkkniemi`) | DeepL account → team members |
| Umami | Traffic statistics | Hanna K. K. Niemi (`hkkniemi`) | Umami → Settings → Users |
| Trello | Board that mirrors GitHub issues | Hanna K. K. Niemi (`hkkniemi`) | Trello board → members |
| Wagtail admin | Editing the site | Site superusers | Wagtail admin → Settings → Users |
| Let's Encrypt | HTTPS certificates, expiry warnings | Hanna K. K. Niemi (`hkkniemi`) | `sudo certbot show_account` on the server |
| Figma | Design files | Hanna K. K. Niemi (`hkkniemi`) | Figma → file/team sharing |
| _(add any missing)_ | | | |

**Where the shared secrets are kept:** _(fill in, for example a shared
password manager)_. The server's `.env` must never be the only copy: if
the VM is lost, so are the values (see
[backups_and_recovery.md](backups_and_recovery.md#what-is-not-covered)).

### GitHub secrets

The deploy secrets are in the `production` environment (repo → Settings →
Environments → `production`). The Trello secrets are repository secrets
(Settings → Secrets and variables → Actions).

| Secret | Where | Used by | Comes from |
| ------ | ----- | ------- | ---------- |
| `SERVER_IP` | `production` environment | `deploy.yml` | The platform VM's IP in NREC |
| `SERVER_USER` | `production` environment | `deploy.yml` | `ubuntu` |
| `SSH_PRIVATE_KEY` | `production` environment | `deploy.yml` | The deploy key; its public half is in `authorized_keys` on the server |
| `TRELLO_KEY`, `TRELLO_TOKEN` | Repository secrets | `trello_sync.yml` | The Trello account above |

The deploy key logs in as `ubuntu`, which has full sudo, so **this secret
gives root access to the server**. That's why it's in the environment
(see the next section).

## Protecting `main` and the deploy key

Nobody can read a secret in GitHub's settings, but a workflow can use it.
With repository secrets, anyone with write access could push a branch
with their own workflow, and GitHub would hand it the deploy key. Three
settings together close that.

**1. The `production` environment** (Settings → Environments) holds the
deploy secrets. Under "Deployment branches and tags", only `main` is
allowed, so a workflow on any other branch is refused the secrets. The
deploy job in `deploy.yml` asks for them with `environment: production`.
Don't turn on "Required reviewers" or "Wait timer": the nightly deploy
would then wait for someone to approve it.

**2. A ruleset on `main`** (Settings → Rules → Rulesets). Without it,
someone could push their workflow straight to `main` and get the secrets
anyway. The rules:

- Require a pull request before merging, with:
  - 1 required approval
  - "Dismiss stale approvals when new commits are pushed", so nobody can
    add a commit after the approval
  - "Require approval of the most recent reviewable push"
  - "Require review from Code Owners"
- Require status checks to pass (the CI jobs)
- Block force pushes
- Restrict deletions
- Bypass list: **Repository admin**, mode "For pull requests only". This
  lets a maintainer who works alone merge their own pull requests.
  Rulesets can't name a single person, so **every repo admin can skip
  these rules**. Only maintainers get the Admin role.

**3. `.github/CODEOWNERS`** lists who must approve changes to `/.github/`
(the workflows, and the file itself) and `/deploy/` (the deploy script,
backups and server config), on top of the normal approval. GitHub reads
the file from `main`, not from the pull request, so nobody can add
themselves on their own branch. A line with a misspelled username, or a
person without write access, is skipped without warning: after changing
the file, open it on GitHub, which shows any errors at the top.

## Adding a person

Only give what the role needs. An editor needs a Wagtail account, not SSH.

- [ ] **GitHub:** add to the `Creators-Guild` org or as a repo
      collaborator, with the lowest role that works. Admin is for
      maintainers only, since admins can skip the rules on `main`.
- [ ] **SSH** (maintainers only): ask for their *public* key and add it on
      its own line:
      ```bash
      nano ~/.ssh/authorized_keys                # add one line: ssh-ed25519 AAAA... name
      ```
      Put their name or handle at the end of the line, so you know whose key
      it is when removing it later. Have them test logging in before you
      close your own session.
      Key pairs in the NREC dashboard are only copied in when a VM is
      *created*. Changing them there does nothing to a running VM, so SSH
      access is always managed in `authorized_keys`.
- [ ] **NREC** (maintainers only): add them to the project.
- [ ] **Wagtail admin:** create the account, or promote their existing one,
      in Settings → Users.
- [ ] **Other accounts** from the table, only as needed.
- [ ] **Shared secrets:** give access to where they're kept, never by chat
      or email.

## Removing a person

Do this the same week someone leaves, even on good terms.

- [ ] **GitHub:** remove them from the org or repo, and from
      `.github/CODEOWNERS`.
- [ ] **SSH:** delete their line from `~/.ssh/authorized_keys` on **both**
      VMs.
- [ ] **NREC:** remove them from the project.
- [ ] **Wagtail admin and Umami:** deactivate their accounts.
- [ ] **Other accounts** from the table: remove them.
- [ ] **If they owned an account** (domain, DeepL, email, Trello): transfer
      ownership *before* they leave (see [Handover](#handover)).
- [ ] **Replace shared secrets they knew.** They may have copies. At least:
  - [ ] the **deploy key** (see below), if they were a repo admin or had
        the key
  - [ ] `DJANGO_SECRET_KEY`, `DB_PASSWORD`, `DEEPL_API_KEY`,
        `EMAIL_HOST_PASSWORD` in `.env`, if they had server access.
        After changing `.env`, run `sudo systemctl restart gunicorn`.
        A new `DB_PASSWORD` also has to be set in PostgreSQL:
        `sudo -u postgres psql -c "ALTER USER ifiplatform_user PASSWORD '<new>';"`
  - [ ] the Trello token, if it was theirs

Changing `DJANGO_SECRET_KEY` logs everyone out and invalidates any
password reset links that are still open, which is harmless.

### Replacing the deploy key

On your own computer:

```bash
ssh-keygen -t ed25519 -f ifiplatform_deploy -C "github-actions-deploy-<yyyy-mm>"   # no passphrase
```

The date in the comment tells the new key's line in `authorized_keys`
apart from the old one.

1. On the server, add the contents of `ifiplatform_deploy.pub` as a new
   line in `~/.ssh/authorized_keys`.
2. In GitHub, go to Settings → Environments → `production` and set the
   `SSH_PRIVATE_KEY` secret to the contents of `ifiplatform_deploy` (the
   file without `.pub`).
3. Run the deploy workflow by hand to check that it works.
4. Delete the old deploy key's line from `authorized_keys`.
5. Delete both key files from your computer.

## Handover

When the current maintainers are about to leave the project:

- [ ] Every account in the table has at least **two** people with owner
      access, and at least one of them is staying.
- [ ] Ownership of the domain, NREC project and GitHub org is transferred
      to someone who is staying, or to an organisation (such as the
      student group or UiO) rather than a personal account.
- [ ] The new maintainers have logged in to the server, run a deploy and
      read [prod_server.md](prod_server.md),
      [backups_and_recovery.md](backups_and_recovery.md) and
      [server_setup.md](server_setup.md).
- [ ] Payment details on any paid account (domain, DeepL, email) are
      moved, so nothing expires unnoticed.
- [ ] `.github/CODEOWNERS` names at least one maintainer who is staying.
      Otherwise nobody can merge changes to `/.github/` or `/deploy/`.
- [ ] The repo admins are the maintainers who are staying, since every
      admin can skip the rules on `main` (see
      [Protecting `main` and the deploy key](#protecting-main-and-the-deploy-key)).
- [ ] The table above is up to date, and the date at the top is changed.
