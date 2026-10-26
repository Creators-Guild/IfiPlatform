# ifi cleanup

# Your issue-5 branch, sent as a pull request and merged by a teammate.
merged_issue_branch() {
    clone_as contributor
    start_issue
    commit README.md "Better readme"
    run_ifi pull-request
    merge_pull_request bug/orange-cards
    git switch --quiet main
}

t_cleanup_deletes_merged_branches_here_and_on_your_fork() {
    merged_issue_branch
    IN=$'y\n' run_ifi cleanup
    succeeds
    has "These branches are merged into main"
    has "They're on your fork on GitHub too"
    git show-ref --verify --quiet refs/heads/bug/orange-cards && fail "should be deleted on your computer"
    [[ -z "$(git ls-remote origin refs/heads/bug/orange-cards)" ]] || fail "should be deleted on your fork"
}

t_cleanup_asks_first() {
    merged_issue_branch
    IN=$'n\n' run_ifi cleanup
    fails
    has "Nothing was deleted."
    git show-ref --verify --quiet refs/heads/bug/orange-cards || fail "should still be there"
}

t_cleanup_keeps_branches_that_arent_merged() {
    merged_issue_branch
    issue 6 Bug "Blue cards"
    run_ifi fix-issue 6
    commit docs/notes.md "Blue"
    git switch --quiet main
    IN=$'y\n' run_ifi cleanup
    succeeds
    git show-ref --verify --quiet refs/heads/bug/blue-cards || fail "bug/blue-cards isn't merged, so it should stay"
}

t_cleanup_keeps_a_new_branch_without_commits() {
    merged_issue_branch
    issue 6 Bug "Blue cards"
    run_ifi update
    run_ifi fix-issue 6
    git switch --quiet main
    IN=$'y\n' run_ifi cleanup
    hasnt "bug/blue-cards"
    git show-ref --verify --quiet refs/heads/bug/blue-cards ||
        fail "bug/blue-cards was just made and has no work yet, so it should stay"
}

t_cleanup_lists_backups_on_their_own() {
    clone_as contributor
    start_issue
    commit README.md "Better readme"
    commit docs/notes.md "Oops"
    run_ifi undo-file docs/notes.md
    merge_pull_request bug/orange-cards
    git switch --quiet main
    IN=$'n\n' run_ifi cleanup
    has "And these backups from ifi undo-file"
}

t_cleanup_with_nothing_to_clean() {
    clone_as contributor
    start_issue
    commit README.md "Better readme"
    run_ifi cleanup
    succeeds
    has "Nothing to clean up"
}

t_cleanup_switches_you_off_a_merged_branch() {
    merged_issue_branch
    git switch --quiet bug/orange-cards
    IN=$'y\n' run_ifi cleanup
    succeeds
    has "bug/orange-cards   (you're on it, so ifi switches you to main first)"
    has "✓ Switched to main, since bug/orange-cards is merged"
    has "Want another issue?"
    same "$(git branch --show-current)" main "branch"
    git show-ref --verify --quiet refs/heads/bug/orange-cards && fail "bug/orange-cards should be deleted"
    return 0
}

t_cleanup_keeps_a_merged_branch_with_unsaved_changes() {
    merged_issue_branch
    git switch --quiet bug/orange-cards
    echo "new work" >>docs/notes.md
    IN=$'y\n' run_ifi cleanup
    succeeds
    has "Nothing to clean up"
    has "bug/orange-cards is merged too, but it has changes that aren't saved"
    same "$(git branch --show-current)" bug/orange-cards "branch"
}

t_cleanup_makes_main_again_when_it_is_gone() {
    merged_issue_branch
    git switch --quiet bug/orange-cards
    git branch --quiet -D main
    IN=$'y\n' run_ifi cleanup
    succeeds
    has "✓ Switched to a new main"
    same "$(git branch --show-current)" main "branch"
    same "$(git rev-parse HEAD)" "$(git rev-parse upstream/main)" "main"
}

t_cleanup_doesnt_call_a_new_branch_merged() {
    clone_as contributor
    start_issue
    run_ifi cleanup
    succeeds
    hasnt "which is merged"
}

t_cleanup_names_changes_put_aside() {
    merged_issue_branch
    git switch --quiet bug/orange-cards
    echo "more" >>docs/notes.md
    git stash push --quiet -m "ifi: bug/orange-cards"
    git switch --quiet main
    IN=$'y\n' run_ifi cleanup
    succeeds
    has "bug/orange-cards has changes put aside. They're kept after it's deleted: git stash show -p stash@{0}"
    same "$(git stash list | wc -l | tr -d ' ')" 1 "stashes"
}

# Merges <branch> in the main repo into main, like GitHub's merge button.
merge_in_main_repo() {
    (
        cd "$SANDBOX/teammate" || exit 1
        git pull --quiet --rebase origin main
        git fetch --quiet origin "$1"
        git merge --quiet --no-ff -m "Merge $1" FETCH_HEAD
        git push --quiet origin main
    )
}

t_cleanup_deletes_only_your_merged_branches_in_the_main_repo() {
    clone_as collaborator
    (cd "$SANDBOX/teammate" && git switch --quiet -c task/theirs && echo "theirs" >theirs.md &&
        git add -A && git commit --quiet -m "Theirs" && git push --quiet origin HEAD && git switch --quiet main)
    merge_in_main_repo task/theirs
    start_issue
    commit README.md "Better readme"
    git push --quiet -u origin HEAD
    merge_in_main_repo bug/orange-cards
    git switch --quiet main
    IN=$'y\n' run_ifi cleanup
    succeeds
    has "They're on the main repo on GitHub too"
    [[ -z "$(git ls-remote origin refs/heads/bug/orange-cards)" ]] || fail "should be deleted in the main repo"
    [[ -n "$(git ls-remote origin refs/heads/task/theirs)" ]] || fail "a teammate's branch you don't have should stay"
}

t_cleanup_skips_branches_already_deleted_on_github() {
    merged_issue_branch
    git push --quiet origin --delete bug/orange-cards
    git update-ref refs/remotes/origin/bug/orange-cards HEAD
    IN=$'y\n' run_ifi cleanup
    succeeds
    hasnt "on your fork on GitHub"
    git show-ref --verify --quiet refs/heads/bug/orange-cards && fail "should be deleted on your computer"
    return 0
}
