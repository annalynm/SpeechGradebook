#!/usr/bin/env node
/**
 * Small webhook server: receives export JSON from the SpeechGradebook dashboard
 * ("Export and submit to ISAAC"), saves to exported.json, and runs run_training.sh.
 *
 * Run on your machine (or a server) so the dashboard can POST to it:
 *   node receive_export_server.js [--port 3131]
 *
 * In the app: set Webhook URL to http://YOUR_IP:3131/export (e.g. http://localhost:3131/export
 * if the app runs on the same machine). Then click "Export and submit to ISAAC".
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const args = process.argv.slice(2);
const portIdx = args.indexOf('--port');
const PORT = portIdx >= 0 && args[portIdx + 1] ? parseInt(args[portIdx + 1], 10) : 3131;

const SCRIPT_DIR = path.resolve(path.dirname(__filename));
const EXPORTED_JSON = path.join(SCRIPT_DIR, 'exported.json');
const RUN_TRAINING = path.join(SCRIPT_DIR, 'run_training.sh');

const server = http.createServer((req, res) => {
  if (req.method !== 'POST' || req.url !== '/export') {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found. POST /export with JSON body.');
    return;
  }

  const chunks = [];
  req.on('data', (chunk) => chunks.push(chunk));
  req.on('end', () => {
    const body = Buffer.concat(chunks).toString('utf8');
    let data;
    try {
      data = JSON.parse(body);
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid JSON' }));
      return;
    }
    if (!Array.isArray(data)) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Body must be a JSON array' }));
      return;
    }
    if (data.length === 0) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, message: 'No data to export', count: 0 }));
      return;
    }

    try {
      fs.writeFileSync(EXPORTED_JSON, JSON.stringify(data, null, 2), 'utf8');
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Failed to write exported.json', detail: e.message }));
      return;
    }

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, count: data.length, message: 'Saved; starting training.' }));

    const child = spawn('bash', [RUN_TRAINING], {
      cwd: SCRIPT_DIR,
      stdio: 'inherit',
      detached: true,
    });
    child.unref();
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Receive-export server listening on http://0.0.0.0:${PORT}/export`);
  console.log('In SpeechGradebook: set Webhook URL to http://YOUR_IP:' + PORT + '/export and click "Export and submit to ISAAC".');
});
