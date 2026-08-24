# docs/claude_context/ — what this is

This folder holds implementation-level design rationale for Claude (or any
AI agent) working in this codebase — not for human contributors. If you're
a person reading this, you probably don't need to be here; see the root
[README.md](../../README.md) and [CONTRIBUTING.md](../../CONTRIBUTING.md)
instead.

## Why this exists

Several files in `ifiplatform/ifi_home_app/` used to carry very long inline
comments and docstrings — multi-paragraph explanations of *why* a piece of
code looks the way it does: edge cases it handles, history behind a
decision, gotchas that'd cause a silent bug if "cleaned up" without
understanding them. That level of detail is genuinely useful context for an
AI making changes to the code, but it made the code itself harder for a
human to read at a glance.

The fix: keep the code short and readable, and move the deeper "why" here
instead. Each source file that needs it links to its notes with a one-line
pointer, e.g.:

```python
"""Per-block style overrides and their effective-value resolution.

Design rationale/history: docs/claude_context/article_block_style.md"""
```

## How this differs from docs/claude_references/

[docs/claude_references/](../claude_references/readme.md) holds AI-drafted
**starting points for human docs** — meant to eventually be rewritten by
hand into something real and published (README-style guides, project-goals
writeups). This folder is the opposite: it's not a draft of anything, and
it isn't meant to "graduate" into a human-facing doc. It's permanent,
technical, and written for an AI's working context — think of it as the
extended footnotes a human reader would skip but an agent editing the code
should read first.

## Conventions

- One file per source file or tightly-related cluster of files, named
  after what it documents (e.g. `event_models.md` for
  `ifi_home_app/models/event_models.py`, `article_style_and_page_mixins.md`
  for the two files it covers together).
- The source file itself gets a short pointer comment/docstring back here
  — never the reverse-only link. A reader starting from the code should
  always be one line away from finding the deeper context; a reader
  starting here doesn't need to be pointed back.
- Write for an agent that hasn't seen this conversation: state the file/
  function/field being discussed by name, not "this" or "the above."
- When you trim a comment out of a source file into one of these notes,
  keep enough in the code to know *that* deeper context exists and where —
  never leave a change with zero trace, since that's indistinguishable
  from the reasoning simply never having been written down.
- If a note here goes stale (the code it describes changed and the
  rationale no longer applies), fix or delete it — a wrong note is worse
  than no note.
- Not everything moves here. A short comment that's genuinely necessary
  to understand non-obvious or complicated logic right where it happens —
  a tricky edge case, a non-obvious ordering requirement, a gotcha —
  still belongs in the code itself. This folder is for the longer *why*
  and history that isn't needed just to read and safely modify the code;
  it isn't a place to default every comment to.

## Running the test suite

Don't reflexively run `manage.py test` after every change. For a small or
purely cosmetic edit — CSS (spacing, alignment, color), copy/text changes,
comment/docstring-only edits, template markup that doesn't touch template
logic — running the full suite (or even a scoped one) burns real time and
resources for a change the suite was never going to catch anything in.
Save it for changes that could actually break something: model/field
changes, template *logic* (a new `{% if %}`, a changed queryset/property),
view/command behavior, migrations. When in doubt, running one quick,
narrowly-scoped test is cheaper than the full suite.
