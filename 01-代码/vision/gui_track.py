# -*- coding: utf-8 -*-
"""
gui_track.py  —— 综合实践III《单目标跟踪系统》本地交互演示界面
作者：【姓名】  学号：【学号】  创建时间：2026-07
功能描述：
    提供简洁易操作的用户交互界面（对应任务书"系统提供简洁、易操作的用户交互界面"）：
      1) 打开本地视频文件（--video）或摄像头（--camera 0）；
      2) 在第一帧画面中用鼠标拖拽框选目标对象；
      3) 回车/空格键开始跟踪：实时显示跟踪框、运动轨迹与状态（TRACKING/SEARCHING），
         目标被短暂遮挡后自动重新捕捉继续跟踪；
      4) 按 S 保存结果视频，按 ESC 退出。
运行方式：
    python gui_track.py --video ../../demo/demo_ball_track.mp4
    python gui_track.py --camera 0 --save 1
"""
import argparse
import os
import time

import cv2

from tracker import SingleObjectTracker

roi = []          # 鼠标拖拽框选的 ROI
dragging = False


def on_mouse(event, x, y, flags, param):
    global roi, dragging
    if event == cv2.EVENT_LBUTTONDOWN:
        roi = [x, y, x, y]
        dragging = True
    elif event == cv2.EVENT_MOUSEMOVE and dragging:
        roi[2], roi[3] = x, y
    elif event == cv2.EVENT_LBUTTONUP:
        roi[2], roi[3] = x, y
        dragging = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=None, help="本地视频路径")
    ap.add_argument("--camera", type=int, default=None, help="摄像头编号")
    ap.add_argument("--save", type=int, default=0, help="1=跟踪结束后保存结果视频")
    ap.add_argument("--out_dir", default=".")
    args = ap.parse_args()

    if args.camera is not None:
        cap = cv2.VideoCapture(args.camera)
        src_name = f"camera{args.camera}"
    else:
        cap = cv2.VideoCapture(args.video)
        src_name = os.path.splitext(os.path.basename(args.video))[0]
    if not cap.isOpened():
        print("无法打开视频源")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    cv2.namedWindow("Select Target: drag to select, ENTER to start, ESC to quit")
    cv2.setMouseCallback("Select Target: drag to select, ENTER to start, ESC to quit", on_mouse)

    tracker = SingleObjectTracker(backend="CSRT")
    started = False
    writer = None
    out_path = os.path.join(os.path.abspath(args.out_dir),
                            src_name + "_gui_tracked.mp4")

    # 实时帧率统计：stats["fps"] 只在 process_video() 结束时才写入，
    # 交互式循环里必须自己统计，否则界面上永远显示 FPS:0.0
    fps_win = []          # 最近若干帧的耗时
    fps = 0.0
    t_last = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        display = frame.copy()
        if not started:
            if len(roi) == 4 and roi[2] > roi[0] and roi[3] > roi[1]:
                cv2.rectangle(display, (roi[0], roi[1]), (roi[2], roi[3]),
                              (0, 255, 0), 2)
            cv2.putText(display, "Drag to select target, ENTER to start, ESC quit",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.imshow("Select Target: drag to select, ENTER to start, ESC to quit", display)
            key = cv2.waitKey(30) & 0xFF
            if key in (13, 32) and len(roi) == 4 and roi[2] > roi[0] and roi[3] > roi[1]:
                bbox = (roi[0], roi[1], roi[2] - roi[0], roi[3] - roi[1])
                tracker.init(frame, bbox)
                started = True
                if args.save:
                    writer = cv2.VideoWriter(
                        out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
            elif key == 27:
                break
        else:
            box, state = tracker.update(frame)
            tracker._annotate(display, box, state)
            now = time.time()
            dt = now - t_last
            t_last = now
            if dt > 0:
                fps_win.append(dt)
                if len(fps_win) > 30:
                    fps_win.pop(0)
                avg = sum(fps_win) / len(fps_win)
                fps = 1.0 / avg if avg > 0 else 0.0
            tracker.stats["fps"] = round(fps, 2)     # 同步到统计信息，便于退出后查看
            cv2.putText(display, "FPS:%.1f" % fps,
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            if writer:
                writer.write(display)
            cv2.imshow("Select Target: drag to select, ENTER to start, ESC to quit", display)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("s"):
                writer = cv2.VideoWriter(
                    out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
                print("开始保存:", out_path)
            elif key == 27:
                break

    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()
    print("GUI 跟踪结束，最终状态:", tracker.state)
    print("统计:", tracker.stats)


if __name__ == "__main__":
    main()
