/*
 * web_screens.mjs —— 通过 Chrome DevTools Protocol 截取 Web 管理端真实运行截图
 * 作者：【姓名】  学号：【学号】
 * 功能：登录页 / 用户管理 / 任务记录 / 结果弹窗 四张 PNG，输出到 ../../demo/screenshots
 * 前置：后端已启动(http://127.0.0.1:8080)，且有至少一条 SUCCESS 任务与若干用户
 * 运行：node web_screens.mjs
 */
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.resolve(__dirname, '../demo/screenshots');
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = 'http://127.0.0.1:8080';
const PORT = 9223;
const USER_DIR = path.resolve(__dirname, '../../demo/.edge-profile');

mkdirSync(OUT_DIR, { recursive: true });

async function getAdminToken() {
  const r = await fetch(BASE + '/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: '123456' })
  });
  const j = await r.json();
  if (j.code !== 0) throw new Error('admin 登录失败: ' + j.msg);
  return j.data.token;
}

const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

function launchEdge() {
  return new Promise((resolve, reject) => {
    const proc = spawn(EDGE, [
      '--headless=new', '--disable-gpu', '--no-first-run', '--mute-audio',
      `--remote-debugging-port=${PORT}`, `--user-data-dir=${USER_DIR}`,
      '--window-size=1400,900', 'about:blank'
    ], { stdio: 'ignore' });
    proc.on('error', reject);
    resolve(proc);
  });
}

async function getWsUrl() {
  for (let i = 0; i < 40; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch (e) { /* retry */ }
    await sleep(250);
  }
  throw new Error('无法连接 CDP');
}

class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); }
  static async connect(url) {
    const ws = new WebSocket(url);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    const c = new CDP(ws);
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && c.pending.has(m.id)) {
        const { resolve, reject } = c.pending.get(m.id);
        c.pending.delete(m.id);
        m.error ? reject(new Error(m.error.message)) : resolve(m.result);
      }
    };
    return c;
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  async shot(name) {
    const { data } = await this.send('Page.captureScreenshot', { format: 'png' });
    writeFileSync(path.join(OUT_DIR, name), Buffer.from(data, 'base64'));
    console.log('saved', name);
  }
}

async function main() {
  const token = await getAdminToken();
  const proc = await launchEdge();
  const wsUrl = await getWsUrl();
  const cdp = await CDP.connect(wsUrl);
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');

  // 1. 登录页
  await cdp.send('Page.navigate', { url: BASE + '/admin.html' });
  await sleep(2500);
  await cdp.shot('web_01_登录页.png');

  // 2. 注入 token -> 用户管理
  await cdp.send('Runtime.evaluate', {
    expression: `localStorage.setItem('zs3_admin_token', '${token}')`
  });
  await cdp.send('Page.reload');
  await sleep(3000);
  await cdp.shot('web_02_用户管理.png');

  // 3. 切到任务记录
  await cdp.send('Runtime.evaluate', {
    expression: `document.querySelector('[data-tab="tasks"]').click()`
  });
  await sleep(2000);
  await cdp.shot('web_03_任务记录.png');

  // 4. 打开第一条 SUCCESS 任务的结果弹窗（视频播放首帧）
  await cdp.send('Runtime.evaluate', {
    expression: `(function(){
      var ids = [];
      document.querySelectorAll('#taskRows button').forEach(function(b){
        if (b.textContent.indexOf('查看结果') >= 0) { ids.push(b); }
      });
      if (ids.length) ids[0].click();
      return ids.length;
    })()`
  });
  await sleep(3500);
  await cdp.shot('web_04_结果弹窗.png');

  cdp.ws.close();
  proc.kill();
  console.log('done');
}

main().catch((e) => { console.error(e); process.exit(1); });
