#!/usr/bin/env bash

set -e

ESLINT_FAILED=0
RUFF_FAILED=0
MYPY_FAILED=0
PWD=$(pwd)

# https://stackoverflow.com/a/246128
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT=$(realpath "$SCRIPT_PATH/../")

CHANGED_FILES=()
ALL=0
REMOTES=$(git remote)

while [[ "$#" -gt 0 ]]; do
    case $1 in
    --files)
        shift
        if [[ "$#" -eq 0 || "$1" =~ ^-- ]]; then
            echo "Error: --files option requires at least one file argument." >&2
            exit 1
        fi
        while [[ "$#" -gt 0 && ! "$1" =~ ^-- ]]; do
            CHANGED_FILES+=("$1")
            shift
        done
        continue
        ;;
    --all)
        ALL=1
        shift
        ;;
    *)
        echo "Unknown parameter passed: $1" >&2
        exit 1
        ;;
    esac
done

if [[ $ALL -eq 1 ]]; then
    echo "Running against all git files"
    mapfile -t CHANGED_FILES < <(git ls-files --exclude-standard | while read -r f; do [ -f "$f" ] && echo "$f"; done)
elif [[ ${#CHANGED_FILES[@]} -gt 0 ]]; then
    echo "Specific files run: running against ${CHANGED_FILES[*]}"
elif [[ $REMOTES == "" ]]; then
    echo "No origin, running against all git files"
    mapfile -t CHANGED_FILES < <(git ls-files --exclude-standard | while read -r f; do [ -f "$f" ] && echo "$f"; done)
elif [ -z "$ORIGIN" ]; then
    if [ "$GITHUB_BASE_REF" != "" ]; then
        TARGET_BRANCH="origin/$GITHUB_BASE_REF"
        echo "PR event: running against base branch $TARGET_BRANCH"
    elif [ "$GITHUB_EVENT_NAME" = "push" ]; then
        TARGET_BRANCH=$(git rev-parse HEAD~1)
        echo "Push event: running against previous commit $TARGET_BRANCH"
    else
        TARGET_BRANCH="origin/main"
        echo "Local run: running against default branch $TARGET_BRANCH"
    fi

    target_ref=$(git merge-base "$TARGET_BRANCH" HEAD)
    mapfile -t CHANGED_FILES < <(git diff --name-only --diff-filter d --relative "$target_ref")
else
    echo "Invalid fix options"
    exit 1
fi

# Filter into typed arrays
mapfile -t CHANGED_PY_FILES < <(printf '%s\n' "${CHANGED_FILES[@]}" | grep -E '\.pyi?$' || true)
mapfile -t CHANGED_PRETTIER_FILES < <(printf '%s\n' "${CHANGED_FILES[@]}" | grep -E '\.(jsx?|tsx?|ya?ml|json|md)$' || true)
mapfile -t CHANGED_TS_JS_FILES < <(printf '%s\n' "${CHANGED_FILES[@]}" | grep -E '\.(jsx?|tsx?)$' || true)
mapfile -t CHANGED_SH_FILES < <(printf '%s\n' "${CHANGED_FILES[@]}" | grep -E '\.sh$' || true)
mapfile -t CHANGED_NIX_FILES < <(printf '%s\n' "${CHANGED_FILES[@]}" | grep -E '\.nix$' || true)

echo "[Python]:"
printf '%s\n' "${CHANGED_PY_FILES[@]}"
echo ""
echo "[Prettier]:"
printf '%s\n' "${CHANGED_PRETTIER_FILES[@]}"
echo ""
echo "[TypeScript/JS]:"
printf '%s\n' "${CHANGED_TS_JS_FILES[@]}"
echo ""
echo "[Shell]:"
printf '%s\n' "${CHANGED_SH_FILES[@]}"
echo ""
echo "[Nix]:"
printf '%s\n' "${CHANGED_NIX_FILES[@]}"
echo ""

cd "$PROJECT_ROOT"

if [[ ${#CHANGED_PY_FILES[@]} -gt 0 ]]; then
    ruff check --force-exclude --fix "${CHANGED_PY_FILES[@]}" || true

    ruff format --force-exclude "${CHANGED_PY_FILES[@]}" || true

    if ! ruff check --force-exclude "${CHANGED_PY_FILES[@]}"; then
        echo "ruff check failed or found issues."
        RUFF_FAILED=1
    fi

    if ! mypy "${CHANGED_PY_FILES[@]}"; then
        echo "mypy failed or found issues."
        MYPY_FAILED=1
    fi
fi

if [[ ${#CHANGED_TS_JS_FILES[@]} -gt 0 ]]; then
    if ! npm exec eslint -- --fix "${CHANGED_TS_JS_FILES[@]}"; then
        echo "ESLint failed or found issues."
        ESLINT_FAILED=1
    fi
fi

if [[ ${#CHANGED_PRETTIER_FILES[@]} -gt 0 ]]; then
    npm exec prettier -- --ignore-path .gitignore --write "${CHANGED_PRETTIER_FILES[@]}" || true
fi

if [[ ${#CHANGED_SH_FILES[@]} -gt 0 ]] && command -v shellcheck &>/dev/null; then
    set +e
    SHELLCHECK_DIFF_OUTPUT=$(shellcheck -x -f diff "${CHANGED_SH_FILES[@]}")
    shellcheck_exit_code=$?
    set -e

    if [ $shellcheck_exit_code -ne 0 ]; then
        if [ -z "$SHELLCHECK_DIFF_OUTPUT" ]; then
            echo "Shellcheck: Non-fixable issues found."
            echo "Running shellcheck to display issues (please fix manually):"
            shellcheck "${CHANGED_SH_FILES[@]}" || true
            ESLINT_FAILED=1
        else
            echo "$SHELLCHECK_DIFF_OUTPUT" | git apply --allow-empty || true
        fi
    fi

    shfmt -w "${CHANGED_SH_FILES[@]}" || true
fi

if [[ ${#CHANGED_NIX_FILES[@]} -gt 0 ]] && command -v nixfmt &>/dev/null; then
    nixfmt "${CHANGED_NIX_FILES[@]}" || true
fi

cd "$PWD"
exit $((ESLINT_FAILED || RUFF_FAILED || MYPY_FAILED))
