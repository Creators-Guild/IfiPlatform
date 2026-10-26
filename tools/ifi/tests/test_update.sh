# ifi update, ifi update --abort

CARDS=ifiplatform/static/css/cards.css

t_update_when_already_up_to_date() {
    clone_as contributor
    start_issue
    commit "$CARDS" ".event-card { background: orange; }"
    run_ifi update
    succeeds
    has "Already up to date"
}

t_update_puts_your_commits_on_top_of_main() {
    clone_as contributor
    start_issue
    commit "$CARDS" ".event-card { background: orange; }"
    teammate docs/other.md "Other"
    run_ifi update
    succeeds
    has "Updated: bug/orange-cards now has the newest main"
    git merge-base --is-ancestor upstream/main HEAD || fail "main's new commit isn't in the branch"
    same "$(git rev-list --merges --count upstream/main..HEAD)" 0 "merge commits"
    [[ -n "$(git config branch.bug/orange-cards.ifi-before-update)" ]] ||
        fail "should remember where the branch was, for ifi pull-request"
}

t_update_refuses_unsaved_changes() {
    clone_as contributor
    start_issue
    echo "x" >>README.md
    run_ifi update
    fails
    has "Commit your changes first"
}

t_update_refuses_on_main() {
    clone_as contributor
    run_ifi update
    fails
    has "You're on main."
}

t_update_abort_without_an_update() {
    clone_as contributor
    start_issue
    run_ifi update --abort
    fails
    has "No update is running"
}

# Your commit and a teammate's both change the same line of cards.css.
conflict_on_cards() {
    clone_as contributor
    start_issue
    commit "$CARDS" ".event-card { background: orange; }" "Orange cards"
    teammate "$CARDS" ".event-card { background: blue; }"
}

t_update_explains_a_conflict() {
    conflict_on_cards
    run_ifi update
    fails
    has "Conflict! Someone else changed the same lines as you"
    has "This file needs it:"
    has "  $CARDS"
    has "ifi update --abort"
}

t_update_refuses_to_go_on_with_markers_left() {
    conflict_on_cards
    run_ifi update
    run_ifi update
    fails
    has "These files still have conflict markers"
    has "  $CARDS"
}

t_update_goes_on_after_the_conflict_is_fixed() {
    conflict_on_cards
    run_ifi update
    echo ".event-card { background: orange; }" >"$CARDS"
    run_ifi update
    succeeds
    has "Updated:"
    same "$(cat "$CARDS")" ".event-card { background: orange; }" "the fixed file"
    git merge-base --is-ancestor upstream/main HEAD || fail "main's commit isn't in the branch"
}

t_update_leaves_unrelated_new_files_out() {
    conflict_on_cards
    run_ifi update
    echo ".event-card { background: orange; }" >"$CARDS"
    echo "my own notes" >my-notes.txt
    run_ifi update
    succeeds
    git ls-files --error-unmatch my-notes.txt >/dev/null 2>&1 &&
        fail "my-notes.txt was never saved, so the update shouldn't commit it"
    [[ -f my-notes.txt ]] || fail "my-notes.txt should still be there"
}

t_update_abort_puts_the_branch_back() {
    conflict_on_cards
    before="$(git rev-parse HEAD)"
    run_ifi update
    run_ifi update --abort
    succeeds
    has "Back to how your branch was before the update."
    same "$(git rev-parse HEAD)" "$before" "the branch"
    same "$(git status --porcelain)" "" "unsaved changes"
}

# Two commits of yours that touch cards.css, and a teammate's change to it.
two_commits_and_a_conflict() {
    clone_as contributor
    start_issue
    commit "$CARDS" ".event-card { background: orange; }" "Orange cards"
    commit "$CARDS" ".event-card { background: darkorange; }" "Darker orange"
    teammate "$CARDS" ".event-card { background: blue; }"
}

t_update_asks_merge_or_rebase_with_several_commits() {
    two_commits_and_a_conflict
    IN=$'1\nn\n' run_ifi_tty update
    has "How do you want to do that?"
    has "Conflict!"
    git rev-parse --verify --quiet MERGE_HEAD >/dev/null || fail "choosing 1 should start a merge"
    echo ".event-card { background: darkorange; }" >"$CARDS"
    run_ifi update
    succeeds
    same "$(git rev-list --merges --count upstream/main..HEAD)" 1 "merge commits"
}

t_update_rebase_can_stop_once_per_commit() {
    two_commits_and_a_conflict
    IN=$'2\nn\n' run_ifi_tty update
    has "Conflict!"
    # A mix of both, so your next commit (orange -> darkorange) clashes too.
    echo ".event-card { background: purple; }" >"$CARDS"
    run_ifi update
    fails
    has "Another conflict, in your next commit (\"Darker orange\")."
    echo ".event-card { background: darkorange; }" >"$CARDS"
    run_ifi update
    succeeds
    same "$(git rev-list --count upstream/main..HEAD)" 2 "your commits"
}

t_update_shows_the_conflict_how_to() {
    conflict_on_cards
    IN=$'y\n' run_ifi_tty update
    has "Want help fixing it?"
    has "Take one file at a time."
    has "\"Current\" is main's version"
}

MIGRATIONS=ifiplatform/apps/x_app/migrations

t_update_says_when_both_added_a_migration() {
    clone_as contributor
    start_issue
    commit "$MIGRATIONS/0002_mine.py" "# mine"
    teammate "$MIGRATIONS/0002_theirs.py" "# theirs"
    run_ifi update
    succeeds
    has "You and main both added a database change (a migration) in:"
    has "  $MIGRATIONS"
    has "ifi migrate"
    same "$(git config branch.bug/orange-cards.ifi-migration-clash || true)" "" "remembered clash after the update"
}

t_update_quiet_about_migrations_in_different_apps() {
    clone_as contributor
    start_issue
    commit "$MIGRATIONS/0002_mine.py" "# mine"
    teammate ifiplatform/apps/y_app/migrations/0002_theirs.py "# theirs"
    run_ifi update
    succeeds
    hasnt "database change"
}

PO=ifiplatform/locale/nb/LC_MESSAGES/django.po
MO=ifiplatform/locale/nb/LC_MESSAGES/django.mo

# Writes $PO with these "text=translation" pairs, and its $MO.
po_file() {
    mkdir -p "$(dirname "$PO")"
    {
        printf '#\nmsgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n'
        local pair
        for pair in "$@"; do printf '\nmsgid "%s"\nmsgstr "%s"\n' "${pair%%=*}" "${pair#*=}"; done
    } >"$PO"
    msgfmt -o "$MO" "$PO"
}

# The teammate's translations, merged into main: teammate_po "text=translation" ...
teammate_po() {
    (
        cd "$SANDBOX/teammate" || exit 1
        git pull --quiet --rebase origin main
        po_file "$@"
        git add -A
        git commit --quiet -m "Teammate's translations"
        git push --quiet origin main
    )
}

# A fake manage.py (no Django here) whose compilemessages runs msgfmt.
translations_setup() {
    command -v msgcat >/dev/null && command -v msgfmt >/dev/null || skip "needs gettext (msgcat, msgfmt)"
    (
        cd "$SANDBOX/teammate" || exit 1
        cat >ifiplatform/manage.py <<'PY'
import glob, subprocess, sys

lang = sys.argv[sys.argv.index("-l") + 1]
for po in glob.glob(f"locale/{lang}/LC_MESSAGES/*.po"):
    subprocess.run(["msgfmt", "-o", po[:-3] + ".mo", po], check=True)
PY
        git add -A
        git commit --quiet -m "manage.py"
        git push --quiet origin main
    )
    teammate_po "Hello=Hei" "Cards=Kort"
    clone_as contributor
    mkdir -p venv/bin
    printf '#!/bin/sh\nexec python3 "$@"\n' >venv/bin/python
    chmod +x venv/bin/python
    echo /venv >>.git/info/exclude
    start_issue
}

has_both_translations() {
    grep -qF 'msgstr "Registrer deg"' "$PO" || fail "your new text is missing in $PO"
    grep -qF 'msgstr "Logg ut"' "$PO" || fail "main's new text is missing in $PO"
    grep -qF 'msgstr "Kortene"' "$PO" || fail "your translation of Cards should win"
    grep -qF 'msgstr "Kort"' "$PO" && fail "main's translation of Cards should be gone"
    msgunfmt "$MO" | grep -qF "Logg ut" || fail "$MO wasn't rebuilt"
    same "$(git status --porcelain)" "" "unsaved changes"
}

t_update_joins_clashing_translations() {
    translations_setup
    po_file "Hello=Hei" "Sign up=Registrer deg" "Cards=Kortene"
    git add -A
    git commit --quiet -m "Sign up"
    teammate_po "Hello=Hei" "Log out=Logg ut" "Cards=Kort"
    run_ifi update
    succeeds
    has "Only translation files clash, so ifi joins them for you."
    has "✓ Joined your nb translations with main's"
    has "✓ Rebuilt the nb .mo file"
    has "ifi joined these translation files for you"
    hasnt "Conflict!"
    has_both_translations
}

# Two commits of yours that change translations, and a teammate's.
two_translation_commits() {
    translations_setup
    po_file "Hello=Hei" "Sign up=Registrer deg" "Cards=Kort"
    git add -A
    git commit --quiet -m "Sign up"
    po_file "Hello=Hei" "Sign up=Registrer deg" "Cards=Kortene"
    git add -A
    git commit --quiet -m "Better Cards"
    teammate_po "Hello=Hei" "Log out=Logg ut" "Cards=Kort"
}

t_update_joins_translations_at_each_commit_of_a_rebase() {
    two_translation_commits
    IN=$'2\n' run_ifi_tty update
    has "Updated:"
    [[ "$(grep -c "Joined your nb translations" <<<"$OUT")" -eq 2 ]] || fail "should join once per commit"
    same "$(git rev-list --count upstream/main..HEAD)" 2 "your commits"
    has_both_translations
}

t_update_joins_translations_in_a_merge() {
    two_translation_commits
    IN=$'1\n' run_ifi_tty update
    has "How do you want to do that?"
    has "Joined your nb translations"
    has "Updated:"
    same "$(git rev-list --merges --count upstream/main..HEAD)" 1 "merge commits"
    has_both_translations
}

t_update_translations_and_other_files_get_the_usual_help() {
    translations_setup
    po_file "Hello=Hei" "Sign up=Registrer deg" "Cards=Kortene"
    commit "$CARDS" ".event-card { background: orange; }" "Sign up, orange cards"
    teammate_po "Hello=Hei" "Log out=Logg ut" "Cards=Kort"
    teammate "$CARDS" ".event-card { background: blue; }"
    run_ifi update
    fails
    has "Conflict!"
    has "  $PO"
    has "  $CARDS"
    hasnt "ifi joins them"
}

t_update_with_a_new_file_left_out() {
    clone_as contributor
    start_issue
    commit "$CARDS" ".event-card { background: orange; }"
    echo "scratch" >notes.txt
    teammate docs/other.md "Other"
    run_ifi update
    succeeds
    same "$(git status --porcelain)" "?? notes.txt" "git status"
}

t_update_other_commands_wait_for_the_conflict() {
    conflict_on_cards
    run_ifi update
    run_ifi save "Fixed"
    fails
    has "ifi update stopped at a conflict"
    run_ifi pull-request
    has "ifi update stopped at a conflict"
    run_ifi check
    has "ifi update stopped at a conflict"
}

t_update_save_doesnt_commit_markers_in_a_merge() {
    two_commits_and_a_conflict
    IN=$'1\nn\n' run_ifi_tty update
    before="$(git rev-parse HEAD)"
    run_ifi save "Fixed"
    fails
    has "ifi update stopped at a conflict"
    same "$(git rev-parse HEAD)" "$before" "the branch"
}

t_update_stopped_by_a_new_file_in_the_way() {
    clone_as contributor
    start_issue
    commit README.md "Readme"
    echo "mine" >docs/new.md
    teammate docs/new.md "theirs"
    run_ifi update
    fails
    hasnt "Conflict!"
    has "Git stopped the update before it changed anything."
    has "docs/new.md"
    same "$(git config branch.bug/orange-cards.ifi-before-update || true)" "" "remembered update"
}

t_update_refuses_staged_conflict_markers() {
    conflict_on_cards
    run_ifi update
    git add "$CARDS"
    run_ifi update
    fails
    has "These files still have conflict markers"
    has "  $CARDS"
}

t_update_says_not_to_use_vs_codes_sync_button() {
    clone_as contributor
    start_issue
    commit "$CARDS" ".event-card { background: orange; }"
    teammate docs/other.md "Other"
    run_ifi update
    succeeds
    has "not VS Code's Sync button"
}
