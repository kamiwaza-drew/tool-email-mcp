# Code Style Rules

## Principles
YAGNI: Build only what's required now
KISS: Simplest solution wins
DRY: Extract on third occurrence
INCREMENTAL: Working skeleton first

## Size Limits
FUNCTION: 30 lines max
FILE: 200 lines max
CLASS: 5 public methods max
TASK: 2-4 hours max
COMMIT: 30 minutes max

## Python Patterns
TYPE_HINTS: def process(data: list[str]) -> dict[str, Any]
PATHLIB: from pathlib import Path
CONTEXT_MANAGERS: with open('file.txt') as f:
ASYNC: async/await throughout

## JavaScript/TypeScript Patterns
ASYNC: const data = await fetchData()
OPTIONAL_CHAINING: obj?.nested?.value ?? defaultValue
EXPLICIT_TYPES: function process(data: string[]): Promise<Result>

## Bash Patterns
STRICT_MODE: set -euo pipefail
QUOTE_VARS: echo "${VAR}"
CHECK_COMMANDS: command -v git >/dev/null 2>&1 || exit 1

## Task Management
ONE_TASK: Complete before starting next
VERTICAL_SLICES: UI → API → DB for one feature
CHECKPOINT: Every 30 minutes (pwd, git status, test)
SEARCH_FIRST: grep -r "pattern" . before creating

## Git Workflow
SMALL_COMMITS: git add -p && git commit -m "Add specific feature"
MESSAGE_FORMAT: "Add user validation", not "Update code"
NO_AI_REFERENCES: Never mention Claude/AI in commits

## Quality Gates
BEFORE_CODING: Task defined, code searched, tests planned
STOP_IF: File >200 lines, function >30 lines, scope creep
BEFORE_COMMIT: Tests pass, lint passes, scope verified

## Red Flags
PHRASES: "base class", "all endpoints first", "fix tests later"
ACTIONS: Creating without searching, premature abstraction, multiple tasks