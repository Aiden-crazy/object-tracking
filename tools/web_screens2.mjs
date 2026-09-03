/*
 * web_screens2.mjs —— 截取【网页检测端】track.html 运行截图
 * 前置：后端已启动(8080)，webdemo 账号已存在且有 SUCCESS 任务（track.js 会自动登录）
 * 输出：../../demo/screenshots/web_05_*.png  web_06_*.png
 */
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.resolve(__dirname, '../demo/screenshots');
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = 'http://127.0.0.1:8080';
const PORT = 9224;
const USER_DIR = path.resolve(__dirname, '../demo/.edge-profile2');

mkdirSync(OUT_DIR, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function launch() {
  return new Promise((resolve, reject) => {
    const p = spawn(EDGE, [
      '--headless=new', '--disable-gpu', '--no-first-run', '--mute-audio',
      `--remote-debugging-port=${PORT}`, `--user-data-dir=${USER_DIR}`,
      '--window-size=1360,980', 'about:blank'
    ], { stdio: 'ignore' });
    p.on('error', reject);
    resolve(p);
  });
}

async function wsUrl() {
  for (let i = 0; i < 40; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch (e) { /* retry */ }
    await sleep(250);
  }
  throw new Error('CDP connect fail');
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
  const proc = await launch();
  const cdp = await CDP.connect(await wsUrl());
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');

  // 1. 网页检测端默认页（自动登录体验账号 + 上传拖拽区 + 历史记录）
  await cdp.send('Page.navigate', { url: BASE + '/track.html' });
  await sleep(4200);
  await cdp.shot('web_05_网页检测端_拖拽上传.png');

  // 2. ?demo=1：自动回看最近成功结果（视频 + 统计）
  await cdp.send('Page.navigate', { url: BASE + '/track.html?demo=1' });
  await sleep(4500);
  await cdp.shot('web_06_网页检测端_检测结果.png');

  cdp.ws.close();
  proc.kill();
  console.log('done');
}

main().catch((e) => { console.error(e); process.exit(1); });
