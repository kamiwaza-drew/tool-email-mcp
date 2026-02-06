#!/usr/bin/env bash
# Post-edit hook for TypeScript/JavaScript linting and type checking
# Uses eslint for linting and tsc for type checking

set -euo pipefail

FILE_PATH="${CLAUDE_TOOL_ARG_FILE_PATH:-}"

# Skip if no file path or not a JS/TS file
if [[ -z "$FILE_PATH" ]] || [[ ! "$FILE_PATH" =~ \.(ts|tsx|js|jsx|mjs|cjs)$ ]]; then
    exit 0
fi

# Skip if file doesn't exist (was deleted)
if [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# Skip node_modules, dist, build directories
if [[ "$FILE_PATH" =~ (node_modules|dist/|build/|\.next/) ]]; then
    exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Find the nearest package.json to determine project root
find_package_root() {
    local dir
    dir=$(dirname "$FILE_PATH")
    while [[ "$dir" != "/" ]] && [[ "$dir" != "." ]]; do
        if [[ -f "$dir/package.json" ]]; then
            echo "$dir"
            return 0
        fi
        dir=$(dirname "$dir")
    done
    return 1
}

PACKAGE_ROOT=$(find_package_root) || {
    # No package.json found, skip JS/TS checks
    exit 0
}

cd "$PACKAGE_ROOT"

ERRORS=()

# Run eslint if available
if [[ -f "node_modules/.bin/eslint" ]] || command -v eslint &>/dev/null; then
    ESLINT_BIN="${PACKAGE_ROOT}/node_modules/.bin/eslint"
    [[ -x "$ESLINT_BIN" ]] || ESLINT_BIN="eslint"

    echo "Running eslint on $FILE_PATH..."
    if ! "$ESLINT_BIN" "$FILE_PATH" 2>&1; then
        ERRORS+=("eslint found issues")
    fi
elif [[ -f "biome.json" ]] || [[ -f "biome.jsonc" ]]; then
    # Biome as alternative
    BIOME_BIN="${PACKAGE_ROOT}/node_modules/.bin/biome"
    if [[ -x "$BIOME_BIN" ]]; then
        echo "Running biome on $FILE_PATH..."
        if ! "$BIOME_BIN" check "$FILE_PATH" 2>&1; then
            ERRORS+=("biome found issues")
        fi
    fi
fi

# Run TypeScript type check for .ts/.tsx files
if [[ "$FILE_PATH" =~ \.(ts|tsx)$ ]]; then
    if [[ -f "tsconfig.json" ]]; then
        TSC_BIN="${PACKAGE_ROOT}/node_modules/.bin/tsc"
        [[ -x "$TSC_BIN" ]] || TSC_BIN="tsc"

        if command -v "$TSC_BIN" &>/dev/null || [[ -x "$TSC_BIN" ]]; then
            echo "Running tsc type check..."
            # --noEmit to only check types, not compile
            if ! "$TSC_BIN" --noEmit 2>&1; then
                ERRORS+=("tsc found type errors")
            fi
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

echo "TypeScript/JavaScript checks passed for $FILE_PATH"
exit 0
