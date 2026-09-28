# docs/

Project documentation beyond the main [README.md](../README.md). Each
folder holds one kind of document. When you add a new doc, put it in the
folder whose description fits, and add a line for it below.

## architecture/ — how the system is built

- [tech_stack.md](architecture/tech_stack.md): languages, frameworks,
  database, external services and GitHub workflows
- [frontend.md](architecture/frontend.md): how HTML templates and CSS are
  organized, loaded and written
- [eraser_links.md](architecture/eraser_links.md): feature concept map

## operations/ — how it runs in production

- [prod_server.md](operations/prod_server.md): the NREC server, deploy
  flow, security and routine checks
- [server_toolbox.md](operations/server_toolbox.md): how to use journalctl,
  systemctl, Nginx logs and friends to track down problems on the server
- [management_commands.md](operations/management_commands.md): this
  project's custom `manage.py` commands

## contributing/ — how to contribute (not created yet)

Guides for contributors beyond the basics in
[CONTRIBUTING.md](../CONTRIBUTING.md): reviewing, writing content, writing
docs, testing. See [Planned docs](#planned-docs) below.

## design/ — UI and visual design

- [figma_links.md](design/figma_links.md): Figma files

## claude_context/ — implementation notes for AI agents

Design rationale behind specific features, kept out of code comments. See
[claude_context/readme_claude.md](claude_context/readme_claude.md).

## claude_references/ — AI-drafted starting points

Drafts to finish by hand, not final docs. See
[claude_references/readme.md](claude_references/readme.md).

## Planned docs

Docs the project is missing, most important first. When you write one,
tick it off here and add it to its folder's list above in the same PR.

### Operations: do these first

These are the risky gaps. If the server is lost or the maintainer leaves,
nobody can recover without them.

- [ ] `operations/backups_and_recovery.md`: what is backed up (PostgreSQL
  and `media/`), how often, where the copies are stored *outside* the VM,
  and step-by-step restore. Test a restore at least once.
- [ ] `operations/server_setup.md`: how to rebuild the server from zero:
  packages, PostgreSQL user and database, venv, `.env`, `gunicorn.service`,
  the Nginx site config, Certbot, fail2ban jails, sudo scope and NREC
  security groups. Consider also checking these config files into `deploy/`.
- [ ] `operations/access_and_handover.md`: who has access to what (NREC
  project, SSH keys, GitHub admin and secrets, domain/DNS, DeepL, Umami,
  Peoply, email) and how to add or remove a person.
- [ ] `operations/incidents.md`: what to do when production breaks:
  rolling back a bad deploy, pausing the nightly deploy, who to tell.
- [ ] `SECURITY.md` (repo root): how to report a security problem
  privately. GitHub shows it on the repo's Security tab.

### Community and governance

- [ ] `CODE_OF_CONDUCT.md` (repo root): expected behaviour, and who
  handles reports.
- [ ] `GOVERNANCE.md` (repo root): the roles (moved from CONTRIBUTING.md),
  how someone becomes Collaborator or Committer, how decisions are made,
  and what happens when the current maintainers leave.
- [ ] `contributing/code_review.md`: checklist and tone for reviewers, and
  what a PR needs before it can be approved.
- [ ] `contributing/content_guide.md`: for non-developers: writing and
  translating articles in the Wagtail admin, editor terms, images.
- [ ] `contributing/writing_docs.md`: finished version of
  [claude_references/writing_guidelines.md](claude_references/writing_guidelines.md).
- [ ] Finished version of
  [claude_references/community_goals.md](claude_references/community_goals.md),
  either in the main README's "About" section or as its own doc.
- [ ] `.github/pull_request_template.md`: what changed, why, linked
  issue, how it was tested. There are issue templates but no PR template.

### Developer guides

- [ ] `architecture/overview.md`: how the apps and the Wagtail page tree
  fit together, the main models, and the path from request to view to
  template.
- [ ] `architecture/translations.md`: the Norwegian/English workflow end to
  end: wagtail-localize, DeepL and its glossary,
  `makemessages`/`compilemessages`, locale aliases.
- [ ] `contributing/testing.md`: running tests, writing new ones, and
  adding a new app to the test list in `ci.yml`.
- [ ] `operations/privacy_and_data.md`: which personal data is stored,
  where, and for how long (for example, unverified accounts are deleted
  after 7 days), and how to handle a deletion request. Backs up the public
  privacy policy page.

### Small fixes to existing docs

- [ ] [CONTRIBUTING.md](../CONTRIBUTING.md): pylint runs on pull requests
  to `main`, not on every push. The contact email is still "(coming)".
  Typo: "how high value".
- [ ] [TUTORIALS.md](../TUTORIALS.md): links JavaScript and React
  tutorials, but the project uses neither framework. Swap in Wagtail and
  PostgreSQL resources.
