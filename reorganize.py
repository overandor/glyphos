#!/usr/bin/env python3
"""Directory Reorganization Plan — Move systems into 7 layer folders.

This script GENERATES A PLAN only. It does not move anything.
Review the plan, then run with --execute to perform the moves.

Usage:
  python3 reorganize.py --plan       — show the move plan
  python3 reorganize.py --execute    — perform the moves
  python3 reorganize.py --symlinks   — create symlinks instead of moving

Strategy:
  - Create L1_Infrastructure/, L2_Observation/, ..., L7_Product/ directories
  - Move each system directory/file into its layer folder
  - Root-level Python files stay in root (too many cross-imports)
  - Git history preserved (git mv)
"""

from __future__ import annotations
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# Import the registry
sys.path.insert(0, str(ROOT))
from unified_os import REGISTRY, LAYER_NAMES

# Systems that should NOT be moved (root-level infrastructure, shared)
DO_NOT_MOVE = {
    "ReceiptLedger", "HyperFlow", "AFCProtocol", "AFCServer",
    "GlyphLock", "ProofBook", "ProofWallet", "CodeAppraiser",
    "OverLang", "GlyphForge", "BlurHash64", "SonicGlyph64", "AudioGlyph",
    "SPEC", "DataStore", "Receipts", "AutopilotReceipts", "Scripts", "CI",
    "LOGS", "RUNS", "Tests", "Docs", "Assets", "Dist", "Build",
    "Goliath", "UnifiedOS",  # root controllers
    # Root Python files that are entry points
    "Autopilot", "AppStoreSubmitter", "ASCClient", "Orchestrator",
    "AutonomousLoop", "AutonomousPipeline", "RunAll", "LaunchAll",
}

# Systems that are directories and can be moved
def get_move_plan() -> list[tuple[str, str, str]]:
    """Returns list of (system_name, source_path, dest_path)"""
    moves = []
    layer_dirs = {
        1: "L1_Infrastructure",
        2: "L2_Observation",
        3: "L3_Execution",
        4: "L4_Learning",
        5: "L5_Cognition",
        6: "L6_Venture",
        7: "L7_Product",
    }

    for s in REGISTRY:
        if s.name in DO_NOT_MOVE:
            continue

        src = ROOT / s.path
        if not src.exists():
            continue
        if src.is_file() and s.path.endswith(".py") and "/" not in s.path:
            continue  # Skip root Python files

        layer_dir = ROOT / layer_dirs[s.layer]
        dst = layer_dir / src.name

        # Don't move if already in a layer dir or is a root structure
        if src.parent == ROOT and not src.is_dir():
            continue

        moves.append((s.name, str(src.relative_to(ROOT)), str(dst.relative_to(ROOT))))

    return moves


def show_plan():
    moves = get_move_plan()
    print(f"\n  Directory Reorganization Plan")
    print(f"  {len(moves)} systems to reorganize\n")

    by_layer = {}
    for name, src, dst in moves:
        layer_num = int(dst.split("_")[0][1:])
        if layer_num not in by_layer:
            by_layer[layer_num] = []
        by_layer[layer_num].append((name, src, dst))

    for layer in sorted(by_layer.keys()):
        items = by_layer[layer]
        print(f"  Layer {layer} — {LAYER_NAMES[layer]} ({len(items)} moves)")
        print(f"  {'─'*50}")
        for name, src, dst in items:
            print(f"    {name:<25} {src:<35} → {dst}")
        print()

    print(f"  Total: {len(moves)} moves")
    print(f"\n  To execute: python3 reorganize.py --execute")
    print(f"  To symlink: python3 reorganize.py --symlinks")


def execute_moves(use_symlinks=False):
    moves = get_move_plan()
    print(f"\n  Executing {len(moves)} moves...\n")

    layer_dirs = {
        1: "L1_Infrastructure",
        2: "L2_Observation",
        3: "L3_Execution",
        4: "L4_Learning",
        5: "L5_Cognition",
        6: "L6_Venture",
        7: "L7_Product",
    }

    # Create layer directories
    for d in layer_dirs.values():
        (ROOT / d).mkdir(exist_ok=True)
        print(f"  ✓ Created {d}/")

    print()

    success = 0
    failed = 0
    for name, src_rel, dst_rel in moves:
        src = ROOT / src_rel
        dst = ROOT / dst_rel

        try:
            if dst.exists():
                print(f"  ⚠ Skip {name}: destination exists {dst_rel}")
                failed += 1
                continue

            if use_symlinks:
                os.symlink(src, dst)
                print(f"  → Symlinked {name}: {src_rel} → {dst_rel}")
            else:
                # Try git mv first, fall back to regular move
                result = os.system(f"cd {ROOT} && git mv '{src_rel}' '{dst_rel}' 2>/dev/null")
                if result != 0:
                    import shutil
                    shutil.move(str(src), str(dst))
                print(f"  → Moved {name}: {src_rel} → {dst_rel}")
            success += 1
        except Exception as e:
            print(f"  ✗ Failed {name}: {e}")
            failed += 1

    print(f"\n  Done: {success} success, {failed} failed")


def main():
    if len(sys.argv) < 2:
        show_plan()
        return

    cmd = sys.argv[1]
    if cmd == "--plan":
        show_plan()
    elif cmd == "--execute":
        execute_moves(use_symlinks=False)
    elif cmd == "--symlinks":
        execute_moves(use_symlinks=True)
    else:
        print(f"Unknown: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
