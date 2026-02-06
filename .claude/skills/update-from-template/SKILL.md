---
name: update-from-template
description: Update this repository from the upstream Kamiwaza extensions template using copier. Use when the user wants to update infrastructure, sync from template, pull template changes, or mentions copier update.
---

# Update from Template

This skill helps update a Kamiwaza extensions repository from the upstream template.

## When to Use

- User asks to "update from template" or "sync from upstream"
- User mentions "copier update" or "pull template changes"
- User wants to get latest build scripts, make targets, or shared libraries

## Prerequisites

Ensure copier is installed:
```bash
command -v copier || pip install copier
```

## Update Workflow

### Step 1: Check Current State

First, ensure working directory is clean:
```bash
git status
```

If there are uncommitted changes, either commit or stash them first.

### Step 2: Run Copier Update

Run copier update (skips re-prompting for already-answered questions):
```bash
copier update --trust --skip-answered
```

If you need to change previous answers:
```bash
copier update --trust
```

### Step 3: Review Changes

After update completes, review what changed:
```bash
git diff
git status
```

Key directories to review:
- `make/` - Build system changes
- `scripts/` - Script updates
- `shared/` - Shared library updates
- `.ai/` - AI assistant rules updates

### Step 4: Handle Conflicts

If there are merge conflicts (`.rej` files):

1. List reject files:
   ```bash
   find . -name "*.rej" -type f
   ```

2. For each conflict:
   - Review the `.rej` file to see what couldn't be applied
   - Manually merge the changes into the target file
   - Delete the `.rej` file

3. Verify no reject files remain:
   ```bash
   find . -name "*.rej" -type f | wc -l
   ```

### Step 5: Test and Commit

1. Verify everything works:
   ```bash
   make validate
   ```

2. Commit the update:
   ```bash
   git add -A
   git commit -m "Update infrastructure from upstream template"
   ```

## Protected Directories

These directories are NEVER modified by template updates:
- `apps/` - Your applications
- `tools/` - Your MCP tools
- `.env` files - Your local configuration

## Common Options

| Option | Description |
|--------|-------------|
| `--trust` | Trust template (required for tasks) |
| `--skip-answered` | Don't re-prompt for existing answers |
| `--vcs-ref=TAG` | Update to specific template version |
| `--defaults` | Accept all defaults without prompting |

## Updating to Specific Version

To update to a specific template version:
```bash
copier update --trust --vcs-ref=0.1.2
```

To see available versions:
```bash
git ls-remote --tags https://github.com/kamiwaza-internal/kamiwaza-extensions-template.git
```

## Troubleshooting

### "Template not found" Error
The `.copier-answers.yml` file tracks the template source. Verify it exists and contains the correct `_src_path`.

### Conflicts with Local Changes
If you've modified template files locally (like Makefile), you may need to manually merge. Review the diff carefully.

### Missing Dependencies
After update, you may need to rebuild shared libraries:
```bash
make package-libs CLEAN=1
```
