# -*- coding: utf-8 -*-
"""regression_test.py —— 综合实践III《单目标跟踪系统》全链路接口回归测试
作者：【姓名】  学号：【学号】  创建时间：2026-07
功能描述：
    对已启动的系统做端到端回归。先启动系统（双击 启动-网页检测端.bat，或手工启动
    9000 视觉服务与 8080 Web 后端），然后执行：
        python tools/regression_test.py
    覆盖：
      0) 视觉服务健康检查
      1) 注册/登录/改密/弱口令/重复用户名
      2) 视频两段式流程（defer 上传 -> 首帧 + 自动框 -> start -> SUCCESS -> 结果视频）
      3) 图片流程（defer 上传 -> 首帧 -> start -> 结果图片；以及一步式 defer=false）
      4) 任务归属越权校验（他人任务详情/启动均返回 403）
      5) 管理端：用户增/查/重置/删、任务状态过滤、统计、普通用户 403
      6) 视觉服务 prepare / track_local（视频与图片）
    退出码：0=全部通过，1=存在失败项（可接入 CI）。
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BASE = "http://127.0.0.1:8080"
VISION = "http://127.0.0.1:9000"
DEMO_VIDEO = os.path.join(ROOT, "demo", "demo_ball_track.mp4")
TEST_IMAGE = os.path.join(ROOT, "demo", "demo_test_image.png")

PASS, FAIL = [], []


def _parse_args():
    """支持指定服务地址（默认本机 8080/9000），便于测局域网上的那台机器。"""
    global BASE, VISION
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE, help="Web 后端地址")
    ap.add_argument("--vision", default=VISION, help="视觉服务地址")
    args = ap.parse_args()
    BASE = args.base.rstrip("/")
    VISION = args.vision.rstrip("/")


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + str(detail)) if detail else ""))


def req(method, path, token=None, body=None, raw=None, ctype=None, base=BASE):
    url = base + path
    data = None
    headers = {}
    if raw is not None:
        data = raw
        headers["Content-Type"] = ctype or "application/octet-stream"
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=300) as resp:
            txt = resp.read().decode("utf-8", "ignore")
            try:
                return resp.status, json.loads(txt)
            except Exception:
                return resp.status, txt
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(txt)
        except Exception:
            return e.code, txt


def multipart(fields, files):
    """构造 multipart/form-data 请求体。files: [(name, filename, bytes, ctype)]"""
    b = "----zongshe3" + uuid.uuid4().hex
    out = b""
    for k, v in fields.items():
        out += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                % (b, k, v)).encode("utf-8")
    for name, fn, content, ct in files:
        out += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                "Content-Type: %s\r\n\r\n" % (b, name, fn, ct)).encode("utf-8")
        out += content + b"\r\n"
    out += ("--%s--\r\n" % b).encode("utf-8")
    return out, "multipart/form-data; boundary=" + b


def upload(path, token, file_path, extra=None):
    with open(file_path, "rb") as f:
        content = f.read()
    ct = ("video/mp4" if file_path.lower().endswith(".mp4")
          else "image/png" if file_path.lower().endswith(".png") else "application/octet-stream")
    body, ctype = multipart(extra or {}, [("file", os.path.basename(file_path), content, ct)])
    return req("POST", path, token, raw=body, ctype=ctype)


def wait_task(tid, token, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        _, r = req("GET", "/api/task/%d" % tid, token)
        d = r.get("data") or {}
        if d.get("status") in ("SUCCESS", "FAILED"):
            return d
        time.sleep(0.7)
    return {"status": "TIMEOUT"}


_parse_args()

def ensure_test_image():
    """图片链路测试素材：缺失时用 OpenCV 现场生成（蓝色圆球 + 网格背景）。"""
    if os.path.exists(TEST_IMAGE):
        return True
    try:
        import cv2
        import numpy as np
    except Exception as e:  # noqa: BLE001
        print("  [WARN] 缺少测试图片且未安装 OpenCV，跳过图片链路用例:", e)
        return False
    bg = np.full((480, 640, 3), 245, dtype=np.uint8)
    for x in range(0, 640, 40):
        cv2.line(bg, (x, 0), (x, 480), (215, 215, 215), 1)
    for y in range(0, 480, 40):
        cv2.line(bg, (0, y), (640, y), (215, 215, 215), 1)
    cv2.circle(bg, (190, 160), 40, (0, 90, 220), -1)
    cv2.circle(bg, (190, 160), 26, (120, 170, 250), -1)
    cv2.rectangle(bg, (420, 60), (520, 200), (60, 60, 60), -1)
    ok, buf = cv2.imencode(".png", bg)
    if not ok:
        return False
    with open(TEST_IMAGE, "wb") as f:
        f.write(buf.tobytes())
    print("  已生成测试图片:", TEST_IMAGE)
    return True


print("=" * 78)
print("0. 视觉服务健康检查")
print("   后端: %s   视觉服务: %s" % (BASE, VISION))
s, r = req("GET", "/api/v1/health", base=VISION)
check("GET /api/v1/health", s == 200 and r.get("code") == 0, r.get("msg") if isinstance(r, dict) else r)

print("=" * 78)
print("1. 用户注册 / 登录 / 错误口令")
u1 = "e2e_a_" + uuid.uuid4().hex[:6]
u2 = "e2e_b_" + uuid.uuid4().hex[:6]
s, r = req("POST", "/api/auth/register", body={"username": u1, "password": "123456", "nickname": "回归A"})
check("注册新用户", s == 200 and r.get("code") == 0, r.get("msg"))
s, r = req("POST", "/api/auth/register", body={"username": u1, "password": "123456"})
check("重复用户名注册被拒绝", r.get("code") != 0, r.get("msg"))
s, r = req("POST", "/api/auth/register", body={"username": "short_" + u1, "password": "123"})
check("密码不足6位被拒绝", r.get("code") != 0, r.get("msg"))
s, r = req("POST", "/api/auth/login", body={"username": u1, "password": "wrongpwd"})
check("错误密码登录被拒绝", r.get("code") != 0, r.get("msg"))
s, r = req("POST", "/api/auth/login", body={"username": u1, "password": "123456"})
tok1 = (r.get("data") or {}).get("token")
check("正确登录返回 JWT", bool(tok1))
uid1 = (r.get("data") or {}).get("user", {}).get("id")
s, r2 = req("POST", "/api/auth/register", body={"username": u2, "password": "123456", "nickname": "回归B"})
s, r2 = req("POST", "/api/auth/login", body={"username": u2, "password": "123456"})
tok2 = (r2.get("data") or {}).get("token")
check("第二个用户登录返回 JWT", bool(tok2))
s, r = req("PUT", "/api/user/password", tok1, body={"oldPassword": "bad", "newPassword": "654321"})
check("改密校验原密码", r.get("code") != 0, r.get("msg"))

print("=" * 78)
print("2. 视频两段式流程（小程序主流程）")
s, r = upload("/api/task/upload?defer=true", tok1, DEMO_VIDEO)
d = r.get("data") or {}
check("defer 上传视频返回任务", r.get("code") == 0 and d.get("id"), r.get("msg"))
check("返回首帧 frameUrl", bool(d.get("frameUrl")), d.get("frameUrl"))
check("返回素材原始尺寸", d.get("imgWidth") == 640 and d.get("imgHeight") == 480,
      "%sx%s" % (d.get("imgWidth"), d.get("imgHeight")))
check("返回自动识别目标框 autoBbox", bool(d.get("autoBbox")), d.get("autoBbox"))
check("任务状态为 PENDING", d.get("status") == "PENDING", d.get("status"))
tid1 = d.get("id")
s, r = req("GET", d.get("frameUrl") or "/files/frames/0.jpg")
check("首帧图片可访问", s == 200 and isinstance(r, str) and r.startswith("\ufffd") is False)
# 用自动框提交
s, r = req("POST", "/api/task/%d/start" % tid1, tok1, body={"bbox": d.get("autoBbox")})
check("start 提交框选结果", r.get("code") == 0, r.get("msg"))
t = wait_task(tid1, tok1)
check("视频任务处理成功", t.get("status") == "SUCCESS", t.get("errorMsg"))
check("结果视频为 mp4", str(t.get("resultPath", "")).endswith("_tracked.mp4"), t.get("resultPath"))
sj = json.loads(t.get("statsJson") or "{}")
check("统计含遮挡恢复指标", sj.get("lost_events") == 1 and sj.get("recoveries") == 1,
      "lost=%s rec=%s" % (sj.get("lost_events"), sj.get("recoveries")))
check("统计记录目标框来源", sj.get("bbox_source") in ("manual", "auto"), sj.get("bbox_source"))
s, r = req("GET", t.get("resultPath"))
check("结果视频可访问", s == 200)

print("=" * 78)
print("3. 图片素材流程（任务书：图片或者视频）")
ensure_test_image()
check("测试图片已就绪", os.path.exists(TEST_IMAGE), TEST_IMAGE)
s, r = upload("/api/task/upload?defer=true", tok1, TEST_IMAGE)
d2 = r.get("data") or {}
check("defer 上传图片返回任务", r.get("code") == 0 and d2.get("id"), r.get("msg"))
check("图片 media_type=IMAGE", d2.get("mediaType") == "IMAGE", d2.get("mediaType"))
check("图片也能返回首帧", bool(d2.get("frameUrl")), d2.get("frameUrl"))
check("图片返回尺寸", d2.get("imgWidth") and d2.get("imgHeight"),
      "%sx%s" % (d2.get("imgWidth"), d2.get("imgHeight")))
tid2 = d2.get("id")
s, r = req("POST", "/api/task/%d/start" % tid2, tok1, body={"bbox": "150,120,80,80"})
check("图片任务 start", r.get("code") == 0, r.get("msg"))
t2 = wait_task(tid2, tok1)
check("图片任务处理成功", t2.get("status") == "SUCCESS", t2.get("errorMsg"))
check("图片结果路径为 jpg", str(t2.get("resultPath", "")).endswith("_tracked.jpg"), t2.get("resultPath"))
sj2 = json.loads(t2.get("statsJson") or "{}")
check("图片统计 media_type=IMAGE", sj2.get("media_type") == "IMAGE", sj2.get("media_type"))
check("图片统计给出目标框", bool(sj2.get("target_bbox")), sj2.get("target_bbox"))
s, r = req("GET", t2.get("resultPath"))
check("结果图片可访问", s == 200)
# 老流程（defer=false，网页端上传即处理）
s, r = upload("/api/task/upload", tok1, TEST_IMAGE)
d3 = r.get("data") or {}
t3 = wait_task(d3.get("id"), tok1)
check("图片一步式上传(defer=false)成功", t3.get("status") == "SUCCESS", t3.get("errorMsg"))

print("=" * 78)
print("4. 任务归属越权校验")
s, r = req("GET", "/api/task/%d" % tid1, tok2)
check("他人任务查询被拒绝", r.get("code") == 403, "code=%s msg=%s" % (r.get("code"), r.get("msg")))
s, r = req("GET", "/api/task/%d" % tid1, tok1)
check("本人任务查询正常", r.get("code") == 0)
# B 用户创建一个 PENDING 任务，再让 A 去 start
s, rb = upload("/api/task/upload?defer=true", tok2, DEMO_VIDEO)
tidb = (rb.get("data") or {}).get("id")
s, r = req("POST", "/api/task/%d/start" % tidb, tok1, body={"bbox": ""})
check("他人任务启动被拒绝", r.get("code") == 403, "code=%s msg=%s" % (r.get("code"), r.get("msg")))
s, r = req("GET", "/api/task/%d" % tidb, tok2)
check("B 用户查自己的 PENDING 任务正常", r.get("code") == 0)

print("=" * 78)
print("5. 管理端功能")
s, r = req("POST", "/api/auth/login", body={"username": "admin", "password": "123456"})
tokA = (r.get("data") or {}).get("token")
check("admin 登录", bool(tokA), r.get("msg"))
s, r = req("GET", "/api/admin/users?page=1&size=5", tokA)
check("用户分页查询", r.get("code") == 0 and "list" in (r.get("data") or {}))
s, r = req("GET", "/api/admin/users?page=1&size=5", tok1)
check("普通用户访问管理端返回403", r.get("code") == 403, r.get("msg"))
s, r = req("GET", "/api/admin/tasks?status=SUCCESS&page=1&size=5", tokA)
check("任务按状态过滤", r.get("code") == 0)
s, r = req("GET", "/api/admin/stats", tokA)
check("统计卡片", r.get("code") == 0 and "userCount" in (r.get("data") or {}), r.get("data"))
nu = "e2e_c_" + uuid.uuid4().hex[:6]
s, r = req("POST", "/api/admin/user", tokA, body={"username": nu, "password": "123456", "nickname": "回归C"})
nid = (r.get("data") or {}).get("id")
check("管理员新增用户", r.get("code") == 0 and nid, r.get("msg"))
s, r = req("PUT", "/api/admin/user/%s/reset" % nid, tokA, body={"password": "abcdef"})
check("管理员重置密码", r.get("code") == 0, r.get("msg"))
s, r = req("POST", "/api/auth/login", body={"username": nu, "password": "abcdef"})
check("重置后的新密码可登录", r.get("code") == 0, r.get("msg"))
s, r = req("DELETE", "/api/admin/user/%s" % nid, tokA)
check("管理员删除用户(级联任务)", r.get("code") == 0, r.get("msg"))

print("=" * 78)
print("6. 视觉服务接口")
s, r = req("POST", "/api/v1/prepare", body={"video_path": DEMO_VIDEO}, base=VISION)
d = r if isinstance(r, dict) else {}
check("vision /prepare 返回首帧与自动框",
      d.get("code") == 0 and d.get("width") == 640 and d.get("auto_bbox"),
      "%s %s" % (d.get("width"), d.get("auto_bbox")))
s, r = req("POST", "/api/v1/track_local",
           body={"video_path": DEMO_VIDEO, "bbox": "37,222,36,36"}, base=VISION)
d = r if isinstance(r, dict) else {}
check("vision /track_local 视频成功",
      d.get("code") == 0 and str(d.get("result_video", "")).endswith(".mp4"))
check("vision 返回 media_type", d.get("media_type") == "VIDEO", d.get("media_type"))
s, r = req("POST", "/api/v1/track_local",
           body={"video_path": TEST_IMAGE, "bbox": "150,120,80,80"}, base=VISION)
d = r if isinstance(r, dict) else {}
check("vision /track_local 图片成功",
      d.get("code") == 0 and str(d.get("result_video", "")).endswith(".jpg"), d.get("result_video"))
s, r = req("POST", "/api/v1/track_local", body={"video_path": "D:/nope.mp4"}, base=VISION)
check("不存在的路径返回 404", s == 404)

print("=" * 78)
print("汇总：通过 %d 项，失败 %d 项" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  - " + f)
sys.exit(1 if FAIL else 0)
