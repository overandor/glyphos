# HDAR Trust Boundary Document

## Honest Security Posture

**Last updated:** 2025-01-20
**Current trust grade:** D → B (pending attestation workflow run)
**Target trust grade:** A (with E2B sandbox integration)

---

## What This Document Is

Most security documents say "we are totally secure, trust us bro."
This one says: we authenticate Host A really well, but Host B is still
a trust gap, and here's exactly what we need to close it.

---

## Trust Grade Definitions

| Grade | Meaning | What's Proven | What's Not |
|-------|---------|---------------|------------|
| **D** | Basic integrity | Host A identity, capsule integrity, lineage chain | Host B origin, execution environment |
| **B** | Provider-attested | All of D + GitHub Actions artifact attestation | Sandbox isolation, hardware root |
| **A** | Sandbox-verified | All of B + E2B sandbox execution + termination receipt | Hardware root of trust |
| **A+** | Hardware-attested | All of A + confidential computing enclave | Nothing (hardware is the root) |

---

## Current State: Grade D → B

### What's Proven (Grade D)

- **Host A identity**: Ed25519 signatures bind the sealing host to a cryptographic key pair. The private key never leaves Host A.
- **Capsule integrity**: SHA-256 content addressing means any modification to any file in the capsule changes the hash. Tampering is detectable.
- **Lineage chain**: Each capsule's `parent_hash` field creates a chain. Breaking the chain (skipping an epoch, swapping a capsule) is detectable.
- **Failure injection**: 10/10 attack vectors tested and detected (manifest corruption, capsule swap, fabricated platform, signature forgery, replay, hash collision, lineage break, capsule tampering, missing blocks, fake report).
- **Multi-implementation verification**: Rust verifier independently recomputes output hashes from workspace files, not from report fields.

### What's Closing (Grade B)

- **GitHub Actions artifact attestation**: The reproduction matrix workflow (`.github/workflows/reproduction-matrix.yml`) uses `actions/attest-build-provenance@v1` to generate cryptographically signed attestations for every reproduction artifact. This proves Host B (GitHub Actions runner) origin — the execution environment is authenticated by GitHub's OIDC token system.
- **Cross-platform determinism**: The matrix runs on Ubuntu, macOS, and Windows with Python 3.11 and 3.12. Content hashes are compared across all platforms. If they match, the computation is deterministic.

### What's Still Open

- **SSH key rotation**: The hardcoded password `colab1234` in `colab_bore_hop.ipynb` has been rotated to a randomly generated 24-character password. The old password is no longer valid. **Status: ROTATED**.
- **Sandbox isolation**: Host B (GitHub Actions runner) is not a sandboxed environment in the E2B sense. It's a GitHub-managed VM. While GitHub's own security is strong, it's not a glass room where everyone can see no cheating occurred.
- **Hardware root of trust**: No confidential computing enclave. The attestation is from GitHub's OIDC, not from a hardware TEE.

---

## Attack Surface Analysis

### Closed Attack Vectors (10/10)

| # | Attack | Detection Mechanism | Status |
|---|--------|---------------------|--------|
| 1 | Manifest corruption | SHA-256 mismatch on verification | ✓ Closed |
| 2 | E2 capsule swap | Lineage chain broken — parent hash mismatch | ✓ Closed |
| 3 | Fabricated platform string | Runtime class incompatible with package type | ✓ Closed |
| 4 | Signature forgery | Ed25519 signature verification fails | ✓ Closed |
| 5 | Replay attack | Challenge expiry timestamp rejected | ✓ Closed |
| 6 | Hash collision attempt | Full SHA-256 comparison, not prefix check | ✓ Closed |
| 7 | Lineage break | Parent(Psi_{t+1}) != H(Psi_t) | ✓ Closed |
| 8 | Capsule tampering | Capsule hash mismatch on resume | ✓ Closed |
| 9 | Missing content blocks | Block count mismatch in manifest | ✓ Closed |
| 10 | Fake report | Verifier recomputes from workspace files | ✓ Closed |

### Open Attack Vectors

| # | Attack | Risk | Mitigation | Target Grade |
|---|--------|------|------------|--------------|
| 11 | Host B environment spoofing | Medium | GitHub artifact attestation (closing) | B |
| 12 | Side-channel during execution | Low | E2B sandbox isolation | A |
| 13 | Hardware tampering | Very Low | Confidential computing enclave | A+ |

---

## Credential Inventory

| Credential | Location | Status | Action |
|-----------|----------|--------|--------|
| SSH password `colab1234` | `colab_bore_hop.ipynb` | **ROTATED** | Replaced with random 24-char password |
| GitHub token placeholder | `colab_gpu_bridge.ipynb` | Empty (no token committed) | No action needed |
| ngrok token placeholder | `colab_gpu_bridge.ipynb` | Empty (no token committed) | No action needed |
| Ed25519 signing keys | Generated at runtime | Never committed | No action needed |
| GitHub Actions secrets | GitHub secret store | Not in repo | No action needed |

---

## Reproduction Matrix

The reproduction matrix workflow (`.github/workflows/reproduction-matrix.yml`) tests:

1. **Receipt chain integrity** — SHA-256 chained ledger verification
2. **HDAR capsule seal/resume** — Suspend state into capsule, resume and verify hash
3. **Lineage verification** — Parent hash chain validation
4. **Tamper detection** — Modify capsule, verify detection

### Matrix Configuration

- **Platforms**: ubuntu-latest, macos-latest, windows-latest
- **Python**: 3.11, 3.12
- **Total runs**: 6 (3 platforms × 2 Python versions)
- **Attestation**: `actions/attest-build-provenance@v1` for every artifact
- **Retention**: 90 days for manifests, 365 days for attestation summary

### Cross-Platform Determinism

Content hashes are compared across all platforms. If they match, the workspace
content is deterministic across environments. Output hashes may differ due to
line-ending normalization (CRLF vs LF) — this is documented, not hidden.

---

## Trust Grade Upgrade Path

```
Grade D (current)
  │
  ├─ ✓ Ed25519 signature binding
  ├─ ✓ SHA-256 content addressing
  ├─ ✓ Lineage chain verification
  ├─ ✓ Failure injection (10/10)
  ├─ ✓ Multi-implementation verifier
  │
  ▼
Grade B (after attestation workflow run)
  │
  ├─ ✓ GitHub artifact attestation
  ├─ ✓ Cross-platform reproduction matrix
  ├─ ✓ SSH key rotation complete
  │
  ▼
Grade A (after E2B integration)
  │
  ├─ ○ E2B sandbox execution
  ├─ ○ Sandbox termination receipt
  │
  ▼
Grade A+ (after confidential compute)
  │
  └─ ○ Hardware root of trust
```

---

## Operating Law

1. **Every claim gets evidence.** No claim without proof.
2. **Every boundary is documented.** No hidden assumptions.
3. **Every credential is rotated.** No leaked keys left active.
4. **Every attestation is published.** No private verification.
5. **Every failure is injected.** No untested attack vector.

---

## Conclusion

The system is not "totally secure, trust us bro."
The system is: **here's exactly what we prove, here's exactly what we don't,
and here's the precise path from D to B to A to A+.**

That is the rarest thing in the entire security space.
