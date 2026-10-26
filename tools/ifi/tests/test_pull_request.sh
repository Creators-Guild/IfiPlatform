# ifi pull-request

t_pull_request_pushes_to_your_fork_and_gives_the_link() {
    clone_as contributor
    start_issue
    commit README.md "Better readme"
    run_ifi pull-request
    succeeds
    has "✓ Sent your branch to your fork on GitHub"
    has "https://github.com/$MAIN/compare/main...$STUDENT:bug/orange-cards?expand=1"
    has "Merged on GitHub?"
    same "$(git ls-remote origin refs/heads/bug/orange-cards | cut -f1)" "$(git rev-parse HEAD)" "the branch on your fork"
    same "$(git rev-parse --abbrev-ref '@{u}')" "origin/bug/orange-cards" "tracks"
}

t_pull_request_link_for_a_collaborator() {
    clone_as collaborator
    start_issue
    commit README.md "Better readme"
    run_ifi pull-request
    succeeds
    has "https://github.com/$MAIN/compare/main...bug/orange-cards?expand=1"
}

t_pull_request_asks_for_the_issue_when_the_branch_has_none() {
    clone_as contributor
    git switch --quiet -c feature/my-own
    commit README.md "Better readme"
    IN=$'#9\n' run_ifi pull-request
    succeeds
    has "write #9 on its \"Closes #\" line"
    same "$(git config branch.feature/my-own.ifi-issue)" 9 "linked issue"
}

t_pull_request_refuses_unsaved_changes() {
    clone_as contributor
    start_issue
    echo "x" >>README.md
    run_ifi pull-request
    fails
    has "These changes aren't committed yet."
}

t_pull_request_refuses_a_branch_without_commits() {
    clone_as contributor
    start_issue
    run_ifi pull-request
    fails
    has "has no commits yet, so there's nothing to send"
}

t_pull_request_after_update_replaces_the_branch_on_github() {
    clone_as contributor
    start_issue
    commit README.md "Better readme"
    run_ifi pull-request
    teammate docs/other.md "Other"
    run_ifi update
    run_ifi pull-request
    succeeds
    has "Replaced your branch on GitHub with the updated one."
    same "$(git ls-remote origin refs/heads/bug/orange-cards | cut -f1)" "$(git rev-parse HEAD)" "the branch on your fork"
    [[ -z "$(git config branch.bug/orange-cards.ifi-before-update)" ]] || fail "should forget the old branch tip"
}

t_pull_request_never_overwrites_someone_elses_push() {
    clone_as contributor
    start_issue
    commit README.md "Better readme"
    run_ifi pull-request
    # Someone pushes to your branch on GitHub (or presses "Update branch").
    git clone --quiet "https://github.com/$STUDENT/$NAME.git" "$SANDBOX/other"
    (cd "$SANDBOX/other" && git switch --quiet bug/orange-cards && echo "theirs" >theirs.md &&
        git add -A && git commit --quiet -m "Their commit" && git push --quiet origin HEAD)
    theirs="$(git ls-remote origin refs/heads/bug/orange-cards | cut -f1)"
    teammate docs/other.md "Other"
    run_ifi update
    run_ifi pull-request
    fails
    has "Your branch on GitHub has commits that aren't on your computer"
    has '  "Their commit", by Student Testesen'
    hasnt "Replace your branch on GitHub with this version?"
    same "$(git ls-remote origin refs/heads/bug/orange-cards | cut -f1)" "$theirs" "the branch on your fork"
}

# Pushed, then the commit message changed with --amend: same changes, new commit.
amended_after_push() {
    clone_as contributor
    start_issue
    commit README.md "Better readme" "Readme"
    run_ifi pull-request
    git commit --quiet --amend -m "Better readme"
}

t_pull_request_replaces_commits_you_rewrote_when_asked() {
    amended_after_push
    IN=$'y\n' run_ifi pull-request
    succeeds
    has "Your branch on GitHub has older versions of your commits"
    has "✓ Replaced your branch on GitHub with this version."
    same "$(git ls-remote origin refs/heads/bug/orange-cards | cut -f1)" "$(git rev-parse HEAD)" "the branch on your fork"
}

t_pull_request_keeps_commits_you_rewrote_when_you_say_no() {
    amended_after_push
    before="$(git ls-remote origin refs/heads/bug/orange-cards | cut -f1)"
    IN=$'n\n' run_ifi pull-request
    fails
    has "Nothing was sent."
    same "$(git ls-remote origin refs/heads/bug/orange-cards | cut -f1)" "$before" "the branch on your fork"
}

# On the issue-5 branch with a commit, and other changes stashed for it.
commit_and_stashed_changes() {
    clone_as contributor
    start_issue
    commit README.md "Better readme"
    echo "more" >>docs/notes.md
    git stash push --quiet -m "ifi: bug/orange-cards"
}

t_pull_request_stops_for_stashed_changes() {
    commit_and_stashed_changes
    run_ifi pull-request
    fails
    has "You have stashed changes for bug/orange-cards. They aren't in your pull request."
    has "Get them back first: ifi fix-issue 5"
    [[ -z "$(git ls-remote origin refs/heads/bug/orange-cards)" ]] || fail "nothing should be sent"
}

t_pull_request_sends_without_stashed_changes_when_asked() {
    commit_and_stashed_changes
    IN=$'y\n' run_ifi pull-request
    succeeds
    same "$(git ls-remote origin refs/heads/bug/orange-cards | cut -f1)" "$(git rev-parse HEAD)" "the branch on your fork"
}

t_pull_request_without_an_issue_when_you_press_enter() {
    clone_as contributor
    git switch --quiet -c task/small-fix
    commit README.md "# Better"
    IN=$'\n' run_ifi pull-request
    succeeds
    same "$(git config branch.task/small-fix.ifi-issue)" none "linked issue"
    has "There's no issue, so delete the \"Closes #\" line"
    commit README.md "# Even better"
    run_ifi pull-request
    succeeds
    hasnt "Which issue number"
}
