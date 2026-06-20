# Rule 10 — Artifact First

> **Law. No artifact = no claim.**

## Principle

Every agent action that produces a result must produce an artifact. Artifacts are the only acceptable form of proof.

## Artifact Types

| Type | Extension | Example |
|------|-----------|---------|
| Screenshot | `.png` | `/tmp/agent_capture_*.png` |
| Receipt | `.json` | `receipts/*.json` |
| Log | `.log` | `/tmp/agent_*.log` |
| Data export | `.json` | `/tmp/agent_data_*.json` |
| DMG | `.dmg` | `build/*.dmg` |
| Report | `.md` | `receipts/report_*.md` |

## Rules

1. Every claim must reference an artifact by path.
2. "I verified X" without an artifact = fake claim = violation.
3. Artifacts are immutable once written. Modifications require a new artifact + receipt.
4. Artifacts older than 24 hours in `/tmp/` are eligible for cleanup.
5. Receipts in `receipts/` are never auto-deleted.

## Enforcement

- Agent outputs without artifact references are rejected.
- The pipeline tracks `artifact_path` for every action.
