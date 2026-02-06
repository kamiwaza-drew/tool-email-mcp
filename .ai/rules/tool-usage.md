# Tool Usage - Shell Commands & MCPs

## Shell Tools

### File Operations
FIND_FILES: fd [pattern] [path]
FIND_TEXT: rg [pattern] [path]
FIND_CODE: ast-grep run --lang [lang] -p '[pattern]'
SELECT: pipe to fzf for interactive selection

### Code Structure Search (ast-grep)
TYPESCRIPT: ast-grep run --lang ts -p '[pattern]'
TSX_REACT: ast-grep run --lang tsx -p '[pattern]'
JAVASCRIPT: ast-grep run --lang js -p '[pattern]'
PYTHON: ast-grep run --lang python -p '[pattern]'
SHELL: ast-grep run --lang bash -p '[pattern]'

### Pattern Examples
```bash
# Find function definitions
ast-grep run --lang ts -p 'function $NAME($$$) { $$$ }'

# Find React components
ast-grep run --lang tsx -p 'export function $COMP() { $$$ }'

# Find class methods
ast-grep run --lang python -p 'def $METHOD(self, $$$): $$$'

# Find exported functions
ast-grep run --lang js -p 'export const $NAME = ($$$) => $$$'
```

### Selection Workflow
```bash
# Find and select file
fd '\.tsx$' | fzf

# Find and select code match
ast-grep run --lang tsx -p 'useState' | fzf

# Find text and select
rg 'pattern' | fzf
```

### Data Formats
JSON: jq '.field' file.json
YAML: yq '.field' file.yaml
XML: yq -p xml '.field' file.xml

### Diff and Merge
DIFF: difft file1 file2
MERGE_CONFLICTS: mergiraf

### GitHub CLI (gh)
```bash
# Issues
gh issue list
gh issue create --title "Title" --body "Body"
gh issue view [number]

# Pull Requests
gh pr list
gh pr create --title "Title" --body "Body"
gh pr view [number]
gh pr checkout [number]
gh pr merge [number]

# Repository
gh repo view
gh repo clone [owner/repo]
gh repo create [name]

# Workflow
gh run list
gh run view [id]
gh run watch [id]
```

### Tool Preference
1. ast-grep for code structure (when available)
2. rg for plain text search
3. fd for file names
4. fzf for interactive selection
5. gh for GitHub operations

## MCP Tools

### context7 (Documentation)
USE: Fetch up-to-date library documentation
```python
# 1. Resolve library ID
resolve-library-id(libraryName="react")

# 2. Get documentation
get-library-docs(
    context7CompatibleLibraryID="/facebook/react",
    topic="hooks",
    tokens=5000
)
```
WHEN: Need current API docs, examples, best practices

### sequential-thinking (Complex Reasoning)
USE: Multi-step problem solving with revision
```python
sequentialthinking(
    thought="Current step in reasoning",
    thoughtNumber=1,
    totalThoughts=5,
    nextThoughtNeeded=true
)
```
WHEN: Complex architecture decisions, debugging, planning
PATTERN: Break down problem, revise as needed, iterate

### playwright (Browser Automation)
USE: Web scraping, testing, automation
```python
# Navigate
browser_navigate(url="https://example.com")

# Snapshot for actions
browser_snapshot()

# Click element
browser_click(element="button", ref="ref-from-snapshot")

# Fill form
browser_fill_form(fields=[...])

# Take screenshot
browser_take_screenshot(filename="page.png")
```
WHEN: Need to interact with web pages, test UIs

### MCP vs Shell Tools
AST_GREP: Code structure search
CONTEXT7: Library documentation
SEQUENTIAL_THINKING: Complex reasoning
PLAYWRIGHT: Browser automation
GH_CLI: GitHub operations

## Tool Selection Matrix

| Task | Primary Tool | Alternative |
|------|-------------|-------------|
| Find files | fd | find |
| Find text | rg | grep |
| Find code | ast-grep run | rg |
| Select item | fzf | - |
| JSON query | jq | - |
| YAML query | yq | - |
| Diff files | difft | diff |
| Merge conflicts | mergiraf | git mergetool |
| GitHub ops | gh | - |
| Library docs | context7 MCP | web search |
| Complex reasoning | sequential-thinking MCP | - |
| Browser tasks | playwright MCP | puppeteer |

## Anti-Patterns
AVOID: grep for code structure (use ast-grep)
AVOID: find for file search (use fd)
AVOID: awk/sed for JSON (use jq)
AVOID: grep for YAML keys (use yq)
AVOID: Manual GitHub API calls (use gh)

## Quick Reference
```bash
# Code search
ast-grep run --lang [ts|tsx|js|python|bash] -p 'pattern'

# Text search
rg 'pattern' --type [ts|py|md]

# File search
fd 'pattern' --extension [ts|py|md]

# Interactive selection
command | fzf

# Structured data
jq '.path.to.field' file.json
yq '.path.to.field' file.yaml

# Diff with syntax highlighting
difft file1 file2

# Resolve merge conflicts
mergiraf

# GitHub operations
gh [issue|pr|repo|run] [command]
```