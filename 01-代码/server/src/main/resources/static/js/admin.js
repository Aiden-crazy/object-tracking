/* admin.js —— 综合实践III《单目标跟踪系统》Web 管理端逻辑
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：登录鉴权(本地保存 token)、统计卡片、用户 CRUD、任务记录查询与结果预览。
 */
(function () {
  "use strict";

  var TOKEN_KEY = "zs3_admin_token";
  var api = function (url, options) {
    options = options || {};
    options.headers = options.headers || {};
    options.headers["Authorization"] = "Bearer " + localStorage.getItem(TOKEN_KEY);
    if (options.body && typeof options.body !== "string") {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(options.body);
    }
    return fetch(url, options).then(function (r) { return r.json(); })
      .then(function (res) {
        if (res.code !== 0) {
          if (res.code === 401) { showLogin(); }
          throw new Error(res.msg || "请求失败");
        }
        return res.data;
      });
  };

  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var fmtTime = function (t) { return t ? String(t).replace("T", " ").substring(0, 19) : "-"; };

  /* ---------------- 登录态 ---------------- */
  function showLogin() {
    $("mainView").classList.add("hidden");
    $("loginView").classList.remove("hidden");
    localStorage.removeItem(TOKEN_KEY);
  }
  function showMain() {
    $("loginView").classList.add("hidden");
    $("mainView").classList.remove("hidden");
  }

  $("loginBtn").addEventListener("click", function () {
    var username = $("loginUser").value.trim();
    var password = $("loginPwd").value;
    if (!username || !password) { $("loginMsg").textContent = "请输入用户名和密码"; return; }
    fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username, password: password })
    }).then(function (r) { return r.json(); }).then(function (res) {
      if (res.code !== 0) { $("loginMsg").textContent = res.msg; return; }
      if (res.data.user.role !== "ADMIN") {
        $("loginMsg").textContent = "该账号不是管理员，无法登录管理端"; return;
      }
      localStorage.setItem(TOKEN_KEY, res.data.token);
      $("who").textContent = "管理员：" + res.data.user.nickname;
      showMain();
      refreshAll();
    });
  });

  $("logoutBtn").addEventListener("click", function () {
    localStorage.removeItem(TOKEN_KEY);
    showLogin();
  });

  /* ---------------- 统计 ---------------- */
  function loadStats() {
    api("/api/admin/stats").then(function (d) {
      $("stUser").textContent = d.userCount;
      $("stTask").textContent = d.taskCount;
      $("stSuccess").textContent = d.successCount;
      $("stProc").textContent = d.processingCount;
      $("stFailed").textContent = d.failedCount;
    }).catch(function (e) { console.error(e); });
  }

  /* ---------------- 用户管理 ---------------- */
  var userPage = 1, userKw = "";
  function loadUsers() {
    api("/api/admin/users?keyword=" + encodeURIComponent(userKw)
        + "&page=" + userPage + "&size=10").then(function (d) {
      var html = "";
      d.list.forEach(function (u) {
        html += "<tr><td>" + u.id + "</td><td>" + esc(u.username) + "</td>"
          + "<td>" + esc(u.nickname) + "</td>"
          + "<td>" + (u.role === "ADMIN" ? "管理员" : "普通用户") + "</td>"
          + "<td>" + fmtTime(u.createTime) + "</td>"
          + "<td>" + (u.role !== "ADMIN"
              ? "<button class='btn sm' onclick='window.__zs.reset(" + u.id + ")'>重置密码</button> "
                + "<button class='btn sm danger' onclick='window.__zs.delUser(" + u.id + ")'>删除</button>"
              : "<span style='color:#999'>-</span>") + "</td></tr>";
      });
      $("userRows").innerHTML = html || "<tr><td colspan='6' style='color:#999'>暂无数据</td></tr>";
      renderPager($("userPager"), d.total, userPage, function (p) {
        userPage = p; loadUsers();
      });
    }).catch(function (e) { alert(e.message); });
  }

  window.__zs = {
    reset: function (id) {
      var pwd = prompt("请输入新密码（至少6位）：", "123456");
      if (!pwd) return;
      api("/api/admin/user/" + id + "/reset", {
        method: "PUT",
        body: { password: pwd }
      }).then(function () { alert("密码已重置"); loadUsers(); })
        .catch(function (e) { alert(e.message); });
    },
    delUser: function (id) {
      if (!confirm("确定删除该用户？其所有任务记录将一并删除！")) return;
      api("/api/admin/user/" + id, { method: "DELETE" })
        .then(function () { loadUsers(); loadStats(); })
        .catch(function (e) { alert(e.message); });
    },
    delTask: function (id) {
      if (!confirm("确定删除该任务记录？")) return;
      api("/api/admin/task/" + id, { method: "DELETE" })
        .then(function () { loadTasks(); loadStats(); })
        .catch(function (e) { alert(e.message); });
    },
    play: function (id) {
      api("/api/task/" + id).then(function (t) {
        if (!t.resultPath) { alert("该任务暂无结果视频"); return; }
        $("resultVideo").src = t.resultPath;
        $("resultStats").textContent = t.statsJson
          ? "跟踪统计:\n" + JSON.stringify(JSON.parse(t.statsJson), null, 2)
          : "无统计信息";
        $("videoModal").classList.remove("hidden");
      }).catch(function (e) { alert(e.message); });
    }
  };

  $("searchUsersBtn").addEventListener("click", function () {
    userKw = $("kwUsers").value.trim(); userPage = 1; loadUsers();
  });
  $("addUserBtn").addEventListener("click", function () {
    var u = prompt("新增用户（格式：用户名 密码 昵称，空格分隔）：", "zhangsan 123456 张三");
    if (!u) return;
    var parts = u.trim().split(/\s+/);
    if (parts.length < 2) { alert("格式应为：用户名 密码 [昵称]"); return; }
    api("/api/admin/user", {
      method: "POST",
      body: { username: parts[0], password: parts[1],
              nickname: parts[2] || parts[0], role: "USER" }
    }).then(function () { alert("新增成功"); loadUsers(); loadStats(); })
      .catch(function (e) { alert(e.message); });
  });

  /* ---------------- 任务记录 ---------------- */
  var taskPage = 1, taskStatus = "";
  function loadTasks() {
    api("/api/admin/tasks?status=" + taskStatus
        + "&page=" + taskPage + "&size=10").then(function (d) {
      var html = "";
      d.list.forEach(function (t) {
        html += "<tr><td>" + t.id + "</td><td>" + esc(t.username || t.userId) + "</td>"
          + "<td>" + t.mediaType + "</td>"
          + "<td title='" + esc(t.fileName) + "'>" + esc((t.fileName || "").substring(0, 16)) + "</td>"
          + "<td>" + esc(t.bbox || "自动") + "</td>"
          + "<td><span class='status " + t.status + "'>" + t.status + "</span></td>"
          + "<td>" + fmtTime(t.createTime) + "</td>"
          + "<td>"
          + (t.status === "SUCCESS"
              ? "<button class='btn sm' onclick='window.__zs.play(" + t.id + ")'>查看结果</button> "
              : (t.errorMsg ? "<span title='" + esc(t.errorMsg) + "' style='color:#e74c3c;cursor:help'>!</span> " : ""))
          + "<button class='btn sm danger' onclick='window.__zs.delTask(" + t.id + ")'>删除</button>"
          + "</td></tr>";
      });
      $("taskRows").innerHTML = html || "<tr><td colspan='8' style='color:#999'>暂无数据</td></tr>";
      renderPager($("taskPager"), d.total, taskPage, function (p) {
        taskPage = p; loadTasks();
      });
    }).catch(function (e) { alert(e.message); });
  }

  $("searchTasksBtn").addEventListener("click", function () {
    taskStatus = $("fltStatus").value; taskPage = 1; loadTasks();
  });

  /* ---------------- 分页与弹窗 ---------------- */
  function renderPager(el, total, page, gotoFn) {
    var pages = Math.max(1, Math.ceil(total / 10));
    if (pages <= 1) { el.innerHTML = "共 " + total + " 条"; return; }
    var html = "共 " + total + " 条 ";
    html += "<button " + (page <= 1 ? "disabled" : "") + " onclick='window.__zsG(" + (page - 1) + ")'>上一页</button> ";
    html += "<button class='cur'>" + page + "/" + pages + "</button> ";
    html += "<button " + (page >= pages ? "disabled" : "") + " onclick='window.__zsG(" + (page + 1) + ")'>下一页</button>";
    el.innerHTML = html;
    window.__zsG = gotoFn;
  }

  $("closeModal").addEventListener("click", function () {
    $("videoModal").classList.add("hidden");
    $("resultVideo").pause();
  });

  document.querySelectorAll(".tab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".tab").forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      document.querySelectorAll(".tab-panel").forEach(function (p) { p.classList.add("hidden"); });
      $("tab-" + btn.dataset.tab).classList.remove("hidden");
    });
  });

  function refreshAll() { loadStats(); loadUsers(); loadTasks(); }

  /* ---------------- 启动 ---------------- */
  if (localStorage.getItem(TOKEN_KEY)) {
    api("/api/admin/stats").then(function () {
      $("who").textContent = "管理员";
      showMain();
      refreshAll();
    }).catch(function () { showLogin(); });
  } else {
    showLogin();
  }
})();
