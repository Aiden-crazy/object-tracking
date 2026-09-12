# -*- coding: utf-8 -*-
"""
api_service.py  —— 综合实践III《单目标跟踪系统》视觉处理 Web 服务
作者：【姓名】  学号：【学号】  创建时间：2026-07
功能描述：
    将视觉核心模块封装为 HTTP 服务（服务器端视觉处理模块），供 Web 后端调用：
      1) POST /api/v1/track        : multipart 上传视频/图片文件 + 可选 bbox，返回处理结果
      2) POST /api/v1/track_local  : 传入服务器本地视频/图片路径（同机部署时由 Java 后端调用），
                                     避免大文件二次传输
      3) POST /api/v1/prepare      : 提取首帧图片 + 返回视频原始尺寸与自动识别目标框，
                                     供小程序"先看首帧、再手指画框"的两段式流程使用
      4) GET  /api/v1/health       : 健康检查
      5) GET  /api/v1/file         : 读取结果文件（调试用）
    素材支持视频与图片两种（对应任务书"用户提交要处理的图片或者视频"）：
    视频输出 *_tracked.mp4，图片输出 *_tracked.jpg，统计口径一致。
    处理完成的结果与日志保存在 out_dir 下，返回绝对路径给调用方。
运行方式：
    python api_service.py --host 127.0.0.1 --port 9000 --out_dir ../../demo/vision_out
"""
import argparse
import json
import os
import shutil
import uuid

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from tracker import (SingleObjectTracker, auto_detect_bbox, center_bbox,
                     extract_first_frame, is_image_path)

app = FastAPI(title="单目标跟踪视觉处理服务", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OUT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "demo", "vision_out"))


@app.get("/", response_class=HTMLResponse)
def index():
    """服务状态首页：浏览器直接打开 http://localhost:9000/ 即可查看。"""
    return """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>单目标跟踪 - 视觉处理服务</title>
<style>
 body{font-family:'Microsoft YaHei',sans-serif;background:#f0f2f5;margin:0}
 .wrap{max-width:760px;margin:60px auto;background:#fff;border-radius:14px;
       padding:36px 44px;box-shadow:0 6px 24px rgba(0,0,0,.08)}
 h1{color:#2a5298;border-left:6px solid #e67e22;padding-left:14px;font-size:24px}
 .ok{display:inline-block;background:#e8f8ee;color:#27ae60;padding:6px 18px;
     border-radius:999px;font-weight:bold;margin:6px 0 18px}
 a{display:inline-block;margin:6px 12px 6px 0;padding:10px 22px;border-radius:8px;
   background:#2a5298;color:#fff;text-decoration:none;font-size:15px}
 a.alt{background:#fff;color:#2a5298;border:1px solid #2a5298}
 li{line-height:2;color:#444;font-size:15px}
 code{background:#f2f2f2;padding:2px 8px;border-radius:4px}
</style></head><body>
<div class="wrap">
 <h1>综合实践III · 单目标跟踪视觉处理服务</h1>
 <span class="ok">● 服务运行中</span>
 <p>服务器端机器视觉模块（Python + OpenCV + FastAPI），由 Web 后端自动调用。</p>
 <p>
   <a href="/docs">Swagger 接口文档</a>
   <a class="alt" href="/api/v1/health">健康检查 JSON</a>
   <a class="alt" href="/redoc">ReDoc</a>
 </p>
 <ul>
   <li><code>GET  /api/v1/health</code> —— 健康检查</li>
   <li><code>POST /api/v1/prepare</code> —— 提取首帧 + 原始尺寸 + 自动识别目标框（小程序框选流程）</li>
   <li><code>POST /api/v1/track_local</code> —— 传入本地视频/图片路径+bbox，执行单目标跟踪（Web后端调用）</li>
   <li><code>POST /api/v1/track</code> —— multipart 上传视频/图片直接处理</li>
 </ul>
 <p style="color:#888;font-size:13px">单目标跟踪系统 · 综合实践III 课程设计</p>
</div></body></html>"""


@app.on_event("startup")
def _startup():
    os.makedirs(OUT_DIR, exist_ok=True)


@app.get("/api/v1/health")
def health():
    return {"code": 0, "msg": "vision service ok", "out_dir": OUT_DIR}


def _do_track(video_path: str, bbox_str: str | None, out_dir: str) -> dict:
    """统一处理入口：按素材类型分派到视频跟踪 / 图片定位，返回结果路径与统计。"""
    task_id = uuid.uuid4().hex[:12]
    os.makedirs(out_dir, exist_ok=True)
    bbox = None
    if bbox_str:
        bbox = [int(v) for v in bbox_str.replace(" ", "").split(",")]
        if len(bbox) != 4:
            raise HTTPException(400, "bbox 格式应为 x,y,w,h")
    image_mode = is_image_path(video_path)
    suffix = ".jpg" if image_mode else ".mp4"
    out_video = os.path.join(out_dir, f"{task_id}_tracked{suffix}")
    log_path = os.path.join(out_dir, f"{task_id}_log.json")
    try:
        st = SingleObjectTracker(backend="CSRT")
        if image_mode:
            stats = st.process_image(video_path, bbox,
                                     out_image=out_video, log_path=log_path)
        else:
            stats = st.process_video(video_path, bbox,
                                     out_video=out_video, log_path=log_path)
    except HTTPException:
        raise
    except Exception as e:  # noqa
        raise HTTPException(500, f"视觉处理失败: {e}")
    return {"code": 0, "task_id": task_id, "stats": stats,
            "media_type": "IMAGE" if image_mode else "VIDEO",
            "result_video": os.path.abspath(out_video),
            "log_file": os.path.abspath(log_path)}


@app.post("/api/v1/prepare")
def prepare(payload: dict):
    """首帧提取 + 自动目标识别（供小程序「先看首帧、再手指画框」流程使用）。

    同时返回：
      image     : 首帧图片绝对路径（与跟踪初始化的第 0 帧严格一致）
      width/height : 视频原始像素尺寸，客户端据此把手指坐标换算回原始像素
      auto_bbox : 运动检测给出的建议目标框 "x,y,w,h"，无可靠结果时为 null
    """
    video_path = payload.get("video_path")
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(404, "video_path 不存在: " + str(video_path))

    try:
        image, width, height = extract_first_frame(video_path, payload.get("out_image"))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, "首帧提取失败: %s" % e)

    auto_bbox = None
    if is_image_path(video_path):
        # 图片素材没有帧间运动，无法做运动检测：自动目标回退为画面中央区域
        auto_bbox = ",".join(str(int(v))
                             for v in center_bbox(width, height))
    else:
        try:
            box = auto_detect_bbox(video_path)
            if box:
                auto_bbox = ",".join(str(int(v)) for v in box)
        except Exception as e:  # noqa: BLE001 —— 自动识别失败不影响首帧可用
            print("[警告] 自动目标检测异常:", e)

    return {"code": 0, "image": image, "width": width, "height": height,
            "auto_bbox": auto_bbox}


@app.post("/api/v1/track")
async def track_upload(file: UploadFile = File(...),
                       bbox: str | None = Form(None)):
    """multipart 上传方式：小程序->Java后端 转发或直接调用。"""
    suffix = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = os.path.join(OUT_DIR, f"upload_{uuid.uuid4().hex[:8]}{suffix}")
    with open(tmp, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return _do_track(tmp, bbox, OUT_DIR)


@app.post("/api/v1/track_local")
def track_local(payload: dict):
    """同机部署：Java 后端传入本地视频绝对路径 + bbox。"""
    video_path = payload.get("video_path")
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(404, "video_path 不存在: " + str(video_path))
    return _do_track(video_path, payload.get("bbox"), OUT_DIR)


@app.get("/api/v1/file")
def get_file(path: str):
    """读取结果文件（供调试/展示）。"""
    p = os.path.abspath(path)
    if not p.startswith(os.path.abspath(OUT_DIR)) or not os.path.exists(p):
        raise HTTPException(404, "文件不存在")
    return FileResponse(p)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--out_dir", default=OUT_DIR)
    args = ap.parse_args()
    OUT_DIR = os.path.abspath(args.out_dir)
    os.makedirs(OUT_DIR, exist_ok=True)
    uvicorn.run(app, host=args.host, port=args.port)
