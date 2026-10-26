# ifi hide <file>, ifi unhide <file>, and ifi check's list of hidden files

t_hide_makes_git_ignore_a_file() {
    clone_as contributor
    echo "scratch" >docs/scratch.md
    cd docs
    run_ifi hide scratch.md
    succeeds
    has "✓ Added /docs/scratch.md to .git/info/exclude"
    same "$(git status --porcelain)" "" "git status"
    run_ifi hide scratch.md
    has "scratch.md is hidden already."
    [[ "$(grep -c scratch ../.git/info/exclude)" -eq 1 ]] || fail "the line should be there once"
}

t_hide_refuses_a_tracked_file() {
    clone_as contributor
    run_ifi hide README.md
    fails
    has "Git tracks README.md, so hiding it does nothing."
    has "ifi undo-file README.md"
}

t_unhide_shows_the_file_to_git_again() {
    clone_as contributor
    echo "scratch" >scratch.md
    run_ifi hide scratch.md
    run_ifi unhide scratch.md
    succeeds
    has "✓ Removed /scratch.md from .git/info/exclude"
    same "$(git status --porcelain)" "?? scratch.md" "git status"
}

t_unhide_says_where_else_a_file_is_ignored() {
    clone_as contributor
    echo "*.log" >.gitignore
    echo "log" >debug.log
    run_ifi unhide debug.log
    has "debug.log isn't hidden with ifi hide."
    has "Git ignores it because of: .gitignore:1:*.log"
}

t_check_lists_hidden_files() {
    clone_as contributor
    echo "scratch" >scratch.md
    run_ifi hide scratch.md
    run_ifi check
    has "Git ignores these on this computer only (ifi hide): scratch.md"
    has "ifi unhide <file>"
}
