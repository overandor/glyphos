# AGENTS.md — Membra Desktop Operator

> **The missing operating layer between AI agents, your desktop, terminal, browser, and release artifacts.**

## What This Is

Membra Desktop Operator is a governed desktop automation envelope for AI coding agents. It installs a local execution layer plus a version-controlled agent law system into every repo.

## Architecture

```
Observe → Decide under Rules → Execute Workflow → Use Skill → Produce Artifact → Write Receipt → Verify Result
```

## Product Brain Hierarchy

| Layer | Authority | Purpose |
|-------|-----------|---------|
| **Rules** | Law | Hard constraints. Non-negotiable. Violation = abort. |
| **Workflows** | Procedure | Step-by-step execution sequences for specific tasks. |
| **Skills** | Machinery | Reusable capabilities that workflows call. |
| **Receipts** | Proof | Cryptographic evidence that an action occurred. Required for every artifact. |
| **Memories** | Notes | Context hints. NOT authoritative. Sticky notes, not law. |

## Sacred Commands (MVP)

```
/verify-space    — Validate HF Space deployment is live and correct
/build-dmg       — Build a macOS DMG package from source
/inspect-dmg     — Mount and inspect a DMG's contents safely
/terminal-audit  — Audit terminal commands for safety violations
/create-receipt  — Generate a signed receipt for the last artifact
```

## Sacred Rules

1. **No stealth capture.** Screen observation must be declared. No hidden recording.
2. **No destructive terminal actions without approval.** `rm -rf`, `dd`, `mkfs`, `chmod 777` require explicit user consent.
3. **No credential printing.** API keys, tokens, passwords are never echoed to logs, receipts, or chat.
4. **No fake verification claims.** Every claim must be backed by a command output or inspection result.
5. **Every artifact needs a receipt.** No receipt = artifact doesn't exist.

## Agent Roles

| Agent | Quadrant | Responsibility |
|-------|----------|----------------|
| CodeReviewer | 1 (top-left) | Observe IDE, generate code reviews under rules |
| WebResearcher | 2 (top-right) | Search web, summarize findings, type into Cascade |
| TaskManager | 3 (bottom-left) | Track tasks, monitor progress, assign next steps |
| SystemAgent | 4 (bottom-right) | System messages, receipt generation, health monitoring |

## File Structure

```
repo/
├── AGENTS.md                          ← You are here. Product brain entry point.
├── .devin/
│   ├── rules/                         ← Law. Hard constraints.
│   │   ├── 00-security-baseline.md
│   │   ├── 10-artifact-first.md
│   │   ├── 20-terminal-safety.md
│   │   ├── 30-hf-space.md
│   │   ├── 40-dmg-packaging.md
│   │   └── 50-receipts.md
│   ├── workflows/                     ← Procedure. Step-by-step.
│   │   ├── inspect-dmg.md
│   │   ├── mount-dmg-local.md
│   │   ├── extract-dmg-hf.md
│   │   ├── verify-space.md
│   │   ├── build-dmg.md
│   │   ├── notarize-release.md
│   │   ├── create-receipt.md
│   │   ├── screen-debug.md
│   │   └── terminal-audit.md
│   └── skills/                        ← Machinery. Reusable.
│       ├── dmg-reader-skill/
│       ├── hf-space-deploy-skill/
│       ├── macos-notarization-skill/
│       ├── screen-vision-qa-skill/
│       ├── terminal-safety-broker-skill/
│       └── chrome-extension-iframe-skill/
└── receipts/                          ← Proof. Signed artifacts.
```

## Enforcement

Rules are enforced by `agent_controller.py` at runtime:
- Terminal commands are checked against `20-terminal-safety.md` before execution
- Screen captures are logged with timestamp and purpose per `00-security-baseline.md`
- Every typed message, built artifact, and executed workflow generates a receipt
- Receipts are written to `receipts/` as JSON with SHA-256 content hashes
