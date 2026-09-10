# 小程序端 —— 怎么运行（重要）

## ⚠️ 不要双击 `app.js` 之类的文件

Windows 上 `.js` 默认由 **Windows Script Host** 打开，双击等于"执行脚本"，
会弹出这样的错误：

```
脚本: ...\miniprogram\app.js
行: 14   错误: 缺少 ...   代码: 800A03EB
```

**这不是代码有问题**，而是用错了运行环境：WSH 内置的 JScript 是很老的引擎，
不支持小程序使用的 ES6 语法（`onLaunch() {}` 简写方法、`const`、箭头函数等），
所以一到 `app.js` 第 15 行就报语法错误。

## ✅ 正确运行方式

1. 下载安装 **微信开发者工具**：https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html
   （选「稳定版 Stable Build」→ Windows 64 位）
2. 打开后选 **导入项目**：
   - **目录**：选中本文件夹（`01-代码/miniprogram`），注意是这一层，不是仓库根目录
   - **AppID**：点「测试号」即可（工程里已填 `touristappid`，无需注册）
3. 点「确定」后模拟器就会加载出小程序（底部三个 tab：上传跟踪 / 我的记录 / 我的）

## 前置条件：后端必须在运行

小程序要调用 `http://127.0.0.1:8080`，所以请先在仓库根目录双击
`启动-网页检测端.bat`（或 `tools\start_all.ps1`）把后端跑起来。

- **模拟器调试**：用 `127.0.0.1` 即可（`project.config.json` 里已设 `urlCheck: false`，
  允许 http 明文请求，无需配置域名白名单）。
- **真机预览**：手机上的 `127.0.0.1` 指向手机自己，必须改成电脑的局域网 IP，
  例如 `app.js` 里改为 `baseUrl: 'http://192.168.1.5:8080'`（用 `ipconfig` 查），
  并保证手机与电脑同一 Wi-Fi。

## 账号

小程序端需要自己注册：登录页 → 注册 → 填用户名/密码/昵称。
（管理端 `admin/123456` 是 ADMIN 角色，不要用于小程序登录测试。）
