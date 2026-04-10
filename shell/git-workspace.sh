# git-workspace shell integration
#
# Source this file in your shell config to enable cd behavior for commands
# that return a path (up, rm).
#
# bash/zsh:
#   source /path/to/git-workspace/shell/git-workspace.sh
#
# The function shadows the `git-workspace` binary. Commands that output a
# navigable path (up, rm) will cd to it automatically; all other commands
# pass through unchanged.

git-workspace() {
    local cmd="${1:-}"
    case "$cmd" in
        up|rm)
            local path exit_code
            path=$(command git-workspace "$@")
            exit_code=$?
            if [ $exit_code -eq 0 ] && [ -d "$path" ]; then
                cd "$path"
            fi
            return $exit_code
            ;;
        *)
            command git-workspace "$@"
            ;;
    esac
}
