# SYSTEM MAP — Scientific Taxonomy of the Overandor/GlyphOS Machine

**Generated**: 2026-07-23
**Total systems**: 110+ directories, 144 root Python files, 18 Swift packages, 2 C++ projects, 9 Rust modules, 7 JS/TS projects
**Total code**: ~83,567 lines Python (root only), 264 Swift files, 28 C++ files, 20 C files, 9 Rust modules

---

## Taxonomy: 7 Scientific Layers

Every system on this machine belongs to exactly one layer. Layers are stacked — higher layers depend on lower ones.

```
Layer 7 — PRODUCT LAUNCH     (ship apps to market)
Layer 6 — VENTURE PROOF      (prove ideas have value)
Layer 5 — COGNITION & POLICY (think, decide, gate)
Layer 4 — LEARNING SUBSTRATE (train, compress, adapt)
Layer 3 — EXECUTION & AUTOMATION (act on screen/browser)
Layer 2 — OBSERVATION & TELEMETRY (see the machine)
Layer 1 — INFRASTRUCTURE     (receipts, ledgers, protocols)
```

---

## Layer 1 — INFRASTRUCTURE (Receipts, Ledgers, Protocols)

The foundation. Every action above produces a receipt here.

| System | Path | Language | Status | Description |
|--------|------|----------|--------|-------------|
| ReceiptLedger | `receipt_ledger.py` | Python | ✅ Active | SHA-256 chained JSONL ledger, tamper-evident |
| HyperFlow | `hyperflow/` | Python | ✅ Active | Task ledger, receipts, CLI, CI integration |
| AFC Protocol | `afc_protocol.py`, `afc_server.py` | Python | ✅ Active | Bonded claims + oracle settlement for information goods |
| GlyphLock | `glyphlock.py`, `glyphlock_data/` | Python | ✅ Active | Cryptographic key packs, signed artifacts |
| ProofBook | `proofbook.py`, `proofbook_integration/` | Python | ✅ Active | Hash, store, reference decision memos as auditable evidence |
| ProofWallet | `proofwallet.py`, `proofwallet_concierge/` | Swift/Python | ✅ Active | Proof wallet, receipt concierge app |
| ProofPulse | `proofpulse/` | Swift | ✅ Active | Receipt pulse monitor |
| Code Appraiser | `code_appraiser.py` | Python | ✅ Active | Code asset appraisal + Merkle proof distance verification |
| GlyphState | `overandor-glythos/rpfbs/src/glyphstate.rs` | Rust | ✅ Active | Unifying 9-verb state alphabet (O−M/=#!VR) |
| RPFBS | `overandor-glythos/rpfbs/` | Rust | ✅ Active | File-birth-state surface, compiler, grammar |
| FoldLang | `foldlang/` | Python | ✅ Active | Fold language compiler + grammar |
| OverLang | `overlang.py`, `overlang_*.py`, `overlanguage.py` | Python | ✅ Active | Over language parser, file ops, types |
| GlyphForge | `glyphforge.py` | Python | ✅ Active | Glyph forging tool |
| BlurHash64 | `blurhash64.py` | Python | ✅ Active | Perceptual fingerprint without reconstruction |
| SonicGlyph64 | `sonicglyph64.py` | Python | ✅ Active | Audio glyph encoding |
| AudioGlyph | `audioglyph.py` | Python | ✅ Active | Audio-to-glyph pipeline |
| UnimemLang | `unimemlang/` | Python | ✅ Active | Unified memory language |
| NyxML | `nyxml/` | C | ✅ Active | Nyx XML core parser |
| SPEC | `SPEC/` | Markdown | ✅ Active | Protocol whitepapers, technical notes |
| Data | `data/` | Mixed | ✅ Active | Central data store (DBs, proofs, indexes, audits) |
| Receipts | `receipts/`, `autopilot_receipts/` | JSON | ✅ Active | Receipt storage |
| Scripts | `scripts/`, `hyperflow/scripts/` | Shell | ✅ Active | Build/test/lint scripts |
| CI | `ci/`, `.github/workflows/` | YAML | ✅ Active | GitHub Actions CI/CD |

---

## Layer 2 — OBSERVATION & TELEMETRY (See the Machine)

Sensors that observe system state, screen, memory, processes.

| System | Path | Language | Status | Description |
|--------|------|----------|--------|-------------|
| RAMFold Observer | `ramfold-research/ramfold/observer/` | Python | ✅ Active | Live vm_stat, swap, MLX memory, thermal probing |
| RAMFold Daemon | `ramfold-research/ramfold_daemon.py` | Python | ✅ Active | HTTP daemon :8801, KV cache control, memory monitor |
| Browser Telemetry | `browser_telemetry.py` | Python | ✅ Active | Browser state observation |
| ScreenDB | `screendb.py`, `screendb_*.py` | Python | ✅ Active | Screen capture DB, overlay, voice |
| Live Monitor | `live_monitor.py` | Python | ✅ Active | Real-time system monitor |
| OverCPU | `over_cpu.py` | Python | ✅ Active | CPU/process monitor |
| ProbeAll | `probe_all.py` | Python | ✅ Active | Multi-API path prober |
| KPIs | `kpis.py`, `hourly_metrics_collector.py` | Python | ✅ Active | KPI collection + hourly metrics |
| Content Metrics | `content/` | JSON | ✅ Active | Bios, decisions, experiments, metrics ingest |
| SignalForge | `signalforge.py`, `signalforge_data/` | Python | ✅ Active | Signal forging + data |
| QRC Spider | `qrc_spider.py`, `qrc_spider_out/` | Python | ✅ Active | QRC spider output |
| Layer Crawler ETL | `layer_crawler_etl/`, `layer_crawler.py` | Python | ✅ Active | Source registry, crawlers, ETL, scoring |
| Mutewitness | `mutewitness/` | Python | ✅ Active | Mutation witness server |
| Snapshots | `snapshots/` | Mixed | ✅ Active | System snapshots |
| LOGS | `LOGS/` | Log | ✅ Active | Central log directory |
| RUNS | `RUNS/` | Mixed | ✅ Active | Execution run artifacts |

---

## Layer 3 — EXECUTION & AUTOMATION (Act on Screen/Browser)

Hands that execute actions in browsers, on desktop, on devices.

| System | Path | Language | Status | Description |
|--------|------|----------|--------|-------------|
| BrowserBridge | `browser_bridge/` | C++ | ✅ Active | CDP browser hand: launch, click, inspect, screenshot, receipts |
| SwiftSelenium | `swift_selenium/` | Swift/C | ✅ Active | Native WKWebView browser automation, SHA-256 receipts |
| NyxSemantic | `nyx-semantic/` | Swift | ✅ Active | Semantic element location via TF-IDF (no selectors) |
| Nyx | `nyx/` | Swift/C | ✅ Active | Nyx core |
| NyxOllama | `nyx-ollama/` | Swift | ✅ Active | Nyx + Ollama integration |
| MicroCursor | `microcursor/` | Swift/C++ | ✅ Active | Autopilot daemon, Q-table, macro detection, event tap |
| Autonomous Tine | `tine-demo/` | Swift | ✅ Active | Second cursor for Mac, screen-aware execution |
| Sniffies AI Companion | `sniffies_ai_companion/` | Python | ✅ Active | Policy engine, approval gates, action queue |
| SniffyAI | `sniffy_ai/`, `sniffy_ai_data/` | Python/JS | ✅ Active | AI companion data + logic |
| Samsung Cast | `samsung_cast/` | C++ | ✅ Active | DLNA client, HTTP server, TSMuxer, LLM engine |
| TV Hub | `tv_hub/` | Mixed | ✅ Active | TV hub control |
| TV Standard | `tv_standard/` | Swift | ✅ Active | TV standard protocol |
| ScreenMirror Pro | `screenmirror_pro/` | Swift | ✅ Active | Screen mirroring |
| AirPlay Agent | `airplay_agent/` | Swift | ✅ Active | AirPlay agent |
| Clipboard Desk | `clipboard_desk/` | Swift | ✅ Active | Clipboard desk app |
| Voice Mac Remote | `voice_mac_remote/` | Mixed | ✅ Active | Voice-controlled Mac remote |
| Relay | `relay/` | Python | ✅ Active | Relay server |
| Echoscope | `echoscope/` | HTML | ✅ Active | Echo scope visualizer |
| Quarantine | `_quarantine/` | Python | ⚠️ Quarantined | Browser automation scripts (Selenium/Playwright) |
| Miner1-4 | `miner1/`–`miner4/` | Python | ⚠️ Experimental | CDP probe dumps, screenshots, compliance ledgers |

---

## Layer 4 — LEARNING SUBSTRATE (Train, Compress, Adapt)

Local ML training, model compression, memory management.

| System | Path | Language | Status | Description |
|--------|------|----------|--------|-------------|
| HotTensorC | `overglythswift/Sources/SubstrateC/hot_tensor.c` | C | ✅ Active | Truth-weighted hot tensor learning, v3.0 |
| ColdTensor | `overglythswift/Sources/SubstrateC/cold_tensor.c` | C | ✅ Active | Geometry-controlled learned compression (G1+G2) |
| DeepLearning | `overglythswift/Sources/SubstrateC/deep_learning.c` | C | ✅ Active | Deep learning primitives |
| CausalModel | `overglythswift/Sources/SubstrateC/causal_model.c` | C | ✅ Active | Causal modeling |
| EpisodicMemory | `overglythswift/Sources/SubstrateC/episodic_memory.c` | C | ✅ Active | Episodic memory system |
| MemoryLattice | `overglythswift/Sources/SubstrateC/memory_lattice.c` | C | ✅ Active | Memory lattice structure |
| RewardKernel | `overglythswift/Sources/SubstrateC/reward_kernel.c` | C | ✅ Active | Reward computation kernel |
| CuriosityKernel | `overglythswift/Sources/SubstrateC/curiosity_kernel.c` | C | ✅ Active | Curiosity-driven exploration |
| TwinRiskKernel | `overglythswift/Sources/SubstrateC/twin_risk_kernel.c` | C | ✅ Active | Twin risk assessment |
| SpinorKnot | `overglythswift/Sources/SubstrateC/spinor_knot.c` | C | ✅ Active | Spinor knot memory |
| Consciousness | `overglythswift/Sources/SubstrateC/consciousness.c` | C | ✅ Active | Consciousness model |
| CognitiveBridge | `overglythswift/Sources/SubstrateC/cognitive_bridge.c` | C | ✅ Active | Bridge between cognition layers |
| ShadowShard M-Forge | `shadowshard_mforge/` | Python | ✅ Active | 7-layer Apple-first intelligence substrate |
| MacForge Trainer | `macforge_real_trainer/`, `macforge_metal_trainer*/` | Python/Swift | ✅ Active | MLX/Metal trainer, LoRA adapters |
| MacForge Starters | `macforge_micro_starters/`, `macforge_microstarters_30/`, `macforge_global_starters/` | Python | ✅ Active | 30+ micro starter modules |
| ML Glyph | `glyph_ml.py` | Python | ✅ Active | ML pipeline for glyphs |
| HF Pipeline | `hf_llm_pipeline.py`, `hf_space_app.py`, `hf_brute30.py`, `hf_freekey_app.py` | Python | ✅ Active | Hugging Face LLM pipeline |
| HF Proxy | `hf-proxy/` | JS | ✅ Active | HF proxy server |
| Ollama Nexus | `ollama_nexus.py` | Python | ✅ Active | Ollama orchestration |
| OneFile ML Token | `onefile_ml_token_launcher.py` | Python | ✅ Active | Single-file ML token launcher |
| Spinnor | `spinnor/` | Mixed | ✅ Active | Spinnor system |
| Audio Cascade | `audio_cascade/` | Mixed | ✅ Active | Audio cascade pipeline, AGI session, hallucination engine |

---

## Layer 5 — COGNITION & POLICY (Think, Decide, Gate)

Reasoning, safety, anti-logic, policy engines, agent governors.

| System | Path | Language | Status | Description |
|--------|------|----------|--------|-------------|
| OverAntiLogic | `overantilogic/`, `OverAntiLogicDaemon/` | C++/Swift | ✅ Active | Anti-logic calculus, impossibility indexing, daemon |
| AntiGlyph | `anti_glyph.cpp` | C++ | ✅ Active | Anti-glyph calculus |
| Goliath | `goliath/` | Python | ✅ Active | Unified control plane :7777, 40+ API endpoints |
| Agent Bridge | `agent_bridge/` | Python | ✅ Active | ChatGPT poller, bridge server, ETL, workflow engine |
| MCP Unified | `mcp/` | Python | ✅ Active | MCP unified server, HyperFlow bridge, Jorki MCP |
| OverAgent Desk | `overagent_desk/`, `overagent_data/` | Mixed | ✅ Active | OverAgent control plane |
| Sentinel Desk | `sentinel_desk/` | Mixed | ✅ Active | Sentinel monitoring desk |
| Satan Desk | `satan_desk/` | Swift | ✅ Active | Satan desk app |
| QuadrantOS | `quadrantos/` | Swift/Python | ✅ Active | Quadrant OS CLI + app |
| QuestionOS | `questionos/` | Python | ✅ Active | Question OS CLI |
| SystemLake | `systemlake/` | Python | ✅ Active | System lake orchestrator |
| LatentOS | `latentos/` | Python | ✅ Active | Latent OS app + core |
| Reality Wall | `reality_wall/` | JS | ✅ Active | Reality wall |
| Reality Compiler | `reality_compiler.py` | Python | ✅ Active | Reality compiler |
| Carpathian | `carpathian.py` | Python | ✅ Active | Carpathian engine |
| OverAgent Control | `overagent_control_plane.py` | Python | ✅ Active | OverAgent control plane |
| Fortress Gateway | `fortress_gateway.py` | Python | ✅ Active | Fortress gateway |
| Orchestrator | `orchestrator.py` | Python | ✅ Active | System orchestrator |
| Autonomous Loop | `autonomous_loop.py`, `autonomous_pipeline.py` | Python | ✅ Active | Autonomous execution loop |
| Freelance Agent | `freelance_agent.py` | Python | ✅ Active | Freelance agent |
| Mac Agent | `mac_agent.py`, `mac_runtime.py` | Python | ✅ Active | Mac agent + runtime |
| MacPilot | `macpilot-0/` | Python | ✅ Active | Mac pilot actions, agent loop |
| Macos Automation | `macos_automation/` | Python | ✅ Active | macOS automation CLI, Python bridge |
| TrackGlyph | `trackglyph/` | Swift | ✅ Active | Track glyph app |
| MirrorMind | `mirrormind/` | Swift | ✅ Active | Mirror mind app |
| GlyphAura | `GlyphAura/` | Swift | ✅ Active | Glyph aura app |
| MetalAgent | `MetalAgent/` | Swift | ✅ Active | Metal agent |
| CodeForge | `codeforge/` | Swift | ✅ Active | Code forge |
| YTL MCP Lab | `ytl-mcp-lab/` | Python | ✅ Active | YTL MCP lab |
| Skills | `skills/`, `skills_integration/` | Python | ✅ Active | Skills system |
| Plans | `plans/` | Markdown | ✅ Active | Planning documents |
| Tasks | `tasks/` | Mixed | ✅ Active | Task definitions |
| Patches | `patches/` | Diff | ✅ Active | Code patches |

---

## Layer 6 — VENTURE PROOF (Prove Ideas Have Value)

DealOS, breakthrough verification, demand signals, revenue oracle.

| System | Path | Language | Status | Description |
|--------|------|----------|--------|-------------|
| DealOS | `overglythswift/Sources/VentureProof/DealOS*.swift` | Swift | ✅ Active | Multi-venture deal engine, D2 benchmark |
| Rapture Engine | `overglythswift/Sources/VentureProof/RaptureEngine.swift` | Swift | ✅ Active | Idea ascension through proof (R^1–R^10) |
| Breakthrough Engine | `overglythswift/Sources/VentureProof/Breakthrough*.swift` | Swift | ✅ Active | Claim verification, falsification |
| Demand Verifier | `overglythswift/Sources/VentureProof/DemandVerification*.swift` | Swift | ✅ Active | App Store demand verification |
| Prior Art Verifier | `overglythswift/Sources/VentureProof/PriorArtVerifier*.swift` | Swift | ✅ Active | Prior art risk mapping |
| ShipOS | `overglythswift/Sources/VentureProof/ShipOS*.swift` | Swift | ✅ Active | Clean release factory, launch packets |
| GPT of Money | (concept in DealOS/Rapture) | Swift | ✅ Active | Next-money-action prediction |
| Revenue Oracle | `revenue_oracle/` | Python | ✅ Active | Revenue prediction oracle |
| Revenue Store | `revenue_store.py` | Python | ✅ Active | Revenue store |
| Money Dashboard | `money_dashboard.py` | Python | ✅ Active | Money dashboard |
| Compute Capital | `compute_capital.py` | Python | ✅ Active | Compute capital tracker |
| Budget | `budget/` | Markdown | ✅ Active | Budget plans |
| Broll | `broll/` | Python | ✅ Active | Video lake: evidence, investigation, media compiler |
| Evidence Scorer | `evidence_scorer.py` | Python | ✅ Active | Evidence scoring |
| Content Monetizer | `content_monetizer.py` | Python | ✅ Active | Content monetization |
| POptimizer | `poptimizer.py`, `poptimizer_etl_engine.py` | Python | ✅ Active | P-optimizer + ETL engine |
| Masseuros | `masseuros/` | Python | ✅ Active | A/B testing, attribution, competitive analysis |
| RM Traffic | `rm_traffic/` | Python/C++ | ✅ Active | Traffic system, bio generators |
| RM AGI | `rm_agi/` | Python/C++ | ✅ Active | RM AGI engine |
| RM Engagement | `rm_engagement_daemon.py` | Python | ✅ Active | RM engagement daemon |
| Traffic Overclock | `traffic_overclock.py` | Python | ✅ Active | Traffic overclock AI layer |
| ClientPulse | `clientpulse.py` | Python | ✅ Active | Client pulse tracker |
| Booking Ledger | `booking_ledger.py` | Python | ✅ Active | Booking ledger |
| Rentmasseur | `rentmasseur_*.py` | Python | ✅ Active | RentMasseur availability/login/setting |
| Visit Clients | `visit_clients.py`, `rm_visit_back.py` | Python | ✅ Active | Client visit automation |
| Email Pipeline | `email_pipeline.py`, `email_collector.py`, `email_crawler*.py` | Python | ✅ Active | Email collection/crawling |
| Aider Email Daemon | `aider_email_daemon.py` | Python | ✅ Active | Aider email daemon |
| Genetic Pane Scheduler | `genetic_pane_scheduler.py` | Python | ✅ Active | Genetic pane scheduler |
| Jorki | `jorki/`, `jorki.py`, `jorki_*.py` | Python/JS | ✅ Active | Jorki AI file gateway, audio server, clipboard, menubar |
| Jorki Data | `jorki_data/`, `jorki_audio_data/` | Mixed | ✅ Active | Jorki indexes + audio data |
| Autonomous Products | `autonomous_products/` | Python | ✅ Active | ForgeRun, GridRun, LinkOps, TaskForge |
| SignalForge Data | `signalforge_data/` | JSON | ✅ Active | Signal data store |

---

## Layer 7 — PRODUCT LAUNCH (Ship Apps to Market)

Autopilot, App Store submission, landing pages, distribution.

| System | Path | Language | Status | Description |
|--------|------|----------|--------|-------------|
| Autopilot | `autopilot.py` | Python | ✅ Active | Generate → build → sign → notarize → submit |
| Autopilot Apps | `autopilot_apps/` | Swift | ✅ Active | 10 built apps: CleanSweep, ClipFlow, DimLight, FocusBeam, GlyphBoard, NetSignal, QuickLaunch, ReceiptVault, ScreenPulse, SnapBarrier |
| Autopilot Templates | `autopilot_templates/` | Swift | ✅ Active | App templates for generation |
| App Store Submitter | `app_store_submitter.py` | Python | ✅ Active | ASC API / altool submission |
| ASC Client | `asc_client.py` | Python | ✅ Active | App Store Connect client |
| App Scraper | `app_scraper.py`, `app_scraper_phase2.py`, `app_deep_scraper.py`, `app_enricher*.py`, `real_app_scraper.py` | Python | ✅ Active | App Store scraping + enrichment |
| Scraped Apps | `scraped_apps/` | JSON | ✅ Active | Scraped app data |
| Frontend | `frontend/`, `app/` | React/Next | ✅ Active | React frontend, Next.js app |
| Jorki (product) | `jorki/` | React | ✅ Active | Jorki product frontend |
| NoVNC | `noVNC/` | JS | ✅ Active | NoVNC web client |
| Screenshot Gen | `screenshot_gen.py` | Python | ✅ Active | Screenshot generation |
| ZiptoApp | `ziptoapp.py` | Python | ✅ Active | ZIP to app converter |
| Military Upgrade | `military_upgrade.py` | Python | ✅ Active | Military upgrade pipeline |
| Fetch Build Stream | `fetch_build_stream.py` | Python | ✅ Active | Build stream fetcher |
| Demo Live | `demo_live.py` | Python | ✅ Active | Live demo |
| Run All | `run_all.py`, `launch_all.py` | Python | ✅ Active | System launchers |
| Add Endpoints | `add_endpoints.py`, `fix_endpoints.py` | Python | ✅ Active | Endpoint management |
| Replace UI | `replace_ui.py` | Python | ✅ Active | UI replacement |
| Extract Tools | `extract_*.py` | Python | ✅ Active | ChatGPT/CDP/LevelDB/Applescript extraction tools |
| ChatGPT Exports | `chatgpt_exports/` | Markdown/JSON | ✅ Active | ChatGPT conversation exports |
| Assets | `assets/` | Mixed | ✅ Active | Shared assets |
| Dist | `dist/` | Python | ✅ Active | Distribution packages |
| Build | `build/` | Mixed | ✅ Active | Build output |
| Tests | `test/`, `tests/` | Python | ✅ Active | Test suite |
| Docs | `docs/` | Markdown | ✅ Active | Documentation |
| OverGlyth CLI | `overglythswift/Sources/OverGlythCLI/` | Swift | ✅ Active | Unified CLI (astropilotd) |
| OverGlyth App | `overglythswift/Sources/GlyphOSApp/` | Swift | ✅ Active | Desktop app with all panels |
| AgentVM | `overglythswift/Sources/AgentVM/` | Swift | ✅ Active | Agent VM controller + view |
| OverGlythSwift (sub) | `overandor-glythos/OverGlythSwift/` | Swift | ✅ Active | OverGlyth Swift subproject |
| RoboJoseph | `overandor-glythos/RoboJoseph/`, `RoboJosephWidget/` | Swift | ✅ Active | RoboJoseph app + widget |
| BOA Protocol | `overandor-glythos/rpfbs/src/boa_protocol.rs` | Rust | ✅ Active | Birth of Agent protocol |
| Media Organism | `overandor-glythos/rpfbs/src/media_organism.rs` | Rust | ✅ Active | Receipted media engine |
| Frontier Forge | `overandor-glythos/rpfbs/src/frontier_forge.rs` | Rust | ✅ Active | Real mutation + sandbox builds |
| Twin OS | `overandor-glythos/rpfbs/src/twin_os.rs` | Rust | ✅ Active | Twin execution with real commands |
| Frontier Arena | `overandor-glythos/rpfbs/src/frontier_arena.rs` | Rust | ✅ Active | Frontier arena |
| RAIT | `overandor-glythos/rpfbs/src/rait.rs` | Rust | ✅ Active | RAIT system |
| Metal932 | `overandor-glythos/metal932/` | Python | ✅ Active | Glyph932 compiler, 67 symbols |
| OverGlyth Compiler | `overandor-glythos/compiler/` | Python | ✅ Active | Glyth compiler |
| OverGlyth Runtime | `overandor-glythos/runtime/` | Python | ✅ Active | Runtime engine |
| GodPiper | `overandor-glythos/godpiper/` | Python | ✅ Active | God piper |
| MicroGPT Coder | `overandor-glythos/microgpt-coder/` | Python | ✅ Active | Micro GPT coder |
| AgentOS Playground | `overandor-glythos/agentos-playground/` | Python | ✅ Active | Agent OS playground |
| OverGlyth Examples | `overandor-glythos/examples/` | Glyth | ✅ Active | 14 example contracts |
| OverGlyth Papers | `overandor-glythos/paper/` | Markdown | ✅ Active | AntiLogic + OverMetal papers |
| OverGlyth Missions | `overandor-glythos/missions/` | Markdown | ✅ Active | Mission definitions |
| OverGlyth Receipts | `overandor-glythos/receipts/` | JSON | ✅ Active | OverGlyth receipts |
| OverGlyth Graphs | `overandor-glythos/graphs/` | Mixed | ✅ Active | Graph data |
| OverGlyth Benchmarks | `overandor-glythos/benchmarks/` | Mixed | ✅ Active | Benchmark results |

---

## Cross-Cutting Concerns

These span all layers:

| Concern | Systems | Description |
|---------|---------|-------------|
| **Receipts** | Every system | SHA-256 chained JSONL, tamper-evident |
| **Safety/Policy** | Sniffies Companion, OverAntiLogic, ShadowShard governors | Action gating: auto-safe / approval-required / blocked |
| **GlyphState** | All surfaces | 9-verb state alphabet: O−M/=#!VR |
| **Goliath** | All Python systems | Unified control plane at :7777 |
| **OverGlyth CLI** | All Swift systems | Unified CLI (astropilotd) |
| **MCP** | IDE integration | Windsurf/Devin bridge |

---

## Language Distribution

| Language | Files | LOC (approx) | Primary Use |
|----------|-------|-------------|-------------|
| Python | 506 | 83,567+ | Infrastructure, observation, cognition, venture |
| Swift | 264 | 50,000+ | Execution, learning, product, CLI |
| C | 20 | 15,000+ | Learning substrate kernels |
| C++ | 28 | 8,000+ | Browser bridge, anti-logic, bio generators |
| Rust | 9 | 5,000+ | RPFBS, BOA, frontier forge, twin OS |
| JS/TS | 50+ | 10,000+ | Frontend, HF proxy, NoVNC |
| Markdown | 100+ | 30,000+ | Specs, papers, docs |

---

## Unified Entry Points

| Entry Point | URL/Command | Scope |
|-------------|-------------|-------|
| Goliath | `python3 goliath/launch.py` → :7777 | All Python systems |
| OverGlyth CLI | `swift run astropilotd` | All Swift systems |
| RPFBS | `rpfbs glyph <surface>` | All Rust systems |
| Unified OS | `python3 unified_os.py` (new) | All systems, all layers |
