# -*- coding: utf-8 -*-
"""
extract_screens.py —— 从跟踪结果视频中抽取关键帧，作为报告/PPT 的真实运行截图
作者：【姓名】  学号：【学号】
运行：python extract_screens.py
输出：demo/screenshots/*.png
"""
import os

import cv2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "demo"))
VIDEO = os.path.join(ROOT, "vision_out", "demo_ball_track_tracked.mp4")
SRC_VIDEO = os.path.join(ROOT, "demo_ball_track.mp4")
OUT = os.path.join(ROOT, "screenshots")

# (文件名, 帧号, 是否用源视频[未标注])
SHOTS = [
    ("shot1_源视频首帧_目标待框选.png", 0, True),
    ("shot2_跟踪中_简单运动.png", 150, False),
    ("shot3_目标被遮挡_进入搜索.png", 220, False),
    ("shot4_遮挡后重新捕获_继续跟踪.png", 300, False),
    ("shot5_跟踪至末尾_轨迹完整.png", 410, False),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, frame_idx, use_src in SHOTS:
        path = SRC_VIDEO if use_src else VIDEO
        cap = cv2.VideoCapture(path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        cap.release()
        if not ok:
            print("skip", name)
            continue
        out_path = os.path.join(OUT, name)
        # cv2.imwrite 在 Windows 下不支持中文路径，改用 imencode + 文件写入
        ok, buf = cv2.imencode(".png", frame)
        if not ok:
            print("encode fail", name)
            continue
        with open(out_path, "wb") as f:
            f.write(buf.tobytes())
        print("saved", out_path)


if __name__ == "__main__":
    main()
