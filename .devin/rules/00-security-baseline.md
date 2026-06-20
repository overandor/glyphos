# Rule 00 — Security Baseline

> **Law. Violation = abort. No exceptions.**

## Screen Capture

1. All screen captures must be declared with a purpose.
2. Captures are logged: `{timestamp, purpose, window_index, file_path}`.
3. No hidden recording. No continuous streaming without user awareness.
4. Screenshot buffer is capped at 100 frames, 1/sec. Old frames are deleted.
5. Captures never include credential entry fields if detectable.

## Credential Protection

1. API keys, tokens, passwords are NEVER echoed to logs, receipts, or chat.
2. Environment variables matching `*KEY*`, `*TOKEN*`, `*SECRET*`, `*PASSWORD*` are redacted in all outputs.
3. Clipboard is restored after paste operations. No credential leakage via clipboard.
4. Receipts hash content with SHA-256 — never store raw credentials.

## Network

1. All outbound HTTP requests must have a 10-second timeout.
2. No data exfiltration. Screenshots and OCR text stay local.
3. Ollama calls are local-only (localhost:11434).
4. Web search queries are stripped of credentials before sending.

## Enforcement

- Violation of any rule in this file causes immediate abort of the current operation.
- Violations are logged as `SECURITY_VIOLATION` with full context.
- Three violations in a session = full agent shutdown.
