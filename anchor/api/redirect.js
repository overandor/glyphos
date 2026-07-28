/**
 * Serverless Tunnel Redirect — Zero-Uptime Continuity Endpoint
 *
 * Deploy this as a Vercel serverless function or Netlify function.
 * It reads tunnel.json from a configurable source and returns a 302 redirect
 * to the current live tunnel URL. No HTML, no client-side JS, no polling.
 *
 * URL: https://your-anchor.vercel.app/api/redirect → 302 → live tunnel
 *
 * Config sources (set TUNNEL_CONFIG_URL env var):
 *   - Raw GitHub: https://raw.githubusercontent.com/user/repo/main/anchor/tunnel.json
 *   - JSONBin: https://api.jsonbin.io/v3/b/<BIN_ID>/latest
 *   - Vercel KV / Netlify Blobs
 *   - Any URL returning JSON with { state, url, fallback_urls }
 *
 * Fallback chain: primary URL → fallback_urls[0..2] → dormant page
 */

const DEFAULT_CONFIG_URL = process.env.TUNNEL_CONFIG_URL || '';
const DORMANT_HTML = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Tunnel Dormant</title>
<meta http-equiv="refresh" content="10">
<style>body{background:#06060a;color:#c0c0d0;font-family:monospace;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.box{text-align:center;padding:40px;border:1px solid rgba(80,80,120,.25);border-radius:14px;max-width:500px}
h1{color:#7878c8;font-size:20px}p{color:#666;font-size:13px;line-height:1.6}
.dot{width:10px;height:10px;border-radius:50%;background:#666;display:inline-block;margin-right:8px}
</style></head>
<body><div class="box">
<h1><span class="dot"></span>Tunnel Dormant</h1>
<p>Zero active compute. Identity persists.<br>Ignition will materialize a new body.<br>Auto-retrying in 10s...</p>
</div></body></html>`;

async function fetchTunnelConfig(url) {
  const r = await fetch(url + '?t=' + Date.now(), { cache: 'no-store' });
  if (!r.ok) return null;
  return r.json();
}

async function checkUrl(url, timeoutMs = 5000) {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    const r = await fetch(url, { method: 'HEAD', signal: ctrl.signal, redirect: 'follow' });
    clearTimeout(t);
    return r.ok || r.status < 500;
  } catch {
    return false;
  }
}

module.exports = async (req, res) => {
  const configUrl = DEFAULT_CONFIG_URL || req.query.config;

  if (!configUrl) {
    return res.status(500).json({
      error: 'TUNNEL_CONFIG_URL not set',
      hint: 'Set env var TUNNEL_CONFIG_URL to the URL of your tunnel.json'
    });
  }

  let data;
  try {
    data = await fetchTunnelConfig(configUrl);
  } catch (e) {
    return res.status(502).json({ error: 'Cannot fetch tunnel config', detail: e.message });
  }

  if (!data) {
    return res.status(502).json({ error: 'Invalid tunnel config response' });
  }

  // Active tunnel — redirect immediately
  if (data.state === 'active' && data.url) {
    // Quick health check (non-blocking: redirect even if check is slow)
    const healthy = await checkUrl(data.url).catch(() => true);
    if (healthy) {
      return res.redirect(302, data.url);
    }
    // Primary failed — try fallbacks
    const fallbacks = data.fallback_urls || [];
    for (const fb of fallbacks) {
      if (await checkUrl(fb)) {
        return res.redirect(302, fb);
      }
    }
    // All failed — show dormant
    return res.status(503).setHeader('Content-Type', 'text/html').send(DORMANT_HTML);
  }

  // Transitioning — brief wait then redirect to new URL if available
  if (data.state === 'transitioning') {
    if (data.new_url && await checkUrl(data.new_url)) {
      return res.redirect(302, data.new_url);
    }
    return res.status(503).setHeader('Content-Type', 'text/html').send(
      DORMANT_HTML.replace('Tunnel Dormant', 'Tunnel Transitioning')
        .replace('Zero active compute', 'Warm-up relay in progress')
    );
  }

  // Dormant — try fallbacks, then show dormant page
  const fallbacks = data.fallback_urls || [];
  for (const fb of fallbacks) {
    if (await checkUrl(fb)) {
      return res.redirect(302, fb);
    }
  }

  return res.status(503).setHeader('Content-Type', 'text/html').send(DORMANT_HTML);
};
