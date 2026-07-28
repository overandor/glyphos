#!/usr/bin/env python3
"""
Tunnel Rotator — Zero-Uptime Continuity anchor manager.

Manages the lifecycle of ephemeral tunnels and updates the static anchor.

Flow:
  1. Start ephemeral tunnel (cloudflare/ngrok/localtunnel)
  2. Get the ephemeral URL
  3. Update anchor/tunnel.json with the new URL + state=active
  4. Serve content through the tunnel
  5. When tunnel dies or needs to rotate:
     a. Set state=transitioning in tunnel.json
     b. Start new tunnel
     c. Verify new tunnel is healthy
     d. Update tunnel.json with new URL
     e. Kill old tunnel
  6. When shutting down:
     a. Set state=dormant in tunnel.json
     b. Record last_seen timestamp
     c. Kill tunnel

The static anchor (index.html + tunnel.json) lives on a permanent host
(Netlify/Vercel/GitHub Pages). The ephemeral body updates tunnel.json
via git push, API call, or direct file write if co-located.

Usage:
  python3 tunnel_rotator.py start --port 8000 --provider cloudflare
  python3 tunnel_rotator.py start --port 8000 --provider ngrok
  python3 tunnel_rotator.py start --port 8000 --provider localtunnel
  python3 tunnel_rotator.py rotate
  python3 tunnel_rotator.py stop
  python3 tunnel_rotator.py status
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ANCHOR_DIR = Path(__file__).parent / "anchor"
TUNNEL_JSON = ANCHOR_DIR / "tunnel.json"
RECEIPTS_DIR = Path(__file__).parent / "receipts" / "tunnel_rotator"
RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
RECEIPT_LEDGER = RECEIPTS_DIR / "chain.jsonl"

PROVIDERS = {
    "cloudflare": {
        "cmd": "cloudflared",
        "args": ["tunnel", "--url", "http://localhost:{port}"],
        "url_pattern": "https://*.trycloudflare.com",
        "extract_url": lambda line: _extract_cloudflare_url(line),
    },
    "ngrok": {
        "cmd": "ngrok",
        "args": ["http", "{port}"],
        "url_pattern": "https://*.ngrok.io",
        "api_url": "http://localhost:4040/api/tunnels",
    },
    "localtunnel": {
        "cmd": "lt",
        "args": ["--port", "{port}"],
        "url_pattern": "https://*.loca.lt",
        "extract_url": lambda line: line.strip() if "https://" in line and ".loca.lt" in line else None,
    },
}


def _extract_cloudflare_url(line):
    """Extract URL from cloudflared output — appears in banner box or as a logged URL."""
    import re
    m = re.search(r'(https://[a-z0-9-]+\.trycloudflare\.com)', line)
    return m.group(1) if m else None


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_tunnel_json():
    if TUNNEL_JSON.exists():
        return json.loads(TUNNEL_JSON.read_text())
    return {}


def save_tunnel_json(data):
    ANCHOR_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_tunnel_json()
    existing.update(data)
    TUNNEL_JSON.write_text(json.dumps(existing, indent=2) + "\n")


def write_receipt(event, data):
    """SHA-256 chained receipt for tunnel events."""
    entries = []
    if RECEIPT_LEDGER.exists():
        entries = [json.loads(l) for l in RECEIPT_LEDGER.read_text().strip().split("\n") if l]
    prev_hash = entries[-1]["hash"] if entries else "0" * 64
    body = json.dumps({"event": event, "data": data, "prev": prev_hash, "ts": now_iso()}, sort_keys=True)
    h = hashlib.sha256(body.encode()).hexdigest()
    entry = {"event": event, "data": data, "prev": prev_hash, "hash": h, "ts": now_iso()}
    with open(RECEIPT_LEDGER, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return h


def verify_receipts():
    if not RECEIPT_LEDGER.exists():
        return True, 0
    entries = [json.loads(l) for l in RECEIPT_LEDGER.read_text().strip().split("\n") if l]
    for i, entry in enumerate(entries):
        prev = "0" * 64 if i == 0 else entries[i - 1]["hash"]
        body = json.dumps({"event": entry["event"], "data": entry["data"], "prev": prev, "ts": entry["ts"]}, sort_keys=True)
        h = hashlib.sha256(body.encode()).hexdigest()
        if h != entry["hash"]:
            return False, i
        if entry["prev"] != prev:
            return False, i
    return True, len(entries)


def wait_for_tunnel_url(proc, provider, timeout=30):
    """Watch tunnel process output for the URL."""
    cfg = PROVIDERS[provider]
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            print(f"  [tunnel] {line.rstrip()}")
            url = None
            if "extract_url" in cfg:
                url = cfg["extract_url"](line)
            if url and url.startswith("https://"):
                return url
        time.sleep(0.3)
    return None


def get_ngrok_url():
    """Get URL from ngrok API."""
    try:
        r = urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=3)
        data = json.loads(r.read())
        for t in data.get("tunnels", []):
            if t.get("public_url", "").startswith("https://"):
                return t["public_url"]
    except Exception:
        pass
    return None


def check_tunnel_health(url, timeout=5, expected_substring=None):
    """Verify the tunnel is actually serving the expected content.

    If expected_substring is provided, checks that the response body contains it.
    This prevents false positives where Ollama (port 11434) is served instead of
    the web app (port 8000).
    """
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        if r.status != 200:
            return False
        if expected_substring:
            body = r.read(4096).decode('utf-8', errors='replace')
            return expected_substring.lower() in body.lower()
        return True
    except Exception:
        return False


def check_local_health(port, timeout=3):
    """Check if the local service on the given port is reachable."""
    try:
        r = urllib.request.urlopen(f"http://localhost:{port}/", timeout=timeout)
        return r.status == 200
    except Exception:
        return False


def check_ollama(timeout=3):
    """Check if Ollama is reachable and return model count."""
    try:
        r = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=timeout)
        data = json.loads(r.read())
        return len(data.get("models", []))
    except Exception:
        return None


def measure_tunnel_latency(url, timeout=5):
    """Measure round-trip latency to the tunnel URL in milliseconds."""
    try:
        import time as _t
        start = _t.time()
        urllib.request.urlopen(url, timeout=timeout)
        return int((_t.time() - start) * 1000)
    except Exception:
        return None


def start_tunnel(port, provider):
    """Start an ephemeral tunnel and update the anchor."""
    cfg = PROVIDERS.get(provider)
    if not cfg:
        print(f"Unknown provider: {provider}. Available: {list(PROVIDERS.keys())}")
        return None

    if not TUNNEL_JSON.exists():
        save_tunnel_json({"state": "dormant"})

    current = load_tunnel_json()
    if current.get("state") == "active" and current.get("url"):
        print(f"Tunnel already active: {current['url']}")
        print("Use 'rotate' to switch to a new tunnel.")
        return current["url"]

    print(f"Starting {provider} tunnel on port {port}...")

    args = [cfg["cmd"]] + [a.format(port=port) for a in cfg["args"]]
    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError:
        print(f"  {cfg['cmd']} not found. Install it first:")
        if provider == "cloudflare":
            print("  brew install cloudflared")
        elif provider == "ngrok":
            print("  brew install ngrok")
        elif provider == "localtunnel":
            print("  npm install -g localtunnel")
        return None

    # Set transitioning state
    save_tunnel_json({"state": "transitioning", "thermal_mode": "warm preparation"})

    # Wait for URL
    url = None
    if provider == "ngrok":
        time.sleep(3)
        url = get_ngrok_url()
    else:
        url = wait_for_tunnel_url(proc, provider)

    if not url:
        print("  Failed to get tunnel URL")
        save_tunnel_json({"state": "dormant", "thermal_mode": "deep dormancy"})
        proc.kill()
        return None

    # Health check — verify content is the web app, not Ollama or something else
    print(f"  Tunnel URL: {url}")
    print("  Health check...", end=" ")
    time.sleep(2)
    if not check_tunnel_health(url):
        print("FAILED (unreachable)")
        save_tunnel_json({"state": "dormant", "thermal_mode": "deep dormancy"})
        proc.kill()
        return None
    print("OK")

    # Check local service is also reachable
    local_ok = check_local_health(port)

    # Check Ollama and measure latency
    ollama_models = check_ollama()
    latency_ms = measure_tunnel_latency(url)

    # Read rotation count
    rotation_count = current.get("rotation_count", 0)

    # Update anchor
    receipt_hash = write_receipt("materialize", {
        "url": url,
        "provider": provider,
        "port": port,
        "pid": proc.pid,
    })

    save_tunnel_json({
        "state": "active",
        "url": url,
        "provider": provider,
        "port": port,
        "pid": proc.pid,
        "materialized_at": now_iso(),
        "updated_at": now_iso(),
        "lease_expires": "ephemeral",
        "predecessor_hash": current.get("receipt_hash"),
        "receipt_hash": receipt_hash,
        "thermal_mode": "active",
        "local_reachable": local_ok,
        "ollama_reachable": ollama_models is not None,
        "ollama_models": ollama_models,
        "latency_ms": latency_ms,
        "rotation_count": rotation_count,
        "fallback_urls": [],
    })

    # Save PID for later cleanup
    pid_file = RECEIPTS_DIR / "tunnel.pid"
    pid_file.write_text(str(proc.pid))

    print(f"  Anchor updated: tunnel.json → state=active")
    print(f"  Local service: {'reachable' if local_ok else 'UNREACHABLE'}")
    print(f"  Receipt: {receipt_hash[:16]}...")
    print(f"\n  Ephemeral URL: {url}")
    print(f"  Visitors hit static URL → auto-redirected to ephemeral URL")

    # Keep process alive
    try:
        proc.wait()
    except KeyboardInterrupt:
        stop_tunnel(proc)
    return url


def rotate_tunnel():
    """Rotate to a new tunnel without downtime."""
    current = load_tunnel_json()
    if current.get("state") != "active":
        print("No active tunnel to rotate. Use 'start' first.")
        return

    old_url = current.get("url")
    old_provider = current.get("provider", "cloudflare")
    port = current.get("port", 8000)
    rotation_count = current.get("rotation_count", 0)
    print(f"Rotating from {old_url}...")

    # Set transitioning
    save_tunnel_json({
        "state": "transitioning",
        "old_url": old_url,
        "new_url": None,
        "baton_status": "warm-up relay starting",
        "thermal_mode": "warm preparation",
    })

    write_receipt("rotate_start", {"old_url": old_url})

    # Start new tunnel
    cfg = PROVIDERS.get(old_provider, PROVIDERS["cloudflare"])
    args = [cfg["cmd"]] + [a.format(port=port) for a in cfg["args"]]

    try:
        new_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except FileNotFoundError:
        print(f"  {cfg['cmd']} not found. Cannot rotate.")
        save_tunnel_json({"state": "active", "url": old_url, "thermal_mode": "active"})
        return

    new_url = None
    if old_provider == "ngrok":
        time.sleep(3)
        new_url = get_ngrok_url()
    else:
        new_url = wait_for_tunnel_url(new_proc, old_provider)

    if not new_url or not check_tunnel_health(new_url):
        print("  New tunnel failed. Keeping old tunnel.")
        save_tunnel_json({"state": "active", "url": old_url, "thermal_mode": "active"})
        new_proc.kill()
        return

    print(f"  New tunnel: {new_url}")
    print("  Health check... OK")

    # Keep old URL as fallback
    fallback = current.get("fallback_urls", [])
    if old_url and old_url not in fallback:
        fallback = [old_url] + fallback[:2]  # Keep last 2 fallbacks

    # Check Ollama and measure latency for new tunnel
    ollama_models = check_ollama()
    latency_ms = measure_tunnel_latency(new_url)

    # Update anchor to new URL
    receipt_hash = write_receipt("rotate_complete", {
        "old_url": old_url,
        "new_url": new_url,
        "provider": old_provider,
    })

    save_tunnel_json({
        "state": "active",
        "url": new_url,
        "old_url": None,
        "new_url": None,
        "baton_status": None,
        "materialized_at": now_iso(),
        "updated_at": now_iso(),
        "predecessor_hash": current.get("receipt_hash"),
        "receipt_hash": receipt_hash,
        "thermal_mode": "active",
        "port": port,
        "pid": new_proc.pid,
        "ollama_reachable": ollama_models is not None,
        "ollama_models": ollama_models,
        "latency_ms": latency_ms,
        "rotation_count": rotation_count + 1,
        "fallback_urls": fallback,
    })

    # Kill old tunnel
    pid_file = RECEIPTS_DIR / "tunnel.pid"
    if pid_file.exists():
        old_pid = int(pid_file.read_text())
        try:
            os.kill(old_pid, signal.SIGTERM)
            print(f"  Old tunnel (pid {old_pid}) terminated.")
        except ProcessLookupError:
            pass

    pid_file.write_text(str(new_proc.pid))
    print(f"  Rotation complete. New URL: {new_url}")
    print(f"  Rotation count: {rotation_count + 1}")
    print(f"  Static visitors now redirect to new ephemeral URL.")

    try:
        new_proc.wait()
    except KeyboardInterrupt:
        stop_tunnel(new_proc)


def stop_tunnel(proc=None):
    """Stop tunnel and set dormant state."""
    pid_file = RECEIPTS_DIR / "tunnel.pid"

    if proc is None:
        if pid_file.exists():
            pid = int(pid_file.read_text())
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Tunnel (pid {pid}) stopped.")
            except ProcessLookupError:
                print("Tunnel process not found (already dead).")
        else:
            print("No tunnel PID file found.")
    else:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Tunnel stopped.")

    current = load_tunnel_json()
    receipt_hash = write_receipt("drain", {
        "url": current.get("url"),
        "last_state": current.get("state"),
    })

    save_tunnel_json({
        "state": "dormant",
        "url": None,
        "last_seen": now_iso(),
        "updated_at": now_iso(),
        "receipt_hash": receipt_hash,
        "thermal_mode": "deep dormancy",
        "successor_capsule": "ready",
    })

    if pid_file.exists():
        pid_file.unlink()

    print("Anchor updated: state=dormant")
    print("Identity persists. Zero active compute.")


def status():
    """Show current tunnel and anchor status."""
    data = load_tunnel_json()
    print("=== Tunnel Rotator Status ===")
    print(f"  State:          {data.get('state', 'unknown')}")
    print(f"  URL:            {data.get('url', 'none')}")
    print(f"  Provider:       {data.get('provider', 'none')}")
    print(f"  Port:           {data.get('port', 'unknown')}")
    print(f"  Materialized:   {data.get('materialized_at', 'never')}")
    print(f"  Updated:        {data.get('updated_at', 'never')}")
    print(f"  Thermal mode:   {data.get('thermal_mode', 'unknown')}")
    print(f"  Local reachable:{data.get('local_reachable', 'unknown')}")
    print(f"  Rotation count: {data.get('rotation_count', 0)}")
    print(f"  Receipt:        {data.get('receipt_hash', 'none')[:16] if data.get('receipt_hash') else 'none'}...")
    print(f"  Last seen:      {data.get('last_seen', 'never')}")
    print(f"  Predecessor:    {data.get('predecessor_hash', 'none')[:16] if data.get('predecessor_hash') else 'none'}...")

    fallbacks = data.get("fallback_urls", [])
    if fallbacks:
        print(f"  Fallback URLs:  {len(fallbacks)}")
        for i, fb in enumerate(fallbacks):
            print(f"    [{i}] {fb}")

    valid, count = verify_receipts()
    print(f"\n  Receipt chain:  {count} entries, {'VALID' if valid else 'BROKEN'}")

    pid_file = RECEIPTS_DIR / "tunnel.pid"
    if pid_file.exists():
        pid = pid_file.read_text()
        print(f"  Tunnel PID:     {pid}")
    else:
        print(f"  Tunnel PID:     none")


def watchdog(port=8000, provider="cloudflare", interval=30):
    """Watchdog mode: monitor tunnel health and auto-rotate on failure."""
    print(f"Watchdog mode: checking every {interval}s (port={port}, provider={provider})")
    while True:
        data = load_tunnel_json()
        state = data.get("state")
        url = data.get("url")

        if state == "active" and url:
            healthy = check_tunnel_health(url, timeout=10)
            local_ok = check_local_health(port)
            if not healthy:
                print(f"  [{now_iso()}] Tunnel unhealthy: {url}")
                print(f"  [{now_iso()}] Auto-rotating...")
                # Kill the dead tunnel process if still alive
                pid_file = RECEIPTS_DIR / "tunnel.pid"
                if pid_file.exists():
                    try:
                        old_pid = int(pid_file.read_text())
                        os.kill(old_pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                # Start new tunnel in background
                cfg = PROVIDERS.get(provider, PROVIDERS["cloudflare"])
                args = [cfg["cmd"]] + [a.format(port=port) for a in cfg["args"]]
                try:
                    new_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    new_url = wait_for_tunnel_url(new_proc, provider)
                    if new_url and check_tunnel_health(new_url):
                        rotation_count = data.get("rotation_count", 0)
                        fallback = data.get("fallback_urls", [])
                        if url and url not in fallback:
                            fallback = [url] + fallback[:2]
                        receipt_hash = write_receipt("auto_rotate", {
                            "old_url": url,
                            "new_url": new_url,
                            "reason": "health_check_failed",
                        })
                        save_tunnel_json({
                            "state": "active",
                            "url": new_url,
                            "provider": provider,
                            "port": port,
                            "pid": new_proc.pid,
                            "materialized_at": now_iso(),
                            "updated_at": now_iso(),
                            "receipt_hash": receipt_hash,
                            "thermal_mode": "active",
                            "local_reachable": local_ok,
                            "rotation_count": rotation_count + 1,
                            "fallback_urls": fallback,
                        })
                        pid_file.write_text(str(new_proc.pid))
                        print(f"  [{now_iso()}] Rotated to: {new_url}")
                    else:
                        print(f"  [{now_iso()}] Rotation failed. Trying fallbacks...")
                        for fb in data.get("fallback_urls", []):
                            if check_tunnel_health(fb):
                                save_tunnel_json({"state": "active", "url": fb, "updated_at": now_iso()})
                                print(f"  [{now_iso()}] Fallback active: {fb}")
                                break
                except FileNotFoundError:
                    print(f"  [{now_iso()}] {cfg['cmd']} not found. Cannot rotate.")
            elif not local_ok:
                print(f"  [{now_iso()}] WARNING: local service on port {port} unreachable but tunnel up")
                save_tunnel_json({"local_reachable": False, "updated_at": now_iso()})
            else:
                save_tunnel_json({"local_reachable": True, "updated_at": now_iso()})
                print(f"  [{now_iso()}] OK: {url}")
        elif state != "active":
            print(f"  [{now_iso()}] Tunnel state: {state}. Skipping health check.")

        time.sleep(interval)


def main():
    p = argparse.ArgumentParser(description="Tunnel Rotator — Zero-Uptime Continuity anchor manager")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("start", help="Start ephemeral tunnel and update anchor")
    sp.add_argument("--port", type=int, default=8000)
    sp.add_argument("--provider", choices=list(PROVIDERS.keys()), default="cloudflare")

    sub.add_parser("rotate", help="Rotate to a new tunnel without downtime")
    sub.add_parser("stop", help="Stop tunnel and set dormant")
    sub.add_parser("status", help="Show current status")
    sub.add_parser("receipts", help="Verify receipt chain")

    sw = sub.add_parser("watchdog", help="Monitor tunnel health and auto-rotate on failure")
    sw.add_argument("--port", type=int, default=8000)
    sw.add_argument("--provider", choices=list(PROVIDERS.keys()), default="cloudflare")
    sw.add_argument("--interval", type=int, default=30)

    args = p.parse_args()

    if args.cmd == "start":
        start_tunnel(args.port, args.provider)
    elif args.cmd == "rotate":
        rotate_tunnel()
    elif args.cmd == "stop":
        stop_tunnel()
    elif args.cmd == "status":
        status()
    elif args.cmd == "receipts":
        valid, count = verify_receipts()
        print(f"Receipt chain: {count} entries, {'VALID' if valid else 'BROKEN'}")
    elif args.cmd == "watchdog":
        watchdog(args.port, args.provider, args.interval)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
