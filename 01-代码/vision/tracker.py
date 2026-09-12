# -*- coding: utf-8 -*-
"""
tracker.py  —— 综合实践III《单目标跟踪系统》视觉核心模块
作者：【姓名】  学号：【学号】  创建时间：2026-07
功能描述：
    基于 OpenCV 的单目标跟踪器，包含三大能力（对应任务书要求）：
      1) 目标跟踪：使用 OpenCV CSRT 相关滤波跟踪器对视频/摄像头画面中的目标进行持续跟踪；
      2) 遮挡检测：跟踪过程中周期性用"参考直方图相似度"监测跟踪质量，
                   目标被遮挡/丢失（跟踪框漂移、相似度骤降）时进入搜索模式；
      3) 重检测与恢复：搜索模式下使用【多尺度灰度模板匹配 + HSV 直方图验证】在全图
                       重新定位目标，连续多帧确认后重新初始化跟踪器，实现
                       "目标被短暂遮挡后再次出现能再次捕捉并继续跟踪"。
    本模块为无界面核心逻辑，供 GUI 演示（gui_track.py）、Web 服务（api_service.py）复用。

输入支持视频与图片两种素材（对应任务书"用户提交要处理的图片或者视频"）：
    - 视频：process_video() —— 逐帧跟踪并输出带标注的结果视频；
    - 图片：process_image() —— 单帧定位目标并在图上标注目标框，输出结果图片。

运行方式：
    python tracker.py --video ../../demo/demo_ball_track.mp4 --bbox x,y,w,h
                      [--out_dir ...] [--show]
    python tracker.py --image ../../demo/screenshots/shot1_源视频首帧_目标待框选.png
"""
import argparse
import json
import os
import subprocess
import time

import cv2
import numpy as np


def to_h264(src):
    """将视频原地转码为 H.264(AVC) + yuv420p + faststart（浏览器可直接播放）。
    OpenCV 默认 mp4v(MPEG-4) 编码 Chromium/Edge 无法解码，转码后解决网页播放问题。
    依赖：pip install imageio-ffmpeg（自带 ffmpeg 二进制）。失败时仅警告不中断。
    """
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        print("[警告] 未安装 imageio-ffmpeg，视频保持 mp4v 编码，浏览器将无法播放。"
              "请执行: pip install imageio-ffmpeg")
        return False
    tmp = src + ".h264tmp.mp4"
    cmd = [exe, "-y", "-i", src, "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-an", tmp]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=300)
        if r.returncode != 0:
            print("[警告] H.264 转码失败:",
                  r.stderr.decode("utf-8", "ignore")[-300:])
            return False
        os.replace(tmp, src)
        print("H.264 转码完成:", src)
        return True
    except Exception as e:
        print("[警告] H.264 转码异常:", e)
        return False

# ---------------- 可调参数 ----------------
HIST_FOUND_TH = 0.55    # 候选框直方图相关度阈值（高于此值视为"像目标"）
HIST_LOST_TH = 0.28     # 跟踪框直方图相关度低于此值判定目标可能丢失
TM_FOUND_TH = 0.72      # 模板匹配归一化分数阈值（搜索命中）
SEARCH_CONFIRM = 2      # 连续 N 帧命中才确认找回（防误报）
LOST_CONFIRM = 3        # 连续 N 次直方图校验未通过才进入搜索模式（防抖）
OOB_CONFIRM = 3         # 连续 N 帧跟踪框越界才进入搜索模式（防抖）
SCALES = [0.85, 1.0, 1.15]   # 模板匹配多尺度
VERIFY_EVERY = 5        # 每 N 帧做一次直方图质量校验
MAX_TRAIL = 60          # 轨迹拖尾点数


# ---------------- 首帧提取 / 自动目标检测 ----------------

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def is_image_path(path):
    """按扩展名判断素材是图片还是视频（任务书要求图片、视频都能处理）。"""
    return os.path.splitext(str(path))[1].lower() in IMAGE_EXTS


def imread_unicode(path):
    """读取图片，返回 BGR ndarray；失败抛 IOError。

    与 imwrite_unicode 同理：cv2.imread 在 Windows 上不支持非 ASCII 路径
    （本工程目录名是中文），必须用 Python 原生 open() 读字节再 imdecode。
    """
    with open(path, "rb") as f:
        buf = np.frombuffer(f.read(), dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        raise IOError("图片读取失败或格式不支持: " + str(path))
    return img


def imwrite_unicode(path, image, jpeg_quality=92):
    """把图片写到 path，返回是否成功。

    ⚠️ 不能用 cv2.imwrite：它在 Windows 上走 ANSI 文件接口，路径含中文等非 ASCII
    字符时会**静默失败**（返回 False 且不抛异常）。本工程目录名就是中文，
    所以必须走 imencode 编码到内存 + Python 原生 open() 写文件。
    （VideoWriter / VideoCapture 走 FFmpeg，支持 Unicode 路径，无此问题。）
    """
    ext = os.path.splitext(path)[1].lower() or ".jpg"
    params = []
    if ext in (".jpg", ".jpeg"):
        params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
    elif ext == ".png":
        params = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
    ok, buf = cv2.imencode(ext, image, params)
    if not ok:
        return False
    with open(path, "wb") as f:
        f.write(buf.tobytes())
    return True


def extract_first_frame(video_path, out_image):
    """提取素材首帧保存为图片，返回 (图片路径, 宽, 高)。

    视频：取第 0 帧；图片：素材本身即"首帧"。
    注意：视频这里固定取**第 0 帧**，与 process_video() 初始化跟踪器的帧保持一致；
    若取别的帧，用户在该图上画的框就会和跟踪起点错位。
    """
    if is_image_path(video_path):
        # 图片素材：本身就是首帧，直接写出一份供前端显示
        frame = imread_unicode(video_path)
        if not out_image:
            base, _ = os.path.splitext(video_path)
            out_image = base + "_first.jpg"
        d = os.path.dirname(os.path.abspath(out_image))
        if d:
            os.makedirs(d, exist_ok=True)
        if not imwrite_unicode(out_image, frame, 92):
            raise IOError("首帧图片写入失败: " + out_image)
        h, w = frame.shape[:2]
        return os.path.abspath(out_image), w, h

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError("无法打开视频: " + video_path)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise IOError("视频为空，读不到首帧: " + video_path)
    if not out_image:
        base, _ = os.path.splitext(video_path)
        out_image = base + "_first.jpg"
    d = os.path.dirname(os.path.abspath(out_image))
    if d:
        os.makedirs(d, exist_ok=True)
    if not imwrite_unicode(out_image, frame, 92):
        raise IOError("首帧图片写入失败: " + out_image)
    h, w = frame.shape[:2]
    return os.path.abspath(out_image), w, h


def auto_detect_bbox(video_path, sample_frames=40, max_side=320):
    """自动定位目标：基于"中值背景差"的运动目标检测。

    旧实现是"取画面正中 20%"——只要画面中央有静止的 UI 元素（例如播放器的
    暂停键），就必然框错。这里改成真正的检测：

      1) 均匀采样若干帧，取**逐像素中值**作为背景估计（能自动滤掉运动目标）；
      2) 用第 0 帧减去背景，得到"目标在前景上的位置"；
      3) Otsu 阈值 + 形态学去噪，取最大连通域外接矩形。

    因为跟踪器是在第 0 帧初始化的，所以检测结果也取第 0 帧上的位置。
    检测失败（目标静止、镜头整体晃动、画面过暗等）返回 None，由调用方回退。
    图片素材没有"运动"概念，直接返回 None（由调用方回退为画面中央区域）。
    """
    if is_image_path(video_path):
        return None
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    try:
        w0 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h0 = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if w0 <= 0 or h0 <= 0:
            return None
        scale = min(1.0, float(max_side) / max(w0, h0))
        tw, th = max(32, int(w0 * scale)), max(32, int(h0 * scale))

        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        # 采样步长：视频很长时均匀跳帧，兼顾速度与背景估计质量
        step = max(1, total // sample_frames) if total > sample_frames else 1

        first_gray = None
        samples = []
        idx = 0
        while len(samples) < sample_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % step == 0:
                small = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)
                g = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY),
                                     (5, 5), 0)
                if first_gray is None:
                    first_gray = g
                samples.append(g)
            idx += 1

        if first_gray is None or len(samples) < 3:
            return None

        bg = np.median(np.stack(samples, axis=0), axis=0).astype(np.uint8)
        diff = cv2.absdiff(first_gray, bg)
        # Otsu 自适应阈值：不同视频对比度差异很大，固定阈值不稳
        _, mask = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None
        c = max(cnts, key=cv2.contourArea)
        area = cv2.contourArea(c)
        frame_area = float(tw * th)
        # 太小 => 噪声；太大 => 镜头整体晃动/全屏变化，都不是可靠的单目标
        if area < frame_area * 0.0008 or area > frame_area * 0.85:
            return None

        x, y, bw, bh = cv2.boundingRect(c)
        inv = 1.0 / scale
        x, y = int(x * inv), int(y * inv)
        bw, bh = int(bw * inv), int(bh * inv)
        # 裁到画面内，并保证最小尺寸（跟踪器要求 >=5 像素）
        x = max(0, min(x, w0 - 1))
        y = max(0, min(y, h0 - 1))
        bw = max(8, min(bw, w0 - x))
        bh = max(8, min(bh, h0 - y))
        return (x, y, bw, bh)
    except Exception as e:  # noqa: BLE001 —— 自动检测失败不应中断流程
        print("[警告] 自动目标检测失败，回退中央区域:", e)
        return None
    finally:
        cap.release()


def center_bbox(width, height, ratio=0.2):
    """回退方案：画面中央区域（仅在自动检测失败时使用）。"""
    bw = max(20, int(width * ratio))
    bh = max(20, int(height * ratio))
    return ((width - bw) // 2, (height - bh) // 2, bw, bh)


# ---------------- 跟踪器创建（跨 OpenCV 版本兼容） ----------------
# OpenCV 4.5.1+ : cv2.TrackerCSRT_create()      —— 主模块工厂函数
# OpenCV 4.5.4+ : cv2.legacy.TrackerCSRT_create()
# OpenCV 5.x    : 已彻底移除 CSRT/KCF（且无 cv2.legacy），仅保留
#                 MIL/DaSiamRPN/Nano/Vit；此时自动降级为 MIL 并给出明确提示，
#                 保证流程仍可跑通（算法精度下降，建议按 requirements.txt 装回 4.x）。
_TRACKER_FACTORIES = {
    "CSRT": ["TrackerCSRT_create", "TrackerCSRT", "legacy.TrackerCSRT_create"],
    "KCF": ["TrackerKCF_create", "TrackerKCF", "legacy.TrackerKCF_create"],
}
# OpenCV 5.x 兜底跟踪器（按优先级尝试）
_TRACKER_FALLBACKS = ["TrackerMIL", "TrackerNano", "TrackerVit"]


def _resolve_attr(dotted):
    """按 'legacy.TrackerCSRT_create' 形式逐级取属性；任一级不存在返回 None。"""
    obj = cv2
    for part in dotted.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj


def create_tracker(backend="CSRT"):
    """创建单目标跟踪器，返回 (tracker, 实际使用的后端名)。

    兼容 OpenCV 4.x 与 5.x；返回对象保证具备 init(img, bbox) 与 update(img)。
    OpenCV 4.x 中这些名字是工厂函数，5.x 中是类（需再调 .create()），故统一处理。
    """
    want = (backend or "CSRT").upper()
    candidates = _TRACKER_FACTORIES.get(want, _TRACKER_FACTORIES["CSRT"])
    for name in candidates:
        obj = _resolve_attr(name)
        if obj is None:
            continue
        try:
            factory = obj.create if isinstance(obj, type) else obj
            return factory(), want
        except Exception:  # noqa: BLE001 —— 换下一个候选
            continue
    for name in _TRACKER_FALLBACKS:
        obj = _resolve_attr(name)
        if obj is None:
            continue
        try:
            factory = obj.create if isinstance(obj, type) else obj
            tracker = factory()
            print("[警告] 当前 OpenCV %s 不含 %s 跟踪器，已降级为 %s（精度下降）。"
                  "建议执行: pip install \"opencv-python>=4.8,<5\""
                  % (cv2.__version__, want, name))
            return tracker, name
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError(
        "无法创建跟踪器：当前 OpenCV %s 缺少 CSRT/KCF 且无可用替代跟踪器。"
        "请执行 pip install \"opencv-python>=4.8,<5\"" % cv2.__version__)


class TrackerState:
    """跟踪器状态机：INIT -> TRACKING <-> SEARCHING"""
    INIT = "INIT"
    TRACKING = "TRACKING"
    SEARCHING = "SEARCHING"
    LOST_FINAL = "LOST_FINAL"
    ERROR = "ERROR"


class SingleObjectTracker:
    def __init__(self, backend="CSRT"):
        self.backend = backend
        self.state = TrackerState.INIT
        self._tracker = None
        # 参考模型（第一帧目标框内）
        self._ref_template = None     # 灰度模板（原始尺度）
        self._ref_hist = None         # HSV 直方图
        self._ref_bbox = None
        self._ref_size = None
        # 运行统计
        self.stats = {
            "total_frames": 0, "tracking_frames": 0, "searching_frames": 0,
            "lost_events": 0, "recoveries": 0, "final_state": "",
            "fps": 0.0, "tracker": backend, "tracker_requested": backend,
            "opencv": cv2.__version__,
        }
        self._lost_counter = 0     # 连续"直方图相似度过低"的校验次数
        self._oob_counter = 0      # 连续"跟踪框越界"的帧数
        self._search_hits = 0
        self._last_bbox = None
        self._trail = []

    # ------------------------------------------------------------
    def init(self, frame, bbox):
        """以 frame 帧上的 bbox(x,y,w,h) 初始化。"""
        x, y, w, h = [int(v) for v in bbox]
        x, y = max(0, x), max(0, y)
        w = min(w, frame.shape[1] - x)
        h = min(h, frame.shape[0] - y)
        if w < 5 or h < 5:
            raise ValueError("目标框过小，无法初始化跟踪器")
        self._ref_bbox = (x, y, w, h)
        self._ref_size = (w, h)
        self._lost_counter = 0
        self._oob_counter = 0
        self._search_hits = 0
        self._build_reference(frame)
        self._new_tracker(frame, (x, y, w, h))
        self.state = TrackerState.TRACKING
        return (x, y, w, h)

    # ------------------------------------------------------------
    def _build_reference(self, frame):
        x, y, w, h = self._ref_bbox
        roi = frame[y:y + h, x:x + w]
        self._ref_template = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        self._ref_hist = self._hist_of(roi)

    @staticmethod
    def _hist_of(roi_bgr):
        hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60],
                            [0, 180, 0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        return hist

    def _hist_similarity(self, roi_bgr):
        """与参考目标的外观相似度（HSV 直方图相关度）。"""
        if roi_bgr.size == 0:
            return 0.0
        hist = self._hist_of(roi_bgr)
        return float(cv2.compareHist(self._ref_hist, hist, cv2.HISTCMP_CORREL))

    def _new_tracker(self, frame, bbox):
        # 兼容 OpenCV 4.x/5.x；stats["tracker"] 记录实际生效的后端
        self._tracker, used = create_tracker(self.backend)
        self.stats["tracker"] = used
        self._tracker.init(frame, tuple(bbox))

    # ------------------------------------------------------------
    def update(self, frame):
        """处理一帧，返回 (bbox, state)。state 取值见 TrackerState。"""
        self.stats["total_frames"] += 1
        h, w = frame.shape[:2]

        if self.state == TrackerState.TRACKING:
            ok, bbox = self._tracker.update(frame)
            if not ok:
                self._enter_search()
                return self._search(frame)

            x, y, bw, bh = [int(v) for v in bbox]
            # 越界判定：连续越界 OOB_CONFIRM 帧判定丢失
            out_of_bounds = (x + bw <= 0 or y + bh <= 0 or
                             x >= w or y >= h)
            self._oob_counter = self._oob_counter + 1 if out_of_bounds else 0

            # 周期性直方图质量校验：只有校验帧才更新计数，
            # 否则"每隔 VERIFY_EVERY 帧才看一次"会被中间帧的默认相似度冲掉，
            # LOST_CONFIRM 这个连续帧确认阈值将永远无法达到（防抖形同虚设）。
            if self.stats["total_frames"] % VERIFY_EVERY == 0:
                cx0, cy0 = max(0, x), max(0, y)
                cx1 = min(w, x + bw)
                cy1 = min(h, y + bh)
                if cx1 - cx0 > 4 and cy1 - cy0 > 4:
                    sim = self._hist_similarity(
                        frame[cy0:cy1, cx0:cx1])
                else:
                    sim = 0.0
                self._lost_counter = (self._lost_counter + 1
                                      if sim < HIST_LOST_TH else 0)

            if (self._lost_counter >= LOST_CONFIRM
                    or self._oob_counter >= OOB_CONFIRM):
                # 目标判定丢失：进入搜索模式
                self._enter_search()
                return self._search(frame)

            # 未达到确认阈值：继续按跟踪器给出的框输出（防抖，避免单帧抖动就全图搜索）
            self._last_bbox = (x, y, bw, bh)
            self._trail.append(((x + bw / 2), (y + bh / 2)))
            if len(self._trail) > MAX_TRAIL:
                self._trail.pop(0)
            self.stats["tracking_frames"] += 1
            return self._last_bbox, self.state

        # SEARCHING 分支
        return self._search(frame)

    # ------------------------------------------------------------
    def _enter_search(self):
        if self.state == TrackerState.TRACKING:
            self.stats["lost_events"] += 1
        self.state = TrackerState.SEARCHING
        self._search_hits = 0
        self._lost_counter = 0
        self._oob_counter = 0

    def _search(self, frame):
        """全图重检测：多尺度模板匹配 + 直方图验证 + 连续帧确认。"""
        self.stats["searching_frames"] += 1
        best = self._detect(frame)
        if best is None:
            self._search_hits = 0
            return None, self.state

        sim = self._hist_similarity(frame[best[1]:best[1] + best[3],
                                          best[0]:best[0] + best[2]])
        if sim >= HIST_FOUND_TH:
            self._search_hits += 1
            if self._search_hits >= SEARCH_CONFIRM:
                # 找回目标，重新初始化跟踪器
                self._new_tracker(frame, best)
                self.state = TrackerState.TRACKING
                self.stats["recoveries"] += 1
                self._lost_counter = 0
                self._oob_counter = 0
                self._last_bbox = best
                self._trail.append(((best[0] + best[2] / 2),
                                    (best[1] + best[3] / 2)))
                if len(self._trail) > MAX_TRAIL:
                    self._trail.pop(0)
                return best, self.state
        else:
            self._search_hits = 0
        return best, self.state

    def _detect(self, frame):
        """模板匹配主流程：在多尺度下搜索与参考模板最相似的位置。"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        best_score = TM_FOUND_TH
        best_box = None
        tw, th = self._ref_size
        h, w = gray.shape[:2]
        for scale in SCALES:
            tws, ths = max(8, int(tw * scale)), max(8, int(th * scale))
            if tws > w or ths > h:
                continue
            tpl = cv2.resize(self._ref_template, (tws, ths))
            res = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val > best_score:
                best_score = max_val
                best_box = (max_loc[0], max_loc[1], tws, ths)
        return best_box

    # ------------------------------------------------------------
    def process_video(self, video_path, bbox, out_video=None, log_path=None,
                      max_frames=None, show=False):
        """对视频文件执行完整跟踪，返回统计信息。

        bbox=None 时自动识别目标：先用 auto_detect_bbox() 做运动目标检测，
        检测失败才回退到画面中央区域（不再无条件取中央）。
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError("无法打开视频: " + video_path)

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        auto_used = None
        if bbox is None:
            auto_used = auto_detect_bbox(video_path)
            if auto_used is None:
                auto_used = center_bbox(width, height)
                print("[提示] 未能自动识别运动目标，回退为画面中央区域:", auto_used)
            else:
                print("[提示] 自动识别到目标框:", auto_used)
            bbox = auto_used

        # 记录最终采用的目标框来源，便于排查"框错了目标"这类问题
        self.stats["auto_bbox"] = (",".join(map(str, auto_used))
                                   if auto_used else None)
        self.stats["bbox_source"] = ("auto" if auto_used else "manual")

        writer = None
        if out_video:
            writer = cv2.VideoWriter(
                out_video, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

        log_rows = []          # 每帧轨迹日志
        frame_idx = 0
        t0 = time.time()
        ok, frame = cap.read()
        if not ok:
            cap.release()
            raise IOError("视频为空")
        self.init(frame, bbox)

        while ok:
            box, state = self.update(frame)
            self._annotate(frame, box, state)
            log_rows.append({
                "frame": frame_idx, "state": state,
                "bbox": list(map(int, box)) if box else None,
            })
            if writer:
                writer.write(frame)
            if show:
                cv2.imshow("tracker", frame)
                if cv2.waitKey(1) & 0xFF == 27:   # ESC
                    break
            frame_idx += 1
            if max_frames and frame_idx >= max_frames:
                break
            ok, frame = cap.read()

        elapsed = time.time() - t0
        cap.release()
        if writer:
            writer.release()
        if show:
            cv2.destroyAllWindows()

        # OpenCV mp4v 输出浏览器无法解码，转码为 H.264（浏览器可直接播放）
        if out_video and os.path.exists(out_video):
            try:
                to_h264(out_video)
            except Exception as e:  # noqa
                print("[警告] 结果视频 H.264 转码失败:", e)

        if self.state == TrackerState.SEARCHING:
            self.state = TrackerState.LOST_FINAL
        self.stats.update({
            "final_state": self.state,
            "media_type": "VIDEO",
            "processed_frames": frame_idx,
            "fps": round(frame_idx / elapsed, 2) if elapsed > 0 else 0.0,
            "out_video": out_video,
        })

        if log_path:
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump({"stats": self.stats, "frames": log_rows},
                          f, ensure_ascii=False, indent=1)
        return self.stats

    # ------------------------------------------------------------
    def process_image(self, image_path, bbox, out_image=None, log_path=None):
        """对**单张图片**执行目标定位与标注，返回统计信息。

        任务书要求"用户提交要处理的图片或者视频"，图片素材没有后续帧，
        因此这里的视觉处理为：在图片上确定目标位置（用户框选或自动识别），
        用目标框标注后输出结果图片，并给出与视频流程一致口径的特征统计
        （颜色直方图相似度、目标框来源等），保证两种素材的处理链路一致。
        """
        frame = imread_unicode(image_path)
        h, w = frame.shape[:2]
        t0 = time.time()

        auto_used = None
        if bbox is None:
            # 单张图片没有帧间运动，无法做运动目标检测，回退为画面中央区域
            auto_used = center_bbox(w, h)
            print("[提示] 图片素材无运动信息，自动目标回退为画面中央区域:", auto_used)
            bbox = auto_used

        self.stats["auto_bbox"] = (",".join(map(str, auto_used))
                                   if auto_used else None)
        self.stats["bbox_source"] = ("auto" if auto_used else "manual")

        x, y, bw, bh = [int(v) for v in bbox]
        x, y = max(0, min(x, w - 5)), max(0, min(y, h - 5))
        bw, bh = max(5, min(bw, w - x)), max(5, min(bh, h - y))
        box = (x, y, bw, bh)

        # 建立特征模型（灰度模板 + HSV 直方图），与视频流程完全一致
        self._ref_bbox = box
        self._ref_size = (bw, bh)
        self._build_reference(frame)
        self._last_bbox = box
        self._trail.append((x + bw / 2, y + bh / 2))
        self.state = TrackerState.TRACKING

        self._annotate(frame, box, TrackerState.TRACKING)
        cv2.putText(frame, "IMAGE TARGET", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)
        if out_image and not imwrite_unicode(out_image, frame, 92):
            raise IOError("结果图片写入失败: " + out_image)

        elapsed = time.time() - t0
        self.stats.update({
            "total_frames": 1,
            "tracking_frames": 1,
            "searching_frames": 0,
            "lost_events": 0,
            "recoveries": 0,
            "final_state": "IMAGE_DONE",
            "media_type": "IMAGE",
            "processed_frames": 1,
            "fps": round(1 / elapsed, 2) if elapsed > 0 else 0.0,
            "out_video": out_image,
            "target_bbox": ",".join(str(int(v)) for v in box),
        })
        if log_path:
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump({"stats": self.stats,
                           "frames": [{"frame": 0, "state": TrackerState.TRACKING,
                                       "bbox": list(box)}]},
                          f, ensure_ascii=False, indent=1)
        return self.stats

    # ------------------------------------------------------------
    def _annotate(self, frame, box, state):
        """绘制跟踪框、状态文字与运动轨迹（仅用于可视化输出）。"""
        color = (0, 200, 0) if state == TrackerState.TRACKING else (0, 0, 255)
        label = state
        if box:
            x, y, w, h = [int(v) for v in box]
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, label, (x, max(15, y - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        else:
            cv2.putText(frame, "SEARCHING ...", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        # 运动轨迹
        if len(self._trail) > 1:
            pts = np.array(self._trail, dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(frame, [pts], False, (0, 200, 255), 2)


# ---------------- CLI ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=None, help="输入视频路径")
    ap.add_argument("--image", default=None, help="输入图片路径（与 --video 二选一）")
    ap.add_argument("--bbox", default=None,
                    help="目标框 x,y,w,h；视频缺省时自动识别运动目标，"
                         "图片缺省时回退为画面中央区域")
    ap.add_argument("--out_dir", default=".")
    ap.add_argument("--backend", default="CSRT", choices=["CSRT", "KCF"])
    ap.add_argument("--show", action="store_true", help="弹窗实时显示")
    ap.add_argument("--max_frames", type=int, default=None)
    args = ap.parse_args()

    if not args.video and not args.image:
        ap.error("请至少指定 --video 或 --image")

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    src = args.image or args.video
    base = os.path.splitext(os.path.basename(src))[0]

    bbox = None
    if args.bbox:
        bbox = [int(v) for v in args.bbox.replace(" ", "").split(",")]

    st = SingleObjectTracker(backend=args.backend)
    if args.image:
        out_image = os.path.join(out_dir, base + "_tracked.jpg")
        log_path = os.path.join(out_dir, base + "_log.json")
        stats = st.process_image(args.image, bbox, out_image=out_image,
                                 log_path=log_path)
    else:
        out_video = os.path.join(out_dir, base + "_tracked.mp4")
        log_path = os.path.join(out_dir, base + "_log.json")
        stats = st.process_video(args.video, bbox, out_video=out_video,
                                 log_path=log_path, max_frames=args.max_frames,
                                 show=args.show)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
