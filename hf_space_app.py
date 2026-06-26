"""SystemLake Underwriter — Privacy-Preserving Code Evaluation Gateway.

The actual product: User uploads files → system crawls + hashes + redacts →
sends only a metadata cognition packet to GPT → GPT evaluates →
returns verdict + receipt. Raw files never leave the user's control.

Pipeline:
    Upload → Extract → Crawl → Hash → Merkle Root → Detect Systems →
    Score Collateral → Redact (strip source, keep metadata) →
    Build Cognition Packet → Send to LLM → Get Evaluation →
    Write Receipt → Return Verdict

What goes to GPT (cognition packet):
    - File hashes (SHA-256), sizes, extensions, categories
    - Merkle root
    - System detection results (has_git, has_tests, has_endpoints)
    - Collateral scores (10 dimensions)
    - Risk register with classifications
    - Verification results
    - Capabilities summary

What does NOT go to GPT:
    - Source code content
    - File names containing secrets
    - .env, .ssh, keys, wallets, credentials
    - Binary file contents
    - Any file content at all — only metadata

Endpoints:
    GET  /              — Upload UI
    POST /upload        — Upload a zip/tar of your repo
    GET  /result/{id}   — Get evaluation result + receipt
    GET  /result/{id}/packet — Get cognition packet only
    GET  /result/{id}/evaluation — Get LLM evaluation only
    GET  /result/{id}/receipt — Get receipt only
    GET  /health        — Health check
    GET  /telemetry     — Pre-baked telemetry (existing audit)
"""

import os
import json
import hashlib
import zipfile
import tarfile
import shutil
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path as _Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Body
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# ─── Configuration ──────────────────────────────────────────────────────

DATA_DIR = os.environ.get("SYSTEMLAKE_DATA_DIR", "/app/audit_data")
UPLOAD_DIR = os.environ.get("SYSTEMLAKE_UPLOAD_DIR", "/tmp/systemlake_uploads")
RESULTS_DIR = os.environ.get("SYSTEMLAKE_RESULTS_DIR", "/tmp/systemlake_results")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
PORT = int(os.environ.get("PORT", 7860))

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ─── Denied file patterns (never hashed, never indexed, never sent) ─────

DENIED_PATTERNS = [
    '.env', '.env.', '.ssh', '.aws', '.npmrc', '.pypirc',
    'id_rsa', 'id_ed25519', 'id_ecdsa',
    '.key', '.pem', '.crt', '.pfx', '.p12',
    'credentials', 'secrets', 'wallet', 'keystore',
    '.keystore', '.keychain', 'Keychains',
    '.gnupg', '.gpg',
]

DENIED_EXTENSIONS = {
    '.env', '.key', '.pem', '.crt', '.pfx', '.p12', '.keystore',
    '.jks', '.gpg', '.pgp',
}

EXCLUDE_DIRS = {
    '__pycache__', '.git', 'node_modules', '.venv', 'venv',
    '.pytest_cache', '.mypy_cache', '.cache', '.npm',
    'dist', 'build', 'target', '.next', '.nuxt',
    '.gradle', '.m2', '.cargo', '.rustup',
    '.vscode', '.cursor', '.windsurf', '.idea',
}

# ─── Data Loading (for pre-baked telemetry) ─────────────────────────────

def _load_json(filename: str) -> Optional[dict]:
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None

def _load_text(filename: str) -> Optional[str]:
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return None

def _load_all() -> dict:
    return {
        "systems": _load_json("systems.json"),
        "scores": _load_json("underwriting_scores.json"),
        "risks": _load_json("risk_register.json"),
        "borrowing": _load_json("borrowing_base.json"),
        "verification": _load_json("verification_results.json"),
        "merkle": _load_json("merkle_root.json"),
        "manifest": _load_json("machine_manifest.json"),
        "receipt": _load_json("receipt.json"),
        "focus": _load_json("focus_packet.json"),
        "memo": _load_text("underwriting_memo.md"),
    }

# ─── Redaction Layer ────────────────────────────────────────────────────

def _is_denied(filename: str) -> bool:
    lower = filename.lower()
    for ext in DENIED_EXTENSIONS:
        if lower.endswith(ext):
            return True
    for pattern in DENIED_PATTERNS:
        if pattern in lower:
            return True
    return False

def _compute_merkle_root(hashes: List[str]) -> str:
    if not hashes:
        return None
    leaves = [hashlib.sha256(h.encode()).hexdigest() for h in hashes]
    while len(leaves) > 1:
        if len(leaves) % 2 != 0:
            leaves.append(leaves[-1])
        leaves = [hashlib.sha256((leaves[i] + leaves[i+1]).encode()).hexdigest()
                  for i in range(0, len(leaves), 2)]
    return leaves[0]

def _build_cognition_packet(extracted_dir: str) -> dict:
    """Crawl extracted files and build a REDACTED cognition packet.
    Contains NO source code, NO file content. Only hashes, sizes, structure.
    """
    packet = {
        "schema": "membra.systemlake.cognition_packet.v1",
        "created_at": datetime.now().isoformat(),
        "files": [],
        "systems": [],
        "stats": {
            "total_files": 0, "total_bytes": 0,
            "denied_files": 0, "by_extension": {}, "by_category": {},
        },
    }
    file_hashes = []

    for dirpath, dirnames, filenames in os.walk(extracted_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            full_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(full_path, extracted_dir)
            if _is_denied(fname) or _is_denied(rel_path):
                packet["stats"]["denied_files"] += 1
                continue
            try:
                st = os.stat(full_path)
            except Exception:
                continue
            try:
                h = hashlib.sha256()
                with open(full_path, "rb") as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        h.update(chunk)
                sha = h.hexdigest()
            except Exception:
                sha = "unreadable"
            ext = os.path.splitext(fname)[1].lower()
            size = st.st_size
            if ext in ('.py',): category = 'python'
            elif ext in ('.js', '.ts', '.jsx', '.tsx'): category = 'javascript'
            elif ext in ('.go',): category = 'go'
            elif ext in ('.rs',): category = 'rust'
            elif ext in ('.java',): category = 'java'
            elif ext in ('.md', '.rst', '.txt'): category = 'documentation'
            elif ext in ('.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'): category = 'config'
            elif ext in ('.html', '.css', '.vue', '.svelte'): category = 'frontend'
            elif ext in ('.sql',): category = 'database'
            elif ext in ('.sh', '.bash'): category = 'script'
            elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico'): category = 'asset'
            else: category = 'other'
            packet["files"].append({"path": rel_path, "sha256": sha, "size": size, "extension": ext, "category": category})
            packet["stats"]["total_files"] += 1
            packet["stats"]["total_bytes"] += size
            packet["stats"]["by_extension"][ext] = packet["stats"]["by_extension"].get(ext, 0) + 1
            packet["stats"]["by_category"][category] = packet["stats"]["by_category"].get(category, 0) + 1
            file_hashes.append(sha)

    packet["merkle_root"] = _compute_merkle_root(file_hashes) if file_hashes else None
    packet["systems"] = _detect_systems_metadata(extracted_dir)
    packet["collateral_scores"] = _score_collateral_metadata(packet)
    packet["risks"] = _build_risk_register(packet)
    return packet

def _detect_systems_metadata(root: str) -> list:
    markers = {'requirements.txt', 'package.json', 'setup.py', 'Makefile',
               'Dockerfile', '.git', 'README.md', 'pyproject.toml'}
    systems = []
    seen = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        has_git_dir = '.git' in dirnames
        dir_files = set(filenames + dirnames)
        if has_git_dir: dir_files.add('.git')
        markers_found = markers & dir_files
        if not markers_found: continue
        dirname = os.path.basename(dirpath) or 'root'
        if dirname in seen: continue
        has_code = any(f.endswith(('.py', '.js', '.ts', '.go', '.rs', '.java')) for f in filenames)
        strong = markers_found & {'requirements.txt', 'setup.py', 'Dockerfile', 'Makefile', '.git'}
        if len(markers_found) < 2 and not strong and not (has_git_dir and has_code): continue
        systems.append({
            "name": dirname, "root_path": os.path.relpath(dirpath, root),
            "markers": sorted(list(markers_found)), "has_git": has_git_dir,
            "has_tests": any('test' in f.lower() for f in filenames),
            "has_endpoints": bool({'app.py', 'server.py', 'main.py', 'server.js', 'index.js'} & set(filenames)),
            "has_receipts": any('receipt' in f.lower() for f in filenames),
            "file_count": len(filenames),
            "has_dockerfile": 'Dockerfile' in markers_found,
            "has_requirements": 'requirements.txt' in markers_found,
            "has_readme": 'README.md' in markers_found,
        })
        seen.add(dirname)
    return systems

def _score_collateral_metadata(packet: dict) -> dict:
    stats = packet["stats"]
    systems = packet["systems"]
    by_cat = stats["by_category"]
    code_files = sum(by_cat.get(c, 0) for c in ("python", "javascript", "go", "rust", "java"))
    doc_files = by_cat.get("documentation", 0)
    config_files = by_cat.get("config", 0)
    has_git = any(s["has_git"] for s in systems)
    has_tests = any(s["has_tests"] for s in systems)
    has_ep = any(s["has_endpoints"] for s in systems)
    has_docker = any(s["has_dockerfile"] for s in systems)
    has_receipts = any(s["has_receipts"] for s in systems)
    has_readme = any(s["has_readme"] for s in systems)

    dims = {
        "functionality": min(100, 20 + code_files * 2 + (15 if has_ep else 0)),
        "reproducibility": min(100, 25 + (20 if has_git else 0) + (15 if has_docker else 0) + (10 if config_files > 0 else 0)),
        "receipt_strength": min(100, 20 + (40 if has_receipts else 0) + (20 if has_git else 0)),
        "deployability": min(100, 20 + (25 if has_docker else 0) + (15 if has_ep else 0) + (10 if config_files > 2 else 0)),
        "test_strength": min(100, 15 + (50 if has_tests else 0)),
        "documentation": min(100, 20 + doc_files * 5 + (20 if has_readme else 0)),
        "security_cleanliness": min(100, 40 + (20 if stats["denied_files"] == 0 else 0) + (20 if stats["total_files"] < 1000 else 0)),
        "provenance": min(100, 20 + (50 if has_git else 0) + (15 if has_receipts else 0)),
        "economic_evidence": min(100, 15 + (10 if has_ep else 0) + (5 if has_receipts else 0)),
        "marketability": min(100, 20 + (15 if doc_files > 0 else 0) + (10 if has_ep else 0) + (10 if len(systems) > 1 else 0)),
    }
    dims = {k: round(v, 1) for k, v in dims.items()}
    weights = {"functionality": 0.18, "reproducibility": 0.14, "receipt_strength": 0.14,
               "deployability": 0.12, "test_strength": 0.10, "documentation": 0.10,
               "security_cleanliness": 0.10, "provenance": 0.08,
               "economic_evidence": 0.08, "marketability": 0.06}
    raw = sum(dims[k] * weights[k] for k in dims)
    haircuts = {}
    if not has_tests: haircuts["no_tests"] = 10.0
    if not has_receipts: haircuts["no_receipts"] = 8.0
    if not has_git: haircuts["no_provenance"] = 15.0
    if stats["denied_files"] > 0: haircuts["secret_exposure"] = 20.0
    if not has_readme: haircuts["no_documentation"] = 5.0
    total_hc = sum(haircuts.values())
    final = max(0, raw - total_hc)
    grade = "A" if final >= 80 else "B" if final >= 65 else "C" if final >= 50 else "D" if final >= 35 else "F"
    return {
        "dimensions": dims, "raw_score": round(raw, 1), "haircuts": haircuts,
        "total_haircut": round(total_hc, 1), "final_score": round(final, 1),
        "grade": grade,
        "borrowing_base_estimate_usd": {"low": round(final*5,2), "mid": round(final*15,2), "high": round(final*25,2)},
        "systems_count": len(systems),
        "capabilities": {"has_git": has_git, "has_tests": has_tests, "has_endpoints": has_ep,
                         "has_dockerfile": has_docker, "has_receipts": has_receipts},
    }

def _build_risk_register(packet: dict) -> list:
    risks = []
    haircuts = packet.get("collateral_scores", {}).get("haircuts", {})
    risk_map = {
        "no_tests": ("missing_evidence", "No test coverage", "Add test files"),
        "no_receipts": ("missing_evidence", "No execution receipts", "Generate receipts"),
        "no_provenance": ("missing_evidence", "No git history", "Initialize git repo"),
        "secret_exposure": ("real", "Exposed secrets detected", "Remove .env and secrets"),
        "no_documentation": ("missing_evidence", "No README", "Add README.md"),
    }
    for hname, val in haircuts.items():
        cls, desc, rem = risk_map.get(hname, ("real", hname, "Review"))
        risks.append({"risk_type": hname, "severity": "high" if val >= 15 else "medium" if val >= 8 else "low",
                      "haircut": val, "classification": cls, "description": desc, "remediation": rem})
    return risks

# ─── LLM Evaluation Gateway ─────────────────────────────────────────────

def _build_llm_prompt(packet: dict) -> str:
    scores = packet.get("collateral_scores", {})
    stats = packet["stats"]
    systems = packet["systems"]
    sys_summary = "\n".join([
        f"  - {s['name']}: {s['file_count']} files, markers={s['markers']}, "
        f"git={s['has_git']}, tests={s['has_tests']}, endpoints={s['has_endpoints']}"
        for s in systems]) or "  (none detected)"
    return f"""You are a software collateral underwriter. Evaluate the following software asset metadata.

IMPORTANT: You receive ONLY metadata — hashes, sizes, extensions, structure. NO source code. NO file contents. NO proprietary information.

## Asset Summary
- Files: {stats['total_files']}, Size: {stats['total_bytes']:,} bytes
- Denied (secrets filtered): {stats['denied_files']}
- Merkle root: {packet.get('merkle_root', 'N/A')[:16]}...
- Systems: {len(systems)}

## Systems
{sys_summary}

## Categories
{json.dumps(stats.get('by_category', {}), indent=2)}

## Extensions
{json.dumps(stats.get('by_extension', {}), indent=2)}

## Scores
- Final: {scores.get('final_score', 0)}/100, Grade: {scores.get('grade', 'F')}
- Dimensions: {json.dumps(scores.get('dimensions', {}))}
- Haircuts: {json.dumps(scores.get('haircuts', {}))}

## Risks
{json.dumps(packet.get('risks', []), indent=2)}

## Borrowing Base
{json.dumps(scores.get('borrowing_base_estimate_usd', {}))}

## Capabilities
{json.dumps(scores.get('capabilities', {}))}

## Task
Provide:
1. VERDICT: underwritable / underwritable_after_remediation / not_underwritable
2. GRADE JUSTIFICATION
3. KEY STRENGTHS
4. KEY RISKS
5. REMEDIATION PATH
6. BORROWING BASE OPINION
7. CONFIDENCE (high/medium/low)

Be honest and conservative. Missing evidence = missing evidence, not positive evidence."""

async def _call_llm(prompt: str) -> str:
    if OPENAI_API_KEY:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post("https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "gpt-4o-mini", "messages": [
                        {"role": "system", "content": "You are a software collateral underwriter. Be precise, honest, and conservative."},
                        {"role": "user", "content": prompt}],
                        "max_tokens": 2000, "temperature": 0.3})
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[LLM call failed: {e}]\n\n" + _local_evaluation(prompt)
    if HF_TOKEN:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post("https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct",
                    headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
                    json={"inputs": prompt, "parameters": {"max_new_tokens": 1000, "temperature": 0.3}})
                resp.raise_for_status()
                data = resp.json()
                return data[0].get("generated_text", str(data)) if isinstance(data, list) else str(data)
        except Exception as e:
            return f"[HF inference failed: {e}]\n\n" + _local_evaluation(prompt)
    return _local_evaluation(prompt)

def _local_evaluation(prompt: str) -> str:
    final_score = 0; grade = "F"
    for line in prompt.split('\n'):
        if "Final:" in line:
            try: final_score = float(line.split(":")[1].split("/")[0].split(",")[0].strip())
            except: pass
        if "Grade:" in line:
            try: grade = line.split("Grade:")[1].strip().split(",")[0].strip()
            except: pass
    if final_score >= 65: verdict = "underwritable"; conf = "medium"
    elif final_score >= 35: verdict = "underwritable_after_remediation"; conf = "medium"
    else: verdict = "not_underwritable"; conf = "low"
    return f"""## 1. VERDICT
{verdict}

## 2. GRADE JUSTIFICATION
Grade {grade} (score: {final_score}/100). Metadata-only analysis. Higher grade requires passing tests, execution receipts, and external validation.

## 3. KEY STRENGTHS
- Software structure is detectable and measurable
- Merkle root provides tamper-evident state proof
- Systems detected with project markers

## 4. KEY RISKS
- Source code quality NOT evaluated (metadata only)
- Tests may exist but not pass
- No external validation of economic claims

## 5. REMEDIATION PATH
- Add tests and ensure they pass
- Generate execution receipts
- Add LICENSE file and lockfile
- Document usage and deployment

## 6. BORROWING BASE OPINION
Conservative estimate based on structural metadata. Adjusts upward with: passing tests, receipts, usage logs, market validation. Adjusts downward with: failing tests, secret exposure, license conflicts.

## 7. CONFIDENCE
{conf} — Metadata-only evaluation. Full confidence requires source code review, test execution, and external audit.

---
Note: Local evaluation (no LLM API configured). Set OPENAI_API_KEY or HF_TOKEN for LLM-powered evaluation."""

# ─── Evaluation Pipeline ────────────────────────────────────────────────

_evaluations = {}

async def _run_evaluation(eval_id: str, extracted_dir: str, filename: str):
    result = {"id": eval_id, "status": "crawling", "filename": filename,
              "started_at": datetime.now().isoformat(), "steps": []}
    _evaluations[eval_id] = result
    try:
        result["status"] = "building_cognition_packet"
        result["steps"].append({"step": "crawl_hash_redact", "status": "running", "timestamp": datetime.now().isoformat()})
        packet = _build_cognition_packet(extracted_dir)
        result["steps"][-1].update({"status": "complete", "files_indexed": packet["stats"]["total_files"],
                                     "files_denied": packet["stats"]["denied_files"],
                                     "merkle_root": (packet.get("merkle_root") or "")[:16] + "...",
                                     "systems_detected": len(packet["systems"])})
        result["status"] = "building_llm_prompt"
        result["steps"].append({"step": "build_prompt", "status": "running", "timestamp": datetime.now().isoformat()})
        prompt = _build_llm_prompt(packet)
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        result["steps"][-1].update({"status": "complete", "prompt_hash": prompt_hash[:16] + "...", "prompt_size": len(prompt)})
        result["status"] = "evaluating_with_llm"
        result["steps"].append({"step": "llm_evaluation", "status": "running", "timestamp": datetime.now().isoformat()})
        llm_response = await _call_llm(prompt)
        result["steps"][-1].update({"status": "complete", "response_length": len(llm_response)})
        result["status"] = "writing_receipt"
        receipt = {
            "schema": "membra.systemlake.evaluation_receipt.v1",
            "receipt_id": eval_id, "timestamp": datetime.now().isoformat(), "filename": filename,
            "merkle_root": packet.get("merkle_root"), "files_indexed": packet["stats"]["total_files"],
            "files_denied": packet["stats"]["denied_files"], "systems_detected": len(packet["systems"]),
            "collateral_score": packet["collateral_scores"]["final_score"], "grade": packet["collateral_scores"]["grade"],
            "prompt_hash": prompt_hash, "llm_used": bool(OPENAI_API_KEY or HF_TOKEN),
            "cognition_packet_schema": packet["schema"],
            "safety_guarantees": {"source_code_sent_to_llm": False, "file_contents_sent_to_llm": False,
                                  "secrets_sent_to_llm": False, "only_metadata_hashes_structure": True},
        }
        receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
        result["steps"].append({"step": "write_receipt", "status": "complete", "timestamp": datetime.now().isoformat()})
        result["status"] = "complete"
        result["completed_at"] = datetime.now().isoformat()
        result["packet"] = packet
        result["llm_evaluation"] = llm_response
        result["receipt"] = receipt
        result_path = os.path.join(RESULTS_DIR, f"{eval_id}.json")
        with open(result_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        shutil.rmtree(extracted_dir, ignore_errors=True)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        shutil.rmtree(extracted_dir, ignore_errors=True)

def _run_evaluation_sync(eval_id: str, extract_dir: str, filename: str):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: loop.run_until_complete(_run_evaluation(eval_id, extract_dir, filename))
    finally: loop.close()

# ─── FastAPI App ────────────────────────────────────────────────────────

app = FastAPI(title="SystemLake Underwriter", version="2.0.0")

@app.get("/health")
async def health():
    data = _load_all()
    return {"status": "ok", "data_dir": DATA_DIR, "has_audit_data": data["systems"] is not None,
            "openai_configured": bool(OPENAI_API_KEY), "hf_token_configured": bool(HF_TOKEN),
            "evaluations_run": len(_evaluations)}

@app.get("/telemetry")
async def telemetry():
    data = _load_all()
    if not data["systems"]: raise HTTPException(404, "No pre-baked audit data found.")
    systems = data["systems"].get("systems", [])
    grades = {}
    for s in systems:
        g = s.get("grade", "F"); grades[g] = grades.get(g, 0) + 1
    bb = data["borrowing"] or {}
    risks = data["risks"] or {}
    return {"schema": "membra.systemlake.telemetry.v1", "timestamp": datetime.now().isoformat(),
            "audit": {"systems_total": len(systems), "grade_distribution": dict(sorted(grades.items())),
                      "borrowing_base": {"low": bb.get("total_low",0), "mid": bb.get("total_mid",0), "high": bb.get("total_high",0)},
                      "risks": {"total": risks.get("total_risks",0), "high": risks.get("high_severity",0),
                                "medium": risks.get("medium_severity",0), "low": risks.get("low_severity",0)},
                      "merkle_root": data["merkle"].get("root","") if data["merkle"] else "",
                      "receipt_id": data["receipt"].get("receipt_id","") if data["receipt"] else ""},
            "evaluations": list(_evaluations.keys())}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a zip/tar of your repo. Source code is NEVER sent to any LLM.
    Only metadata (hashes, sizes, extensions, structure) is sent for evaluation.
    Secrets, keys, and credentials are filtered out entirely."""
    eval_id = str(uuid.uuid4())
    upload_path = os.path.join(UPLOAD_DIR, f"{eval_id}_{file.filename}")
    with open(upload_path, "wb") as f:
        content = await file.read(); f.write(content)
    extract_dir = os.path.join(UPLOAD_DIR, f"{eval_id}_extracted")
    os.makedirs(extract_dir, exist_ok=True)
    if file.filename.endswith('.zip'):
        with zipfile.ZipFile(upload_path, 'r') as z: z.extractall(extract_dir)
    elif file.filename.endswith(('.tar.gz', '.tgz', '.tar')):
        with tarfile.open(upload_path, 'r:*') as t: t.extractall(extract_dir)
    else:
        shutil.copy(upload_path, os.path.join(extract_dir, file.filename))
    os.unlink(upload_path)
    entries = os.listdir(extract_dir)
    if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
        extract_dir = os.path.join(extract_dir, entries[0])
    threading.Thread(target=lambda: _run_evaluation_sync(eval_id, extract_dir, file.filename), daemon=True).start()
    return {"eval_id": eval_id, "filename": file.filename, "status": "started",
            "message": "File uploaded. Poll GET /result/{eval_id} for results.", "result_url": f"/result/{eval_id}"}

@app.get("/result/{eval_id}")
async def get_result(eval_id: str):
    if eval_id in _evaluations: return _evaluations[eval_id]
    result_path = os.path.join(RESULTS_DIR, f"{eval_id}.json")
    if os.path.exists(result_path):
        with open(result_path, "r") as f: return json.load(f)
    raise HTTPException(404, f"Evaluation '{eval_id}' not found")

@app.get("/result/{eval_id}/packet")
async def get_packet(eval_id: str):
    result = _evaluations.get(eval_id)
    if not result:
        rp = os.path.join(RESULTS_DIR, f"{eval_id}.json")
        if os.path.exists(rp):
            with open(rp, "r") as f: result = json.load(f)
    if not result: raise HTTPException(404, f"Evaluation '{eval_id}' not found")
    return result.get("packet", {})

@app.get("/result/{eval_id}/evaluation")
async def get_evaluation(eval_id: str):
    result = _evaluations.get(eval_id)
    if not result:
        rp = os.path.join(RESULTS_DIR, f"{eval_id}.json")
        if os.path.exists(rp):
            with open(rp, "r") as f: result = json.load(f)
    if not result: raise HTTPException(404, f"Evaluation '{eval_id}' not found")
    return PlainTextResponse(result.get("llm_evaluation", "No evaluation available"))

@app.get("/result/{eval_id}/receipt")
async def get_receipt(eval_id: str):
    result = _evaluations.get(eval_id)
    if not result:
        rp = os.path.join(RESULTS_DIR, f"{eval_id}.json")
        if os.path.exists(rp):
            with open(rp, "r") as f: result = json.load(f)
    if not result: raise HTTPException(404, f"Evaluation '{eval_id}' not found")
    return result.get("receipt", {})

# ─── Legacy telemetry endpoints ─────────────────────────────────────────

@app.get("/systems")
async def list_systems():
    data = _load_all()
    if not data["systems"]: raise HTTPException(404, "No audit data found.")
    return data["systems"]

@app.get("/risks")
async def risks():
    data = _load_all()
    if not data["risks"]: raise HTTPException(404, "No audit data found.")
    return data["risks"]

@app.get("/borrowing")
async def borrowing():
    data = _load_all()
    if not data["borrowing"]: raise HTTPException(404, "No audit data found.")
    return data["borrowing"]

@app.get("/scores")
async def scores():
    data = _load_all()
    if not data["scores"]: raise HTTPException(404, "No audit data found.")
    return data["scores"]

@app.get("/merkle")
async def merkle():
    data = _load_all()
    if not data["merkle"]: raise HTTPException(404, "No audit data found.")
    return data["merkle"]

@app.get("/receipt")
async def receipt_legacy():
    data = _load_all()
    if not data["receipt"]: raise HTTPException(404, "No audit data found.")
    return data["receipt"]

@app.get("/scope")
async def scope():
    data = _load_all()
    if not data["focus"]: raise HTTPException(404, "No audit data found.")
    return data["focus"].get("scope", {})

@app.get("/memo")
async def memo():
    data = _load_all()
    if not data["memo"]: raise HTTPException(404, "No audit data found.")
    return HTMLResponse(f"<pre>{data['memo']}</pre>")

@app.get("/verification")
async def verification():
    data = _load_all()
    if not data["verification"]: raise HTTPException(404, "No audit data found.")
    return data["verification"]

# ─── Dashboard / Upload UI ──────────────────────────────────────────────

@app.get("/")
async def root():
    ui_path = _Path("/app/jorki_ui_dist/index.html")
    if ui_path.exists():
        return FileResponse(str(ui_path))
    return HTMLResponse("<h1>Jorki</h1><p>UI not built. Visit /systemlake for the legacy dashboard.</p>")

@app.get("/systemlake", response_class=HTMLResponse)
async def dashboard():
    data = _load_all()
    has_telemetry = data["systems"] is not None
    if has_telemetry:
        systems = data["systems"].get("systems", [])
        bb = data["borrowing"] or {}
        merkle = data["merkle"] or {}
        receipt = data["receipt"] or {}
        tel_block = f"""
        <div class="section-title">Reference Audit (Pre-computed)</div>
        <div class="grid">
            <div class="card"><h2>Borrowing Base</h2><div class="big-number green">${bb.get('total_mid', 0):,.0f}</div>
            <div class="stat-row"><span class="stat-label">Low</span><span class="stat-value">${bb.get('total_low', 0):,.0f}</span></div>
            <div class="stat-row"><span class="stat-label">High</span><span class="stat-value">${bb.get('total_high', 0):,.0f}</span></div></div>
            <div class="card"><h2>Systems Scored</h2><div class="big-number">{len(systems)}</div>
            <div class="stat-row"><span class="stat-label">Merkle root</span><span class="stat-value mono">{merkle.get('root', 'N/A')[:16]}...</span></div>
            <div class="stat-row"><span class="stat-label">Receipt</span><span class="stat-value mono">{receipt.get('receipt_id', 'N/A')[:16]}...</span></div></div>
        </div>
        <div class="api-list" style="margin-bottom:24px">
            <a href="/telemetry">/telemetry</a> · <a href="/systems">/systems</a> · <a href="/risks">/risks</a> · <a href="/borrowing">/borrowing</a>
        </div>"""
    else:
        tel_block = ""

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SystemLake Underwriter — Privacy-Preserving Code Evaluation</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0d1117; color:#c9d1d9; padding:20px; max-width:1200px; margin:0 auto; }}
h1 {{ color:#58a6ff; font-size:24px; margin-bottom:4px; }}
.subtitle {{ color:#8b949e; font-size:14px; margin-bottom:24px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:16px; margin-bottom:24px; }}
.card {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:20px; }}
.card h2 {{ font-size:14px; color:#8b949e; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:12px; }}
.big-number {{ font-size:32px; font-weight:700; color:#58a6ff; }}
.big-number.green {{ color:#3fb950; }}
.stat-row {{ display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #21262d; font-size:14px; }}
.stat-row:last-child {{ border-bottom:none; }}
.stat-label {{ color:#8b949e; }} .stat-value {{ color:#c9d1d9; font-weight:600; }}
.section-title {{ font-size:18px; color:#58a6ff; margin:24px 0 12px; }}
.mono {{ font-family:'SF Mono',Monaco,monospace; font-size:12px; color:#8b949e; }}
a {{ color:#58a6ff; text-decoration:none; }} a:hover {{ text-decoration:underline; }}
.api-list {{ font-family:monospace; font-size:12px; padding:12px; }}
.footer {{ margin-top:32px; padding-top:16px; border-top:1px solid #30363d; color:#8b949e; font-size:12px; }}
.upload-zone {{ border:2px dashed #30363d; border-radius:12px; padding:48px 24px; text-align:center; margin-bottom:24px; transition:border-color 0.3s,background 0.3s; cursor:pointer; }}
.upload-zone:hover,.upload-zone.dragover {{ border-color:#58a6ff; background:#161b22; }}
.upload-zone h3 {{ color:#58a6ff; font-size:20px; margin-bottom:8px; }}
.upload-zone p {{ color:#8b949e; font-size:14px; margin-bottom:16px; }}
.upload-btn {{ display:inline-block; padding:10px 24px; background:#238636; color:#fff; border-radius:6px; font-size:14px; font-weight:600; cursor:pointer; border:none; }}
.upload-btn:hover {{ background:#2ea043; }}
#file-input {{ display:none; }} .file-info {{ margin-top:12px; font-size:13px; color:#8b949e; }}
.pipeline {{ display:flex; flex-wrap:wrap; gap:8px; margin:16px 0; }}
.pipeline-step {{ padding:8px 16px; background:#161b22; border:1px solid #30363d; border-radius:6px; font-size:12px; display:flex; align-items:center; gap:6px; }}
.pipeline-step.active {{ border-color:#58a6ff; background:#0d1117; }}
.pipeline-step.complete {{ border-color:#238636; }}
.pipeline-step.error {{ border-color:#f85149; }}
.result-box {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:20px; margin:16px 0; display:none; }}
.result-box.visible {{ display:block; }}
.result-box h3 {{ color:#58a6ff; margin-bottom:12px; font-size:16px; }}
.result-pre {{ background:#0d1117; border:1px solid #21262d; border-radius:6px; padding:16px; font-family:'SF Mono',Monaco,monospace; font-size:12px; white-space:pre-wrap; word-wrap:break-word; max-height:600px; overflow-y:auto; }}
.safety-badge {{ display:inline-block; padding:4px 12px; border-radius:4px; font-size:11px; font-weight:600; margin-bottom:4px; margin-right:8px; }}
.grade-display {{ font-size:48px; font-weight:700; display:inline-block; width:64px; height:64px; line-height:64px; text-align:center; border-radius:8px; margin-right:16px; }}
.grade-A {{ background:#2ecc71; color:#fff; }} .grade-B {{ background:#27ae60; color:#fff; }}
.grade-C {{ background:#f39c12; color:#fff; }} .grade-D {{ background:#e67e22; color:#fff; }}
.grade-F {{ background:#e74c3c; color:#fff; }}
</style>
</head>
<body>
<h1>SystemLake Underwriter</h1>
<p class="subtitle">Privacy-preserving code evaluation gateway · Upload your repo → get an underwriting verdict · Your source code never leaves your control</p>

<div class="card" style="margin-bottom:24px;">
    <div class="safety-badge" style="background:#238636">PRIVACY GATE: No source code sent to LLM · Only metadata, hashes, and structure</div>
    <div class="upload-zone" id="upload-zone" onclick="document.getElementById('file-input').click()">
        <h3>Upload Your Repository</h3>
        <p>Drop a .zip or .tar.gz of your codebase here, or click to browse</p>
        <button class="upload-btn" onclick="event.stopPropagation();document.getElementById('file-input').click()">Choose File</button>
        <div class="file-info" id="file-info"></div>
    </div>
    <input type="file" id="file-input" accept=".zip,.tar.gz,.tgz,.tar" />
    <div class="pipeline" id="pipeline" style="display:none">
        <div class="pipeline-step" id="step-upload"><span class="icon">📤</span> Upload</div>
        <div class="pipeline-step" id="step-crawl"><span class="icon">🔍</span> Crawl+Hash</div>
        <div class="pipeline-step" id="step-merkle"><span class="icon">🌳</span> Merkle</div>
        <div class="pipeline-step" id="step-score"><span class="icon">📊</span> Score</div>
        <div class="pipeline-step" id="step-llm"><span class="icon">🤖</span> LLM</div>
        <div class="pipeline-step" id="step-receipt"><span class="icon">🧾</span> Receipt</div>
    </div>
    <div class="result-box" id="result-box"><h3>Evaluation Result</h3><div id="result-content"></div></div>
</div>

{tel_block}

<div class="section-title">How It Works</div>
<div class="card">
    <div class="stat-row"><span class="stat-label">1. Upload</span><span class="stat-value">You upload a zip/tar of your repo</span></div>
    <div class="stat-row"><span class="stat-label">2. Crawl + Hash</span><span class="stat-value">System hashes every file (SHA-256)</span></div>
    <div class="stat-row"><span class="stat-label">3. Redact</span><span class="stat-value">Source code stripped — only metadata kept</span></div>
    <div class="stat-row"><span class="stat-label">4. Merkle Root</span><span class="stat-value">Tamper-evident state proof computed</span></div>
    <div class="stat-row"><span class="stat-label">5. Score</span><span class="stat-value">10-dimension collateral scoring</span></div>
    <div class="stat-row"><span class="stat-label">6. Cognition Packet</span><span class="stat-value">Redacted packet = hashes + sizes + structure + scores</span></div>
    <div class="stat-row"><span class="stat-label">7. LLM Evaluate</span><span class="stat-value">ONLY the packet sent to GPT — never your code</span></div>
    <div class="stat-row"><span class="stat-label">8. Receipt</span><span class="stat-value">Cryptographic receipt proving the evaluation occurred</span></div>
</div>

<div class="section-title">API Endpoints</div>
<div class="card api-list">
    <a href="/health">GET /health</a> — Service status<br>
    <a href="/telemetry">GET /telemetry</a> — Reference audit telemetry<br>
    POST /upload — Upload zip/tar.gz (multipart form, field: "file")<br>
    GET /result/{{id}} — Full evaluation result<br>
    GET /result/{{id}}/packet — Redacted cognition packet only<br>
    GET /result/{{id}}/evaluation — LLM evaluation text only<br>
    GET /result/{{id}}/receipt — Cryptographic receipt only
</div>

<div class="footer">
    SystemLake Underwriter v2.0 · Privacy-preserving code evaluation ·
    No source code sent to LLM · Only metadata, hashes, and structure ·
    Secrets, keys, and credentials filtered out entirely
</div>

<script>
const uploadZone=document.getElementById('upload-zone'),fileInput=document.getElementById('file-input'),
      fileInfo=document.getElementById('file-info'),pipeline=document.getElementById('pipeline'),
      resultBox=document.getElementById('result-box'),resultContent=document.getElementById('result-content');
let evalId=null,pollTimer=null;

uploadZone.addEventListener('dragover',e=>{{e.preventDefault();uploadZone.classList.add('dragover');}});
uploadZone.addEventListener('dragleave',()=>uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop',e=>{{e.preventDefault();uploadZone.classList.remove('dragover');if(e.dataTransfer.files.length)handleFile(e.dataTransfer.files[0]);}});
fileInput.addEventListener('change',e=>{{if(e.target.files.length)handleFile(e.target.files[0]);}});

function handleFile(file){{
    fileInfo.textContent=`Selected: ${{file.name}} (${{(file.size/1024).toFixed(1)}} KB)`;
    const fd=new FormData();fd.append('file',file);
    pipeline.style.display='flex';setStep('step-upload','active');
    fetch('/upload',{{method:'POST',body:fd}}).then(r=>r.json()).then(data=>{{
        setStep('step-upload','complete');evalId=data.eval_id;pollResult();
    }}).catch(err=>{{setStep('step-upload','error');fileInfo.textContent=`Error: ${{err}}`;}});
}}

function setStep(id,s){{const e=document.getElementById(id);e.classList.remove('active','complete','error');e.classList.add(s);
    if(s==='complete')e.querySelector('.icon').textContent='✓';if(s==='active')e.querySelector('.icon').textContent='⏳';}}

function pollResult(){{pollTimer=setInterval(()=>{
    fetch(`/result/${{evalId}}`).then(r=>r.json()).then(data=>{{
        updatePipeline(data);
        if(data.status==='complete'||data.status==='error'){{clearInterval(pollTimer);showResult(data);}}
    }}).catch(()=>{{}});
}},2000);}}

function updatePipeline(data){{
    const m={{'crawling':['step-crawl'],'building_cognition_packet':['step-crawl','step-merkle','step-score'],
        'building_llm_prompt':['step-crawl','step-merkle','step-score'],
        'evaluating_with_llm':['step-crawl','step-merkle','step-score','step-llm'],
        'writing_receipt':['step-crawl','step-merkle','step-score','step-llm'],
        'complete':['step-crawl','step-merkle','step-score','step-llm','step-receipt']}};
    const steps=m[data.status]||[];const all=['step-crawl','step-merkle','step-score','step-llm','step-receipt'];
    all.forEach(s=>{{const e=document.getElementById(s);e.classList.remove('active','complete','error');}});
    steps.forEach((s,i)=>setStep(s,i<steps.length-1||data.status==='complete'?'complete':'active'));
}}

function showResult(data){{
    resultBox.classList.add('visible');
    if(data.status==='error'){{resultContent.innerHTML=`<pre class="result-pre">Error: ${{data.error}}</pre>`;return;}}
    const p=data.packet||{{}},s=p.collateral_scores||{{}},g=s.grade||'F',r=data.receipt||{{}};
    let h=`<div style="display:flex;align-items:center;margin-bottom:16px">
        <div class="grade-display grade-${{g}}">${{g}}</div>
        <div><div style="font-size:24px;font-weight:700">Score: ${{s.final_score||0}}/100</div>
        <div style="color:#8b949e;font-size:14px">Borrowing base: $${{(s.borrowing_base_estimate_usd||{{}}).mid||0}}</div></div></div>
        <div class="safety-badge" style="background:#1f6feb">RECEIPT: ${{r.receipt_id||'N/A'}}</div>
        <div class="safety-badge" style="background:#238636">SOURCE CODE SENT TO LLM: NO</div>
        <div class="safety-badge" style="background:#238636">SECRETS FILTERED: ${{r.files_denied||0}} files</div>
        <div class="safety-badge" style="background:#238636">MERKLE: ${{(r.merkle_root||'').substring(0,16)}}...</div>`;
    h+=`<h3 style="margin-top:16px;color:#58a6ff">LLM Underwriting Verdict</h3><pre class="result-pre">${{data.llm_evaluation||'No evaluation'}}</pre>`;
    h+=`<h3 style="margin-top:16px;color:#58a6ff">Cognition Packet (sent to LLM)</h3><pre class="result-pre">${{JSON.stringify({{stats:p.stats,systems:p.systems,collateral_scores:p.collateral_scores,risks:p.risks,merkle_root:(p.merkle_root||'').substring(0,32)+'...'}},null,2)}}</pre>`;
    h+=`<h3 style="margin-top:16px;color:#58a6ff">Receipt</h3><pre class="result-pre">${{JSON.stringify(r,null,2)}}</pre>`;
    h+=`<div style="margin-top:16px"><a href="/result/${{evalId}}/packet" style="margin-right:12px">[Packet]</a><a href="/result/${{evalId}}/evaluation" style="margin-right:12px">[Evaluation]</a><a href="/result/${{evalId}}/receipt">[Receipt]</a></div>`;
    resultContent.innerHTML=h;
}}
</script>
</body></html>""")

# ─── JORKI API Endpoints ─────────────────────────────────────────────────

import sqlite3
import re
import time

JORKI_DATA_DIR = _Path(os.environ.get("SYSTEMLAKE_DATA_DIR", "/tmp/systemlake_v4b")) / "jorki"
JORKI_DATA_DIR.mkdir(parents=True, exist_ok=True)
JORKI_INDEX_DIR = JORKI_DATA_DIR / "indexes"
JORKI_INDEX_DIR.mkdir(parents=True, exist_ok=True)
JORKI_REGISTRY_PATH = JORKI_DATA_DIR / "registry.json"

def _jorki_load_registry():
    if JORKI_REGISTRY_PATH.exists():
        return json.loads(JORKI_REGISTRY_PATH.read_text())
    return {}

def _jorki_save_registry(reg):
    JORKI_REGISTRY_PATH.write_text(json.dumps(reg, indent=2))

def _jorki_index_file(filepath):
    path = _Path(filepath)
    content = path.read_bytes()
    size = len(content)
    merkle_root = hashlib.sha256(content).hexdigest()
    file_id = merkle_root[:12]
    text = content.decode("utf-8", errors="replace")
    lines = text.split("\n")
    line_count = len(lines)
    words = re.findall(r"\b\w+\b", text)
    word_freq = {}
    for w in words:
        word_freq[w] = word_freq.get(w, 0) + 1
    top_words = sorted(word_freq.items(), key=lambda x: -x[1])[:20]

    chunks = []
    current_chunk = []
    chunk_start = 0
    for i, line in enumerate(lines):
        current_chunk.append(line)
        is_boundary = (
            (line.strip() == "" and len(current_chunk) > 5)
            or line.strip().startswith("def ")
            or line.strip().startswith("class ")
            or line.strip().startswith("func ")
            or line.strip().startswith("workflow:")
        )
        if is_boundary and len(current_chunk) >= 3:
            chunks.append({"idx": len(chunks), "line_start": chunk_start, "line_end": i,
                           "boundary_type": "function" if line.strip().startswith(("def ", "class ", "func ")) else "paragraph",
                           "preview": "\n".join(current_chunk[:3])[:200], "line_count": len(current_chunk)})
            current_chunk = []
            chunk_start = i + 1
    if current_chunk:
        chunks.append({"idx": len(chunks), "line_start": chunk_start, "line_end": line_count - 1,
                       "boundary_type": "final", "preview": "\n".join(current_chunk[:3])[:200], "line_count": len(current_chunk)})

    symbols = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        for prefix in ["def ", "class ", "func ", "async def "]:
            if stripped.startswith(prefix):
                name = stripped[len(prefix):].split("(")[0].split(":")[0].strip()
                symbols.append({"line": i + 1, "name": name, "type": prefix.strip()})

    idx_path = JORKI_INDEX_DIR / f"{file_id}.idx"
    conn = sqlite3.connect(str(idx_path))
    conn.execute("CREATE TABLE IF NOT EXISTS file_meta (key TEXT, value TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS chunks (idx INTEGER, line_start INTEGER, line_end INTEGER, boundary_type TEXT, preview TEXT, line_count INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS word_freq (word TEXT, count INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS symbols (line INTEGER, name TEXT, type TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS capabilities (id INTEGER, name TEXT)")
    conn.execute("DELETE FROM file_meta")
    conn.execute("DELETE FROM chunks")
    conn.execute("DELETE FROM word_freq")
    conn.execute("DELETE FROM symbols")
    conn.execute("DELETE FROM capabilities")
    meta = {"filename": path.name, "size_bytes": str(size), "total_lines": str(line_count),
            "total_words": str(len(words)), "merkle_root": merkle_root,
            "total_chunks": str(len(chunks)), "total_symbols": str(len(symbols)),
            "file_id": file_id, "size_human": f"{size/1024:.1f}KB" if size < 1048576 else f"{size/1048576:.1f}MB"}
    for k, v in meta.items():
        conn.execute("INSERT INTO file_meta VALUES (?,?)", (k, str(v)))
    for c in chunks:
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", (c["idx"], c["line_start"], c["line_end"], c["boundary_type"], c["preview"], c["line_count"]))
    for w, cnt in top_words:
        conn.execute("INSERT INTO word_freq VALUES (?,?)", (w, cnt))
    for s in symbols:
        conn.execute("INSERT INTO symbols VALUES (?,?,?)", (s["line"], s["name"], s["type"]))
    caps = [(i, name) for i, name in enumerate(["sql", "nosql", "search", "chunk", "summary", "meta", "mcp", "word_freq", "symbols", "chunks", "merkle", "sha256", "capabilities", "revocation"])]
    conn.executemany("INSERT INTO capabilities VALUES (?,?)", caps)
    conn.commit()
    conn.close()

    index_size = idx_path.stat().st_size
    return {"file_id": file_id, "filename": path.name, "size_bytes": size,
            "size_human": f"{size/1024:.1f}KB" if size < 1048576 else f"{size/1048576:.1f}MB",
            "total_lines": line_count, "total_words": len(words),
            "total_chunks": len(chunks), "total_symbols": len(symbols),
            "merkle_root": merkle_root, "index_size_bytes": index_size,
            "index_ratio": round(index_size / max(size, 1) * 100, 1)}

# JORKI query tracking
_jorki_query_log = {}

def _jorki_track_query(file_id, query_type):
    if file_id not in _jorki_query_log:
        _jorki_query_log[file_id] = {"total_queries": 0, "query_breakdown": {}}
    _jorki_query_log[file_id]["total_queries"] += 1
    _jorki_query_log[file_id]["query_breakdown"][query_type] = _jorki_query_log[file_id]["query_breakdown"].get(query_type, 0) + 1
    _jorki_query_log[file_id]["last_access"] = time.time()

@app.get("/health")
async def jorki_health():
    reg = _jorki_load_registry()
    return {"status": "ok", "service": "jorki", "version": "2.0",
            "files_registered": len(reg),
            "persistent_storage": os.path.exists("/data"),
            "endpoints": ["/health", "/files", "/meta/{id}", "/summary/{id}",
                          "/capabilities/{id}", "/superpose/state/{id}",
                          "/search/{id}", "/chunk/{id}/{idx}", "/query/sql/{id}", "/stats/{id}"]}

@app.get("/files")
async def jorki_files():
    reg = _jorki_load_registry()
    files = []
    for fid, entry in reg.items():
        files.append({"file_id": fid, "filename": entry.get("filename", "unknown"),
                       "size": entry.get("size_human", ""), "format": entry.get("format", ""),
                       "status": entry.get("status", "unknown")})
    return {"files": files, "total": len(files)}

@app.get("/meta/{file_id}")
async def jorki_meta(file_id: str):
    idx_path = JORKI_INDEX_DIR / f"{file_id}.idx"
    if not idx_path.exists():
        return {"error": f"Index not found for {file_id}"}
    conn = sqlite3.connect(str(idx_path))
    rows = conn.execute("SELECT key, value FROM file_meta").fetchall()
    caps = conn.execute("SELECT name FROM capabilities").fetchall()
    conn.close()
    meta = {r[0]: r[1] for r in rows}
    return {"file_id": file_id, "meta": meta,
            "capabilities": [r[0] for r in caps],
            "endpoints": {"meta": f"/meta/{file_id}", "search": f"/search/{file_id}?q=",
                          "chunk": f"/chunk/{file_id}/{{idx}}", "sql": f"/query/sql/{file_id}"}}

@app.get("/summary/{file_id}")
async def jorki_summary(file_id: str):
    idx_path = JORKI_INDEX_DIR / f"{file_id}.idx"
    if not idx_path.exists():
        return {"error": f"Index not found for {file_id}"}
    conn = sqlite3.connect(str(idx_path))
    chunks = conn.execute("SELECT idx, boundary_type, line_start, line_end, line_count, preview FROM chunks LIMIT 50").fetchall()
    symbols = conn.execute("SELECT line, name, type FROM symbols LIMIT 50").fetchall()
    words = conn.execute("SELECT word, count FROM word_freq ORDER BY count DESC LIMIT 20").fetchall()
    conn.close()
    _jorki_track_query(file_id, "summary")
    return {"file_id": file_id,
            "semantic_chunks": [{"idx": r[0], "type": r[1], "lines": f"{r[2]}-{r[3]}", "line_count": r[4], "size": len(r[5])} for r in chunks],
            "functions": [{"line": r[0], "symbol": r[1]} for r in symbols],
            "top_words": [{"word": r[0], "count": r[1]} for r in words]}

@app.get("/capabilities/{file_id}")
async def jorki_capabilities(file_id: str):
    idx_path = JORKI_INDEX_DIR / f"{file_id}.idx"
    if not idx_path.exists():
        return {"error": f"Index not found for {file_id}"}
    conn = sqlite3.connect(str(idx_path))
    caps = conn.execute("SELECT id, name FROM capabilities").fetchall()
    conn.close()
    return {"file_id": file_id, "total": len(caps),
            "capabilities": [{"id": r[0], "name": r[1], "enabled": True} for r in caps]}

@app.get("/superpose/state/{file_id}")
async def jorki_state(file_id: str):
    reg = _jorki_load_registry()
    entry = reg.get(file_id, {})
    ql = _jorki_query_log.get(file_id, {"total_queries": 0, "query_breakdown": {}})
    idx_path = JORKI_INDEX_DIR / f"{file_id}.idx"
    index_size = idx_path.stat().st_size if idx_path.exists() else 0
    return {"file_id": file_id,
            "session_status": "live" if entry.get("status") == "active" else "idle",
            "uploaded_at": entry.get("indexed_at"),
            "last_access": ql.get("last_access"),
            "total_queries": ql.get("total_queries", 0),
            "query_breakdown": ql.get("query_breakdown", {}),
            "index_size_bytes": index_size,
            "original_size": entry.get("size_human", ""),
            "compression_ratio": f"{round(index_size / max(int(entry.get('size_bytes', 1)), 1) * 100, 1)}%" if entry.get('size_bytes') else ""}

@app.get("/search/{file_id}")
async def jorki_search(file_id: str, q: str = ""):
    idx_path = JORKI_INDEX_DIR / f"{file_id}.idx"
    if not idx_path.exists():
        return {"error": f"Index not found for {file_id}"}
    conn = sqlite3.connect(str(idx_path))
    chunk_results = conn.execute("SELECT idx, line_start, line_end, preview FROM chunks WHERE preview LIKE ?", (f"%{q}%",)).fetchall()
    sym_results = conn.execute("SELECT line, name, type FROM symbols WHERE name LIKE ?", (f"%{q}%",)).fetchall()
    conn.close()
    _jorki_track_query(file_id, "search")
    return {"file_id": file_id, "query": q,
            "results": [{"line": r[1], "text": r[3][:200]} for r in chunk_results] +
                       [{"line": r[0], "text": r[1]} for r in sym_results]}

@app.get("/chunk/{file_id}/{idx}")
async def jorki_chunk(file_id: str, idx: int):
    idx_path = JORKI_INDEX_DIR / f"{file_id}.idx"
    if not idx_path.exists():
        return {"error": f"Index not found for {file_id}"}
    conn = sqlite3.connect(str(idx_path))
    row = conn.execute("SELECT idx, line_start, line_end, boundary_type, preview, line_count FROM chunks WHERE idx = ?", (idx,)).fetchone()
    conn.close()
    _jorki_track_query(file_id, "chunk")
    if not row:
        return {"error": f"Chunk {idx} not found"}
    return {"idx": row[0], "line_start": row[1], "line_end": row[2],
            "boundary_type": row[3], "content": row[4], "line_count": row[5]}

@app.post("/query/sql/{file_id}")
async def jorki_sql(file_id: str, body: dict = Body(...)):
    sql = body.get("sql", "")
    if not sql.strip().upper().startswith("SELECT"):
        return {"error": "Only SELECT statements allowed"}
    for kw in ["INSERT", "UPDATE", "DELETE", "DROP", "ATTACH", "PRAGMA", "CREATE", "ALTER"]:
        if kw in sql.upper():
            return {"error": f"{kw} not allowed"}
    idx_path = JORKI_INDEX_DIR / f"{file_id}.idx"
    if not idx_path.exists():
        return {"error": f"Index not found for {file_id}"}
    conn = sqlite3.connect(str(idx_path))
    try:
        cursor = conn.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(1000)
        conn.close()
        _jorki_track_query(file_id, "sql")
        return {"file_id": file_id, "columns": columns, "rows": [list(r) for r in rows], "row_count": len(rows)}
    except Exception as e:
        conn.close()
        return {"error": str(e)}

@app.get("/stats/{file_id}")
async def jorki_stats(file_id: str):
    ql = _jorki_query_log.get(file_id, {"total_queries": 0, "query_breakdown": {}})
    return {"file_id": file_id, "stats": [{"type": k, "count": v} for k, v in ql.get("query_breakdown", {}).items()],
            "total_queries": ql.get("total_queries", 0)}

# Mount React UI static assets if dist exists
_ui_dist = _Path("/app/jorki_ui_dist")
if _ui_dist.exists():
    _assets_dist = _ui_dist / "assets"
    if _assets_dist.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dist)), name="jorki_assets")

    @app.get("/ui")
    async def jorki_ui():
        return FileResponse(str(_ui_dist / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
