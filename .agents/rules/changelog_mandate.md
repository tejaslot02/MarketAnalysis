# Mandatory Commit-Wise Changelog Rule

## Overview
Every time code, configurations, schemas, or features are implemented, modified, or committed in this repository, **`CHANGELOG.md` MUST be updated** commit-wise.

## Behavioral Requirements for AI Agents & Developers
1. **Never Commit Without Updating `CHANGELOG.md`**:
   - Any commit touching source files (`api/`, `core/`, `flows/`, `scrapers/`, `ai/`, `scripts/`, `db/`, `docs/`, etc.) must include an updated section in `CHANGELOG.md`.
2. **Commit-Wise Structure**:
   - Document changes commit-by-commit with:
     - Header: `## [Commit <hash or SHA-short>] — <Date>`
     - Author and commit message
     - Affected files and modules
     - Granular bullet points of functional changes, UI updates, and API modifications.
3. **Keep `CHANGELOG.md` Staged with Changes**:
   - Always run `git add CHANGELOG.md` alongside your code edits so commits are not rejected by the `.githooks/pre-commit` hook.
