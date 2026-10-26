# ifi undo-file <file>

CARDS=ifiplatform/static/css/cards.css

t_undo_file_puts_a_file_back_as_in_main() {
    clone_as contributor
    start_issue
    commit "$CARDS" ".event-card { background: orange; }"
    commit README.md "Oops"
    run_ifi pull-request
    before="$(git rev-parse HEAD)"
    run_ifi undo-file README.md
    succeeds
    same "$(cat README.md)" "# The project" "README.md"
    same "$(cat "$CARDS")" ".event-card { background: orange; }" "the change you keep"
    same "$(git rev-parse bug/orange-cards-backup)" "$before" "the backup"
    same "$(git ls-remote origin refs/heads/bug/orange-cards | cut -f1)" "$(git rev-parse HEAD)" "pushed"
    same "$(git diff --name-only upstream/main...HEAD)" "$CARDS" "files in the pull request"
}

t_undo_file_takes_a_new_file_out_but_keeps_it() {
    clone_as contributor
    start_issue
    commit docs/extra.md "Extra"
    run_ifi undo-file docs/extra.md
    succeeds
    git ls-files --error-unmatch docs/extra.md >/dev/null 2>&1 && fail "docs/extra.md should be out of Git"
    [[ -f docs/extra.md ]] || fail "docs/extra.md should still be on your computer"
    same "$(git status --porcelain)" "?? docs/extra.md" "git status (untracked, not hidden)"
    has "ifi save asks before adding it again."
}

t_undo_file_with_a_file_git_doesnt_know() {
    clone_as contributor
    start_issue
    commit README.md "Oops"
    run_ifi undo-file no/such/file.txt
    fails
    has "Git doesn't know no/such/file.txt."
}

t_undo_file_when_the_file_is_unchanged() {
    clone_as contributor
    start_issue
    commit README.md "Oops"
    run_ifi undo-file docs/notes.md
    succeeds
    has "Nothing to undo: docs/notes.md is already the same as when your branch started."
}

t_undo_file_refuses_unsaved_changes() {
    clone_as contributor
    start_issue
    commit README.md "Oops"
    echo "x" >>docs/notes.md
    run_ifi undo-file README.md
    fails
    has "These changes aren't committed yet."
}

t_undo_file_keeps_one_backup_per_branch() {
    clone_as contributor
    start_issue
    commit README.md "Oops"
    commit docs/notes.md "Oops too"
    run_ifi undo-file README.md
    before="$(git rev-parse HEAD)"
    run_ifi undo-file docs/notes.md
    succeeds
    has "Moved your backup up to how your branch is now"
    same "$(git rev-parse bug/orange-cards-backup)" "$before" "the backup"
    git show-ref --verify --quiet refs/heads/bug/orange-cards-backup-2 && fail "there should be one backup"
    return 0
}

t_undo_file_makes_a_second_backup_after_a_rebase() {
    clone_as contributor
    start_issue
    commit README.md "Oops"
    commit docs/notes.md "Oops too"
    run_ifi undo-file README.md
    teammate docs/other.md "Other"
    run_ifi update
    run_ifi undo-file docs/notes.md
    succeeds
    git show-ref --verify --quiet refs/heads/bug/orange-cards-backup-2 ||
        fail "the first backup has commits the rebased branch lost, so it needs a -backup-2"
}


t_undo_file_after_main_changed_the_file() {
    clone_as contributor
    start_issue
    commit README.md "Oops"
    teammate README.md "# The project, newer"
    run_ifi undo-file README.md
    succeeds
    same "$(cat README.md)" "# The project" "README.md"
    same "$(git diff --name-only upstream/main...HEAD)" "" "files in the pull request"
}
