/* test_extract.mjs —— 功能验证：网页检测端"提取首帧"按钮
 * 流程：打开 track.html → 自动登录 → 注入 H.264 测试视频文件 →
 *       点击"提取首帧" → 检查画布是否成功绘制（修复验证）。
 */
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const PORT = 9227;
const USER_DIR = path.resolve(__dirname, '../demo/.edge-test');
const VIDEO = 'C:/Users/Administrator/Desktop/C/综设3-单目标跟踪/demo/demo_ball_track.mp4';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function launch() {
  return new Promise((res, rej) => {
    const p = spawn(EDGE, ['--headless=new', '--disable-gpu', '--no-first-run',
      '--autoplay-policy=no-user-gesture-required',
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

  // 1) 打开检测页，等待自动登录 + 历史加载
  await cdp.send('Page.navigate', { url: 'http://127.0.0.1:8080/track.html' });
  await sleep(4000);

  // 2) 注入视频文件到 <input type=file>
  const doc = await cdp.send('DOM.getDocument');
  const q = await cdp.send('DOM.querySelector', { nodeId: doc.root.nodeId, selector: '#fileInput' });
  await cdp.send('DOM.setFileInputFiles', { nodeId: q.nodeId, files: [VIDEO] });
  await cdp.eval(`document.getElementById('fileInput').dispatchEvent(new Event('change', { bubbles: true }))`);
  await sleep(2500);
  let st = await cdp.eval(`JSON.stringify({
    previewVisible: !document.getElementById('previewBox').classList.contains('hidden'),
    submitVisible: !document.getElementById('submitBtn').classList.contains('hidden'),
    videoW: document.getElementById('srcVideo').videoWidth
  })`);
  console.log('[选择视频后]', st);

  // 3) 点击"提取首帧"
  await cdp.eval(`document.getElementById('extractBtn').click()`);
  await sleep(3500);
  st = await cdp.eval(`JSON.stringify({
    btnText: document.getElementById('extractBtn').textContent,
    canvasHidden: document.getElementById('canvasWrap').classList.contains('hidden'),
    canvasW: document.getElementById('boxCanvas').width,
    canvasH: document.getElementById('boxCanvas').height,
    msg: document.getElementById('uploadMsg').textContent
  })`);
  console.log('[点击提取首帧后]', st);

  // 4) 在画布上模拟拖拽框选
  await cdp.eval(`(function(){
    var cv = document.getElementById('boxCanvas');
    var r = cv.getBoundingClientRect();
    function ev(type, x, y){ cv.dispatchEvent(new MouseEvent(type, {bubbles:true, clientX: r.left + x * r.width / cv.width, clientY: r.top + y * r.height / cv.height, button: 0})); }
    ev('mousedown', 0.10, 0.35);
    ev('mousemove', 0.32, 0.55);
    ev('mouseup',   0.32, 0.55);
  })()`);
  await sleep(600);
  st = await cdp.eval(`JSON.stringify({
    bboxInfo: document.getElementById('bboxInfo').textContent,
    bboxVisible: !document.getElementById('bboxInfo').classList.contains('hidden')
  })`);
  console.log('[画框后]', st);

  cdp.ws.close(); proc.kill();
  console.log('test done');
}
main().catch((e) => { console.error(e); process.exit(1); });
