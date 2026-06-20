# Rule 50 — Receipts

> **Law. No receipt = artifact doesn't exist.**

## Receipt Format

Every receipt is a JSON file in `receipts/` with this schema:

```json
{
  "receipt_id": "uuid4",
  "timestamp": "ISO 8601",
  "agent": "CodeReviewer|WebResearcher|SystemAgent|...",
  "action": "review|search|type|build|verify|...",
  "artifact_path": "absolute/path/to/artifact",
  "artifact_hash": "SHA-256 of artifact content",
  "commands_run": ["command1", "command2"],
  "result": "success|failure|partial",
  "details": {},
  "previous_receipt": "receipt_id of prior related action or null"
}
```

## Rules

1. Every agent action that produces output generates a receipt.
2. Receipts are append-only. Never modified after creation.
3. Receipts are named: `receipts/{timestamp}_{agent}_{action}.json`.
4. `artifact_hash` is SHA-256 of the artifact file content.
5. If no artifact is produced, `artifact_path` and `artifact_hash` are null, and `result` must be "failure" with explanation.
6. Receipts chain via `previous_receipt` to form an audit trail.

## Verification

1. `/create-receipt` generates a receipt for the last action.
2. Receipt validity: `artifact_hash` must match actual file hash.
3. Invalid receipts are flagged but not deleted (audit trail).

## Enforcement

- `ReceiptLedger` class in `agent_controller.py` handles receipt creation.
- Agent outputs without receipts are rejected by the pipeline.
- Receipt count is logged at session end.
