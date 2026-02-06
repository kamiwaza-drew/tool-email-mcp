#!/usr/bin/env bash
# Post-edit hook for Python linting and type checking
# Uses ruff for linting/formatting and mypy for type checking

set -euo pipefail

FILE_PATH="${CLAUDE_TOOL_ARG_FILE_PATH:-}"

# Skip if no file path or not a Python file
if [[ -z "$FILE_PATH" ]] || [[ ! "$FILE_PATH" =~ \.py$ ]]; then
    exit 0
fi

# Skip if file doesn't exist (was deleted)
if [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# Skip test files, migrations, and generated files
if [[ "$FILE_PATH" =~ (__pycache__|\.pyc|migrations/|\.egg-info/) ]]; then
    exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

ERRORS=()

# Run ruff check (linting)
if command -v ruff &>/dev/null; then
    echo "Running ruff check on $FILE_PATH..."
    if ! ruff check "$FILE_PATH" 2>&1; then
        ERRORS+=("ruff check found issues")
    fi

    # Run ruff format check (don't auto-fix, just report)
    echo "Checking ruff format on $FILE_PATH..."
    if ! ruff format --check "$FILE_PATH" 2>&1; then
        ERRORS+=("ruff format: file needs formatting (run 'ruff format $FILE_PATH')")
    fi
else
    echo "Warning: ruff not found, skipping lint check"
fi

# Run mypy for type checking (only if file is in a typed package)
if command -v mypy &>/dev/null; then
    # Check if there's a py.typed marker or mypy config covers this file
    if [[ -f "pyproject.toml" ]] || [[ -f "mypy.ini" ]] || [[ -f ".mypy.ini" ]]; then
        echo "Running mypy on $FILE_PATH..."
        # Use --no-error-summary to reduce noise, ignore missing imports for flexibility
        if ! mypy "$FILE_PATH" --ignore-missing-imports --no-error-summary 2>&1; then
            ERRORS+=("mypy found type errors")
        fi
    fi
fi

# Report results
if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo ""
    echo "=== Lint/Type Issues Found ==="
    for err in "${ERRORS[@]}"; do
        echo "  - $err"
    done
    exit 1
fi

echo "Python checks passed for $FILE_PATH"
exit 0
