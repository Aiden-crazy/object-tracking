/* test_boxdraw.mjs —— 用 CDP Input 真实鼠标事件验证画布框选 */
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const PORT = 9228;
const USER_DIR = path.resolve(__dirname, '../demo/.edge-test2');
const VIDEO = path.resolve(__dirname, '../demo/demo_ball_track.mp4');   // 仓库内相对定位，换电脑/换目录都不受影响
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function launch() {
  return new Promise((res, rej) => {
    const p = spawn(EDGE, ['--headless=new', '--disable-gpu', '--no-first-run',
      `--remote-debugging-port=${PORT}`, `--user-data-dir=${USER_DIR}`,
      '--window-size=1360,980', 'about:blank'], { stdio: 'ignore' });
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
      if (m.id && c.p.has(m.id)) {
        const { res, rej } = c.p.get(m.id); c.p.delete(m.id);
        m.error ? rej(new Error(m.error.message)) : res(m.result);
      }
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

async function main() {
  const proc = await launch();
  const cdp = await CDP.connect(await wsUrl());
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('DOM.enable');

  await cdp.send('Page.navigate', { url: 'http://127.0.0.1:8080/track.html' });
  await sleep(4000);
  const doc = await cdp.send('DOM.getDocument');
  const q = await cdp.send('DOM.querySelector', { nodeId: doc.root.nodeId, selector: '#fileInput' });
  await cdp.send('DOM.setFileInputFiles', { nodeId: q.nodeId, files: [VIDEO] });
  await cdp.eval(`document.getElementById('fileInput').dispatchEvent(new Event('change', { bubbles: true }))`);
  await sleep(2000);
  await cdp.eval(`document.getElementById('extractBtn').click()`);
  await sleep(3000);

  // 获取画布中心屏幕坐标，用 Input.dispatchMouseEvent 拖拽
  const box = JSON.parse(await cdp.eval(`JSON.stringify((function(){
    var cv = document.getElementById('boxCanvas');
    var r = cv.getBoundingClientRect();
    return { x0: r.left + r.width*0.10, y0: r.top + r.height*0.35,
             x1: r.left + r.width*0.34, y1: r.top + r.height*0.60 };
  })())`));
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: box.x0, y: box.y0, button: 'left', buttons: 1, clickCount: 1 });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x1, y: box.y1, button: 'left', buttons: 1 });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: box.x1, y: box.y1, button: 'left', buttons: 0, clickCount: 1 });
  await sleep(800);

  const st = await cdp.eval(`JSON.stringify({
    bbox: document.getElementById('bboxInfo').textContent,
    visible: !document.getElementById('bboxInfo').classList.contains('hidden'),
    resetVisible: !document.getElementById('resetBox').classList.contains('hidden')
  })`);
  console.log('[真实鼠标拖拽画框后]', st);

  cdp.ws.close(); proc.kill();
  console.log('done');
}
main().catch((e) => { console.error(e); process.exit(1); });
