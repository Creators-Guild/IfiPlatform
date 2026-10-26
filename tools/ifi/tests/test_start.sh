# ifi start <type> <few words>

t_start_makes_a_branch_without_an_issue() {
    clone_as contributor
    run_ifi start docs Fix typo in the readme
    succeeds
    same "$(git branch --show-current)" "docs/fix-typo-in-the" "branch"
    same "$(git config branch.docs/fix-typo-in-the.ifi-issue)" none "linked issue"
    same "$(git rev-parse HEAD)" "$(git rev-parse upstream/main)" "starts from"
    has "it won't ask for an issue"
}

t_start_wants_a_known_type() {
    clone_as contributor
    run_ifi start chore tidy up
    fails
    has "Which type? One of: bug feature task docs ci"
    same "$(git branch --show-current)" main "branch"
}

t_start_wants_a_few_words() {
    clone_as contributor
    run_ifi start ci
    fails
    has "A few words about it"
}

t_start_refuses_a_branch_you_have() {
    clone_as contributor
    run_ifi start ci Faster tests
    git switch --quiet main
    run_ifi start ci Faster tests
    fails
    has "You already have a branch called ci/faster-tests."
}

t_start_then_pull_request_doesnt_ask_for_an_issue() {
    clone_as contributor
    run_ifi start docs Fix typo
    commit README.md "# The project, fixed"
    run_ifi pull-request
    succeeds
    hasnt "Which issue number"
    has "There's no issue, so delete the \"Closes #\" line"
}
