# TASK LEDGER

## Status Values

- TODO
- ACTIVE
- BLOCKED
- DONE
- FAILED_VERIFIED

## Task Format

```
## TASK-XXXX — Title
Status: TODO
Owner: Agent name
Goal: One-line objective
Acceptance:
- Criterion 1
- Criterion 2
Evidence required:
- File diff
- Build/test command output
- Receipt path
```

---

## TASK-0001 — Initialize Hyper Flow Control Plane
Status: DONE
Owner: Windsurf
Goal: Add AGENTS.md, HYPERFLOW.md, SPEC/, RECEIPTS/, and baseline commands.
Acceptance:
- Repo has canonical control files.
- Build command is documented.
- Test command is documented.
- Receipt template exists.
Evidence required:
- File diff
- Receipt path: RECEIPTS/build_receipts/TASK-0001.md

---

## TASK-0002 — Create SPEC/ Documents
Status: DONE
Owner: ChatGPT / Windsurf
Goal: Write product_spec.md, architecture.md, api_contract.md, acceptance_tests.md.
Acceptance:
- All four SPEC files exist with meaningful content.
- Architecture matches HYPERFLOW.md roles.
Evidence required:
- File contents
- Receipt path

---

## TASK-0003 — Create Receipt Template
Status: DONE
Owner: Windsurf
Goal: Add RECEIPTS/receipt_template.md with canonical format.
Acceptance:
- Template exists with all required fields.
Evidence required:
- File exists

---

## TASK-0004 — Create Build/Test Scripts
Status: DONE
Owner: Codex / Windsurf
Goal: Add scripts/build.sh, scripts/test.sh, scripts/lint.sh.
Acceptance:
- Scripts are executable.
- Scripts exit non-zero on failure.
Evidence required:
- Script output

---

## TASK-0005 — Create MCP Tool Bridge
Status: DONE
Owner: Windsurf
Goal: Add mcp/hyperflow_bridge.py for Windsurf MCP integration.
Acceptance:
- MCP server exposes task ledger, receipt creation, and build status.
Evidence required:
- MCP server starts and responds

---

## TASK-0006 — Create GitHub Actions CI
Status: DONE
Owner: Windsurf / Codex
Goal: Add ci/hyperflow-ci.yml that runs build, test, lint, and receipt validation.
Acceptance:
- CI workflow file is valid YAML.
- Workflow runs on push and PR.
Evidence required:
- YAML lint passes
- Workflow file exists
