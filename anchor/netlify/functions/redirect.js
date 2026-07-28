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

exports.handler = async (event) => {
  const configUrl = DEFAULT_CONFIG_URL || (event.queryStringParameters && event.queryStringParameters.config);

  if (!configUrl) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'TUNNEL_CONFIG_URL not set' })
    };
  }

  let data;
  try {
    data = await fetchTunnelConfig(configUrl);
  } catch (e) {
    return { statusCode: 502, body: JSON.stringify({ error: 'Cannot fetch tunnel config', detail: e.message }) };
  }

  if (!data) {
    return { statusCode: 502, body: JSON.stringify({ error: 'Invalid tunnel config' }) };
  }

  if (data.state === 'active' && data.url) {
    const healthy = await checkUrl(data.url).catch(() => true);
    if (healthy) {
      return { statusCode: 302, headers: { Location: data.url } };
    }
    const fallbacks = data.fallback_urls || [];
    for (const fb of fallbacks) {
      if (await checkUrl(fb)) {
        return { statusCode: 302, headers: { Location: fb } };
      }
    }
    return { statusCode: 503, headers: { 'Content-Type': 'text/html' }, body: DORMANT_HTML };
  }

  if (data.state === 'transitioning') {
    if (data.new_url && await checkUrl(data.new_url)) {
      return { statusCode: 302, headers: { Location: data.new_url } };
    }
    return {
      statusCode: 503,
      headers: { 'Content-Type': 'text/html' },
      body: DORMANT_HTML.replace('Tunnel Dormant', 'Tunnel Transitioning').replace('Zero active compute', 'Warm-up relay in progress')
    };
  }

  const fallbacks = data.fallback_urls || [];
  for (const fb of fallbacks) {
    if (await checkUrl(fb)) {
      return { statusCode: 302, headers: { Location: fb } };
    }
  }

  return { statusCode: 503, headers: { 'Content-Type': 'text/html' }, body: DORMANT_HTML };
};
