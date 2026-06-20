# Rule 20 — Terminal Safety

> **Law. Destructive commands require explicit user approval.**

## Blocked Commands (Require Approval)

| Pattern | Reason | Risk |
|---------|--------|------|
| `rm -rf` | Recursive delete | Data loss |
| `rm -r` | Recursive delete | Data loss |
| `dd` | Disk operations | Disk corruption |
| `mkfs` | Filesystem format | Disk wipe |
| `chmod 777` | World-writable | Security hole |
| `chown` | Ownership change | Security hole |
| `sudo` | Privilege escalation | System damage |
| `kill -9` | Force kill | Process corruption |
| `pkill` | Process kill | Service disruption |
| `> /dev/` | Device write | Hardware damage |
| `curl * \| bash` | Remote execution | Supply chain attack |
| `wget * \| sh` | Remote execution | Supply chain attack |

## Safe Commands (Auto-Approved)

| Pattern | Use |
|---------|-----|
| `ls`, `cat`, `head`, `tail` | Reading files |
| `grep`, `find`, `fd` | Searching |
| `git status`, `git log`, `git diff` | Git inspection |
| `python3 -c "import py_compile"` | Syntax check |
| `screencapture` | Screenshots |
| `cliclick` | Mouse/keyboard automation |
| `osascript` | AppleScript automation |
| `pgrep` | Process check |
| `open -a` | App launch |
| `pbcopy`, `pbpaste` | Clipboard |
| `which` | Path resolution |
| `echo` | Output |
| `mkdir` | Directory creation |

## Approval Protocol

1. Agent proposes command.
2. Terminal safety broker checks against blocked list.
3. If blocked → log `TERMINAL_APPROVAL_REQUIRED` with command and context.
4. User approves or denies.
5. Only approved commands execute.
6. Every execution (approved or auto) generates a receipt.

## Enforcement

- The `TerminalSafetyBroker` class in `agent_controller.py` intercepts all `subprocess.run` calls.
- Blocked commands raise `TerminalSafetyError` unless pre-approved.
- Approval state is per-session, not persistent.
