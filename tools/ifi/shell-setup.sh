# Sourced by the dev container's ~/.bashrc (Dockerfile.dev), and without
# Docker by the line `ifi install` adds to the venv's activate script, so
# only while the venv is active: Tab completion for ifi and manage.py, a
# "(container)" mark in the container's prompt, a hint in every new
# terminal, and a setup check in the first one. Works in bash 3.2 too (a
# Mac), so no mapfile. In zsh (a Mac's default) only Tab completion and
# the hint.

# Only for terminals you type in: scp, rsync and scripts break when a
# non-interactive shell prints anything, and some ~/.bashrc files don't stop
# those before the line that loads this.
[[ $- == *i* ]] || return 0

if [[ -n "${ZSH_VERSION:-}" ]]; then
    # zsh runs bash completions through bashcompinit, which needs compinit.
    (( $+functions[compdef] )) || { autoload -Uz compinit && compinit -u; }
    autoload -Uz bashcompinit && bashcompinit
fi

# ${COMP_WORDS[@]:i:1}: counts from 0 in zsh too, where COMP_WORDS[i] doesn't.
_ifi_complete() {
    local cur="${COMP_WORDS[@]:COMP_CWORD:1}" first="${COMP_WORDS[@]:1:1}" words=""
    if [[ $COMP_CWORD -eq 1 ]]; then
        words="help check fix-issue save update pull-request undo-file cleanup test migrate restart-server reset-database rebuild-docker install account"
    elif [[ $COMP_CWORD -eq 2 && "$first" == help ]]; then
        words="git docker django ifi"
    elif [[ $COMP_CWORD -eq 2 && "$first" == update ]]; then
        words="--abort"
    elif [[ $COMP_CWORD -eq 2 && "$first" == account ]]; then
        words="switch"
    fi
    COMPREPLY=($(compgen -W "$words" -- "$cur"))
}
complete -o default -F _ifi_complete ifi

# Tab completion for manage.py's commands (ours too) and their options:
# Django lists them itself when DJANGO_AUTO_COMPLETE is set, but pip's
# Django leaves out the script that hooks it up. Each Tab starts Django,
# so it takes about a second. For `manage.py`, `./manage.py` and
# `py`/`python`/`python3 manage.py`. Any other python command goes to the
# completion python had (bash-completion's: options, -m modules), loaded
# now since it's normally loaded on the first Tab. zsh keeps its own
# python completion, so there only `py` and `manage.py` get this.
_ifi_python_complete=""
if [[ -z "${ZSH_VERSION:-}" ]]; then
    declare -F _comp_load >/dev/null && _comp_load python 2>/dev/null
    _ifi_python_complete="$(complete -p python 2>/dev/null | sed -n 's/.* -F \([^ ]*\) .*/\1/p')"
fi
_ifi_manage_py_complete() {
    local python=python script="${COMP_WORDS[@]:0:1}" skip=0
    if [[ "$script" != *manage.py ]]; then
        python="$script" script="${COMP_WORDS[@]:1:1}" skip=1
        if [[ "$script" != *manage.py || $COMP_CWORD -lt 2 ]]; then
            [[ -n "$_ifi_python_complete" ]] && "$_ifi_python_complete" "$@"
            return 0
        fi
    fi
    # tr: Python on Windows ends lines with \r\n.
    COMPREPLY=($(COMP_WORDS="${COMP_WORDS[*]:skip}" COMP_CWORD=$((COMP_CWORD - skip)) \
        DJANGO_AUTO_COMPLETE=1 "$python" "$script" 2>/dev/null | tr -d '\r'))
}
complete -o default -F _ifi_manage_py_complete manage.py ./manage.py py
[[ -n "${ZSH_VERSION:-}" ]] || complete -o default -F _ifi_manage_py_complete python python3

# The branch you're on, for the prompt: "$1" with %s as the name, like
# printf. Nothing outside this project (the check common.sh does) or on a
# detached HEAD.
_ifi_branch() {
    local top b
    top="$(git rev-parse --show-toplevel 2>/dev/null)" || return 0
    [[ -f "$top/tools/ifi/ifi" ]] || return 0
    b="$(git branch --show-current 2>/dev/null)" || return 0
    [[ -n "$b" ]] && printf "$1" "$b"
    return 0
}

# The prompt shows where a terminal runs (inside the container, ifi and the
# site's Python are there; on your own computer, your GitHub login is) and
# the branch you're on, so you notice before you commit to the wrong one:
#   (container) bug/orange-cards ~/ifiplatform $
# On your own computer the branch goes in front of your own prompt, unless
# it already shows one (Git Bash's does). zsh's prompt works differently,
# so it's left alone there.
if [[ -n "${ZSH_VERSION:-}" ]]; then
    :
elif [[ -f /.dockerenv ]]; then
    PS1='\[\e[1;35m\](container)\[\e[0m\]\[\e[1;33m\]$(_ifi_branch " %s")\[\e[0m\] \w \$ '
elif [[ "$PS1" != *__git_ps1* && "$PS1" != *_ifi_branch* ]]; then
    PS1='\[\e[1;33m\]$(_ifi_branch "(%s) ")\[\e[0m\]'"$PS1"
fi

# The rest only in a terminal you can see. VS Code also starts a hidden
# shell when it connects to the container, to read the environment: it
# would take the setup check below, and nobody would see it.
[[ -t 0 && -t 1 ]] || return 0

echo "Stuck? Type: ifi check (what's wrong) or ifi help (cheat sheets)"

# The first terminal after the container starts (or is rebuilt) checks the
# setup and shows only what's broken. Later terminals don't check again:
# they show the result of the last ifi check, with when it ran, and how to
# check again. VS Code sometimes replaces a new terminal by itself (when an
# extension changes its environment), so the first terminal's output can
# disappear. /dev/shm is emptied every time the container starts, and
# noclobber lets only one terminal run the check when VS Code opens several
# at once. IFI_STATE_DIR lets the tests (tests/) use a folder of their own.
_ifi_startup_check() {
    local dir="${IFI_STATE_DIR:-/dev/shm}" kind="" count when cmd=$'\e[36m' off=$'\e[0m'
    if (set -o noclobber; : >"$dir/ifi-checked") 2>/dev/null; then
        echo "Checking your setup..."
        ifi check --quiet
        return 0
    fi
    IFS='|' read -r kind count when <"$dir/ifi-check-result" 2>/dev/null
    case "$kind" in
        ok)
            echo "✅ Setup OK (checked $when)"
            printf '  Check again?  →  %sifi check%s\n' "$cmd" "$off"
            ;;
        bad)
            echo "❌ The setup check found $count problem(s) (checked $when)"
            printf '  See them?  →  %sifi check%s\n' "$cmd" "$off"
            ;;
        offline)
            echo "⚠️  The setup check couldn't reach GitHub (checked $when)"
            printf '  Check again?  →  %sifi check%s\n' "$cmd" "$off"
            ;;
        *)
            echo "The setup check is still running in another terminal."
            printf '  See it here?  →  %sifi check%s\n' "$cmd" "$off"
            ;;
    esac
}
if [[ -f /.dockerenv || -n "${IFI_STATE_DIR:-}" ]]; then
    _ifi_startup_check
fi
