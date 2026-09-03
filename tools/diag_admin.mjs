/* diag_admin.mjs —— 复现并诊断"管理端崩溃"：捕获 console/异常/崩溃事件 */
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const PORT = 9229;
const USER_DIR = path.resolve(__dirname, '../demo/.edge-diag');
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
  constructor(ws) { this.ws = ws; this.id = 0; this.p = new Map(); this.events = []; }
  static async connect(u) {
    const ws = new WebSocket(u);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    const c = new CDP(ws);
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && c.p.has(m.id)) {
        const { res, rej } = c.p.get(m.id); c.p.delete(m.id);
        m.error ? rej(new Error(m.error.message)) : res(m.result);
      } else if (m.method) {
        c.events.push(m.method + ': ' + (m.params && m.params.errorText || m.params && m.params.text || ''));
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
    if (r.exceptionDetails) { return 'EXC: ' + JSON.stringify(r.exceptionDetails).slice(0, 300); }
    return r.result && r.result.value;
  }
}

async function main() {
  const proc = await launch();
  const cdp = await CDP.connect(await wsUrl());
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Log.enable');
  await cdp.send('Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: false, flatten: true });

  // 从 track.html 顶栏点击"管理端"链接（复现用户路径）
  await cdp.send('Page.navigate', { url: 'http://127.0.0.1:8080/track.html' });
  await sleep(3500);
  console.log('[track.html] topbar 管理端链接:', await cdp.eval(`document.querySelector('a.btn-mini') ? document.querySelector('a.btn-mini').href : 'NOT FOUND'`));
  await cdp.eval(`document.querySelector('a.btn-mini') ? document.querySelector('a.btn-mini').click() : null`);
  await sleep(3500);
  console.log('[点击后] URL:', await cdp.eval('location.href'));
  console.log('[点击后] 登录页可见:', await cdp.eval(`!document.getElementById('loginView').classList.contains('hidden')`));
  console.log('[点击后] 主界面可见:', await cdp.eval(`!document.getElementById('mainView').classList.contains('hidden')`));
  console.log('[页面崩溃?]', await cdp.eval('document.readyState'));

  // 模拟登录点击
  await cdp.eval(`document.getElementById('loginUser').value='admin'`);
  await cdp.eval(`document.getElementById('loginPwd').value='123456'`);
  await cdp.eval(`document.getElementById('loginBtn').click()`);
  await sleep(3500);
  console.log('[登录后] 主界面可见:', await cdp.eval(`!document.getElementById('mainView').classList.contains('hidden')`));
  console.log('[登录后] 统计用户数:', await cdp.eval(`document.getElementById('stUser').textContent`));
  console.log('[登录后] 用户行数:', await cdp.eval(`document.querySelectorAll('#userRows tr').length`));
  console.log('[登录后] 错误信息:', await cdp.eval(`document.getElementById('loginMsg').textContent`));

  console.log('[捕获事件]', cdp.events.slice(0, 20));
  cdp.ws.close(); proc.kill();
  console.log('done');
}
main().catch((e) => { console.error(e); process.exit(1); });
