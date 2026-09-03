/* probe_playback.mjs —— 检测 Edge(Chromium) 能否播放 OpenCV mp4v 输出 */
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const PORT = 9226;
const USER_DIR = path.resolve(__dirname, '../demo/.edge-probe');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function launch() {
  return new Promise((res, rej) => {
    const p = spawn(EDGE, ['--headless=new', '--disable-gpu', '--no-first-run',
      `--remote-debugging-port=${PORT}`, `--user-data-dir=${USER_DIR}`,
      '--window-size=1000,700', 'about:blank'], { stdio: 'ignore' });
    p.on('error', rej); res(p);
  });
}
async function wsUrl() {
  for (let i = 0; i < 40; i++) {
    try {
      const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = l.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch (e) { /* retry */ }
    await sleep(250);
  }
  throw new Error('CDP fail');
}
class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.p = new Map(); }
  static async connect(u) {
    const ws = new WebSocket(u);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    const c = new CDP(ws);
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && c.p.has(m.id)) { const { res, rej } = c.p.get(m.id); c.p.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
    };
    return c;
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((res, rej) => { this.p.set(id, { res, rej }); this.ws.send(JSON.stringify({ id, method, params })); });
  }
  async eval(expression) {
    const r = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    return r.result && r.result.value;
  }
}

async function probe(cdp, label, url) {
  await cdp.eval(`(async function(){
    var v = document.createElement('video');
    v.muted = true; v.preload = 'auto';
    v.src = ${JSON.stringify(url)};
    document.body.appendChild(v);
    await new Promise(function(ok){ v.onloadeddata = ok; v.onerror = function(){ ok(); }; setTimeout(ok, 6000); });
    return JSON.stringify({
      readyState: v.readyState,
      videoWidth: v.videoWidth,
      videoHeight: v.videoHeight,
      duration: v.duration,
      error: v.error ? (v.error.code + ':' + v.error.message) : null,
      canPlay: v.canPlayType('video/mp4; codecs="mp4v.20.9"'),
      currentSrc: v.currentSrc
    });
  })()`).then((s) => {
    console.log('[' + label + ']', s);
  }).catch((e) => console.log('[' + label + '] ERR', e.message));
}

async function main() {
  const proc = await launch();
  const cdp = await CDP.connect(await wsUrl());
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Page.navigate', { url: 'http://127.0.0.1:8080/index.html' });
  await sleep(2000);
  await cdp.eval(`(function(){
    var codes = ['avc1.42E01E','mp4v.20.9','vp09.00.10.08','vp8','hvc1.1.6.L120.B0'];
    var out = {};
    codes.forEach(function(c){ out[c] = document.createElement('video').canPlayType('video/mp4; codecs="'+c+'"'); });
    return JSON.stringify(out);
  })()`).then((s) => console.log('[canPlayType]', s));
  await probe(cdp, '结果视频3_tracked(mp4v)', 'http://127.0.0.1:8080/files/results/3_tracked.mp4');
  await probe(cdp, '原始上传1ed8a84e(mp4v)', 'http://127.0.0.1:8080/files/origin/1ed8a84e.mp4');
  cdp.ws.close(); proc.kill();
  console.log('probe done');
}
main().catch((e) => { console.error(e); process.exit(1); });
