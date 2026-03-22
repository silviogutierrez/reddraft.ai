#!/usr/bin/env bash

set -e

PWD=$(pwd)

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT=$(realpath "$SCRIPT_PATH/../")

SERVER=1
CLIENT=1
INFRASTRUCTURE=1

while [[ "$#" -gt 0 ]]; do
    case $1 in
    --server)
        SERVER=1
        CLIENT=0
        INFRASTRUCTURE=0
        shift
        ;;
    --client)
        SERVER=0
        CLIENT=1
        INFRASTRUCTURE=0
        shift
        ;;
    --infrastructure)
        SERVER=0
        CLIENT=0
        INFRASTRUCTURE=1
        shift
        ;;
    *)
        echo "Unknown parameter passed: $1" >&2
        exit 1
        ;;
    esac
done

FAILED=0

cd "$PROJECT_ROOT"

run() {
    echo -n "Running $*..."
    if OUTPUT=$("$@" 2>&1); then
        echo " ok"
    else
        echo " FAILED"
        printf '%s\n' "$OUTPUT"
        FAILED=1
    fi
}

if [[ $SERVER -eq 1 ]]; then
    run ruff check --force-exclude .
    run ruff format --force-exclude --check .
    run mypy --no-incremental .
    run python manage.py makemigrations --dry-run --check
fi

if [[ $CLIENT -eq 1 ]]; then
    run npm exec eslint -- .
    run npm exec prettier -- --ignore-path .gitignore --check '**/*.{js,jsx,ts,tsx,yaml,yml,json,md}'
    run npm exec tsc
fi

if [[ $INFRASTRUCTURE -eq 1 ]]; then
    mapfile -t SH_FILES < <(git ls-files --exclude-standard '*.sh')
    mapfile -t NIX_FILES < <(git ls-files --exclude-standard '*.nix')

    if [[ ${#SH_FILES[@]} -gt 0 ]]; then
        run shellcheck -x "${SH_FILES[@]}"
        run shfmt -d "${SH_FILES[@]}"
    fi

    if [[ ${#NIX_FILES[@]} -gt 0 ]]; then
        run nixfmt -c "${NIX_FILES[@]}"
    fi
fi

cd "$PWD"
exit $FAILED
