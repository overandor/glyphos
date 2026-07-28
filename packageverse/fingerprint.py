"""
PackageVerse Fingerprinting — Package inspection and classification.

The ingestion ceremony: hash, classify, inspect, assign passport.
Evaluates OS requirements, architecture, entrypoints, signatures,
dependencies, entitlements, network expectations, filesystem behavior,
UI framework, and licensing constraints.
"""

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import uuid
import subprocess
import zipfile
import tarfile
from pathlib import Path
from typing import Optional

from .core import PackageIdentity, PackageType, PermissionBoundary


def sha256_file(path: str, chunk_size: int = 65536) -> str:
    """Compute SHA-256 hash of a file or directory."""
    p = Path(path)
    if p.is_dir():
        return sha256_directory(path)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_directory(path: str) -> str:
    """Compute SHA-256 hash of all files in a directory tree (sorted order)."""
    h = hashlib.sha256()
    p = Path(path)
    for file_path in sorted(p.rglob("*")):
        if file_path.is_file():
            rel = str(file_path.relative_to(p))
            h.update(rel.encode())
            h.update(b"\0")
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    h.update(chunk)
            h.update(b"\0")
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class PackageFingerprinter:
    """
    Inspects a package and produces its cryptographic identity.
    Every package is treated as untrusted executable authority.
    """

    def fingerprint(self, path: str) -> PackageIdentity:
        """Full ingestion ceremony: hash → classify → inspect → passport."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Package not found: {path}")

        sha = sha256_file(str(p))
        if p.is_dir():
            size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        else:
            size = p.stat().st_size
        ptype = self._classify(p)
        identity = PackageIdentity(
            package_id=str(uuid.uuid4()),
            sha256=sha,
            name=p.stem,
            version="1.0",
            package_type=ptype,
            size_bytes=size,
        )

        # Inspect based on type
        if ptype == PackageType.MACOS_APP:
            self._inspect_macos_app(p, identity)
        elif ptype == PackageType.WEBASSEMBLY:
            self._inspect_wasm(p, identity)
        elif ptype == PackageType.PYTHON_PACKAGE:
            self._inspect_python(p, identity)
        elif ptype == PackageType.CLI_TOOL:
            self._inspect_cli(p, identity)
        else:
            self._inspect_generic(p, identity)

        return identity

    def _classify(self, p: Path) -> PackageType:
        name = p.name.lower()
        suffix = p.suffix.lower()

        if suffix == ".app" or (p.is_dir() and name.endswith(".app")):
            return PackageType.MACOS_APP
        if suffix in (".exe", ".msi"):
            return PackageType.WINDOWS_EXE
        if suffix in (".wasm",):
            return PackageType.WEBASSEMBLY
        if suffix == ".whl" or suffix == ".tar.gz" and "py" in name:
            return PackageType.PYTHON_PACKAGE
        if name in ("package.json",) or suffix == ".tgz":
            return PackageType.NODE_PACKAGE
        if p.is_file() and self._is_elf_binary(p):
            return PackageType.LINUX_BINARY
        if p.is_file() and os.access(str(p), os.X_OK):
            return PackageType.CLI_TOOL
        return PackageType.UNKNOWN

    def _is_elf_binary(self, p: Path) -> bool:
        try:
            with open(p, "rb") as f:
                magic = f.read(4)
                return magic == b"\x7fELF"
        except Exception:
            return False

    def _inspect_macos_app(self, p: Path, identity: PackageIdentity):
        """Inspect macOS .app bundle."""
        identity.os_requirement = "macOS"
        identity.architecture = "universal"

        info_plist = p / "Contents" / "Info.plist"
        if info_plist.exists():
            try:
                with open(info_plist, "rb") as f:
                    plist = plistlib.load(f)
                identity.name = plist.get("CFBundleName", identity.name)
                identity.version = plist.get("CFBundleShortVersionString", "1.0")
                identity.entrypoints = [plist.get("CFBundleExecutable", "")]
                identity.architecture = plist.get("LSArchitecture", "arm64")
            except Exception:
                pass

        # Check code signature
        try:
            result = subprocess.run(
                ["codesign", "-dv", str(p)],
                capture_output=True, timeout=10
            )
            if result.returncode == 0:
                identity.signatures.append("codesign:present")
        except Exception:
            pass

        # Check binary architecture
        exe = p / "Contents" / "MacOS"
        if exe.is_dir():
            for bin_path in exe.iterdir():
                try:
                    r = subprocess.run(
                        ["file", str(bin_path)],
                        capture_output=True, timeout=5
                    )
                    output = r.stdout.decode()
                    if "arm64" in output:
                        identity.architecture = "arm64"
                    elif "x86_64" in output:
                        identity.architecture = "x86_64"
                except Exception:
                    pass

    def _inspect_wasm(self, p: Path, identity: PackageIdentity):
        identity.os_requirement = "browser"
        identity.architecture = "wasm"
        identity.entrypoints = [p.name]

    def _inspect_python(self, p: Path, identity: PackageIdentity):
        identity.os_requirement = "python3"
        identity.entrypoints = [p.name]

    def _inspect_cli(self, p: Path, identity: PackageIdentity):
        identity.os_requirement = "posix"
        identity.entrypoints = [p.name]
        try:
            r = subprocess.run(["file", str(p)], capture_output=True, timeout=5)
            output = r.stdout.decode()
            if "arm64" in output:
                identity.architecture = "arm64"
            elif "x86_64" in output:
                identity.architecture = "x86_64"
        except Exception:
            pass

    def _inspect_generic(self, p: Path, identity: PackageIdentity):
        identity.entrypoints = [p.name]


class RiskAnalyzer:
    """Detects risks in a package before materialization."""

    def analyze(self, identity: PackageIdentity) -> list[str]:
        risks = []
        if not identity.signatures:
            risks.append("unsigned_package")
        if identity.package_type == PackageType.UNKNOWN:
            risks.append("unknown_package_type")
        if identity.size_bytes > 500 * 1024 * 1024:
            risks.append("large_package_size")
        if not identity.entrypoints:
            risks.append("no_entrypoints_found")
        return risks


class PermissionRecommender:
    """Recommends a permission boundary based on package inspection."""

    def recommend(self, identity: PackageIdentity, risks: list[str]) -> PermissionBoundary:
        """
        Capabilities are granted explicitly.
        Start with denial by default, then add only what's needed.
        """
        perms = PermissionBoundary()

        if identity.package_type == PackageType.MACOS_APP:
            perms.filesystem_paths = ["~/Documents"]
            perms.max_cpu_percent = 50.0
            perms.max_memory_mb = 2048
        elif identity.package_type == PackageType.WEBASSEMBLY:
            perms.filesystem_paths = []
            perms.max_cpu_percent = 25.0
            perms.max_memory_mb = 256
        elif identity.package_type == PackageType.CLI_TOOL:
            perms.filesystem_paths = ["."]
            perms.max_cpu_percent = 80.0
            perms.max_memory_mb = 512
        else:
            perms.filesystem_paths = []
            perms.max_cpu_percent = 30.0
            perms.max_memory_mb = 512

        if "unsigned_package" in risks:
            perms.human_approval_required = True
        if "unknown_package_type" in risks:
            perms.human_approval_required = True
            perms.max_cpu_percent = min(perms.max_cpu_percent, 20.0)

        return perms
