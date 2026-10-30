# Repository Agent & Developer Guidelines

## 1. Mandatory Commit-Wise Changelog
- **Rule**: Every code modification and commit MUST be accompanied by an entry in [`CHANGELOG.md`](file:///e:/Work/MarketAnalysis/CHANGELOG.md).
- **Structure**: Each commit entry must record:
  - Commit Hash / ID
  - Date (YYYY-MM-DD)
  - Author and Commit Message
  - Affected components/files
  - Itemized details of added features, refactorings, or bug fixes.
- **Enforcement**:
  - Local: Enforced via Git Pre-Commit Hook (`.githooks/pre-commit`).
  - Remote: Enforced via CI Quality Gate (`.github/workflows/ci.yml`).
  - AI Assistant: Enforced via `.agents/rules/changelog_mandate.md`.
