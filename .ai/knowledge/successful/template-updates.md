# Template Update Playbook

Purpose: keep downstream repos in sync with this template using Copier.

## What Copier updates do
- Adds new files from the template (unless excluded by `_exclude`).
- Updates tracked files; respects `_skip_if_exists` (apps/, tools/, .env, etc.).
- Deletes files removed in newer template versions (unless they were excluded or locally created after copy).
- Executes `_tasks` on update (e.g., cleanup of legacy files).

## Safe update command
```bash
copier update --trust --skip-answered --defaults --vcs-ref HEAD
```
- `--vcs-ref HEAD` always pulls the latest `main` commit (not the last tag).
- Use `--data key=value` to override answers; avoid editing `.copier-answers.yml` manually.

## Workflow
1) Ensure clean working tree (`git status`).
2) Run the command above from repo root.
3) Review changes: `git diff` (apps/ and tools/ should remain untouched).
4) Commit with a conventional message, e.g., `chore: update template`.

## Conflict tips
- If Copier asks about conflicts, pick the option that keeps local app/tool code; infra files can be re-run.
- If the answers file is stale, re-run with `--vcs-ref HEAD --data docker_org=<prefix>`.

## Gotchas
- Do not delete `.copier-answers.yml`; it records template provenance.
- If you see old `copier.yml` in a consumer repo, remove it once; updates after 0.0.6 keep it gone.
