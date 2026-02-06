---
name: update-docs
description: Update documentation based on branch changes. Reviews commits since branch creation and updates docs/, .ai/, CLAUDE.md, and AGENTS.md files with production-grade quality. Takes time to do it right. Can delegate to sub-agents for large updates.
---

# Documentation Update Skill

This skill analyzes changes made on the current branch and produces **production-grade documentation** that reflects those changes.

## Quality Standards

**This skill prioritizes quality over speed.** Documentation is a critical artifact that developers and AI assistants rely on daily. Take the time needed to produce documentation that is:

### Production-Grade Requirements

| Quality Dimension | Requirement |
|-------------------|-------------|
| **Accuracy** | Every command, path, and example must be verified and working |
| **Completeness** | Cover all use cases, options, edge cases, and error conditions |
| **Structure** | Logical organization with clear headings, consistent formatting |
| **Clarity** | Unambiguous language, defined terms, no assumptions about reader knowledge |
| **Maintainability** | Easy to update, no duplicated information, clear ownership |

### Writing Excellence Standards

- **Be thorough** - Document the "why" not just the "what"
- **Be precise** - Use exact terminology consistently throughout
- **Be instructional** - Guide readers step-by-step through processes
- **Be anticipatory** - Address common questions and pitfalls proactively
- **Be professional** - Write as if this documentation represents the organization

### Do Not Rush

- Read existing documentation thoroughly before making changes
- Understand the full context of what changed and why
- Draft, review, and revise documentation before finalizing
- Verify all examples and commands actually work
- Consider how documentation fits into the larger documentation ecosystem

---

## Delegating to Sub-Agents

For large documentation updates, partition the work and delegate to specialized sub-agents. This enables parallel work and focused expertise.

### When to Delegate

Delegate when the documentation update involves:
- **3+ distinct areas** (e.g., scripts, apps, and architecture)
- **Multiple document types** (e.g., AI context + human docs + extension docs)
- **Significant new features** requiring comprehensive documentation
- **Major refactoring** affecting many existing documents

### Delegation Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    update-docs (coordinator)                 │
│  - Analyzes branch changes                                   │
│  - Creates documentation plan                                │
│  - Partitions work by area/type                             │
│  - Delegates to sub-agents                                   │
│  - Reviews and integrates results                           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ AI Context    │   │ Human Docs    │   │ Extension     │
│ Agent         │   │ Agent         │   │ Docs Agent    │
│               │   │               │   │               │
│ - CLAUDE.md   │   │ - docs/       │   │ - apps/*/     │
│ - AGENTS.md   │   │ - README.md   │   │ - tools/*/    │
│ - .ai/        │   │               │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
```

### Sub-Agent Task Template

When delegating, provide each sub-agent with:

```markdown
## Documentation Task: [Area Name]

### Context
- Branch: [branch-name]
- Changes summary: [what changed]
- Commits: [relevant commit hashes]

### Scope
Files to update:
- [file1.md]
- [file2.md]

Files to create (if needed):
- [new-file.md]

### Quality Requirements
- Production-grade documentation
- Follow style guide for [AI/Human/Extension] documents
- Verify all examples work
- Cross-reference related documentation

### Specific Instructions
[Detailed guidance for this particular area]

### Deliverables
- Updated/created files
- Summary of changes made
- Any issues or questions encountered
```

### Launching Sub-Agents

Use the Task tool to launch documentation sub-agents:

```
Task: "Update AI context documentation for registry-v2 changes"
Subagent: general-purpose
Prompt: [Include full task template above]
```

### Integrating Sub-Agent Results

After sub-agents complete:
1. Review each deliverable for quality standards
2. Check for consistency across documents
3. Verify cross-references are correct
4. Ensure no duplicate or conflicting information
5. Make final integration edits as needed

---

## Documentation Types and Writing Styles

| Document Type | Location | Audience | Style |
|---------------|----------|----------|-------|
| AI Context | `.ai/`, `CLAUDE.md`, `AGENTS.md` | AI assistants | Terse, structured, keyword-rich, no prose |
| Repo Docs | `docs/`, `README.md` | Human developers | Comprehensive, instructional, with examples |
| Extension Docs | `apps/*/docs/`, `tools/*/docs/` | End users | Clear, task-oriented, step-by-step |

### AI Context Documents

**Purpose:** Enable AI assistants to quickly understand and operate within the codebase.

**Style requirements:**
- Structured formats (tables, key-value pairs, bullet lists)
- Lead with commands and examples
- Omit articles (a, an, the) where possible
- Use imperative mood
- No pleasantries or transitions
- Maximum information density

**Quality bar:** An AI assistant reading only this document should be able to perform the documented tasks correctly on the first attempt.

```markdown
# Good (.ai/ style)
COMMAND: make build TYPE=app NAME=my-app
OUTPUT: kamiwazaai/my-app:version-dev
REQUIRES: Docker, kamiwaza.json

STAGE_TAGS:
- dev: version-dev (default)
- stage: version-stage
- prod: version (no suffix)
```

### Human-Readable Documents

**Purpose:** Enable developers to understand, use, and contribute to the project.

**Style requirements:**
- Comprehensive explanations with context
- Step-by-step instructions for processes
- Examples with expected output
- Troubleshooting sections for common issues
- Links to related documentation
- Consistent heading hierarchy

**Quality bar:** A new developer should be able to complete any documented task without asking questions.

```markdown
## Building Extensions

To build a Docker image for your extension, use the `make build` command:

\`\`\`bash
make build TYPE=app NAME=my-app
\`\`\`

This creates a local image tagged with the version from `kamiwaza.json`
plus a `-dev` suffix. For example, if your version is `1.0.0`, the
resulting image will be `kamiwazaai/my-app:1.0.0-dev`.

### Build Options

| Option | Description | Example |
|--------|-------------|---------|
| `NO_CACHE=1` | Force rebuild without Docker cache | `make build TYPE=app NAME=my-app NO_CACHE=1` |

### Troubleshooting

**Image not found after build:**
Verify the build completed successfully by checking `docker images | grep my-app`.
```

### Extension Documents

**Purpose:** Enable end users to install, configure, and use extensions.

**Style requirements:**
- Task-oriented organization (Installation, Configuration, Usage)
- Prerequisites clearly stated upfront
- Configuration options fully documented
- Common use cases with examples
- Known limitations documented

**Quality bar:** A user unfamiliar with Kamiwaza should be able to deploy and use the extension successfully.

### AGENTS.md Purpose

`AGENTS.md` defines autonomous agent behaviors and capabilities. Update when:
- Adding new agent types or skills
- Changing agent workflows or permissions
- Modifying tool access patterns
- Adding new automation capabilities

---

## Workflow

### Step 1: Identify the Base Branch

```bash
# Get current branch name
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"

# Find the merge base with main/master
MAIN_BRANCH=$(git remote show origin | grep 'HEAD branch' | cut -d: -f2 | tr -d ' ')
echo "Main branch: $MAIN_BRANCH"

# If main branch detection fails, try common names
if [[ -z "$MAIN_BRANCH" ]]; then
    for branch in main master develop; do
        if git show-ref --verify --quiet refs/heads/$branch; then
            MAIN_BRANCH=$branch
            break
        fi
    done
fi

# Find the commit where this branch diverged
MERGE_BASE=$(git merge-base $CURRENT_BRANCH $MAIN_BRANCH)
echo "Branch point: $MERGE_BASE"
echo "Branch point date: $(git show -s --format=%ci $MERGE_BASE)"
```

### Step 2: Review All Commits on This Branch

```bash
# List all commits since branch point
git log --oneline $MERGE_BASE..HEAD

# Get detailed commit messages
git log --format="%h %s%n%b" $MERGE_BASE..HEAD

# See all files changed on this branch
git diff --name-only $MERGE_BASE..HEAD

# See files changed with stats
git diff --stat $MERGE_BASE..HEAD

# Group changes by type
echo "=== Modified files ==="
git diff --name-status $MERGE_BASE..HEAD | grep "^M"

echo "=== Added files ==="
git diff --name-status $MERGE_BASE..HEAD | grep "^A"

echo "=== Deleted files ==="
git diff --name-status $MERGE_BASE..HEAD | grep "^D"
```

### Step 3: Analyze Changes by Category

```bash
# Scripts changed
git diff --name-only $MERGE_BASE..HEAD | grep -E "^scripts/"

# Apps changed
git diff --name-only $MERGE_BASE..HEAD | grep -E "^apps/"

# Tools changed
git diff --name-only $MERGE_BASE..HEAD | grep -E "^tools/"

# Make/build system changed
git diff --name-only $MERGE_BASE..HEAD | grep -E "^(make/|Makefile)"

# AI context files changed
git diff --name-only $MERGE_BASE..HEAD | grep -E "^\.ai/|CLAUDE\.md|AGENTS\.md"

# Existing docs changed
git diff --name-only $MERGE_BASE..HEAD | grep -E "^docs/|README\.md"
```

### Step 4: Review Actual Changes in Detail

**Do not skip this step.** Read the actual diffs to understand:
- What behavior changed
- Why it changed (from commit messages)
- What the new behavior is
- What edge cases exist

```bash
# See the full diff for a specific file
git diff $MERGE_BASE..HEAD -- path/to/file

# See changes to scripts
git diff $MERGE_BASE..HEAD -- scripts/

# See changes to specific app
git diff $MERGE_BASE..HEAD -- apps/app-name/
```

### Step 5: Create Documentation Plan

Before writing, create a plan:

1. **List all documents that need updates**
2. **For each document, note:**
   - What sections need changes
   - What new sections are needed
   - What content is now stale and should be removed
3. **Identify cross-document dependencies**
4. **Decide whether to delegate** (see Delegation Strategy above)

### Step 6: Identify Documentation to Update

| Changed Area | Documentation to Update |
|--------------|------------------------|
| `scripts/*.sh` | `.ai/rules/development-lifecycle.md`, `docs/scripts.md` |
| `scripts/*.py` | `.ai/rules/development-lifecycle.md`, `docs/scripts.md` |
| `make/*.mk`, `Makefile` | `.ai/rules/development-lifecycle.md`, `CLAUDE.md` |
| `apps/*/` | `apps/*/README.md`, `.ai/knowledge/successful/app-patterns.md` |
| `tools/*/` | `tools/*/README.md`, `.ai/knowledge/successful/mcp-patterns.md` |
| `.claude/skills/` | `AGENTS.md`, skill's `SKILL.md` |
| New features | `.ai/prompts/`, `docs/` |
| Bug fixes | `.ai/knowledge/failures/` if pattern-worthy |
| Architecture changes | `.ai/rules/architecture.md`, `CLAUDE.md` |
| Agent/automation changes | `AGENTS.md` |

### Step 7: Update Documents

For each document:

1. **Read the entire existing document** - Understand its structure and style
2. **Draft changes** - Write new content following the style guide
3. **Integrate changes** - Place new content in logical locations
4. **Remove stale content** - Delete anything that's no longer accurate
5. **Verify examples** - Test every command and code snippet
6. **Review holistically** - Read the updated document start to finish

### Step 8: Cross-Reference Check

After updating all documents:

1. **Check all @references** - Ensure `.ai/` cross-references are valid
2. **Verify links** - Test any hyperlinks in docs
3. **Check for duplicates** - Ensure information isn't repeated across documents
4. **Verify consistency** - Same concepts should use same terminology everywhere

---

## Document Templates

### For New Script Documentation

```markdown
# script-name.sh

PURPOSE: One-line description

USAGE: ./scripts/script-name.sh [OPTIONS]

## Description

[2-3 paragraph explanation of what this script does, when to use it,
and how it fits into the overall workflow.]

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `-x, --flag` | What this flag does | default value |

## Examples

### Basic Usage
\`\`\`bash
./scripts/script-name.sh
\`\`\`
Expected output: [describe what happens]

### With Options
\`\`\`bash
./scripts/script-name.sh --flag value
\`\`\`
Expected output: [describe what happens]

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| VAR_NAME | What it controls | Yes/No | value |

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Error message" | Why it happens | How to fix |

## Related

- [Related script or document](path)
```

### For New Feature in .ai/

```markdown
# Feature Name

CONTEXT: When and why to use this feature
COMMAND: Primary command to execute
OUTPUT: What the command produces

## Overview

[Brief description - 2-3 sentences max]

## Usage

STEP_1: First action
STEP_2: Second action
STEP_3: Third action

## Options

| Option | Effect | Default |
|--------|--------|---------|
| OPT=val | What it does | default |

## Examples

\`\`\`bash
# Example 1: Basic usage
command here

# Example 2: With options
command --option value
\`\`\`

## Common Issues

ISSUE: Description
FIX: Solution

## Related

- @.ai/rules/related-rule.md
- @.ai/knowledge/successful/related-pattern.md
```

---

## Quality Checklist

Before marking documentation complete, verify:

### Accuracy
- [ ] All commands tested and working
- [ ] All paths verified to exist
- [ ] All options/flags documented correctly
- [ ] Version numbers current

### Completeness
- [ ] All new features documented
- [ ] All changed behaviors updated
- [ ] All removed features cleaned up
- [ ] Edge cases and limitations noted
- [ ] Error conditions documented

### Structure
- [ ] Logical heading hierarchy
- [ ] Consistent formatting throughout
- [ ] Tables used for structured data
- [ ] Code blocks properly formatted

### Integration
- [ ] Cross-references valid (@.ai/... links)
- [ ] No duplicate information across documents
- [ ] Consistent terminology used
- [ ] Related documents updated together

### Professionalism
- [ ] No typos or grammatical errors
- [ ] Clear, unambiguous language
- [ ] Professional tone throughout
- [ ] Examples are realistic and useful

---

## Common Documentation Locations

```
.
├── CLAUDE.md                    # Root AI context (commands, structure)
├── AGENTS.md                    # Agent behaviors, skills, automation
├── .ai/
│   ├── rules/
│   │   ├── architecture.md      # Extension structure, Docker patterns
│   │   ├── development-lifecycle.md  # CI/release pipeline
│   │   ├── python-standards.md  # Python/FastAPI patterns
│   │   ├── testing.md           # Test requirements
│   │   └── style.md             # Code style rules
│   ├── prompts/
│   │   ├── new-app.md           # App creation template
│   │   └── new-tool.md          # Tool creation template
│   └── knowledge/
│       ├── successful/          # Working patterns
│       └── failures/            # Known issues
├── .claude/
│   └── skills/                  # Claude Code skills
│       └── */SKILL.md           # Individual skill definitions
├── docs/                        # Human-readable repo docs
├── apps/*/
│   ├── README.md                # App-specific docs
│   └── docs/                    # Extended app docs
└── tools/*/
    ├── README.md                # Tool-specific docs
    └── docs/                    # Extended tool docs
```

---

## Final Reminders

1. **Quality over speed** - Take the time to do it right
2. **Read before writing** - Understand existing documentation first
3. **Verify everything** - Test all examples and commands
4. **Think like the reader** - Will they find what they need?
5. **Delegate when appropriate** - Large updates benefit from parallel work
6. **Review holistically** - Read updated documents end-to-end
