/* track.js —— 综合实践III《单目标跟踪系统》网页检测端逻辑
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：拖拽/粘贴/选择视频 → 首帧画框或自动目标 → 上传检测 →
 *           轮询进度 → 展示结果视频与统计 → 历史记录回看。
 *           URL 带 ?demo=1 时自动展示最近一条成功结果（便于演示/截图）。
 */
(function () {
  "use strict";

  var TOKEN_KEY = "zs3_user_token";
  var USER_KEY = "zs3_user_info";
  var DEMO_ACCOUNT = { username: "webdemo", password: "123456", nickname: "网页体验用户" };

  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var fmtTime = function (t) { return t ? String(t).replace("T", " ").substring(0, 19) : "-"; };

  var state = {
    file: null,          // 选中的视频 File
    url: null,           // objectURL
    bbox: "",            // 手动框选坐标 x,y,w,h（视频原始像素）
    polling: false
  };

  /* ---------------- API ---------------- */
  function api(method, url, body, isForm) {
    var opt = { method: method, headers: { "Authorization": "Bearer " + localStorage.getItem(TOKEN_KEY) } };
    if (body) {
      if (isForm) { opt.body = body; }
      else {
        opt.headers["Content-Type"] = "application/json";
        opt.body = JSON.stringify(body);
      }
    }
    return fetch(url, opt).then(function (r) { return r.json(); }).then(function (res) {
      if (res.code !== 0) { throw new Error(res.msg || "请求失败"); }
      return res.data;
    });
  }

  function login(u, p) {
    return fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, password: p })
    }).then(function (r) { return r.json(); }).then(function (res) {
      if (res.code !== 0) { throw new Error(res.msg); }
      localStorage.setItem(TOKEN_KEY, res.data.token);
      localStorage.setItem(USER_KEY, JSON.stringify(res.data.user));
      return res.data.user;
    });
  }

  function register(u, p, n) {
    return fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, password: p, nickname: n })
    }).then(function (r) { return r.json(); });
  }

  /** 自动接入：优先 webdemo 体验账号，失败则注册并登录 */
  function autoConnect() {
    var saved = localStorage.getItem(TOKEN_KEY);
    var p = saved
      ? Promise.resolve(JSON.parse(localStorage.getItem(USER_KEY) || "{}"))
      : login(DEMO_ACCOUNT.username, DEMO_ACCOUNT.password)
          .catch(function () {
            return register(DEMO_ACCOUNT.username, DEMO_ACCOUNT.password,
                            DEMO_ACCOUNT.nickname)
              .then(function (res) {
                if (res.code !== 0) { throw new Error(res.msg); }
                return login(DEMO_ACCOUNT.username, DEMO_ACCOUNT.password);
              });
          });
    return p.then(function (u) {
      $("who").textContent = "体验账号 @" + (u.nickname || u.username);
      return u;
    }).catch(function (e) {
      $("who").textContent = "未连接";
      alert("自动连接失败：" + e.message + "\n请先确认服务端与视觉服务已启动。");
      throw e;
    });
  }

  /* ---------------- 视频选择：拖拽 / 点击 / 粘贴 ---------------- */
  function acceptFile(file) {
    if (!file) { return; }
    var t = (file.type || "").toLowerCase();
    var name = (file.name || "").toLowerCase();
    var isVideo = t.indexOf("video") >= 0 ||
      /\.(mp4|avi|mov|mkv|webm|flv|wmv)$/.test(name);
    if (!isVideo) { $("uploadMsg").textContent = "请选择视频文件（mp4/avi/mov/mkv 等）"; return; }
    $("uploadMsg").textContent = "";
    if (state.url) { URL.revokeObjectURL(state.url); }
    state.file = file;
    state.url = URL.createObjectURL(file);
    state.bbox = "";
    wantExtract = false;
    $("extractBtn").disabled = false;
    $("extractBtn").textContent = "提取首帧 · 画框选目标";
    $("srcVideo").src = state.url;
    $("previewBox").classList.remove("hidden");
    $("submitBtn").classList.remove("hidden");
    $("srcVideo").load();
    hideBoxUI();
  }

  var drop = $("drop");
  drop.addEventListener("click", function () { $("fileInput").click(); });
  $("fileInput").addEventListener("change", function (e) {
    acceptFile(e.target.files[0]);
    e.target.value = "";
  });
  ["dragover", "dragenter"].forEach(function (ev) {
    drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add("over"); });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    drop.addEventListener(ev, function (e) {
      e.preventDefault(); drop.classList.remove("over");
    });
  });
  drop.addEventListener("drop", function (e) {
    var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    acceptFile(f);
  });
  // Ctrl+V 粘贴视频
  document.addEventListener("paste", function (e) {
    var items = e.clipboardData && e.clipboardData.items;
    if (!items) { return; }
    for (var i = 0; i < items.length; i++) {
      if (items[i].kind === "file") {
        e.preventDefault();
        acceptFile(items[i].getAsFile());
        return;
      }
    }
  });

  /* ============================================================
     首帧提取与画框（稳健版）：
     不依赖单一的 seeked 事件 —— 同时由 loadeddata/seeked 事件驱动，
     并带 800ms 轮询兜底；等待期间显示“正在读取视频…”，
     超时/不支持则给出明确提示，避免“点了没反应”。
     ============================================================ */
  var video = $("srcVideo");
  var canvas = $("boxCanvas");
  var ctx = canvas.getContext("2d");
  var drawing = false, rect = null, scaleK = 1;

  var wantExtract = false;   // 用户是否正在等待取帧
  var pumpTries = 0;

  function hideBoxUI() {
    $("canvasWrap").classList.add("hidden");
    $("bboxInfo").classList.add("hidden");
    $("resetBox").classList.add("hidden");
    rect = null;
  }

  $("extractBtn").addEventListener("click", function () {
    if (!state.file) { return; }
    $("uploadMsg").textContent = "";
    $("extractBtn").disabled = true;
    $("extractBtn").textContent = "正在读取视频…";
    wantExtract = true;
    pumpTries = 0;
    pump();
  });

  // 事件驱动（加速响应）：数据就绪 / seek 完成 都会触发 pump
  video.addEventListener("loadeddata", function () { if (wantExtract) { pump(); } });
  video.addEventListener("seeked", function () { if (wantExtract) { pump(); } });

  function pump() {
    if (!wantExtract) { return; }
    // 1) 元数据已就绪且可解码
    if (video.readyState >= 1 && video.videoWidth > 0 && video.videoHeight > 0) {
      // 2) 对齐到 0.05s 处取首帧（避免部分视频首帧为黑帧）
      var delta = Math.abs(video.currentTime - 0.05);
      if (delta > 0.02) {
        video.pause();
        try { video.currentTime = 0.05; } catch (e) { /* ignore */ }
        // seeked 事件会再次进入 pump 并执行绘制；此处兜底防事件丢失
        setTimeout(pump, 900);
        return;
      }
      drawNow();
      return;
    }
    // 3) 元数据未就绪：等待（loadeddata 会触发 pump）
    if (++pumpTries > 12) { failExtract(); return; }   // 约 10s 上限
    setTimeout(pump, 800);
  }

  function drawNow() {
    var vw = video.videoWidth, vh = video.videoHeight;
    if (!vw || !vh) {
      if (++pumpTries > 14) { failExtract(); }
      return;
    }
    try {
      video.pause();
      var cw = Math.min(vw, 640);
      var ch = Math.round(vh * (cw / vw));
      canvas.width = cw; canvas.height = ch;
      ctx.drawImage(video, 0, 0, cw, ch);
      scaleK = vw / cw;                 // 原始像素 = 画布像素 × scaleK
      wantExtract = false;
      rect = null;
      $("canvasWrap").classList.remove("hidden");
      $("bboxInfo").classList.add("hidden");
      $("resetBox").classList.add("hidden");
      $("extractBtn").disabled = false;
      $("extractBtn").textContent = "重新提取首帧";
      $("uploadMsg").textContent = "";
    } catch (e) {
      // 个别解码器 drawImage 可能抛错：稍后重试
      if (++pumpTries > 14) { failExtract(); }
      else { setTimeout(pump, 500); }
    }
  }

  function failExtract() {
    wantExtract = false;
    $("extractBtn").disabled = false;
    $("extractBtn").textContent = "提取首帧 · 画框选目标";
    $("uploadMsg").textContent =
      "无法读取该视频首帧：格式/编码可能不受浏览器支持。" +
      "建议使用 mp4(H.264) 视频，或直接点击【开始检测】使用自动目标。";
  }

  // 鼠标拖拽画框
  canvas.addEventListener("mousedown", function (e) {
    if ($("canvasWrap").classList.contains("hidden")) { return; }
    var p = pos(e);
    rect = { x0: p.x, y0: p.y, x1: p.x, y1: p.y };
    drawing = true;
  });
  canvas.addEventListener("mousemove", function (e) {
    if (!drawing) { return; }
    var p = pos(e);
    rect.x1 = p.x; rect.y1 = p.y;
    redraw();
  });
  ["mouseup", "mouseleave"].forEach(function (ev) {
    canvas.addEventListener(ev, function () {
      if (!drawing) { return; }
      drawing = false;
      finishBox();
    });
  });

  function pos(e) {
    var r = canvas.getBoundingClientRect();
    return {
      x: (e.clientX - r.left) * (canvas.width / r.width),
      y: (e.clientY - r.top) * (canvas.height / r.height)
    };
  }

  function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    try { ctx.drawImage(video, 0, 0, canvas.width, canvas.height); } catch (e) { /* ignore */ }
    if (!rect) { return; }
    var x = Math.min(rect.x0, rect.x1), y = Math.min(rect.y0, rect.y1);
    var w = Math.abs(rect.x1 - rect.x0), h = Math.abs(rect.y1 - rect.y0);
    ctx.strokeStyle = "#27ae60";
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
  }

  function finishBox() {
    if (!rect) { return; }
    var x = Math.min(rect.x0, rect.x1), y = Math.min(rect.y0, rect.y1);
    var w = Math.abs(rect.x1 - rect.x0), h = Math.abs(rect.y1 - rect.y0);
    if (w < 8 || h < 8) { rect = null; redraw(); return; }
    // 换算为视频原始像素
    var bx = Math.round(x * scaleK), by = Math.round(y * scaleK);
    var bw = Math.round(w * scaleK), bh = Math.round(h * scaleK);
    state.bbox = [bx, by, bw, bh].join(",");
    $("bboxInfo").textContent = "目标框(原始像素): x=" + bx + " y=" + by +
      " w=" + bw + " h=" + bh + "（将使用该框跟踪）";
    $("bboxInfo").classList.remove("hidden");
    $("resetBox").classList.remove("hidden");
  }

  $("resetBox").addEventListener("click", function () {
    state.bbox = "";
    hideBoxUI();
    $("resetBox").classList.add("hidden");
  });

  /* ---------------- 提交与轮询 ---------------- */
  $("submitBtn").addEventListener("click", submit);

  function submit() {
    if (!state.file) { alert("请先放入视频"); return; }
    var btn = $("submitBtn");
    btn.disabled = true;
    btn.textContent = "上传中…";
    var fd = new FormData();
    fd.append("file", state.file, state.file.name);
    if (state.bbox) { fd.append("bbox", state.bbox); }
    api("POST", "/api/task/upload", fd, true).then(function (task) {
      btn.disabled = false;
      btn.textContent = "开始检测";
      showProgress(task.id);
      poll(task.id);
    }).catch(function (e) {
      btn.disabled = false;
      btn.textContent = "开始检测";
      $("uploadMsg").textContent = "提交失败：" + e.message;
    });
  }

  function showProgress(id) {
    $("taskNo").textContent = id;
    $("secProgress").classList.remove("hidden");
    $("secResult").classList.add("hidden");
    window.scrollTo({ top: $("secProgress").offsetTop - 20, behavior: "smooth" });
  }

  function poll(id) {
    if (state.polling) { return; }
    state.polling = true;
    var timer = setInterval(function () {
      api("GET", "/api/task/" + id).then(function (t) {
        if (t.status === "PENDING" || t.status === "PROCESSING") {
          $("progressText").textContent = "视觉模块执行中（CSRT 跟踪 + 遮挡检测）… 任务 #" + id;
          return;
        }
        clearInterval(timer);
        state.polling = false;
        $("secProgress").classList.add("hidden");
        if (t.status === "SUCCESS") { showResult(t); }
        else { showFailed(t); }
        loadHistory();
      }).catch(function () { /* 网络抖动继续轮询 */ });
    }, 1500);
  }

  function showResult(t) {
    $("resTaskNo").textContent = t.id;
    $("resVideo").src = t.resultPath || "";
    $("secResult").classList.remove("hidden");
    $("resError").classList.add("hidden");
    renderStats(t.statsJson);
    window.scrollTo({ top: $("secResult").offsetTop - 20, behavior: "smooth" });
  }

  function showFailed(t) {
    $("secResult").classList.remove("hidden");
    $("resTaskNo").textContent = t.id;
    $("resVideo").removeAttribute("src");
    $("resError").textContent = "处理失败：" + (t.errorMsg || "未知错误");
    $("resError").classList.remove("hidden");
    $("statsGrid").innerHTML = "";
  }

  function renderStats(json) {
    var s = {};
    try { s = JSON.parse(json); } catch (e) { s = {}; }
    var map = {
      processed_frames: { k: "处理帧数", v: s.processed_frames != null ? s.processed_frames : (s.total_frames || "-") },
      fps: { k: "处理速度(FPS)", v: s.fps != null ? s.fps : "-" },
      lost_events: { k: "丢失次数", v: s.lost_events != null ? s.lost_events : "-" },
      recoveries: { k: "自动找回", v: s.recoveries != null ? s.recoveries : "-" },
      final_state: { k: "最终状态", v: s.final_state || "-" }
    };
    var html = "";
    Object.keys(map).forEach(function (key) {
      html += "<div class='stat-chip'><div class='v'>" + esc(map[key].v) +
        "</div><div class='k'>" + map[key].k + "</div></div>";
    });
    $("statsGrid").innerHTML = html;
  }

  /* ---------------- 历史记录 ---------------- */
  function loadHistory() {
    api("GET", "/api/task/list?page=1&size=20").then(function (d) {
      var rows = d.list || [];
      var html = "";
      rows.forEach(function (t) {
        html += "<tr data-id='" + t.id + "'>"
          + "<td>" + t.id + "</td>"
          + "<td title='" + esc(t.fileName) + "'>" + esc((t.fileName || "").substring(0, 22)) + "</td>"
          + "<td>" + esc(t.bbox || "自动") + "</td>"
          + "<td><span class='badge " + t.status + "'>" + t.status + "</span></td>"
          + "<td>" + fmtTime(t.createTime) + "</td>"
          + "<td>查看</td></tr>";
      });
      $("hisRows").innerHTML = html || "<tr><td colspan='6' class='empty'>暂无记录，上传第一个视频试试吧</td></tr>";
      $("hisMore").textContent = rows.length < d.total ? ("共 " + d.total + " 条记录（点击上行查看）") : "";
      bindHistoryClick(rows);
    }).catch(function () { /* 忽略 */ });
  }

  function bindHistoryClick(rows) {
    var map = {};
    rows.forEach(function (t) { map[t.id] = t; });
    $("hisRows").onclick = function (e) {
      var tr = e.target.closest("tr");
      if (!tr) { return; }
      var t = map[tr.dataset.id];
      if (!t) { return; }
      if (t.status === "SUCCESS") {
        showResult(t);
      } else if (t.status === "PENDING" || t.status === "PROCESSING") {
        showProgress(t.id);
        poll(t.id);
      } else {
        showFailed(t);
      }
    };
  }

  /* ---------------- 初始化 ---------------- */
  function boot() {
    autoConnect().then(function () {
      loadHistory();
      // ?demo=1：自动回看最近一条成功记录
      if (location.search.indexOf("demo=1") >= 0) {
        setTimeout(function () {
          api("GET", "/api/task/list?page=1&size=5").then(function (d) {
            var done = null;
            (d.list || []).forEach(function (t) {
              if (!done && t.status === "SUCCESS") { done = t; }
            });
            if (done) {
              $("who").textContent = "体验账号 @webdemo · 正在回看最近结果";
              showResult(done);
            } else {
              alert("还没有成功的结果记录，请先上传一个视频进行检测。");
            }
          }).catch(function () {});
        }, 800);
      }
    });
  }
  boot();
})();
