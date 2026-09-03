# -*- coding: utf-8 -*-
"""
tracker.py  —— 综合实践III《单目标跟踪系统》视觉核心模块
作者：【姓名】  学号：【学号】  创建时间：2026-07
功能描述：
    基于 OpenCV 的单目标跟踪器，包含三大能力（对应任务书要求）：
      1) 目标跟踪：使用 OpenCV CSRT 相关滤波跟踪器对视频/摄像头画面中的目标进行持续跟踪；
      2) 遮挡检测：跟踪过程中周期性用"参考直方图相似度"监测跟踪质量，
                   目标被遮挡/丢失（跟踪框漂移、相似度骤降）时进入搜索模式；
      3) 重检测与恢复：搜索模式下使用【ORB 特征模板匹配 + HSV 直方图验证】在全图
                       重新定位目标，连续多帧确认后重新初始化跟踪器，实现
                       "目标被短暂遮挡后再次出现能再次捕捉并继续跟踪"。
    本模块为无界面核心逻辑，供 GUI 演示（gui_track.py）、Web 服务（api_service.py）复用。

运行方式：
    python tracker.py --video ../../demo/demo_ball_track.mp4 --bbox x,y,w,h
                      [--out_dir ...] [--show]
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
LOST_CONFIRM = 3        # 连续 N 帧疑似丢失才进入搜索模式（防抖）
SCALES = [0.85, 1.0, 1.15]   # 模板匹配多尺度
VERIFY_EVERY = 5        # 每 N 帧做一次直方图质量校验
MAX_TRAIL = 60          # 轨迹拖尾点数


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
            "fps": 0.0, "tracker": backend,
        }
        self._lost_counter = 0
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
        if self.backend.upper() == "KCF":
            self._tracker = cv2.TrackerKCF_create()
        else:
            self._tracker = cv2.TrackerCSRT_create()
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
            # 越界判定
            out_of_bounds = (x + bw <= 0 or y + bh <= 0 or
                             x >= w or y >= h)
            # 周期性直方图质量校验
            sim = 1.0
            if self.stats["total_frames"] % VERIFY_EVERY == 0:
                cx0, cy0 = max(0, x), max(0, y)
                cx1 = min(w, x + bw)
                cy1 = min(h, y + bh)
                if cx1 - cx0 > 4 and cy1 - cy0 > 4:
                    sim = self._hist_similarity(
                        frame[cy0:cy1, cx0:cx1])
                else:
                    sim = 0.0

            if out_of_bounds or sim < HIST_LOST_TH:
                self._lost_counter += 1
                if self._lost_counter >= LOST_CONFIRM:
                    self._enter_search()
                    return self._search(frame)
            else:
                self._lost_counter = 0
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
        """对视频文件执行完整跟踪，返回统计信息。bbox=None 时自动取画面中央区域。"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError("无法打开视频: " + video_path)

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if bbox is None:  # 自动选目标：中央 20% 区域
            bw, bh = max(20, int(width * 0.2)), max(20, int(height * 0.2))
            bbox = ((width - bw) // 2, (height - bh) // 2, bw, bh)

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
    ap.add_argument("--video", required=True, help="输入视频路径")
    ap.add_argument("--bbox", default=None,
                    help="首帧目标框 x,y,w,h；缺省自动取画面中央区域")
    ap.add_argument("--out_dir", default=".")
    ap.add_argument("--backend", default="CSRT", choices=["CSRT", "KCF"])
    ap.add_argument("--show", action="store_true", help="弹窗实时显示")
    ap.add_argument("--max_frames", type=int, default=None)
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.video))[0]
    out_video = os.path.join(out_dir, base + "_tracked.mp4")
    log_path = os.path.join(out_dir, base + "_log.json")

    bbox = None
    if args.bbox:
        bbox = [int(v) for v in args.bbox.replace(" ", "").split(",")]

    st = SingleObjectTracker(backend=args.backend)
    stats = st.process_video(args.video, bbox, out_video=out_video,
                             log_path=log_path, max_frames=args.max_frames,
                             show=args.show)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
