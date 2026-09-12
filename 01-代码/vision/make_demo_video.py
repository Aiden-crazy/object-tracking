# -*- coding: utf-8 -*-
"""
make_demo_video.py  —— 综合实践III《单目标跟踪系统》
作者：【姓名】  学号：【学号】  创建时间：2026-07
功能描述：
    合成一段用于演示与测试的跟踪视频：
    1) 白色网格背景上有一个彩色圆球按设定轨迹运动；
    2) 路径中段有一根竖条"遮挡墙"，圆球经过时被短暂完全遮挡（模拟目标被遮挡场景），
       用于验证系统"目标被短暂遮挡后重新出现能再次捕捉并继续跟踪"的能力；
    3) 同时输出第一帧目标真实位置 bbox 的 JSON 侧车文件，便于自动化测试与报告截图。
运行方式：
    python make_demo_video.py --out_dir ../../demo
"""
import argparse
import json
import os

import cv2
import numpy as np

# ------------------------- 全局参数 -------------------------
W, H = 640, 480          # 画面尺寸
FPS = 30                 # 帧率
FRAMES = 420             # 总帧数（14 秒）
BALL_R = 18              # 圆球半径
BALL_COLOR = (0, 90, 220)      # BGR 蓝色球（区别于背景与遮挡墙）
WALL_X0, WALL_X1 = 290, 360    # 遮挡墙水平范围（宽70>球径36，保证球被完全遮挡）
WALL_COLOR = (60, 60, 60)      # 深灰色墙


def make_grid_bg(w, h, cell=40):
    """生成带浅色网格的白色背景，为模板匹配提供纹理。"""
    bg = np.full((h, w, 3), 245, dtype=np.uint8)
    for x in range(0, w, cell):
        cv2.line(bg, (x, 0), (x, h), (215, 215, 215), 1)
    for y in range(0, h, cell):
        cv2.line(bg, (0, y), (w, y), (215, 215, 215), 1)
    return bg


def ball_center(frame_idx):
    """返回第 frame_idx 帧时球心坐标（匀速水平 + 轻微正弦上下浮动）。"""
    t = frame_idx / (FRAMES - 1)
    cx = 55 + t * (W - 110)                 # 55 -> 585
    cy = H // 2 + int(60 * np.sin(2 * np.pi * 1.5 * t))
    return int(cx), int(cy)


def occluded_by_wall(cx, r):
    """判断球是否与遮挡墙区域相交（此时球画在墙之后，被完全遮住）。"""
    return cx + r > WALL_X0 and cx - r < WALL_X1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default="../../demo")
    ap.add_argument("--video_name", default="demo_ball_track.mp4")
    ap.add_argument("--no_wall", action="store_true",
                    help="不绘制遮挡墙，生成【目标无遮挡匀速运动】的对照测试视频"
                         "（用于视觉专项测试场景A，默认视频含遮挡墙=场景B）")
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    video_path = os.path.join(out_dir, args.video_name)

    bg = make_grid_bg(W, H)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(video_path, fourcc, FPS, (W, H))

    first_bbox = None
    for i in range(FRAMES):
        frame = bg.copy()
        cx, cy = ball_center(i)
        # 球
        cv2.circle(frame, (cx, cy), BALL_R, BALL_COLOR, -1)
        cv2.circle(frame, (cx, cy), BALL_R - 6, (120, 170, 250), -1)  # 高光
        # 遮挡墙画在球之后，产生"被遮挡"效果；--no_wall 时生成对照视频
        if not args.no_wall:
            cv2.rectangle(frame, (WALL_X0, 0), (WALL_X1, H), WALL_COLOR, -1)
            cv2.line(frame, (WALL_X0, 0), (WALL_X0, H), (20, 20, 20), 2)
            cv2.line(frame, (WALL_X1, 0), (WALL_X1, H), (20, 20, 20), 2)

        if i == 0:
            first_bbox = [cx - BALL_R, cy - BALL_R, 2 * BALL_R, 2 * BALL_R]
        writer.write(frame)

    writer.release()

    # OpenCV 的 mp4v 编码 Chromium/Edge 无法播放，转码为 H.264
    from tracker import to_h264
    to_h264(video_path)

    # 侧车信息：第一帧目标框、遮挡区间等（供测试与报告使用）
    meta = {
        "video": video_path,
        "fps": FPS,
        "frames": FRAMES,
        "size": [W, H],
        "first_bbox": first_bbox,
        "wall_x_range": None if args.no_wall else [WALL_X0, WALL_X1],
        "occluded_frames": [] if args.no_wall else [
            i for i in range(FRAMES)
            if occluded_by_wall(ball_center(i)[0], BALL_R)],
    }
    meta_path = os.path.splitext(video_path)[0] + "_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("demo video ->", video_path)
    print("meta       ->", meta_path)
    print("occluded frames count:", len(meta["occluded_frames"]),
          "first bbox:", first_bbox)


if __name__ == "__main__":
    main()
