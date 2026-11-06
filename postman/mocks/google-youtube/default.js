// Contract-derived local stand-in. Synthetic values only; never deploy this publicly.
const http = require('http');
let mode = 'success';
let events = [];
const usedCodes = new Set();
const scopes = 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.force-ssl';

function body(req) {
  if (req.body !== undefined) return Promise.resolve(req.body);
  return new Promise((resolve) => {
    let value = '';
    req.on('data', chunk => { value += chunk; });
    req.on('end', () => resolve(value));
  });
}

function send(res, status, value) {
  res.writeHead(status, {'Content-Type': 'application/json', 'X-TSU-Mock': 'google-youtube'});
  res.end(JSON.stringify(value));
}

http.createServer(async (req, res) => {
  const url = new URL(req.url, 'https://oauth2.googleapis.com');
  if (url.pathname === '/__control' && req.method === 'POST') {
    const raw = await body(req);
    const value = typeof raw === 'string' ? JSON.parse(raw) : raw;
    mode = value.mode;
    events = [];
    return send(res, 200, {mode});
  }
  if (url.pathname === '/__control' && req.method === 'GET') {
    return send(res, 200, {mode, events});
  }
  if (url.pathname === '/token' && req.method === 'POST') {
    const raw = await body(req);
    const data = typeof raw === 'string' ? Object.fromEntries(new URLSearchParams(raw)) : raw;
    events.push({operation: 'token', fields: Object.keys(data).sort()});
    if (data.client_id !== 'fake.apps.googleusercontent.com' || data.client_secret !== 'fake-secret'
        || data.redirect_uri !== 'https://studio.technoinno.live/auth/youtube/callback'
        || data.grant_type !== 'authorization_code' || !data.code
        || !data.code_verifier || data.code_verifier.length < 43) {
      return send(res, 400, {error: 'invalid_request'});
    }
    if (usedCodes.has(data.code)) return send(res, 400, {error: 'invalid_grant'});
    usedCodes.add(data.code);
    if (mode === 'token_failure') return send(res, 400, {error: 'invalid_grant'});
    if (mode === 'server_error') return send(res, 503, {error: 'temporarily_unavailable'});
    const result = {access_token: 'fake-access-token', refresh_token: 'fake-refresh-token',
                    token_type: 'Bearer', expires_in: 3600, scope: scopes};
    if (mode === 'no_refresh') delete result.refresh_token;
    if (mode === 'missing_scope') result.scope = 'https://www.googleapis.com/auth/youtube.readonly';
    if (mode === 'missing_edit_scope') result.scope = scopes.replace(' https://www.googleapis.com/auth/youtube.force-ssl','');
    if (mode === 'timeout') return setTimeout(() => send(res, 200, result), 1000);
    return send(res, 200, result);
  }
  if (url.pathname === '/youtube/v3/channels' && req.method === 'GET') {
    events.push({operation: 'channels', part: url.searchParams.get('part'), mine: url.searchParams.get('mine')});
    if (req.headers.authorization !== 'Bearer fake-access-token'
        || url.searchParams.get('part') !== 'snippet' || url.searchParams.get('mine') !== 'true') {
      return send(res, 403, {error: {code: 403, message: 'Invalid request'}});
    }
    if (mode === 'channel_failure') return send(res, 403, {error: {code: 403}});
    if (mode === 'empty_channel') return send(res, 200, {items: []});
    return send(res, 200, {items: [{id: mode === 'wrong_channel' ? 'UCwrong' : 'UC8DbuevZRxVTWxltG9oDFRw',
                                  snippet: {title: 'TechnoInno', customUrl: '@techno-inno'}}]});
  }
  return send(res, 501, {error: 'This test stand-in does not model this endpoint'});
}).listen(process.env.PORT || 4500);
