#!/usr/bin/env python3
"""Unified OS — Scientific registry of all systems on this machine.

One registry. Seven layers. Every system accounted for.

Usage:
  python3 unified_os.py status          — full system status
  python3 unified_os.py layers          — show 7-layer taxonomy
  python3 unified_os.py layer <N>       — show systems in layer N
  python3 unified_os.py find <name>     — find system by name
  python3 unified_os.py lang            — language distribution
  python3 unified_os.py entry           — show all entry points
  python3 unified_os.py receipt         — write registry receipt
  python3 unified_os.py serve [--port 9999] — HTTP API + dashboard
"""

from __future__ import annotations
import json
import os
import sys
import time
import hashlib
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

ROOT = Path(__file__).parent.resolve()

# ── Layer constants ──
L_INFRA = 1
L_OBSERVE = 2
L_EXECUTE = 3
L_LEARN = 4
L_COGNITION = 5
L_VENTURE = 6
L_PRODUCT = 7

LAYER_NAMES = {
    L_INFRA: "Infrastructure",
    L_OBSERVE: "Observation & Telemetry",
    L_EXECUTE: "Execution & Automation",
    L_LEARN: "Learning Substrate",
    L_COGNITION: "Cognition & Policy",
    L_VENTURE: "Venture Proof",
    L_PRODUCT: "Product Launch",
}


@dataclass
class System:
    name: str
    layer: int
    path: str
    language: str
    description: str
    status: str = "active"  # active, experimental, quarantined, inactive
    entry_point: str = ""
    port: int = 0
    deps: list = field(default_factory=list)


# ── The Registry ──
# Every system on the machine, scientifically classified.

REGISTRY: list[System] = [

    # ── Layer 1: Infrastructure ──
    System("ReceiptLedger", L_INFRA, "receipt_ledger.py", "Python", "SHA-256 chained JSONL ledger"),
    System("HyperFlow", L_INFRA, "hyperflow/", "Python", "Task ledger, receipts, CLI, CI", entry_point="python3 hyperflow/hyperflow_cli.py"),
    System("AFCProtocol", L_INFRA, "afc_protocol.py", "Python", "Bonded claims + oracle settlement"),
    System("AFCServer", L_INFRA, "afc_server.py", "Python", "AFC protocol HTTP server"),
    System("GlyphLock", L_INFRA, "glyphlock.py", "Python", "Cryptographic key packs"),
    System("ProofBook", L_INFRA, "proofbook.py", "Python", "Decision memo hashing + storage"),
    System("ProofWallet", L_INFRA, "proofwallet.py", "Python", "Proof wallet"),
    System("ProofWalletConcierge", L_INFRA, "proofwallet_concierge/", "Swift", "Receipt concierge app", entry_point="swift run proofwallet_concierge"),
    System("ProofPulse", L_INFRA, "proofpulse/", "Swift", "Receipt pulse monitor", entry_point="swift run proofpulse"),
    System("CodeAppraiser", L_INFRA, "code_appraiser.py", "Python", "Code asset appraisal + Merkle proof verification", entry_point="python3 code_appraiser.py portfolio"),
    System("GlyphState", L_INFRA, "overandor-glythos/rpfbs/src/glyphstate.rs", "Rust", "9-verb state alphabet (O−M/=#!VR)"),
    System("RPFBS", L_INFRA, "overandor-glythos/rpfbs/", "Rust", "File-birth-state surface + compiler", entry_point="rpfbs glyph all"),
    System("FoldLang", L_INFRA, "foldlang/", "Python", "Fold language compiler + grammar"),
    System("OverLang", L_INFRA, "overlang.py", "Python", "Over language parser"),
    System("GlyphForge", L_INFRA, "glyphforge.py", "Python", "Glyph forging tool"),
    System("BlurHash64", L_INFRA, "blurhash64.py", "Python", "Perceptual fingerprint without reconstruction"),
    System("SonicGlyph64", L_INFRA, "sonicglyph64.py", "Python", "Audio glyph encoding"),
    System("AudioGlyph", L_INFRA, "audioglyph.py", "Python", "Audio-to-glyph pipeline"),
    System("UnimemLang", L_INFRA, "unimemlang/", "Python", "Unified memory language"),
    System("NyxML", L_INFRA, "nyxml/", "C", "Nyx XML core parser"),
    System("SPEC", L_INFRA, "SPEC/", "Markdown", "Protocol whitepapers, technical notes"),
    System("DataStore", L_INFRA, "data/", "Mixed", "Central data store"),
    System("Receipts", L_INFRA, "receipts/", "JSON", "Receipt storage"),
    System("AutopilotReceipts", L_INFRA, "autopilot_receipts/", "JSON", "Autopilot receipt storage"),
    System("Scripts", L_INFRA, "scripts/", "Shell", "Build/test/lint scripts"),
    System("CI", L_INFRA, ".github/workflows/", "YAML", "GitHub Actions CI/CD"),

    # ── Layer 2: Observation & Telemetry ──
    System("RAMFoldObserver", L_OBSERVE, "ramfold-research/ramfold/observer/", "Python", "Live vm_stat, swap, MLX, thermal probing"),
    System("RAMFoldDaemon", L_OBSERVE, "ramfold-research/ramfold_daemon.py", "Python", "HTTP daemon :8801, KV cache control", port=8801),
    System("BrowserTelemetry", L_OBSERVE, "browser_telemetry.py", "Python", "Browser state observation"),
    System("ScreenDB", L_OBSERVE, "screendb.py", "Python", "Screen capture DB + overlay"),
    System("LiveMonitor", L_OBSERVE, "live_monitor.py", "Python", "Real-time system monitor"),
    System("OverCPU", L_OBSERVE, "over_cpu.py", "Python", "CPU/process monitor"),
    System("ProbeAll", L_OBSERVE, "probe_all.py", "Python", "Multi-API path prober"),
    System("KPIs", L_OBSERVE, "kpis.py", "Python", "KPI collection"),
    System("HourlyMetrics", L_OBSERVE, "hourly_metrics_collector.py", "Python", "Hourly metrics collector"),
    System("ContentMetrics", L_OBSERVE, "content/", "JSON", "Bios, decisions, experiments, metrics"),
    System("SignalForge", L_OBSERVE, "signalforge.py", "Python", "Signal forging"),
    System("LayerCrawlerETL", L_OBSERVE, "layer_crawler_etl/", "Python", "Source registry, crawlers, ETL, scoring"),
    System("Mutewitness", L_OBSERVE, "mutewitness/", "Python", "Mutation witness server", entry_point="python3 mutewitness/server.py"),
    System("LOGS", L_OBSERVE, "LOGS/", "Log", "Central log directory"),
    System("RUNS", L_OBSERVE, "RUNS/", "Mixed", "Execution run artifacts"),

    # ── Layer 3: Execution & Automation ──
    System("BrowserBridge", L_EXECUTE, "browser_bridge/", "C++", "CDP browser hand: launch, click, inspect, screenshot"),
    System("SwiftSelenium", L_EXECUTE, "swift_selenium/", "Swift", "Native WKWebView automation, SHA-256 receipts", entry_point="swift run swiftselenium test"),
    System("NyxSemantic", L_EXECUTE, "nyx-semantic/", "Swift", "Semantic element location via TF-IDF (no selectors)", entry_point="swift run nyx-semantic test"),
    System("Nyx", L_EXECUTE, "nyx/", "Swift", "Nyx core"),
    System("NyxOllama", L_EXECUTE, "nyx-ollama/", "Swift", "Nyx + Ollama integration"),
    System("MicroCursor", L_EXECUTE, "microcursor/", "Swift", "Autopilot daemon, Q-table, macro detection", entry_point="swift run microcursor test"),
    System("AutonomousTine", L_EXECUTE, "tine-demo/", "Swift", "Second cursor for Mac, screen-aware execution"),
    System("SniffiesCompanion", L_EXECUTE, "sniffies_ai_companion/", "Python", "Policy engine, approval gates, action queue"),
    System("SniffyAI", L_EXECUTE, "sniffy_ai/", "Python", "AI companion data + logic"),
    System("SamsungCast", L_EXECUTE, "samsung_cast/", "C++", "DLNA client, HTTP server, TSMuxer, LLM engine"),
    System("TVHub", L_EXECUTE, "tv_hub/", "Mixed", "TV hub control"),
    System("TVStandard", L_EXECUTE, "tv_standard/", "Swift", "TV standard protocol"),
    System("ScreenMirrorPro", L_EXECUTE, "screenmirror_pro/", "Swift", "Screen mirroring"),
    System("AirPlayAgent", L_EXECUTE, "airplay_agent/", "Swift", "AirPlay agent"),
    System("ClipboardDesk", L_EXECUTE, "clipboard_desk/", "Swift", "Clipboard desk app"),
    System("VoiceMacRemote", L_EXECUTE, "voice_mac_remote/", "Mixed", "Voice-controlled Mac remote"),
    System("Relay", L_EXECUTE, "relay/", "Python", "Relay server", entry_point="python3 relay/app.py"),
    System("Echoscope", L_EXECUTE, "echoscope/", "HTML", "Echo scope visualizer"),
    System("Quarantine", L_EXECUTE, "_quarantine/", "Python", "Browser automation scripts (Selenium/Playwright)", status="quarantined"),
    System("Miners", L_EXECUTE, "miner1/", "Python", "CDP probe dumps, compliance ledgers", status="experimental"),

    # ── Layer 4: Learning Substrate ──
    System("HotTensorC", L_LEARN, "overglythswift/Sources/SubstrateC/hot_tensor.c", "C", "Truth-weighted hot tensor learning v3.0"),
    System("ColdTensor", L_LEARN, "overglythswift/Sources/SubstrateC/cold_tensor.c", "C", "Geometry-controlled learned compression (G1+G2)"),
    System("DeepLearning", L_LEARN, "overglythswift/Sources/SubstrateC/deep_learning.c", "C", "Deep learning primitives"),
    System("CausalModel", L_LEARN, "overglythswift/Sources/SubstrateC/causal_model.c", "C", "Causal modeling"),
    System("EpisodicMemory", L_LEARN, "overglythswift/Sources/SubstrateC/episodic_memory.c", "C", "Episodic memory system"),
    System("MemoryLattice", L_LEARN, "overglythswift/Sources/SubstrateC/memory_lattice.c", "C", "Memory lattice structure"),
    System("RewardKernel", L_LEARN, "overglythswift/Sources/SubstrateC/reward_kernel.c", "C", "Reward computation kernel"),
    System("CuriosityKernel", L_LEARN, "overglythswift/Sources/SubstrateC/curiosity_kernel.c", "C", "Curiosity-driven exploration"),
    System("TwinRiskKernel", L_LEARN, "overglythswift/Sources/SubstrateC/twin_risk_kernel.c", "C", "Twin risk assessment"),
    System("SpinorKnot", L_LEARN, "overglythswift/Sources/SubstrateC/spinor_knot.c", "C", "Spinor knot memory"),
    System("Consciousness", L_LEARN, "overglythswift/Sources/SubstrateC/consciousness.c", "C", "Consciousness model"),
    System("CognitiveBridge", L_LEARN, "overglythswift/Sources/SubstrateC/cognitive_bridge.c", "C", "Cognition layer bridge"),
    System("ShadowShardMForge", L_LEARN, "shadowshard_mforge/", "Python", "7-layer Apple-first intelligence substrate"),
    System("MacForgeTrainer", L_LEARN, "macforge_real_trainer/", "Python", "MLX/Metal trainer, LoRA adapters"),
    System("MacForgeStarters", L_LEARN, "macforge_micro_starters/", "Python", "30+ micro starter modules"),
    System("MLGlyph", L_LEARN, "glyph_ml.py", "Python", "ML pipeline for glyphs"),
    System("HFPipeline", L_LEARN, "hf_llm_pipeline.py", "Python", "Hugging Face LLM pipeline"),
    System("HFProxy", L_LEARN, "hf-proxy/", "JS", "HF proxy server"),
    System("OllamaNexus", L_LEARN, "ollama_nexus.py", "Python", "Ollama orchestration"),
    System("OneFileMLToken", L_LEARN, "onefile_ml_token_launcher.py", "Python", "Single-file ML token launcher"),
    System("AudioCascade", L_LEARN, "audio_cascade/", "Mixed", "Audio cascade, AGI session, hallucination engine"),

    # ── Layer 5: Cognition & Policy ──
    System("OverAntiLogic", L_COGNITION, "overantilogic/", "C++", "Anti-logic calculus, impossibility indexing"),
    System("OverAntiLogicDaemon", L_COGNITION, "OverAntiLogicDaemon/", "Swift", "Anti-logic daemon"),
    System("AntiGlyph", L_COGNITION, "anti_glyph.cpp", "C++", "Anti-glyph calculus"),
    System("Goliath", L_COGNITION, "goliath/", "Python", "Unified control plane :7777, 40+ endpoints", port=7777, entry_point="python3 goliath/launch.py"),
    System("AgentBridge", L_COGNITION, "agent_bridge/", "Python", "ChatGPT poller, bridge server, ETL, workflow"),
    System("MCPUUnified", L_COGNITION, "mcp/", "Python", "MCP unified server, HyperFlow bridge, Jorki MCP"),
    System("OverAgentDesk", L_COGNITION, "overagent_desk/", "Mixed", "OverAgent control plane"),
    System("SentinelDesk", L_COGNITION, "sentinel_desk/", "Mixed", "Sentinel monitoring desk"),
    System("SatanDesk", L_COGNITION, "satan_desk/", "Swift", "Satan desk app"),
    System("QuadrantOS", L_COGNITION, "quadrantos/", "Swift", "Quadrant OS CLI + app"),
    System("QuestionOS", L_COGNITION, "questionos/", "Python", "Question OS CLI"),
    System("SystemLake", L_COGNITION, "systemlake/", "Python", "System lake orchestrator"),
    System("LatentOS", L_COGNITION, "latentos/", "Python", "Latent OS app + core"),
    System("RealityWall", L_COGNITION, "reality_wall/", "JS", "Reality wall"),
    System("RealityCompiler", L_COGNITION, "reality_compiler.py", "Python", "Reality compiler"),
    System("Carpathian", L_COGNITION, "carpathian.py", "Python", "Carpathian engine"),
    System("OverAgentControl", L_COGNITION, "overagent_control_plane.py", "Python", "OverAgent control plane"),
    System("FortressGateway", L_COGNITION, "fortress_gateway.py", "Python", "Fortress gateway"),
    System("Orchestrator", L_COGNITION, "orchestrator.py", "Python", "System orchestrator"),
    System("AutonomousLoop", L_COGNITION, "autonomous_loop.py", "Python", "Autonomous execution loop"),
    System("AutonomousPipeline", L_COGNITION, "autonomous_pipeline.py", "Python", "Autonomous pipeline"),
    System("FreelanceAgent", L_COGNITION, "freelance_agent.py", "Python", "Freelance agent"),
    System("MacAgent", L_COGNITION, "mac_agent.py", "Python", "Mac agent"),
    System("MacRuntime", L_COGNITION, "mac_runtime.py", "Python", "Mac runtime"),
    System("MacPilot", L_COGNITION, "macpilot-0/", "Python", "Mac pilot actions, agent loop"),
    System("MacOSAutomation", L_COGNITION, "macos_automation/", "Python", "macOS automation CLI, Python bridge"),
    System("TrackGlyph", L_COGNITION, "trackglyph/", "Swift", "Track glyph app"),
    System("MirrorMind", L_COGNITION, "mirrormind/", "Swift", "Mirror mind app"),
    System("GlyphAura", L_COGNITION, "GlyphAura/", "Swift", "Glyph aura app"),
    System("MetalAgent", L_COGNITION, "MetalAgent/", "Swift", "Metal agent"),
    System("CodeForge", L_COGNITION, "codeforge/", "Swift", "Code forge"),
    System("YTLMCPLab", L_COGNITION, "ytl-mcp-lab/", "Python", "YTL MCP lab"),
    System("Skills", L_COGNITION, "skills/", "Python", "Skills system"),
    System("SkillsIntegration", L_COGNITION, "skills_integration/", "Python", "Skills integration"),

    # ── Layer 6: Venture Proof ──
    System("DealOS", L_VENTURE, "overglythswift/Sources/VentureProof/DealOS.swift", "Swift", "Multi-venture deal engine"),
    System("RaptureEngine", L_VENTURE, "overglythswift/Sources/VentureProof/RaptureEngine.swift", "Swift", "Idea ascension through proof R^1–R^10"),
    System("BreakthroughEngine", L_VENTURE, "overglythswift/Sources/VentureProof/BreakthroughVerificationEngine.swift", "Swift", "Claim verification + falsification"),
    System("DemandVerifier", L_VENTURE, "overglythswift/Sources/VentureProof/DemandVerificationEngine.swift", "Swift", "App Store demand verification"),
    System("PriorArtVerifier", L_VENTURE, "overglythswift/Sources/VentureProof/PriorArtVerifier+Sources.swift", "Swift", "Prior art risk mapping"),
    System("ShipOS", L_VENTURE, "overglythswift/Sources/VentureProof/ShipOS.swift", "Swift", "Clean release factory, launch packets"),
    System("RevenueOracle", L_VENTURE, "revenue_oracle/", "Python", "Revenue prediction oracle"),
    System("RevenueStore", L_VENTURE, "revenue_store.py", "Python", "Revenue store"),
    System("MoneyDashboard", L_VENTURE, "money_dashboard.py", "Python", "Money dashboard"),
    System("ComputeCapital", L_VENTURE, "compute_capital.py", "Python", "Compute capital tracker"),
    System("Broll", L_VENTURE, "broll/", "Python", "Video lake: evidence, investigation, media compiler"),
    System("EvidenceScorer", L_VENTURE, "evidence_scorer.py", "Python", "Evidence scoring"),
    System("ContentMonetizer", L_VENTURE, "content_monetizer.py", "Python", "Content monetization"),
    System("POptimizer", L_VENTURE, "poptimizer.py", "Python", "P-optimizer"),
    System("POptimizerETL", L_VENTURE, "poptimizer_etl_engine.py", "Python", "P-optimizer ETL engine"),
    System("Masseuros", L_VENTURE, "masseuros/", "Python", "A/B testing, attribution, competitive analysis"),
    System("RMTraffic", L_VENTURE, "rm_traffic/", "Python", "Traffic system, bio generators"),
    System("RMAGI", L_VENTURE, "rm_agi/", "Python", "RM AGI engine"),
    System("RMEngagement", L_VENTURE, "rm_engagement_daemon.py", "Python", "RM engagement daemon"),
    System("TrafficOverclock", L_VENTURE, "traffic_overclock.py", "Python", "Traffic overclock AI layer"),
    System("ClientPulse", L_VENTURE, "clientpulse.py", "Python", "Client pulse tracker"),
    System("BookingLedger", L_VENTURE, "booking_ledger.py", "Python", "Booking ledger"),
    System("Rentmasseur", L_VENTURE, "rentmasseur_avail.py", "Python", "RentMasseur availability/login/setting"),
    System("Jorki", L_VENTURE, "jorki/", "Python", "Jorki AI file gateway"),
    System("AutonomousProducts", L_VENTURE, "autonomous_products/", "Python", "ForgeRun, GridRun, LinkOps, TaskForge"),

    # ── Layer 7: Product Launch ──
    System("Autopilot", L_PRODUCT, "autopilot.py", "Python", "Generate → build → sign → notarize → submit"),
    System("AutopilotApps", L_PRODUCT, "autopilot_apps/", "Swift", "10 built apps: CleanSweep, ClipFlow, etc."),
    System("AutopilotTemplates", L_PRODUCT, "autopilot_templates/", "Swift", "App templates for generation"),
    System("AppStoreSubmitter", L_PRODUCT, "app_store_submitter.py", "Python", "ASC API / altool submission"),
    System("ASCClient", L_PRODUCT, "asc_client.py", "Python", "App Store Connect client"),
    System("AppScraper", L_PRODUCT, "app_scraper.py", "Python", "App Store scraping + enrichment"),
    System("Frontend", L_PRODUCT, "frontend/", "React", "React frontend"),
    System("NextApp", L_PRODUCT, "app/", "Next.js", "Next.js app"),
    System("NoVNC", L_PRODUCT, "noVNC/", "JS", "NoVNC web client"),
    System("OverGlythCLI", L_PRODUCT, "overglythswift/Sources/OverGlythCLI/", "Swift", "Unified CLI (astropilotd)", entry_point="swift run astropilotd"),
    System("OverGlythApp", L_PRODUCT, "overglythswift/Sources/GlyphOSApp/", "Swift", "Desktop app with all panels"),
    System("AgentVM", L_PRODUCT, "overglythswift/Sources/AgentVM/", "Swift", "Agent VM controller + view"),
    System("BOAProtocol", L_PRODUCT, "overandor-glythos/rpfbs/src/boa_protocol.rs", "Rust", "Birth of Agent protocol"),
    System("MediaOrganism", L_PRODUCT, "overandor-glythos/rpfbs/src/media_organism.rs", "Rust", "Receipted media engine"),
    System("FrontierForge", L_PRODUCT, "overandor-glythos/rpfbs/src/frontier_forge.rs", "Rust", "Real mutation + sandbox builds"),
    System("TwinOS", L_PRODUCT, "overandor-glythos/rpfbs/src/twin_os.rs", "Rust", "Twin execution with real commands"),
    System("Metal932", L_PRODUCT, "overandor-glythos/metal932/", "Python", "Glyph932 compiler, 67 symbols"),
    System("OverGlythCompiler", L_PRODUCT, "overandor-glythos/compiler/", "Python", "Glyth compiler"),
    System("OverGlythRuntime", L_PRODUCT, "overandor-glythos/runtime/", "Python", "Runtime engine"),
    System("RoboJoseph", L_PRODUCT, "overandor-glythos/RoboJoseph/", "Swift", "RoboJoseph app + widget"),
    System("ChatGPTExports", L_PRODUCT, "chatgpt_exports/", "Markdown", "ChatGPT conversation exports"),
    System("Tests", L_PRODUCT, "tests/", "Python", "Test suite"),
    System("Docs", L_PRODUCT, "docs/", "Markdown", "Documentation"),
]


# ── Registry operations ──

def by_layer(layer: int) -> list[System]:
    return [s for s in REGISTRY if s.layer == layer]


def by_name(name: str) -> Optional[System]:
    name_lower = name.lower()
    for s in REGISTRY:
        if name_lower in s.name.lower():
            return s
    return None


def language_distribution() -> dict:
    dist = {}
    for s in REGISTRY:
        lang = s.language
        dist[lang] = dist.get(lang, 0) + 1
    return dict(sorted(dist.items(), key=lambda x: -x[1]))


def entry_points() -> list[System]:
    return [s for s in REGISTRY if s.entry_point]


def ports() -> list[System]:
    return [s for s in REGISTRY if s.port > 0]


def check_path_exists(s: System) -> bool:
    return (ROOT / s.path).exists()


def registry_hash() -> str:
    content = json.dumps([asdict(s) for s in REGISTRY], sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def write_receipt() -> str:
    receipt_dir = ROOT / "receipts"
    receipt_dir.mkdir(exist_ok=True)
    ts = int(time.time())
    h = registry_hash()
    receipt = {
        "type": "unified_os_registry",
        "timestamp": ts,
        "registry_hash": h,
        "total_systems": len(REGISTRY),
        "layers": {str(k): len(by_layer(k)) for k in range(1, 8)},
        "languages": language_distribution(),
    }
    path = receipt_dir / f"unified_os_{ts}.json"
    path.write_text(json.dumps(receipt, indent=2))
    return str(path)


# ── CLI ──

def cmd_status():
    total = len(REGISTRY)
    existing = sum(1 for s in REGISTRY if check_path_exists(s))
    print(f"\n{'='*60}")
    print(f"  UNIFIED OS — System Registry")
    print(f"{'='*60}")
    print(f"  Total systems:  {total}")
    print(f"  Paths verified: {existing}/{total}")
    print(f"  Registry hash:  {registry_hash()}")
    print(f"{'='*60}\n")
    for layer in range(1, 8):
        systems = by_layer(layer)
        print(f"  Layer {layer} — {LAYER_NAMES[layer]} ({len(systems)} systems)")
    print(f"\n  Entry points: {len(entry_points())}")
    print(f"  HTTP ports:   {len(ports())}")
    print()


def cmd_layers():
    for layer in range(1, 8):
        systems = by_layer(layer)
        print(f"\n{'─'*60}")
        print(f"  Layer {layer} — {LAYER_NAMES[layer]}")
        print(f"{'─'*60}")
        for s in systems:
            exists = "✅" if check_path_exists(s) else "❌"
            print(f"  {exists} {s.name:<25} {s.language:<8} {s.path}")
    print()


def cmd_layer(n: int):
    systems = by_layer(n)
    print(f"\n  Layer {n} — {LAYER_NAMES[n]} ({len(systems)} systems)\n")
    for s in systems:
        exists = "✅" if check_path_exists(s) else "❌"
        status = f"[{s.status}]" if s.status != "active" else ""
        port = f":{s.port}" if s.port else ""
        print(f"  {exists} {s.name:<25} {s.language:<8} {s.path:<45} {port} {status}")
        if s.entry_point:
            print(f"      → {s.entry_point}")
    print()


def cmd_find(name: str):
    s = by_name(name)
    if not s:
        print(f"  Not found: {name}")
        return
    print(f"\n  Name:     {s.name}")
    print(f"  Layer:    {s.layer} — {LAYER_NAMES[s.layer]}")
    print(f"  Path:     {s.path}")
    print(f"  Language: {s.language}")
    print(f"  Status:   {s.status}")
    print(f"  Desc:     {s.description}")
    if s.entry_point:
        print(f"  Entry:    {s.entry_point}")
    if s.port:
        print(f"  Port:     {s.port}")
    exists = check_path_exists(s)
    print(f"  Exists:   {'✅' if exists else '❌'}")
    print()


def cmd_lang():
    dist = language_distribution()
    print(f"\n  Language Distribution ({len(REGISTRY)} systems)\n")
    for lang, count in dist.items():
        bar = "█" * count
        print(f"  {lang:<12} {bar} {count}")
    print()


def cmd_entry():
    print(f"\n  Entry Points ({len(entry_points())})\n")
    for s in entry_points():
        print(f"  {s.name:<25} → {s.entry_point}")
    print(f"\n  HTTP Ports ({len(ports())})\n")
    for s in ports():
        print(f"  {s.name:<25} → :{s.port}")
    print()


def cmd_receipt():
    path = write_receipt()
    print(f"  Receipt written: {path}")
    print(f"  Registry hash:   {registry_hash()}")
    print(f"  Total systems:   {len(REGISTRY)}")


def cmd_serve(port: int = 9999):
    try:
        from flask import Flask, jsonify, render_template_string
    except ImportError:
        print("  Flask not installed. Run: pip install flask")
        return

    app = Flask(__name__, static_folder=None)

    DASHBOARD = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Unified OS</title>
<style>
:root{--bg:#08080a;--s:#0e0e12;--b:#1e1e26;--t:#e0e0e0;--t2:#666;--o:#ff6b1a;--g:#7ec8a0;--r:#ff4466;--c:#00d4ff;}
*{box-sizing:border-box;margin:0;padding:0;font-family:'SF Mono',monospace;}
body{background:var(--bg);color:var(--t);min-height:100vh;}
h{padding:1rem 2rem;border-bottom:1px solid var(--b);display:flex;align-items:center;gap:1rem;}
h h1{font-size:1rem;color:var(--o);letter-spacing:.08em;}
.layer{padding:1rem 2rem;border-bottom:1px solid var(--b);}
.layer-title{font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;color:var(--t2);margin-bottom:.6rem;}
.sys{display:grid;grid-template-columns:20px 200px 80px 1fr 60px;gap:.5rem;padding:.3rem 0;font-size:.75rem;align-items:center;}
.sys:hover{background:var(--s);}
.sys .ok{color:var(--g);} .sys .no{color:var(--r);}
.sys .lang{color:var(--c);font-size:.65rem;}
.sys .path{color:var(--t2);font-size:.65rem;}
.sys .port{color:var(--o);}
.kpi{display:flex;gap:2rem;padding:1rem 2rem;border-bottom:1px solid var(--b);}
.kpi .v{font-size:1.5rem;color:var(--o);} .kpi .l{font-size:.6rem;color:var(--t2);text-transform:uppercase;}
</style></head><body>
<h><h1>◉ UNIFIED OS</h1><span style="color:var(--t2);font-size:.7rem">Scientific Registry</span></h>
<div class="kpi">
<div><div class="v" id="total">-</div><div class="l">Systems</div></div>
<div><div class="v" id="layers">7</div><div class="l">Layers</div></div>
<div><div class="v" id="langs">-</div><div class="l">Languages</div></div>
<div><div class="v" id="ports">-</div><div class="l">HTTP Ports</div></div>
</div>
<div id="layers-container"></div>
<script>
async function load(){
const s=await fetch('/api/registry').then(r=>r.json());
document.getElementById('total').textContent=s.total;
document.getElementById('langs').textContent=Object.keys(s.languages).length;
document.getElementById('ports').textContent=s.ports.length;
const c=document.getElementById('layers-container');
c.innerHTML=s.layers.map(l=>`
<div class="layer"><div class="layer-title">Layer ${l.num} — ${l.name} (${l.systems.length})</div>
${l.systems.map(s=>`<div class="sys"><span class="${s.exists?'ok':'no'}">${s.exists?'✅':'❌'}</span><span>${s.name}</span><span class="lang">${s.language}</span><span class="path">${s.path}</span><span class="port">${s.port?':'+s.port:''}</span></div>`).join('')}
</div>`).join('');
}
load();
</script></body></html>"""

    @app.route("/")
    def index():
        return render_template_string(DASHBOARD)

    @app.route("/api/registry")
    def api_registry():
        layers_data = []
        for n in range(1, 8):
            systems = by_layer(n)
            layers_data.append({
                "num": n,
                "name": LAYER_NAMES[n],
                "systems": [{
                    "name": s.name,
                    "language": s.language,
                    "path": s.path,
                    "exists": check_path_exists(s),
                    "port": s.port,
                    "status": s.status,
                    "entry_point": s.entry_point,
                    "description": s.description,
                } for s in systems]
            })
        return jsonify({
            "total": len(REGISTRY),
            "registry_hash": registry_hash(),
            "layers": layers_data,
            "languages": language_distribution(),
            "ports": [{"name": s.name, "port": s.port} for s in ports()],
        })

    @app.route("/api/system/<name>")
    def api_system(name):
        s = by_name(name)
        if not s:
            return jsonify({"error": "not found"}), 404
        d = asdict(s)
        d["exists"] = check_path_exists(s)
        return jsonify(d)

    @app.route("/api/layers")
    def api_layers():
        return jsonify({
            str(n): {"name": LAYER_NAMES[n], "count": len(by_layer(n))}
            for n in range(1, 8)
        })

    print(f"\n  Unified OS dashboard: http://localhost:{port}")
    print(f"  API: http://localhost:{port}/api/registry\n")
    app.run(host="0.0.0.0", port=port, debug=False)


def main():
    if len(sys.argv) < 2:
        cmd_status()
        return

    cmd = sys.argv[1]
    if cmd == "status":
        cmd_status()
    elif cmd == "layers":
        cmd_layers()
    elif cmd == "layer":
        if len(sys.argv) < 3:
            print("Usage: unified_os.py layer <N>")
            return
        cmd_layer(int(sys.argv[2]))
    elif cmd == "find":
        if len(sys.argv) < 3:
            print("Usage: unified_os.py find <name>")
            return
        cmd_find(sys.argv[2])
    elif cmd == "lang":
        cmd_lang()
    elif cmd == "entry":
        cmd_entry()
    elif cmd == "receipt":
        cmd_receipt()
    elif cmd == "serve":
        port = 9999
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            port = int(sys.argv[idx + 1])
        cmd_serve(port)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
