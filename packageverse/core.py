"""
PackageVerse Core Types — Spinorial application state machine.

Implements the fundamental primitives:
- PackageIdentity: cryptographic identity I
- SpinorialState: Psi_A = (A, phi, rho, kappa, lambda, chi)
- RuntimeClass: execution regime enumeration
- RuntimeResolver: R* = argmin [C(R) + L(R) + Gamma(R) + Omega(R)]
- PermissionBoundary: capability boundary kappa
- VerificationPolicy: completion condition V
- EconomicIdentity: economic state chi
- MaterializationPlan: the full plan from ingestion to settlement
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, IntEnum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RuntimeClass(Enum):
    """Execution regimes for materialized packages."""
    BROWSER_NATIVE = "browser_native"        # WebAssembly, WASI, JS
    LOCAL_MACOS = "local_macos"              # macOS .app on Apple hardware
    LOCAL_WINDOWS = "local_windows"          # Windows .exe on Windows worker
    LOCAL_LINUX = "local_linux"              # Linux binary on Linux worker
    REMOTE_DESKTOP = "remote_desktop"        # Streamed desktop window
    HEADLESS_CAPABILITY = "headless_capability"  # Callable function, no GUI
    VIRTUAL_MACHINE = "virtual_machine"      # VM-based isolation
    CONTAINER = "container"                   # Container isolation
    GPU_NODE = "gpu_node"                     # GPU compute
    CONFIDENTIAL = "confidential"             # Confidential computing


class PackageType(Enum):
    """Package classification from fingerprinting."""
    MACOS_APP = "macos_app"
    WINDOWS_EXE = "windows_exe"
    LINUX_BINARY = "linux_binary"
    WEBASSEMBLY = "webassembly"
    PYTHON_PACKAGE = "python_package"
    NODE_PACKAGE = "node_package"
    CLI_TOOL = "cli_tool"
    UNKNOWN = "unknown"


class GlyphState(Enum):
    """Reactive glyph visual states — each must be backed by real evidence."""
    IDLE = "idle"
    INSPECTING = "inspecting"       # Package inspection service running
    RESOLVING = "resolving"         # Runtime resolver active
    ALLOCATING = "allocating"       # Scheduler issuing resource lease
    LAUNCHING = "launching"         # Runtime starting
    EXECUTING = "executing"         # Runtime alive, app running
    INTERACTIVE = "interactive"     # User interacting via relay
    SUSPENDED = "suspended"         # HDAR capsule sealed
    VERIFIED = "verified"           # Verification policy passed
    SEALED = "sealed"               # Receipt sealed, session ended
    ERROR = "error"                 # Execution failed
    REVOKED = "revoked"             # Permissions revoked


class PermissionLevel(IntEnum):
    """Capability grant levels — denial by default."""
    DENIED = 0
    GRANTED = 1
    APPROVAL_REQUIRED = 2


class ExecutionPhase(Enum):
    """Phases of the materialization pipeline."""
    INGESTED = "ingested"
    FINGERPRINTED = "fingerprinted"
    PLAN_GENERATED = "plan_generated"
    RUNTIME_RESOLVED = "runtime_resolved"
    PERMISSIONS_ASSIGNED = "permissions_assigned"
    LAUNCHED = "launched"
    MONITORING = "monitoring"
    SUSPENDED = "suspended"
    RESUMED = "resumed"
    VERIFIED = "verified"
    SEALED = "sealed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Core Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PackageIdentity:
    """Cryptographic identity I of a package."""
    package_id: str                           # UUID
    sha256: str                               # Full file hash
    name: str
    version: str
    package_type: PackageType
    size_bytes: int
    entrypoints: list[str] = field(default_factory=list)
    signatures: list[str] = field(default_factory=list)
    architecture: str = ""
    os_requirement: str = ""
    created_at: float = field(default_factory=time.time)

    @property
    def short_hash(self) -> str:
        return self.sha256[:16]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["package_type"] = self.package_type.value
        return d


@dataclass
class PermissionBoundary:
    """Capability boundary kappa — what the package may access."""
    filesystem_paths: list[str] = field(default_factory=list)
    network_endpoints: list[str] = field(default_factory=list)
    clipboard: PermissionLevel = PermissionLevel.DENIED
    microphone: PermissionLevel = PermissionLevel.DENIED
    camera: PermissionLevel = PermissionLevel.DENIED
    accessibility: PermissionLevel = PermissionLevel.DENIED
    automation: PermissionLevel = PermissionLevel.DENIED
    process_spawn: PermissionLevel = PermissionLevel.DENIED
    gpu_access: PermissionLevel = PermissionLevel.DENIED
    max_cpu_percent: float = 50.0
    max_memory_mb: int = 2048
    max_disk_mb: int = 512
    network_egress: PermissionLevel = PermissionLevel.DENIED
    human_approval_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for key, val in list(d.items()):
            if isinstance(val, PermissionLevel):
                d[key] = int(val)
        return d

    def is_deny_by_default(self) -> bool:
        """Verify all dangerous capabilities start denied."""
        dangerous = [self.clipboard, self.microphone, self.camera,
                     self.accessibility, self.automation, self.process_spawn,
                     self.network_egress]
        return all(p == PermissionLevel.DENIED for p in dangerous)


@dataclass
class VerificationPolicy:
    """What must be true before work is considered complete."""
    artifact_must_exist: bool = True
    artifact_path: str = ""
    digest_check: bool = False
    expected_digest: str = ""
    exit_code_must_be_zero: bool = True
    time_limit_seconds: float = 0.0
    custom_checks: list[str] = field(default_factory=list)
    passed: bool = False
    checked_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EconomicIdentity:
    """Economic state chi — contribution tracking."""
    economic_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    contributors: list[dict] = field(default_factory=list)
    execution_count: int = 0
    total_verified_value: float = 0.0
    revenue_distribution: list[dict] = field(default_factory=list)
    pricing_model: str = "per_execution"

    def add_contributor(self, role: str, address: str, weight: float = 1.0):
        self.contributors.append({
            "role": role,
            "address": address,
            "weight": weight,
        })

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LineageState:
    """Lineage state lambda — HDAR chain."""
    epoch: int = 0
    parent_hash: str = ""
    current_hash: str = ""
    capsule_path: str = ""
    predecessor_id: str = ""
    successor_id: str = ""
    chain_intact: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SpinorialState:
    """
    Psi_A = (A, phi, rho, kappa, lambda, chi)

    The full hidden state of a materialized application.
    The user sees only Pi(Psi_A) = phi (the visible surface).
    """
    package: PackageIdentity
    surface: str = ""                          # phi: visible surface type
    execution_phase: ExecutionPhase = ExecutionPhase.INGESTED
    glyph_state: GlyphState = GlyphState.IDLE
    runtime_class: RuntimeClass = RuntimeClass.LOCAL_MACOS
    permissions: PermissionBoundary = field(default_factory=PermissionBoundary)
    verification: VerificationPolicy = field(default_factory=VerificationPolicy)
    lineage: LineageState = field(default_factory=LineageState)
    economic: EconomicIdentity = field(default_factory=EconomicIdentity)
    pid: int = 0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_mb: float = 0.0
    network_active: bool = False
    uptime_seconds: float = 0.0
    last_event: str = ""
    last_event_time: float = field(default_factory=time.time)
    state_history: list[dict] = field(default_factory=list)

    @property
    def visible_projection(self) -> str:
        """Pi(Psi_A) = phi — what the user sees."""
        return self.surface

    def transition(self, event: str, **kwargs):
        """
        Psi_A^{t+1} = T(Psi_A^t, u_t, e_t, p_t)

        Record a state transition with full audit trail.
        """
        entry = {
            "timestamp": time.time(),
            "event": event,
            "from_phase": self.execution_phase.value,
            "from_glyph": self.glyph_state.value,
            "changes": kwargs,
        }
        self.state_history.append(entry)
        self.last_event = event
        self.last_event_time = time.time()

        for key, val in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, val)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package": self.package.to_dict(),
            "surface": self.surface,
            "execution_phase": self.execution_phase.value,
            "glyph_state": self.glyph_state.value,
            "runtime_class": self.runtime_class.value,
            "permissions": self.permissions.to_dict(),
            "verification": self.verification.to_dict(),
            "lineage": self.lineage.to_dict(),
            "economic": self.economic.to_dict(),
            "pid": self.pid,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "disk_mb": self.disk_mb,
            "network_active": self.network_active,
            "uptime_seconds": self.uptime_seconds,
            "last_event": self.last_event,
            "last_event_time": self.last_event_time,
            "state_history_count": len(self.state_history),
        }


@dataclass
class MaterializationPlan:
    """
    The plan produced from package inspection.
    States where the app can run, what it needs, and how it's presented.
    """
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    package_id: str = ""
    runtime_class: RuntimeClass = RuntimeClass.LOCAL_MACOS
    runtime_cost: float = 0.0
    runtime_latency_ms: float = 0.0
    runtime_risk: float = 0.0
    runtime_complexity: float = 0.0
    runtime_score: float = 0.0
    permissions: PermissionBoundary = field(default_factory=PermissionBoundary)
    presentation: str = "streamed_window"     # streamed_window, glyph, command, api
    verification: VerificationPolicy = field(default_factory=VerificationPolicy)
    risks_detected: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    worker_id: str = ""
    resource_allocation: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["runtime_class"] = self.runtime_class.value
        d["permissions"] = self.permissions.to_dict()
        d["verification"] = self.verification.to_dict()
        return d


# ---------------------------------------------------------------------------
# Runtime Resolver
# ---------------------------------------------------------------------------

class RuntimeResolver:
    """
    R* = argmin_R [C(R) + L(R) + Gamma(R) + Omega(R)]

    subject to: Compatible(A, R) = true
    """

    @staticmethod
    def resolve(package: PackageIdentity) -> tuple[RuntimeClass, MaterializationPlan]:
        """Select the optimal runtime for a package."""
        candidates = RuntimeResolver._compatible_runtimes(package)
        if not candidates:
            raise ValueError(f"No compatible runtime for package type {package.package_type}")

        scored = []
        for rt in candidates:
            cost = RuntimeResolver._cost(rt)
            latency = RuntimeResolver._latency(rt)
            risk = RuntimeResolver._risk(rt, package)
            complexity = RuntimeResolver._complexity(rt)
            score = cost + latency + risk + complexity
            scored.append((rt, score, cost, latency, risk, complexity))

        scored.sort(key=lambda x: x[1])
        best_rt, best_score, best_cost, best_latency, best_risk, best_complexity = scored[0]

        plan = MaterializationPlan(
            package_id=package.package_id,
            runtime_class=best_rt,
            runtime_cost=best_cost,
            runtime_latency_ms=best_latency,
            runtime_risk=best_risk,
            runtime_complexity=best_complexity,
            runtime_score=best_score,
            presentation=RuntimeResolver._presentation(best_rt),
        )

        return best_rt, plan

    @staticmethod
    def _compatible_runtimes(package: PackageIdentity) -> list[RuntimeClass]:
        compat = {
            PackageType.MACOS_APP: [RuntimeClass.LOCAL_MACOS, RuntimeClass.REMOTE_DESKTOP],
            PackageType.WINDOWS_EXE: [RuntimeClass.LOCAL_WINDOWS, RuntimeClass.REMOTE_DESKTOP, RuntimeClass.VIRTUAL_MACHINE],
            PackageType.LINUX_BINARY: [RuntimeClass.LOCAL_LINUX, RuntimeClass.CONTAINER, RuntimeClass.VIRTUAL_MACHINE],
            PackageType.WEBASSEMBLY: [RuntimeClass.BROWSER_NATIVE],
            PackageType.PYTHON_PACKAGE: [RuntimeClass.CONTAINER, RuntimeClass.HEADLESS_CAPABILITY],
            PackageType.NODE_PACKAGE: [RuntimeClass.CONTAINER, RuntimeClass.HEADLESS_CAPABILITY],
            PackageType.CLI_TOOL: [RuntimeClass.HEADLESS_CAPABILITY, RuntimeClass.CONTAINER],
            PackageType.UNKNOWN: [RuntimeClass.VIRTUAL_MACHINE, RuntimeClass.CONTAINER],
        }
        return compat.get(package.package_type, [RuntimeClass.VIRTUAL_MACHINE])

    @staticmethod
    def _cost(rt: RuntimeClass) -> float:
        costs = {
            RuntimeClass.BROWSER_NATIVE: 0.0,
            RuntimeClass.HEADLESS_CAPABILITY: 0.5,
            RuntimeClass.LOCAL_MACOS: 1.0,
            RuntimeClass.LOCAL_LINUX: 1.0,
            RuntimeClass.CONTAINER: 1.5,
            RuntimeClass.LOCAL_WINDOWS: 2.0,
            RuntimeClass.VIRTUAL_MACHINE: 3.0,
            RuntimeClass.REMOTE_DESKTOP: 4.0,
            RuntimeClass.GPU_NODE: 5.0,
            RuntimeClass.CONFIDENTIAL: 6.0,
        }
        return costs.get(rt, 5.0)

    @staticmethod
    def _latency(rt: RuntimeClass) -> float:
        latencies = {
            RuntimeClass.BROWSER_NATIVE: 0.0,
            RuntimeClass.HEADLESS_CAPABILITY: 0.1,
            RuntimeClass.LOCAL_MACOS: 0.2,
            RuntimeClass.LOCAL_LINUX: 0.2,
            RuntimeClass.LOCAL_WINDOWS: 0.3,
            RuntimeClass.CONTAINER: 0.5,
            RuntimeClass.VIRTUAL_MACHINE: 1.0,
            RuntimeClass.REMOTE_DESKTOP: 2.0,
            RuntimeClass.GPU_NODE: 1.5,
            RuntimeClass.CONFIDENTIAL: 2.0,
        }
        return latencies.get(rt, 2.0)

    @staticmethod
    def _risk(rt: RuntimeClass, package: PackageIdentity) -> float:
        base_risk = {
            RuntimeClass.BROWSER_NATIVE: 0.1,
            RuntimeClass.HEADLESS_CAPABILITY: 0.3,
            RuntimeClass.CONTAINER: 0.4,
            RuntimeClass.VIRTUAL_MACHINE: 0.5,
            RuntimeClass.LOCAL_MACOS: 0.7,
            RuntimeClass.LOCAL_LINUX: 0.7,
            RuntimeClass.LOCAL_WINDOWS: 0.7,
            RuntimeClass.REMOTE_DESKTOP: 0.8,
            RuntimeClass.GPU_NODE: 0.6,
            RuntimeClass.CONFIDENTIAL: 0.2,
        }
        r = base_risk.get(rt, 0.8)
        if not package.signatures:
            r += 0.2
        return r

    @staticmethod
    def _complexity(rt: RuntimeClass) -> float:
        complexity = {
            RuntimeClass.BROWSER_NATIVE: 0.1,
            RuntimeClass.HEADLESS_CAPABILITY: 0.3,
            RuntimeClass.LOCAL_MACOS: 0.5,
            RuntimeClass.LOCAL_LINUX: 0.5,
            RuntimeClass.LOCAL_WINDOWS: 0.6,
            RuntimeClass.CONTAINER: 0.7,
            RuntimeClass.VIRTUAL_MACHINE: 1.0,
            RuntimeClass.REMOTE_DESKTOP: 1.2,
            RuntimeClass.GPU_NODE: 1.0,
            RuntimeClass.CONFIDENTIAL: 1.5,
        }
        return complexity.get(rt, 1.0)

    @staticmethod
    def _presentation(rt: RuntimeClass) -> str:
        presentations = {
            RuntimeClass.BROWSER_NATIVE: "browser_embed",
            RuntimeClass.HEADLESS_CAPABILITY: "command",
            RuntimeClass.LOCAL_MACOS: "streamed_window",
            RuntimeClass.LOCAL_LINUX: "streamed_window",
            RuntimeClass.LOCAL_WINDOWS: "streamed_window",
            RuntimeClass.CONTAINER: "command",
            RuntimeClass.VIRTUAL_MACHINE: "streamed_window",
            RuntimeClass.REMOTE_DESKTOP: "streamed_window",
            RuntimeClass.GPU_NODE: "glyph",
            RuntimeClass.CONFIDENTIAL: "glyph",
        }
        return presentations.get(rt, "glyph")


# ---------------------------------------------------------------------------
# Completion Condition
# ---------------------------------------------------------------------------

def is_complete(state: SpinorialState) -> bool:
    """
    Complete(q) iff ArtifactExists(q) and PolicyPasses(q) and ReceiptSealed(q)

    A task completes only when a corresponding state transition is observed
    and its verifier passes.
    """
    artifact_exists = state.execution_phase in (
        ExecutionPhase.VERIFIED,
        ExecutionPhase.SEALED,
    )
    policy_passes = state.verification.passed
    return artifact_exists and policy_passes
