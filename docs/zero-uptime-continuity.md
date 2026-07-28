# Proof-Carrying Rolling Hibernation Runtime

## Commercial Name: Zero-Uptime Continuity

## Strict Technical Description

A provider-independent execution lineage in which an authenticated dormant capsule can acquire a temporary compute body, resume from a committed predecessor state, perform a bounded transition, emit a verified successor capsule, and return to zero active application compute.

## Core Thesis

The application ceases to be an installation bound to one computer. It becomes an authenticated state-transition lineage capable of acquiring temporary bodies.

- The machine becomes a temporary organ.
- The application becomes the durable identity.
- That is the spinor.

## What Is Not True

- Docker does not create computation from nothing.
- A Docker image is a recipe, not a kitchen. The host is the kitchen. The container runtime is the cook. The processor is the stove.
- A cryptographic hash preserves neither energy nor thermodynamic entropy. It preserves an integrity relationship.
- A static website did not eliminate compute. It transferred compute to the client.
- The hash is not sitting inside the landing page doing little calculations because the CSS gave it permission.

## What Is True

You cannot remove dependency on computation. You can remove dependency on a particular continuously running machine.

Preserved compute is impossible (physical execution cannot continue without hardware, energy, or time).

Preserved computability is achievable (the system can stop consuming active resources while retaining enough authenticated structure to restart somewhere else without losing identity, memory, progress, or proof).

## Architecture: Two Sides of the Spinor

### Visible Side (static, cheap, always available)
- Static Vercel/Netlify page
- Hugging Face Space
- Status glyph
- Agent dashboard
- Activation control
- Current receipts

### Hidden Side (temporary, summoned, compute-bearing)
- Docker image
- Model weights
- Memory snapshot
- Temporary keys
- Mounted storage
- Network access
- CPU, GPU
- Runtime policy
- Active lease

## Continuation Capsule

The deeper primitive (Docker is merely one packaging method).

### Contains or references:
- Runtime image binding
- Predecessor commitment
- Continuation program identifier
- Required capabilities
- Encrypted memory
- Pending tasks
- Epoch
- Policy version
- Acceptable providers / hardware constraints
- Previous receipts
- Successor readiness proof information

### Does NOT contain:
- Permanent unrestricted credentials (authority acquired temporarily after body proves identity and readiness)

## Thermal Modes

| Mode | State | Compute Cost |
|------|-------|-------------|
| Deep dormancy | No body exists. Only static interface, stored capsule, pilot light. | Zero |
| Cold preparation | Provider selected. No image or state loaded. | Minimal |
| Warm preparation | Runtime image + common dependencies cached. No private state or authority. | Low |
| Hot standby | Successor restored state + health checks complete. Does not hold active lease. | Medium |
| Active mode | Body serves work. | Full |
| Draining mode | No new work. Finalizing existing tasks. | Decreasing |
| Sealing mode | Producing successor capsule + receipts. | Decreasing |
| Suspended mode | Compute released. Only durable state remains. | Zero |

## Lifecycle

1. Dormant identity requests a body.
2. Body proves it is running the expected image.
3. Body retrieves private state.
4. Body proves it opened the intended capsule.
5. Body receives a temporary execution lease.
6. Body advances the state.
7. Body produces a successor commitment.
8. Body publishes a receipt.
9. Body relinquishes authority.
10. Body disappears.
11. Identity remains.

## Warm-Up / Warm-Down Relay

Before Host A terminates, Host B begins warming.

- Host A finalizes: stops new work, completes/checkpoints in-flight tasks, flushes memory, writes durable deltas, finalizes logs, signs receipts, updates commitments, records pending tasks, releases capabilities, creates successor capsule, proves predecessor state.
- Host B materializes: allocates hardware, retrieves image, verifies digest, mounts storage, downloads weights, restores indexes, loads dependencies, reconstructs memory, retrieves encrypted state, obtains credentials, opens connections, performs readiness tests.

Overlap = transition interval, not dead time. One body compresses the past into durable state. The other expands durable state into a new active process.

Host B produces a readiness receipt binding: identity, runtime image, state commitment, policy version, epoch, predecessor receipt, health-check result.

Coordinator/verifier decides whether baton may pass.

## Continuity Types

| Type | Meaning | Required? |
|------|---------|-----------|
| Hardware continuity | Same machine remains active | No |
| Process continuity | Same OS process remains alive | No |
| Memory continuity | Relevant state remains available | Yes |
| Identity continuity | Successor proves membership in lineage | Yes |
| Authority continuity | Exactly one accepted successor may advance | Yes |
| Semantic continuity | Successor resumes same goals/obligations | Yes |
| Economic continuity | Balances, rights, liabilities, rewards survive | Yes |
| Cryptographic continuity | Transitions remain independently verifiable | Yes |

## The Baton

The baton does not carry CPU cycles. It carries the consequences and continuation conditions of prior computation.

- Image digest (execution environment)
- State commitment (application state)
- Encrypted memory snapshot pointer
- Continuation cursor (where execution resumes)
- Unresolved goals, pending tasks, open transactions
- Model checkpoints, indexes, cached artifacts
- Policy version, public keys, resource requirements
- Predecessor receipts
- Lease (which body has authority)
- Challenge (preventing old bodies from replaying)

## Pilot Light

The smallest unavoidable always-on dependency. Does not run the whole application. Only detects ignition conditions and directs compute toward materialization.

May be: Vercel edge network, Netlify gateway, Hugging Face routing, queue, webhook, DNS endpoint, browser, or another running agent.

## Connection to Existing Work

This architecture extends ZK File Teleportation from file transport to runtime continuity:

- Predecessor = agent's accepted world state (not merely a file)
- Task = hidden transition obligation (not merely a command)
- Successor = next legitimate manifestation of the software organism (not merely an output file)

Public sees: commitments, policy identifiers, epochs, challenges, receipts, state relationships.
Private body sees: memory, tasks, keys, intermediate computation, hidden successor content.

## Key Insight

Continuous agent does not mean continuously executing agent. It means continuously identifiable agent.

Uptime alone does not prove identity. A proof-carrying lineage can preserve identity even when uptime reaches zero.

## Final Architecture

```
container image describes body
hash identifies body
capsule preserves state
pilot light detects demand
provider supplies compute
lease grants authority
receipt proves transition
successor capsule survives
body disappears
identity continues
```

## Slogan

The software is not alive because Docker exists. The software is alive because every temporary body knows how to inherit, prove, advance, and surrender the same lineage.
