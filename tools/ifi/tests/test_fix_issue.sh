# ifi fix-issue <nr>

CARDS=ifiplatform/static/css/cards.css

t_fix_issue_names_the_branch_after_the_issue() {
    clone_as contributor
    issue 5 Bug "Gjør kortene oransje på forsiden!"
    run_ifi fix-issue 5
    succeeds
    has "Issue #5: Gjør kortene oransje på forsiden!"
    same "$(git branch --show-current)" "bug/gjor-kortene-oransje-pa" "branch"
    same "$(git config branch.bug/gjor-kortene-oransje-pa.ifi-issue)" 5 "linked issue"
    same "$(git rev-parse HEAD)" "$(git rev-parse upstream/main)" "starts from"
    git rev-parse --verify --quiet "@{u}" >/dev/null && fail "the branch shouldn't track upstream/main"
    return 0
}

t_fix_issue_accepts_a_hash() {
    clone_as contributor
    issue 5 Task "Tidy up"
    run_ifi fix-issue "#5"
    succeeds
    same "$(git branch --show-current)" "task/tidy-up" "branch"
}

t_fix_issue_wants_a_number() {
    clone_as contributor
    run_ifi fix-issue abc
    fails
    has "Which issue? For example: ifi fix-issue 42"
}

t_fix_issue_asks_for_the_type_when_the_issue_has_none() {
    clone_as contributor
    issue 5 "" "Orange cards"
    IN=$'idk\nFeature\n' run_ifi fix-issue 5
    succeeds
    same "$(git branch --show-current)" "feature/orange-cards" "branch"
}

t_fix_issue_asks_everything_without_github() {
    clone_as contributor
    IFI_GITHUB_API=http://127.0.0.1:1 IN=$'task\nOrange event cards!\n' run_ifi fix-issue 5
    succeeds
    has "Couldn't look up issue #5 on GitHub"
    same "$(git branch --show-current)" "task/orange-event-cards" "branch"
}

t_fix_issue_says_when_it_is_a_pull_request() {
    clone_as contributor
    issue 7 Bug "Someone's pull request" "" pr
    run_ifi fix-issue 7
    fails
    has "#7 is a pull request, not an issue"
    same "$(git branch --show-current)" main "branch"
}

t_fix_issue_switches_back_to_the_issues_branch() {
    clone_as contributor
    issue 5 Bug "Orange cards"
    run_ifi fix-issue 5
    git switch --quiet main
    run_ifi fix-issue 5
    succeeds
    has "Issue #5 already has a branch: bug/orange-cards."
    same "$(git branch --show-current)" "bug/orange-cards" "branch"
    same "$(git branch --list 'bug/*' | wc -l | tr -d ' ')" 1 "number of bug branches"
}

t_fix_issue_says_when_main_moved_on() {
    clone_as contributor
    issue 5 Bug "Orange cards"
    run_ifi fix-issue 5
    teammate docs/other.md "Other"
    run_ifi fix-issue 5
    succeeds
    has "You're already on bug/orange-cards"
    has "has 1 new commit(s)"
    has "ifi update"
}

t_fix_issue_brings_changes_made_on_main() {
    clone_as contributor
    issue 5 Bug "Orange cards"
    echo "changed" >>README.md
    run_ifi fix-issue 5
    succeeds
    has "The changes you had on main came along to it."
    same "$(git status --porcelain)" " M README.md" "unsaved changes"
}

t_fix_issue_stops_with_unsaved_changes_on_another_branch() {
    clone_as contributor
    issue 5 Bug "Orange cards"
    issue 6 Bug "Blue cards"
    run_ifi fix-issue 5
    echo "changed" >>README.md
    run_ifi fix-issue 6
    fails
    has "You have changes on bug/orange-cards that aren't committed yet."
    same "$(git branch --show-current)" "bug/orange-cards" "branch"
}

t_fix_issue_adds_upstream_when_it_is_missing() {
    clone_as contributor no-upstream
    issue 5 Bug "Orange cards"
    run_ifi fix-issue 5
    succeeds
    same "$(git config remote.upstream.url)" "https://github.com/$MAIN.git" "upstream"
}

t_fix_issue_adds_the_number_when_the_name_is_taken() {
    clone_as contributor
    issue 5 Bug "Orange cards"
    issue 6 Bug "Orange cards"
    run_ifi fix-issue 5
    git switch --quiet main
    run_ifi fix-issue 6
    succeeds
    same "$(git branch --show-current)" "bug/orange-cards-6" "branch"
}

# A second clone of your fork, as on another computer: cd's into it.
other_computer() {
    git clone --quiet "https://github.com/$STUDENT/$NAME.git" "$SANDBOX/laptop"
    cd "$SANDBOX/laptop" || exit 1
    git remote add upstream "https://github.com/$MAIN.git"
}

t_fix_issue_goes_on_with_the_branch_from_another_computer() {
    clone_as contributor
    start_issue
    commit "$CARDS" ".event-card { background: orange; }" "Orange cards"
    run_ifi pull-request
    other_computer
    IN=$'y\n' run_ifi fix-issue 5
    succeeds
    has "There's already a branch called bug/orange-cards on GitHub."
    has '"Orange cards", by Student Testesen'
    same "$(git branch --show-current)" "bug/orange-cards" "branch"
    same "$(cat "$CARDS")" ".event-card { background: orange; }" "your work"
    same "$(git config branch.bug/orange-cards.ifi-issue)" 5 "linked issue"
}

t_fix_issue_makes_a_new_branch_when_the_one_on_github_isnt_yours() {
    clone_as contributor
    start_issue
    commit "$CARDS" ".event-card { background: orange; }"
    run_ifi pull-request
    other_computer
    IN=$'n\n' run_ifi fix-issue 5
    succeeds
    same "$(git branch --show-current)" "bug/orange-cards-5" "branch"
    same "$(git rev-parse HEAD)" "$(git rev-parse upstream/main)" "starts from"
}

t_fix_issue_offers_a_branch_made_with_plain_git() {
    clone_as contributor
    issue 5 Bug "Orange cards"
    git switch --quiet -c bug/orange-cards
    commit "$CARDS" ".event-card { background: orange; }"
    git switch --quiet main
    IN=$'y\n' run_ifi fix-issue 5
    succeeds
    has "There's already a branch called bug/orange-cards here, not linked to an issue."
    same "$(git branch --show-current)" "bug/orange-cards" "branch"
    same "$(git config branch.bug/orange-cards.ifi-issue)" 5 "linked issue"
}

t_fix_issue_for_a_collaborator_starts_from_origin() {
    clone_as collaborator
    issue 5 Bug "Orange cards"
    teammate docs/other.md "Other"
    run_ifi fix-issue 5
    succeeds
    same "$(git rev-parse HEAD)" "$(git rev-parse origin/main)" "starts from"
    git remote get-url upstream >/dev/null 2>&1 && fail "a collaborator doesn't need upstream"
    return 0
}

# Unsaved changes on the issue-5 branch, a new file among them, with issue 6
# waiting.
changes_on_issue_5() {
    clone_as contributor
    start_issue
    issue 6 Bug "Blue cards"
    echo "changed" >>README.md
    echo "idea" >notes.txt
}

t_fix_issue_stops_for_unsaved_changes() {
    changes_on_issue_5
    run_ifi fix-issue 6
    fails
    has "You have changes on bug/orange-cards that aren't committed yet."
    same "$(git branch --show-current)" "bug/orange-cards" "branch"
    same "$(tail -n 1 README.md)" "changed" "README.md"
}

t_fix_issue_for_the_branch_you_are_on_keeps_your_changes() {
    changes_on_issue_5
    run_ifi fix-issue 5
    succeeds
    has "You're already on bug/orange-cards"
    same "$(tail -n 1 README.md)" "changed" "README.md"
}
