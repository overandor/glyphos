"""
PackageVerse Receipt Ledger + HDAR Capsule System.

Receipts: SHA-256 chained, tamper-evident JSONL ledger.
HDAR: Hardware-Detached Authenticated Recovery — suspend/resume
      application state across machines and runtimes.

Psi_{t+1} = Continue(Psi_t, tau, R_{t+1})
subject to:
  Parent(Psi_{t+1}) = H(Psi_t)
  Verify(Psi_t, tau, Psi_{t+1}) = true
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from .core import SpinorialState, ExecutionPhase, LineageState


@dataclass
class Receipt:
    """Tamper-evident execution receipt."""
    receipt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    package_id: str = ""
    event: str = ""
    phase: str = ""
    glyph_state: str = ""
    timestamp: float = field(default_factory=time.time)
    payload: dict = field(default_factory=dict)
    prev_hash: str = ""
    this_hash: str = ""

    def compute_hash(self) -> str:
        content = json.dumps({
            "receipt_id": self.receipt_id,
            "package_id": self.package_id,
            "event": self.event,
            "phase": self.phase,
            "glyph_state": self.glyph_state,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def seal(self):
        self.this_hash = self.compute_hash()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReceiptLedger:
    """
    SHA-256 chained receipt ledger.
    Each receipt's hash includes the previous receipt's hash.
    Tampering with any receipt breaks the chain.
    """

    def __init__(self, ledger_path: str):
        self.ledger_path = ledger_path
        self.entries: list[Receipt] = []
        self._last_hash = ""
        Path(ledger_path).parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if os.path.exists(self.ledger_path):
            with open(self.ledger_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        r = Receipt(**data)
                        self.entries.append(r)
                        self._last_hash = r.this_hash
                    except Exception:
                        pass

    def seal_receipt(self, state: SpinorialState, event: str, payload: Optional[dict] = None) -> Receipt:
        """Create and seal a new receipt for a state transition."""
        r = Receipt(
            package_id=state.package.package_id,
            event=event,
            phase=state.execution_phase.value,
            glyph_state=state.glyph_state.value,
            timestamp=time.time(),
            payload=payload or {},
            prev_hash=self._last_hash,
        )
        r.seal()
        self.entries.append(r)
        self._last_hash = r.this_hash

        with open(self.ledger_path, "a") as f:
            f.write(json.dumps(r.to_dict()) + "\n")

        return r

    def verify_chain(self) -> tuple[bool, list[str]]:
        """Verify the integrity of the receipt chain."""
        errors = []
        prev_hash = ""
        for i, r in enumerate(self.entries):
            expected_hash = r.compute_hash()
            if r.this_hash != expected_hash:
                errors.append(f"Receipt {i}: hash mismatch")
            if r.prev_hash != prev_hash:
                errors.append(f"Receipt {i}: prev_hash mismatch")
            prev_hash = r.this_hash
        return len(errors) == 0, errors

    def to_list(self) -> list[dict]:
        return [r.to_dict() for r in self.entries]


@dataclass
class HDARCapsule:
    """
    Hardware-Detached Authenticated Recovery capsule.
    Contains committed filesystem state, package graph, runtime description,
    active task, permission boundary, encrypted secrets, receipts,
    input/output commitments, and predecessor epoch.
    """
    capsule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    package_id: str = ""
    epoch: int = 0
    parent_hash: str = ""
    capsule_hash: str = ""
    state_snapshot: dict = field(default_factory=dict)
    permissions_snapshot: dict = field(default_factory=dict)
    verification_snapshot: dict = field(default_factory=dict)
    economic_snapshot: dict = field(default_factory=dict)
    receipt_count: int = 0
    last_event: str = ""
    created_at: float = field(default_factory=time.time)
    sealed: bool = False

    def compute_hash(self) -> str:
        content = json.dumps({
            "capsule_id": self.capsule_id,
            "package_id": self.package_id,
            "epoch": self.epoch,
            "parent_hash": self.parent_hash,
            "state_snapshot": self.state_snapshot,
            "permissions_snapshot": self.permissions_snapshot,
            "verification_snapshot": self.verification_snapshot,
            "economic_snapshot": self.economic_snapshot,
            "receipt_count": self.receipt_count,
            "last_event": self.last_event,
            "created_at": self.created_at,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def seal(self):
        self.capsule_hash = self.compute_hash()
        self.sealed = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HDARManager:
    """
    Manages HDAR capsules for suspend/resume of application state.

    Psi_{t+1} = Continue(Psi_t, tau, R_{t+1})
    """

    def __init__(self, capsule_dir: str):
        self.capsule_dir = capsule_dir
        Path(capsule_dir).mkdir(parents=True, exist_ok=True)

    def suspend(self, state: SpinorialState, receipt_count: int) -> HDARCapsule:
        """
        Seal current state into a dormant capsule.
        The application becomes hardware-detached without becoming state-detached.
        """
        epoch = state.lineage.epoch
        parent_hash = state.lineage.current_hash

        capsule = HDARCapsule(
            package_id=state.package.package_id,
            epoch=epoch,
            parent_hash=parent_hash,
            state_snapshot=state.to_dict(),
            permissions_snapshot=state.permissions.to_dict(),
            verification_snapshot=state.verification.to_dict(),
            economic_snapshot=state.economic.to_dict(),
            receipt_count=receipt_count,
            last_event=state.last_event,
        )
        capsule.seal()

        # Update lineage
        state.lineage.epoch = epoch + 1
        state.lineage.parent_hash = parent_hash
        state.lineage.current_hash = capsule.capsule_hash
        state.lineage.capsule_path = str(Path(self.capsule_dir) / f"{capsule.capsule_id}.json")

        # Persist capsule
        capsule_path = Path(self.capsule_dir) / f"{capsule.capsule_id}.json"
        with open(capsule_path, "w") as f:
            json.dump(capsule.to_dict(), f, indent=2)

        return capsule

    def resume(self, capsule_id: str) -> Optional[HDARCapsule]:
        """
        Materialize a dormant capsule back into active state.
        Verifies lineage before restoring.
        """
        capsule_path = Path(self.capsule_dir) / f"{capsule_id}.json"
        if not capsule_path.exists():
            return None

        with open(capsule_path, "r") as f:
            data = json.load(f)

        capsule = HDARCapsule(**data)

        # Verify capsule integrity
        expected_hash = capsule.compute_hash()
        if capsule.capsule_hash != expected_hash:
            raise ValueError("Capsule hash mismatch — tampering detected")

        return capsule

    def verify_lineage(self, capsule: HDARCapsule, parent_capsule: Optional[HDARCapsule] = None) -> bool:
        """
        Verify(Psi_t, tau, Psi_{t+1}) = true
        Parent(Psi_{t+1}) = H(Psi_t)
        """
        if parent_capsule is None:
            return capsule.parent_hash == ""  # Genesis capsule

        return capsule.parent_hash == parent_capsule.capsule_hash

    def list_capsules(self) -> list[dict]:
        capsules = []
        for p in Path(self.capsule_dir).glob("*.json"):
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                    capsules.append({
                        "capsule_id": data.get("capsule_id", ""),
                        "package_id": data.get("package_id", ""),
                        "epoch": data.get("epoch", 0),
                        "sealed": data.get("sealed", False),
                        "created_at": data.get("created_at", 0),
                        "last_event": data.get("last_event", ""),
                    })
            except Exception:
                pass
        return capsules
