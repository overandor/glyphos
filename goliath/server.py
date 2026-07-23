#!/usr/bin/env python3
"""Goliath server — Flask web server + API.

One process. One UI. All subsystems.
"""

from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string

from .config import GOLIATH_PORT, subsystem_status
from .core import GoliathCore

app = Flask(__name__, static_folder=None)
core = GoliathCore()

# ── Web UI ──────────────────────────────────────────────────────────

UI_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GOLIATH — Unified Monolith</title>
<style>
:root{
  --bg:#08080a;--surface:#0e0e12;--surface2:#14141a;--border:#1e1e26;
  --text:#e0e0e0;--text2:#666;--text3:#444;
  --orange:#ff6b1a;--orange-dim:#cc5414;--cyan:#00d4ff;--green:#7ec8a0;
  --red:#ff4466;--gold:#fbbf24;--purple:#a78bfa;
}
*{box-sizing:border-box;margin:0;padding:0;font-family:'SF Mono','Monaco','Cascadia Code',monospace;}
body{background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 20% 0%,rgba(255,107,26,.04),transparent 50%),radial-gradient(ellipse at 80% 100%,rgba(0,212,255,.03),transparent 50%);pointer-events:none;z-index:0;}
header{position:relative;z-index:1;padding:1.2rem 2rem;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:1rem;background:rgba(8,8,10,.8);backdrop-filter:blur(12px);}
header h1{font-size:1.1rem;font-weight:600;letter-spacing:.08em;color:var(--orange);}
header .glyph{font-size:1.3rem;color:var(--orange);}
header .ver{font-size:.65rem;color:var(--text3);border:1px solid var(--border);padding:.15rem .4rem;border-radius:3px;}
header .live{margin-left:auto;font-size:.7rem;color:var(--green);display:flex;align-items:center;gap:.4rem;}
.live .dot{width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s ease-in-out infinite;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.3;}}

.layout{position:relative;z-index:1;display:grid;grid-template-columns:280px 1fr 320px;gap:1px;background:var(--border);min-height:calc(100vh - 56px);}
.col{background:var(--bg);padding:1rem;overflow-y:auto;}
.col::-webkit-scrollbar{width:4px;}
.col::-webkit-scrollbar-thumb{background:var(--border);}

.panel{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:.8rem;margin-bottom:.8rem;transition:border-color .2s;}
.panel:hover{border-color:var(--orange-dim);}
.panel-title{font-size:.65rem;text-transform:uppercase;letter-spacing:.1em;color:var(--text2);margin-bottom:.6rem;display:flex;align-items:center;gap:.4rem;}
.panel-title .g{color:var(--orange);}

.status-row{display:flex;justify-content:space-between;align-items:center;padding:.3rem 0;font-size:.75rem;}
.status-row .label{color:var(--text2);}
.status-row .val{font-size:.7rem;}
.status-row .val.on{color:var(--green);}
.status-row .val.off{color:var(--text3);}
.status-row .val.warn{color:var(--gold);}

.glyph-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.4rem;margin-bottom:.6rem;}
.glyph-cell{text-align:center;padding:.5rem .2rem;background:var(--surface2);border-radius:4px;font-size:.9rem;cursor:default;transition:all .2s;}
.glyph-cell:hover{background:var(--border);}
.glyph-cell .gl{font-size:1.1rem;}
.glyph-cell .lb{font-size:.55rem;color:var(--text3);margin-top:.2rem;}

.btn{display:inline-block;padding:.4rem .8rem;border:1px solid var(--border);border-radius:4px;background:var(--surface2);color:var(--text);font-size:.7rem;cursor:pointer;transition:all .15s;font-family:inherit;}
.btn:hover{border-color:var(--orange);color:var(--orange);}
.btn:active{transform:scale(.97);}
.btn.primary{border-color:var(--orange-dim);color:var(--orange);}
.btn.danger{border-color:var(--red);color:var(--red);}

.input{width:100%;padding:.4rem .6rem;background:var(--surface2);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:.75rem;font-family:inherit;outline:none;}
.input:focus{border-color:var(--orange);}
textarea.input{resize:vertical;min-height:60px;}

.log{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:.6rem;font-size:.7rem;line-height:1.5;max-height:300px;overflow-y:auto;}
.log::-webkit-scrollbar{width:4px;}
.log::-webkit-scrollbar-thumb{background:var(--border);}
.log-line{padding:.1rem 0;color:var(--text2);}
.log-line .ts{color:var(--text3);margin-right:.4rem;}
.log-line.ok{color:var(--green);}
.log-line.err{color:var(--red);}
.log-line.warn{color:var(--gold);}

.kpi-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.5rem;margin-bottom:.8rem;}
.kpi{background:var(--surface2);border-radius:4px;padding:.6rem;text-align:center;}
.kpi .num{font-size:1.3rem;font-weight:600;color:var(--orange);}
.kpi .lb{font-size:.6rem;color:var(--text3);text-transform:uppercase;letter-spacing:.05em;}

.task-bar{display:flex;gap:.4rem;margin-bottom:.6rem;}
.task-bar .input{flex:1;}

.section-label{font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;color:var(--text3);margin:.8rem 0 .4rem;}

pre{font-size:.65rem;color:var(--text2);background:var(--surface2);border-radius:4px;padding:.6rem;overflow-x:auto;font-family:inherit;}
</style>
</head>
<body>

<header>
  <span class="glyph">◉</span>
  <h1>GOLIATH</h1>
  <span class="ver">v1.0.0 monolith</span>
  <span class="live"><span class="dot"></span> <span id="live-status">initializing</span></span>
</header>

<div class="layout">
  <!-- LEFT: Subsystem Status -->
  <div class="col" id="left-col">
    <div class="panel">
      <div class="panel-title"><span class="g">◈</span> Subsystems</div>
      <div id="subsystems"></div>
    </div>

    <div class="panel">
      <div class="panel-title"><span class="g">⟡</span> Glyph Layer</div>
      <div class="glyph-grid">
        <div class="glyph-cell"><div class="gl" style="color:var(--green)">◉</div><div class="lb">live</div></div>
        <div class="glyph-cell"><div class="gl" style="color:var(--cyan)">◇</div><div class="lb">indexed</div></div>
        <div class="glyph-cell"><div class="gl" style="color:var(--orange)">▲</div><div class="lb">rising</div></div>
        <div class="glyph-cell"><div class="gl" style="color:var(--red)">▼</div><div class="lb">falling</div></div>
        <div class="glyph-cell"><div class="gl" style="color:var(--green)">◆</div><div class="lb">verified</div></div>
        <div class="glyph-cell"><div class="gl" style="color:var(--gold)">⟁</div><div class="lb">anomaly</div></div>
        <div class="glyph-cell"><div class="gl" style="color:var(--text3)">◌</div><div class="lb">dormant</div></div>
        <div class="glyph-cell"><div class="gl" style="color:var(--cyan)">⌁</div><div class="lb">stream</div></div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-title"><span class="g">$</span> Membra Ledger</div>
      <div id="ledger-stats"></div>
    </div>

    <div class="panel">
      <div class="panel-title"><span class="g">⧖</span> Companion Pack</div>
      <div id="companion-stats"></div>
    </div>
  </div>

  <!-- CENTER: Main Control -->
  <div class="col" id="center-col">
    <div class="panel">
      <div class="panel-title"><span class="g">⌁</span> LLM Inference — Local Ollama</div>
      <div class="task-bar">
        <input class="input" id="llm-prompt" placeholder="Ask the local LLM..." />
        <button class="btn primary" onclick="llmGenerate()">Send</button>
      </div>
      <div class="log" id="llm-output"><div class="log-line"><span class="ts">--:--:--</span>Waiting for input...</div></div>
    </div>

    <div class="panel">
      <div class="panel-title"><span class="g">◈</span> Browser Bridge — C++ CDP</div>
      <div class="task-bar">
        <select class="input" id="bridge-mode" style="max-width:160px">
          <option value="demo-sniffies-login">demo-sniffies-login</option>
          <option value="login">login</option>
          <option value="recover">recover</option>
          <option value="reset">reset</option>
          <option value="profile">profile</option>
        </select>
        <input class="input" id="bridge-email" placeholder="email" style="max-width:180px" />
        <input class="input" id="bridge-pass" type="password" placeholder="pass" style="max-width:120px" />
        <label style="font-size:.65rem;color:var(--text2);display:flex;align-items:center;gap:.2rem"><input type="checkbox" id="bridge-approval" checked /> approval</label>
        <button class="btn primary" onclick="bridgeRun()">Run</button>
      </div>
      <div class="log" id="bridge-output" style="max-height:200px"><div class="log-line"><span class="ts">--:--:--</span>Bridge idle.</div></div>
    </div>

    <div class="panel">
      <div class="panel-title"><span class="g">⟡</span> Policy Engine — Action Check</div>
      <div class="task-bar">
        <input class="input" id="policy-action" placeholder="e.g. submit_login, mass_message, read_profile" />
        <button class="btn" onclick="policyCheck()">Check</button>
      </div>
      <div id="policy-result"></div>
    </div>

    <div class="panel">
      <div class="panel-title"><span class="g">◇</span> Membra Task Submit</div>
      <div class="task-bar">
        <input class="input" id="task-input" placeholder="Submit a task to the kernel..." />
        <button class="btn" onclick="submitTask()">Submit</button>
      </div>
      <div id="task-result"></div>
    </div>
  </div>

  <!-- RIGHT: Live Feed + KPIs -->
  <div class="col" id="right-col">
    <div class="panel">
      <div class="panel-title"><span class="g">▲</span> KPIs</div>
      <div class="kpi-grid" id="kpi-grid"></div>
    </div>

    <div class="panel">
      <div class="panel-title"><span class="g">⌁</span> Live Feed</div>
      <div class="log" id="live-feed" style="max-height:400px"></div>
    </div>

    <div class="panel">
      <div class="panel-title"><span class="g">◆</span> Receipts</div>
      <div class="log" id="receipt-feed" style="max-height:200px"></div>
    </div>
  </div>
</div>

<script>
const API = '';
let feedLines = [];

function log(el, msg, cls='') {
  const ts = new Date().toLocaleTimeString();
  const div = document.createElement('div');
  div.className = 'log-line ' + cls;
  div.innerHTML = `<span class="ts">${ts}</span>${msg}`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function feed(msg, cls='') {
  feedLines.unshift({msg, cls, ts: new Date().toLocaleTimeString()});
  if (feedLines.length > 50) feedLines.pop();
  const el = document.getElementById('live-feed');
  el.innerHTML = feedLines.map(l => `<div class="log-line ${l.cls}"><span class="ts">${l.ts}</span>${l.msg}</div>`).join('');
}

async function api(path, opts={}) {
  try {
    const r = await fetch(API + path, opts);
    return await r.json();
  } catch(e) {
    return {error: e.message};
  }
}

async function refreshStatus() {
  const s = await api('/api/status');
  if (s.error) return;

  // Subsystems
  const sub = s.subsystems || {};
  const gl = (on, onG='◉', offG='◌') => `<span style="color:${on?'var(--green)':'var(--text3)'}">${on?onG:offG}</span>`;
  document.getElementById('subsystems').innerHTML = `
    <div class="status-row"><span class="label">membra-os</span><span class="val ${sub.membra_os?'on':'off'}">${gl(sub.membra_os)} ${sub.membra_os?'active':'offline'}</span></div>
    <div class="status-row"><span class="label">browser_bridge</span><span class="val ${sub.browser_bridge?'on':'off'}">${gl(sub.browser_bridge)} ${sub.browser_bridge?'built':'missing'}</span></div>
    <div class="status-row"><span class="label">companion_pack</span><span class="val ${sub.companion_pack?'on':'off'}">${gl(sub.companion_pack)} ${sub.companion_pack?'loaded':'missing'}</span></div>
    <div class="status-row"><span class="label">agent_tower</span><span class="val ${sub.agent_tower?'on':'off'}">${gl(sub.agent_tower)} ${sub.agent_tower?'found':'missing'}</span></div>
    <div class="status-row"><span class="label">gentlr</span><span class="val ${sub.gentlr?'on':'off'}">${gl(sub.gentlr)} ${sub.gentlr?'model':'missing'}</span></div>
    <div class="status-row"><span class="label">llm_os</span><span class="val ${sub.llm_os?'on':'off'}">${gl(sub.llm_os)} ${sub.llm_os?'found':'missing'}</span></div>
    <div class="status-row"><span class="label">ollama</span><span class="val ${s.ollama?'on':'off'}">${gl(s.ollama)} ${s.ollama?'running':'offline'}</span></div>
  `;

  // Membra ledger
  if (s.membra) {
    const l = s.membra.ledger || {};
    document.getElementById('ledger-stats').innerHTML = `
      <div class="status-row"><span class="label">workers</span><span class="val on">${s.membra.workers}</span></div>
      <div class="status-row"><span class="label">queued</span><span class="val">${s.membra.queued}</span></div>
      <div class="status-row"><span class="label">ledger total</span><span class="val">${l.total || 0}</span></div>
    `;
  }

  // Companion
  if (s.companion) {
    document.getElementById('companion-stats').innerHTML = `
      <div class="status-row"><span class="label">bridge</span><span class="val ${s.companion.bridge_available?'on':'off'}">${s.companion.bridge_available?'◉ ready':'◌ offline'}</span></div>
      <div class="status-row"><span class="label">queue pending</span><span class="val">${s.companion.queue_pending}</span></div>
      <div class="status-row"><span class="label">queue executed</span><span class="val on">${s.companion.queue_executed}</span></div>
      <div class="status-row"><span class="label">queue rejected</span><span class="val ${s.companion.queue_rejected?'warn':'off'}">${s.companion.queue_rejected}</span></div>
      <div class="status-row"><span class="label">receipts</span><span class="val">${s.companion.ledger.total}</span></div>
    `;
  }

  // KPIs
  const kpis = [
    {num: s.subsystems ? Object.values(s.subsystems).filter(Boolean).length : 0, lb: 'systems'},
    {num: s.ollama ? 1 : 0, lb: 'ollama'},
    {num: s.companion?.ledger?.total || 0, lb: 'receipts'},
    {num: s.membra?.workers || 0, lb: 'workers'},
  ];
  document.getElementById('kpi-grid').innerHTML = kpis.map(k => `<div class="kpi"><div class="num">${k.num}</div><div class="lb">${k.lb}</div></div>`).join('');

  // Live status
  const active = Object.values(s.subsystems || {}).filter(Boolean).length;
  document.getElementById('live-status').textContent = `${active} systems live`;
}

async function llmGenerate() {
  const prompt = document.getElementById('llm-prompt').value.trim();
  if (!prompt) return;
  const el = document.getElementById('llm-output');
  log(el, `> ${prompt}`);
  feed(`LLM query: ${prompt.slice(0,60)}...`);
  const r = await api('/api/ollama/generate', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({prompt})
  });
  if (r.error) { log(el, `Error: ${r.error}`, 'err'); return; }
  log(el, r.response || '(empty)', 'ok');
  feed('LLM response received', 'ok');
}

async function bridgeRun() {
  const mode = document.getElementById('bridge-mode').value;
  const email = document.getElementById('bridge-email').value;
  const pass = document.getElementById('bridge-pass').value;
  const approval = document.getElementById('bridge-approval').checked;
  const el = document.getElementById('bridge-output');
  log(el, `Launching bridge: mode=${mode} approval=${approval}`);
  feed(`Bridge: ${mode} started`);
  const r = await api('/api/bridge/run', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({mode, email, password: pass, approval_required: approval, headless: false})
  });
  if (r.error) { log(el, `Error: ${r.error}`, 'err'); return; }
  const lines = (r.output || '').split('\n').filter(l => l.trim());
  lines.slice(0, 20).forEach(l => log(el, l));
  if (lines.length > 20) log(el, `... ${lines.length - 20} more lines`);
  feed(`Bridge: ${mode} complete`, 'ok');
}

async function policyCheck() {
  const action = document.getElementById('policy-action').value.trim();
  if (!action) return;
  const r = await api(`/api/policy/check?action=${encodeURIComponent(action)}`);
  const el = document.getElementById('policy-result');
  if (r.error) { el.innerHTML = `<pre>Error: ${r.error}</pre>`; return; }
  const color = r.verdict === 'allowed' ? 'var(--green)' : r.verdict === 'blocked' ? 'var(--red)' : 'var(--gold)';
  const icon = r.verdict === 'allowed' ? '✅' : r.verdict === 'blocked' ? '⛔' : '⏸️';
  el.innerHTML = `<div class="status-row"><span class="label">${action}</span><span class="val" style="color:${color}">${icon} ${r.verdict}</span></div><pre>${r.reason}</pre>`;
  feed(`Policy: ${action} → ${r.verdict}`);
}

async function submitTask() {
  const task = document.getElementById('task-input').value.trim();
  if (!task) return;
  const r = await api('/api/membra/submit', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({task})
  });
  const el = document.getElementById('task-result');
  if (r.error) { el.innerHTML = `<pre>Error: ${r.error}</pre>`; return; }
  el.innerHTML = `<pre>Job ID: ${r.job_id}\nStatus: ${r.status}</pre>`;
  feed(`Task submitted: ${r.job_id}`);
}

// Auto-refresh
refreshStatus();
setInterval(refreshStatus, 5000);
feed('Goliath monolith initialized');
</script>
</body>
</html>"""


# ── API Routes ──────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(UI_HTML)


@app.route("/api/status")
def api_status():
    return jsonify(core.status())


@app.route("/api/ollama/generate", methods=["POST"])
def api_ollama():
    body = request.get_json(force=True)
    result = core.ollama_generate(body.get("prompt", ""), body.get("system", ""))
    return jsonify(result)


@app.route("/api/bridge/run", methods=["POST"])
def api_bridge():
    body = request.get_json(force=True)
    output = core.run_bridge(
        mode=body.get("mode", "login"),
        email=body.get("email", ""),
        password=body.get("password", ""),
        headless=body.get("headless", False),
        approval_required=body.get("approval_required", False),
    )
    return jsonify({"output": output})


@app.route("/api/policy/check")
def api_policy():
    action = request.args.get("action", "")
    return jsonify(core.check_policy(action))


@app.route("/api/membra/submit", methods=["POST"])
def api_membra_submit():
    body = request.get_json(force=True)
    result = core.submit_task(body.get("task", ""))
    return jsonify(result)


@app.route("/api/receipts")
def api_receipts():
    if core.companion:
        return jsonify(core.companion["ledger"].summary())
    return jsonify({"total": 0, "by_type": {}})


@app.route("/api/receipts/list")
def api_receipts_list():
    if core.companion:
        return jsonify({"receipts": core.companion["ledger"].read_all()[-50:]})
    return jsonify({"receipts": []})


# ── ShadowShard M-Forge ─────────────────────────────────────────────

@app.route("/api/forge/status")
def api_forge_status():
    if core.forge:
        return jsonify(core.forge.status())
    return jsonify({"error": "forge not available"})


@app.route("/api/forge/process", methods=["POST"])
def api_forge_process():
    if not core.forge:
        return jsonify({"error": "forge not available"})
    body = request.get_json(force=True)
    result = core.forge.process_task(
        prompt=body.get("prompt", ""),
        context=body.get("context", ""),
        expected=body.get("expected", ""),
        skill_hint=body.get("skill_hint", ""),
        privacy_required=body.get("privacy_required", True),
        max_cloud_cost=body.get("max_cloud_cost", 0.05),
        business_value=body.get("business_value", 0.0),
    )
    return jsonify(result.to_dict())


@app.route("/api/forge/ingest", methods=["POST"])
def api_forge_ingest():
    if not core.forge:
        return jsonify({"error": "forge not available"})
    body = request.get_json(force=True)
    result = core.forge.ingest_files(
        body.get("directory", ""),
        max_files=body.get("max_files", 500),
    )
    return jsonify(result)


@app.route("/api/forge/train", methods=["POST"])
def api_forge_train():
    if not core.forge:
        return jsonify({"error": "forge not available"})
    body = request.get_json(force=True)
    result = core.forge.train_adapter(
        body.get("expert", ""),
        body.get("training_shards", []),
    )
    return jsonify(result)


@app.route("/api/forge/experts")
def api_forge_experts():
    if core.forge:
        return jsonify(core.forge.adapter_forge.list_experts())
    return jsonify({"error": "forge not available"})


@app.route("/api/forge/adapters")
def api_forge_adapters():
    if core.forge:
        return jsonify({"trained": core.forge.adapter_forge.list_trained(),
                         "queue": core.forge.adapter_forge.list_queue()})
    return jsonify({"error": "forge not available"})


@app.route("/api/forge/smartness")
def api_forge_smartness():
    if core.forge:
        return jsonify(core.forge.smartness_report())
    return jsonify({"error": "forge not available"})


@app.route("/api/forge/mesh")
def api_forge_mesh():
    if core.forge:
        return jsonify({"stats": core.forge.mesh.stats(),
                         "nodes": core.forge.mesh.list_nodes(),
                         "jobs": core.forge.mesh.list_jobs()})
    return jsonify({"error": "forge not available"})


@app.route("/api/forge/providers")
def api_forge_providers():
    if core.forge:
        return jsonify(core.forge.teacher.list_providers())
    return jsonify({"error": "forge not available"})


# ── AgentSubstrateOS ────────────────────────────────────────────────

@app.route("/api/substrate/status")
def api_substrate_status():
    if core.substrate:
        return jsonify(core.substrate.status())
    return jsonify({"error": "substrate not available"})


@app.route("/api/substrate/prepare", methods=["POST"])
def api_substrate_prepare():
    if not core.substrate:
        return jsonify({"error": "substrate not available"})
    body = request.get_json(force=True)
    result = core.substrate.prepare_task(
        task=body.get("task", ""),
        repo_root=body.get("repo_root", ""),
        symptom=body.get("symptom", ""),
        evidence=body.get("evidence", ""),
        allowed_files=body.get("allowed_files", []),
        forbidden_files=body.get("forbidden_files", []),
        test_cmd=body.get("test_cmd", ""),
        full_test_cmd=body.get("full_test_cmd", ""),
        definition_of_done=body.get("definition_of_done", ""),
        prompt_mode=body.get("prompt_mode", "frontier_over_frontier"),
        autonomous=body.get("autonomous", False),
    )
    return jsonify(result)


@app.route("/api/substrate/session/begin", methods=["POST"])
def api_substrate_begin():
    if not core.substrate:
        return jsonify({"error": "substrate not available"})
    body = request.get_json(force=True)
    before = core.substrate.begin_session(body.get("packet_id", ""))
    return jsonify(before)


@app.route("/api/substrate/session/end", methods=["POST"])
def api_substrate_end():
    if not core.substrate:
        return jsonify({"error": "substrate not available"})
    body = request.get_json(force=True)
    result = core.substrate.end_session(
        packet_id=body.get("packet_id", ""),
        before=body.get("before", {}),
        files_inspected=body.get("files_inspected", 0),
        files_changed=body.get("files_changed", 0),
        retries=body.get("retries", 0),
        tests_run=body.get("tests_run", 0),
        cloud_calls=body.get("cloud_calls", 0),
        cloud_cost=body.get("cloud_cost", 0.0),
        output_quality=body.get("output_quality", 0.0),
        artifact_value=body.get("artifact_value", 0.0),
    )
    return jsonify(result)


# ── Truth Verifier ──────────────────────────────────────────────────

@app.route("/api/truth/status")
def api_truth_status():
    if hasattr(core, 'truth') and core.truth:
        return jsonify(core.truth.stats())
    return jsonify({"error": "truth verifier not available"})


@app.route("/api/truth/verify-input", methods=["POST"])
def api_truth_verify_input():
    if not hasattr(core, 'truth') or not core.truth:
        return jsonify({"error": "truth verifier not available"})
    body = request.get_json(force=True)
    check = core.truth.verify_input(
        task=body.get("task", ""),
        files=body.get("files", []),
        prompt=body.get("prompt", ""),
        budget=body.get("budget", {}),
        verification=body.get("verification", {}),
    )
    return jsonify(check.to_dict())


@app.route("/api/truth/verify-state", methods=["POST"])
def api_truth_verify_state():
    if not hasattr(core, 'truth') or not core.truth:
        return jsonify({"error": "truth verifier not available"})
    body = request.get_json(force=True)
    check = core.truth.verify_state(
        files_changed=body.get("files_changed", []),
        files_expected=body.get("files_expected", []),
        test_cmd=body.get("test_cmd", ""),
        build_cmd=body.get("build_cmd", ""),
        lint_cmd=body.get("lint_cmd", ""),
        typecheck_cmd=body.get("typecheck_cmd", ""),
    )
    return jsonify(check.to_dict())


# ── Agent Governors ─────────────────────────────────────────────────

@app.route("/api/devin/status")
def api_devin_status():
    if hasattr(core, 'devin_gov') and core.devin_gov:
        return jsonify(core.devin_gov.stats())
    return jsonify({"error": "devin governor not available"})


@app.route("/api/devin/prepare", methods=["POST"])
def api_devin_prepare():
    if not hasattr(core, 'devin_gov') or not core.devin_gov:
        return jsonify({"error": "devin governor not available"})
    body = request.get_json(force=True)
    from shadowshard_mforge.agent_substrate import TaskPacket, ComputeBudget, VerificationContract
    packet = TaskPacket(
        packet_id=body.get("packet_id", ""),
        task=body.get("task", ""),
        allowed_inspection=body.get("allowed_files", []),
        verification=VerificationContract(
            tests_required=body.get("test_commands", []),
            acceptance_criteria=body.get("stop_condition", ""),
        ),
    )
    result = core.devin_gov.prepare_packet(packet)
    return jsonify(result)


@app.route("/api/devin/evaluate", methods=["POST"])
def api_devin_evaluate():
    if not hasattr(core, 'devin_gov') or not core.devin_gov:
        return jsonify({"error": "devin governor not available"})
    body = request.get_json(force=True)
    result = core.devin_gov.evaluate_run(
        files_inspected=body.get("files_inspected", 0),
        files_changed=body.get("files_changed", 0),
        retries=body.get("retries", 0),
        tests_passed=body.get("tests_passed", False),
        unrelated_changes=body.get("unrelated_changes", False),
    )
    return jsonify(result)


@app.route("/api/windsurf/status")
def api_windsurf_status():
    if hasattr(core, 'windsurf_gov') and core.windsurf_gov:
        return jsonify(core.windsurf_gov.stats())
    return jsonify({"error": "windsurf governor not available"})


@app.route("/api/windsurf/prepare", methods=["POST"])
def api_windsurf_prepare():
    if not hasattr(core, 'windsurf_gov') or not core.windsurf_gov:
        return jsonify({"error": "windsurf governor not available"})
    body = request.get_json(force=True)
    from shadowshard_mforge.agent_substrate import TaskPacket, ComputeBudget, VerificationContract
    packet = TaskPacket(
        packet_id=body.get("packet_id", ""),
        task=body.get("task", ""),
        allowed_inspection=body.get("allowed_files", []),
    )
    result = core.windsurf_gov.prepare_workspace(packet, body.get("open_files"))
    return jsonify(result)


@app.route("/api/windsurf/check-memory")
def api_windsurf_check_memory():
    if not hasattr(core, 'windsurf_gov') or not core.windsurf_gov:
        return jsonify({"error": "windsurf governor not available"})
    ram_mb = int(request.args.get("ram_mb", 0))
    return jsonify(core.windsurf_gov.check_memory(ram_mb))


@app.route("/api/windsurf/evaluate", methods=["POST"])
def api_windsurf_evaluate():
    if not hasattr(core, 'windsurf_gov') or not core.windsurf_gov:
        return jsonify({"error": "windsurf governor not available"})
    body = request.get_json(force=True)
    result = core.windsurf_gov.evaluate_run(
        open_files=body.get("open_files", 0),
        terminal_lines=body.get("terminal_lines", 0),
        log_lines_in_chat=body.get("log_lines_in_chat", 0),
        tests_narrow_first=body.get("tests_narrow_first", True),
        unrelated_refactors=body.get("unrelated_refactors", False),
    )
    return jsonify(result)


# ── FOF Benchmark ───────────────────────────────────────────────────

@app.route("/api/fof/status")
def api_fof_status():
    if hasattr(core, 'fof_benchmark') and core.fof_benchmark:
        return jsonify(core.fof_benchmark.status())
    return jsonify({"error": "fof benchmark not available"})


@app.route("/api/fof/baseline", methods=["POST"])
def api_fof_baseline():
    if not hasattr(core, 'fof_benchmark') or not core.fof_benchmark:
        return jsonify({"error": "fof benchmark not available"})
    from shadowshard_mforge.agent_governors import FOFMetrics
    body = request.get_json(force=True)
    core.fof_benchmark.record_baseline(FOFMetrics(
        context_compression_ratio=body.get("context_compression_ratio", 0),
        patch_efficiency=body.get("patch_efficiency", 0),
        verification_density=body.get("verification_density", 0),
        frontier_avoidance_ratio=body.get("frontier_avoidance_ratio", 0),
        local_substrate_tax_mb=body.get("local_substrate_tax_mb", 0),
        agent_drift=body.get("agent_drift", 0),
        tokens_consumed=body.get("tokens_consumed", 0),
        cloud_calls=body.get("cloud_calls", 0),
        retries=body.get("retries", 0),
        time_to_first_correct_patch_s=body.get("time_to_first_correct_patch_s", 0),
    ))
    return jsonify({"status": "recorded"})


@app.route("/api/fof/macro", methods=["POST"])
def api_fof_macro():
    if not hasattr(core, 'fof_benchmark') or not core.fof_benchmark:
        return jsonify({"error": "fof benchmark not available"})
    from shadowshard_mforge.agent_governors import FOFMetrics
    body = request.get_json(force=True)
    core.fof_benchmark.record_macro(FOFMetrics(
        context_compression_ratio=body.get("context_compression_ratio", 0),
        patch_efficiency=body.get("patch_efficiency", 0),
        verification_density=body.get("verification_density", 0),
        frontier_avoidance_ratio=body.get("frontier_avoidance_ratio", 0),
        local_substrate_tax_mb=body.get("local_substrate_tax_mb", 0),
        agent_drift=body.get("agent_drift", 0),
        tokens_consumed=body.get("tokens_consumed", 0),
        cloud_calls=body.get("cloud_calls", 0),
        retries=body.get("retries", 0),
        time_to_first_correct_patch_s=body.get("time_to_first_correct_patch_s", 0),
    ))
    return jsonify({"status": "recorded"})


@app.route("/api/fof/compare")
def api_fof_compare():
    if hasattr(core, 'fof_benchmark') and core.fof_benchmark:
        return jsonify(core.fof_benchmark.compare())
    return jsonify({"error": "fof benchmark not available"})


# ── Training Primitives ─────────────────────────────────────────────

@app.route("/api/primitives/status")
def api_primitives_status():
    if hasattr(core, 'primitives') and core.primitives:
        return jsonify(core.primitives.status())
    return jsonify({"error": "training primitives not available"})


@app.route("/api/primitives/apple")
def api_primitives_apple():
    if hasattr(core, 'primitives') and core.primitives:
        return jsonify({"primitives": core.primitives.apple_runnable_primitives()})
    return jsonify({"error": "training primitives not available"})


@app.route("/api/primitives/cluster")
def api_primitives_cluster():
    if hasattr(core, 'primitives') and core.primitives:
        return jsonify({"primitives": core.primitives.cluster_only_primitives()})
    return jsonify({"error": "training primitives not available"})


@app.route("/api/primitives/map")
def api_primitives_map():
    if hasattr(core, 'primitives') and core.primitives:
        return jsonify(core.primitives.shadow_shard_to_primitive_map())
    return jsonify({"error": "training primitives not available"})


@app.route("/api/primitives/assessment")
def api_primitives_assessment():
    if hasattr(core, 'primitives') and core.primitives:
        return jsonify(core.primitives.honest_assessment())
    return jsonify({"error": "training primitives not available"})


# ── Unified OS Registry ──────────────────────────────────────────────

@app.route("/api/unified/registry")
def api_unified_registry():
    """Full system registry — all 164 systems across 7 layers."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from unified_os import REGISTRY, LAYER_NAMES, by_layer, check_path_exists, language_distribution, registry_hash
        layers_data = []
        for n in range(1, 8):
            systems = by_layer(n)
            layers_data.append({
                "num": n,
                "name": LAYER_NAMES[n],
                "count": len(systems),
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
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/unified/system/<name>")
def api_unified_system(name):
    """Find a system by name in the unified registry."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from unified_os import by_name, check_path_exists
        from dataclasses import asdict
        s = by_name(name)
        if not s:
            return jsonify({"error": "not found"}), 404
        d = asdict(s)
        d["exists"] = check_path_exists(s)
        return jsonify(d)
    except Exception as e:
        return jsonify({"error": str(e)})


def start(port: int = GOLIATH_PORT):
    """Start the Goliath monolith server."""
    print(f"\n  ╔══════════════════════════════════════════════════╗")
    print(f"  ║  GOLIATH — Unified Monolith System                ║")
    print(f"  ║  Port: {port:<42} ║")
    print(f"  ╚══════════════════════════════════════════════════╝\n")

    status = core.status()
    for name, available in status["subsystems"].items():
        icon = "◉" if available else "◌"
        print(f"  {icon} {name:20s} {'available' if available else 'missing'}")
    print(f"  {'◉' if status['ollama'] else '◌'} {'ollama':20s} {'running' if status['ollama'] else 'offline'}")
    print(f"\n  → http://localhost:{port}")
    print(f"  → /api/unified/registry — 164 systems across 7 layers\n")

    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Goliath — Unified Monolith")
    parser.add_argument("--port", type=int, default=GOLIATH_PORT)
    args = parser.parse_args()
    start(args.port)
