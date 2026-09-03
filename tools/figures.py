# -*- coding: utf-8 -*-
"""
figures.py —— 生成课程设计报告所需的示意图（架构/用例/时序/状态机/流程图/甘特/E-R/小程序原型）
作者：【姓名】  学号：【学号】  创建时间：2026-07
运行：python figures.py  （输出到 ../../demo/figures/）
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Ellipse

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo", "figures"))
os.makedirs(OUT, exist_ok=True)

C_BLUE = "#2a5298"
C_LIGHT = "#eef3fb"
C_GREEN = "#27ae60"
C_ORANGE = "#e67e22"
C_RED = "#e74c3c"
C_GRAY = "#7f8c8d"


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=170, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("fig:", name)


def box(ax, x, y, w, h, text, fc=C_LIGHT, ec=C_BLUE, fs=11, lw=1.5, bold=False,
        tc="#1a1a1a", rounded=True):
    style = "round,pad=0.08,rounding_size=0.08" if rounded else "square,pad=0"
    p = FancyBboxPatch((x, y), w, h, boxstyle=style,
                       linewidth=lw, edgecolor=ec, facecolor=fc)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, fontweight="bold" if bold else "normal")
    return p


def arrow(ax, x1, y1, x2, y2, color=C_BLUE, lw=1.6, style="-|>", ls="-"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                        mutation_scale=16, linewidth=lw, color=color,
                        linestyle=ls)
    ax.add_patch(a)


# ---------------------------------------------------------------- 图1-1 总体架构
def fig_arch():
    fig, ax = plt.subplots(figsize=(9.2, 6.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 9); ax.axis("off")

    ax.text(5, 8.55, "《单目标跟踪系统》总体架构", ha="center", fontsize=15,
            fontweight="bold", color=C_BLUE)

    # 表现层
    box(ax, 0.6, 6.7, 3.9, 1.3, "微信小程序（用户端）\n登录/上传视频/查看结果", fs=10.5)
    box(ax, 5.5, 6.7, 3.9, 1.3, "Web 管理端（浏览器）\n用户增删改查/任务记录/统计", fs=10.5)
    ax.text(5, 8.25, "表现层", ha="center", fontsize=11, color=C_GRAY)

    # 业务服务层
    box(ax, 1.2, 4.4, 7.6, 1.5,
        "Web 后端（Spring Boot + MyBatis）\n认证鉴权 · 文件存储 · 任务调度(异步) · REST API", fs=11)
    ax.text(5, 6.15, "业务服务层", ha="center", fontsize=11, color=C_GRAY)

    # 视觉处理层
    box(ax, 1.2, 2.2, 7.6, 1.4,
        "视觉处理服务（Python + OpenCV + FastAPI）\n单目标跟踪(CSRT) · 遮挡检测 · 特征重检测恢复", fs=11,
        fc="#e8f8ee", ec=C_GREEN)
    ax.text(5, 3.9, "视觉处理层（服务器端）", ha="center", fontsize=11, color=C_GRAY)

    # 数据层
    box(ax, 0.6, 0.2, 3.9, 1.2, "MySQL\n用户表 t_user / 任务表 t_task", fs=10.5)
    box(ax, 5.5, 0.2, 3.9, 1.2, "磁盘文件存储\n原始视频 / 结果视频 / 跟踪日志", fs=10.5)
    ax.text(5, 1.7, "数据层", ha="center", fontsize=11, color=C_GRAY)

    # 连线
    arrow(ax, 2.5, 6.7, 3.4, 5.9)   # 小程序 -> 后端
    arrow(ax, 7.5, 6.7, 6.6, 5.9)   # 管理端 -> 后端
    arrow(ax, 5.0, 4.4, 5.0, 3.6)   # 后端 -> 视觉
    arrow(ax, 5.0, 2.2, 5.0, 1.7)   # 视觉/后端 -> 数据（示意）
    arrow(ax, 3.2, 4.4, 2.6, 1.4)
    arrow(ax, 6.8, 4.4, 7.4, 1.4)
    save(fig, "fig1_1_系统总体架构图.png")


# ---------------------------------------------------------------- 图1-2 用例图
def fig_usecase():
    fig, ax = plt.subplots(figsize=(10.5, 6.6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 8); ax.axis("off")
    # 系统边界
    ax.add_patch(Rectangle((0.35, 0.3), 11.3, 7.2, fill=False, ec=C_BLUE, lw=1.2))
    ax.text(6, 7.35, "单目标跟踪系统", ha="center", fontsize=12, color=C_BLUE)

    # 参与者
    ax.text(0.8, 5.2, "普通用户", fontsize=11, fontweight="bold", color=C_BLUE)
    ax.add_patch(Ellipse((1.0, 5.0), 0.5, 0.35, fc=C_LIGHT, ec=C_BLUE))
    ax.plot([1.0, 1.0], [4.65, 4.3], color=C_BLUE, lw=1.2)
    ax.plot([0.6, 1.4], [4.5, 4.5], color=C_BLUE, lw=1.2)

    ax.text(11.2, 5.2, "管理员", fontsize=11, fontweight="bold", color=C_BLUE)
    ax.add_patch(Ellipse((11.0, 5.0), 0.5, 0.35, fc=C_LIGHT, ec=C_BLUE))
    ax.plot([11.0, 11.0], [4.65, 4.3], color=C_BLUE, lw=1.2)
    ax.plot([10.6, 11.4], [4.5, 4.5], color=C_BLUE, lw=1.2)

    user_cases = [
        (3.6, 6.3, "注册"), (3.6, 5.2, "登录"), (3.6, 4.1, "修改密码"),
        (3.6, 3.0, "上传视频"), (3.6, 1.9, "查看处理结果"), (3.6, 0.8, "查看我的记录"),
    ]
    admin_cases = [
        (8.5, 6.3, "用户查询"), (8.5, 5.2, "新增用户"), (8.5, 4.1, "删除用户"),
        (8.5, 3.0, "重置密码"), (8.5, 1.9, "任务记录管理"), (8.5, 0.8, "系统统计"),
    ]
    for cx, cy, label in user_cases:
        box(ax, cx - 1.25, cy - 0.28, 2.5, 0.56, label, fc="white", ec=C_GRAY,
            fs=10, rounded=True)
        ax.plot([1.4, cx - 0.9], [4.75, cy], color=C_GRAY, lw=1.0)
    for cx, cy, label in admin_cases:
        box(ax, cx - 1.25, cy - 0.28, 2.5, 0.56, label, fc="white", ec=C_GRAY,
            fs=10, rounded=True)
        ax.plot([10.6, cx + 0.9], [4.75, cy], color=C_GRAY, lw=1.0)
    save(fig, "fig1_2_系统用例图.png")


# ---------------------------------------------------------------- 图1-3 处理时序
def fig_seq():
    fig, ax = plt.subplots(figsize=(10.8, 6.6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 9.4); ax.axis("off")
    xs = [1.2, 4.3, 7.6, 10.4]
    names = ["小程序用户", "Web后端\n(SpringBoot)", "视觉处理服务\n(Python/OpenCV)", "MySQL/文件存储"]
    for x, n in zip(xs, names):
        box(ax, x - 1.05, 8.25, 2.1, 0.8, n, fs=9.5, fc="white")
        ax.plot([x, x], [0.5, 8.2], color="#c9d4e8", lw=1.0, ls="--")

    def msg(i, a, b, text, dy=0.0, color="#333"):
        y = 7.7 - i * 0.85 + dy
        arrow(ax, xs[a], y, xs[b], y, color=color, lw=1.3)
        ax.text((xs[a] + xs[b]) / 2, y + 0.13, text, ha="center", fontsize=8.8,
                color="#444")

    msg(0, 0, 1, "1 上传视频(文件+可选目标框)")
    msg(1, 1, 3, "2 保存文件并登记任务(PENDING)")
    msg(2, 3, 1, "3 返回任务ID", dy=-0.2)
    msg(3, 1, 0, "4 返回任务ID")
    msg(4, 0, 1, "5 轮询任务状态", color=C_ORANGE)
    msg(5, 1, 2, "6 调用 /track_local(视频路径+bbox)", color=C_BLUE)
    msg(6, 2, 2, "7 CSRT跟踪 / 遮挡重检测", dy=-0.32, color=C_GREEN)
    msg(7, 2, 1, "8 返回结果视频与统计", color=C_GREEN)
    msg(8, 1, 3, "9 复制结果并更新任务(SUCCESS)")
    msg(9, 1, 0, "10 返回 SUCCESS + 结果路径")
    msg(10, 0, 0, "11 展示结果视频与统计", color=C_ORANGE)
    save(fig, "fig1_3_系统处理时序图.png")


# ---------------------------------------------------------------- 图3-1 状态机
def fig_state():
    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")
    box(ax, 0.4, 3.0, 1.9, 1.2, "INIT\n初始化", fc="white", ec=C_GRAY, fs=11)
    box(ax, 3.4, 3.4, 2.3, 1.4, "TRACKING\n正常跟踪", fc=C_LIGHT, ec=C_GREEN, fs=12)
    box(ax, 6.9, 3.4, 2.6, 1.4, "SEARCHING\n遮挡/丢失搜索", fc="#fdf3e3", ec=C_ORANGE, fs=11)
    box(ax, 5.0, 0.5, 2.2, 1.1, "LOST_FINAL\n跟踪失败结束", fc="#fdecea", ec=C_RED, fs=10)

    arrow(ax, 2.3, 3.6, 3.4, 4.0, lw=1.4)
    ax.text(2.85, 4.15, "框选目标", fontsize=9, color="#444")
    arrow(ax, 5.7, 3.6, 6.9, 4.2, color=C_ORANGE, lw=1.4)
    ax.text(6.3, 4.15, "相似度骤降/越界(连续3帧)", fontsize=8.4, color=C_ORANGE)
    arrow(ax, 8.2, 3.4, 4.6, 2.0, color=C_RED, lw=1.3)
    ax.text(7.0, 2.35, "超时未找回", fontsize=9, color=C_RED)
    arrow(ax, 6.9, 3.4, 5.7, 3.6, color=C_GREEN, lw=1.4)
    ax.text(5.9, 2.85, "模板匹配+直方图验证\n连续2帧命中 → 重初始化", fontsize=8.4, color=C_GREEN)
    save(fig, "fig3_1_跟踪器状态机图.png")


# ---------------------------------------------------------------- 图3-2 视觉流程
def fig_flow():
    fig, ax = plt.subplots(figsize=(8.6, 9.8))
    ax.set_xlim(0, 10); ax.set_ylim(0, 20); ax.axis("off")
    y = 19.3
    box(ax, 3.3, y - 0.55, 3.4, 1.1, "开始：读取视频/摄像头", fs=10.5,
        fc="#fdecea", ec=C_RED, rounded=False)
    y -= 1.7
    box(ax, 3.0, y - 0.55, 4.0, 1.1, "读取首帧画面", fs=10.5)
    y -= 1.7
    box(ax, 1.6, y - 0.55, 6.8, 1.2, "初始化目标：用户框选或自动中央区域\n构建参考模板与HSV直方图", fs=10)
    y -= 1.8
    box(ax, 3.0, y - 0.55, 4.0, 1.1, "CSRT 逐帧跟踪", fs=10.5, fc=C_LIGHT, ec=C_GREEN)
    y -= 1.7
    box(ax, 1.8, y - 0.5, 6.4, 1.0, "周期性直方图质量校验 + 越界检查", fs=10.5)
    y -= 1.6
    box(ax, 0.6, y - 0.7, 3.4, 1.4, "质量正常？", fs=11, fc="white", ec=C_GRAY, rounded=False)
    ax.text(4.6, y, "是", fontsize=10, color=C_GREEN)
    arrow(ax, 4.0, y, 2.6, y + 1.0, color=C_GREEN)
    box(ax, 6.6, y - 0.7, 3.0, 1.4, "更新轨迹\n输出当前帧", fs=10, fc="white")
    y -= 1.9
    box(ax, 0.4, y - 0.9, 3.8, 1.8, "否 → 进入 SEARCHING：\n多尺度模板匹配 +\nHSV直方图验证", fs=9.5,
        fc="#fdf3e3", ec=C_ORANGE)
    ax.text(5.3, y - 0.2, "否", fontsize=10, color=C_RED)
    arrow(ax, 2.3, y, 2.3, y - 0.9, color=C_RED)
    y -= 2.3
    box(ax, 0.4, y - 0.6, 3.8, 1.2, "连续2帧命中候选？", fs=10.5, fc="white",
        ec=C_GRAY, rounded=False)
    box(ax, 6.0, y - 0.6, 3.6, 1.2, "重新初始化跟踪器\n统计恢复次数", fs=10, fc="#e8f8ee", ec=C_GREEN)
    arrow(ax, 4.2, y, 6.0, y, color=C_GREEN)
    ax.text(5.1, y + 0.16, "是", fontsize=10, color=C_GREEN)
    y -= 1.6
    box(ax, 0.4, y - 0.6, 3.8, 1.2, "视频结束？", fs=10.5, fc="white",
        ec=C_GRAY, rounded=False)
    box(ax, 6.0, y - 0.6, 3.6, 1.2, "保存结果视频与日志\n输出统计", fs=10, fc="#e8f8ee", ec=C_GREEN)
    arrow(ax, 4.2, y, 6.0, y, color=C_GREEN)
    ax.text(5.1, y + 0.16, "是", fontsize=10, color=C_GREEN)
    box(ax, 3.3, y - 2.2, 3.4, 1.0, "结束", fs=10.5, fc="#fdecea",
        ec=C_RED, rounded=False)
    arrow(ax, 7.8, y, 7.8, y - 1.7, color="#444")
    arrow(ax, 5.0, y - 1.65, 5.0, y - 1.7 + 1.05, color="#444") if False else None
    # 补箭头
    arrow(ax, 7.8, y - 1.6, 6.7, y - 1.7, color="#444")
    # 回环箭头：未结束回到跟踪
    arrow(ax, 2.6, y - 0.6, 2.6, y - 1.7 + 1.2, color="#444")
    ax.text(0.8, y - 2.1, "否(下一帧)", fontsize=9, color="#444")
    save(fig, "fig3_2_视觉处理流程图.png")


# ---------------------------------------------------------------- 图2-1 甘特图
def fig_gantt():
    fig, ax = plt.subplots(figsize=(9.4, 4.6))
    tasks = [
        ("需求分析与方案设计", 0, 1),
        ("环境搭建与数据库设计", 1, 2),
        ("视觉跟踪模块开发", 1.5, 3.5),
        ("Web后端与管理端开发", 2.5, 4.5),
        ("小程序端开发", 3.5, 5),
        ("三端集成联调", 5, 6),
        ("系统测试与修复", 6, 7),
        ("报告撰写与答辩准备", 6.5, 8),
    ]
    for i, (name, s, e) in enumerate(tasks):
        y = len(tasks) - i
        ax.barh(y, e - s, left=s, height=0.55, color=C_BLUE if i % 2 == 0 else "#4a7ab8")
        ax.text(s + 0.05, y, name, va="center", fontsize=9.5, color="#fff",
                fontweight="bold")
    ax.set_yticks([])
    ax.set_xticks(range(0, 9))
    ax.set_xticklabels(["第%d周" % i for i in range(8)] + [""], fontsize=9)
    ax.set_xlim(0, 8)
    ax.set_xlabel("项目进度（周）", fontsize=10)
    ax.grid(axis="x", ls=":", alpha=0.5)
    ax.set_title("项目进度计划（甘特图）", fontsize=13, color=C_BLUE)
    save(fig, "fig2_1_项目进度甘特图.png")


# ---------------------------------------------------------------- 图4-1 E-R
def fig_er():
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 6); ax.axis("off")
    # 用户实体
    box(ax, 0.5, 3.6, 3.4, 2.0, "", fc=C_LIGHT, ec=C_BLUE)
    ax.text(2.2, 5.25, "用户 (t_user)", ha="center", fontsize=11,
            fontweight="bold", color=C_BLUE)
    for i, a in enumerate(["id (PK)", "username 用户名", "password 密码",
                           "role 角色", "create_time"]):
        ax.text(2.2, 4.75 - i * 0.4, a, ha="center", fontsize=9)
    # 任务实体
    box(ax, 8.0, 3.6, 3.6, 2.0, "", fc="#e8f8ee", ec=C_GREEN)
    ax.text(9.8, 5.25, "任务 (t_task)", ha="center", fontsize=11,
            fontweight="bold", color=C_GREEN)
    for i, a in enumerate(["id (PK)", "user_id (FK)", "file_name",
                           "status 状态", "result_path 结果"]):
        ax.text(9.8, 4.75 - i * 0.4, a, ha="center", fontsize=9)
    # 关系
    arrow(ax, 3.9, 4.6, 8.0, 4.6, lw=2)
    ax.text(6.0, 5.0, "1 : N", ha="center", fontsize=13, fontweight="bold",
            color=C_ORANGE)
    ax.text(6.0, 4.35, "提交", ha="center", fontsize=11, color=C_ORANGE)
    # 菱形
    d = plt.Polygon([[6, 4.2], [6.7, 3.7], [6, 3.2], [5.3, 3.7]],
                    closed=True, fc="white", ec=C_ORANGE, lw=1.5)
    ax.add_patch(d)
    ax.text(6, 3.7, "提交", ha="center", fontsize=9, color=C_ORANGE)
    save(fig, "fig4_1_数据库E-R图.png")


# ---------------------------------------------------------------- 图3-2 功能结构
def fig_tree():
    fig, ax = plt.subplots(figsize=(9.4, 5.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 7); ax.axis("off")
    box(ax, 3.7, 5.9, 2.6, 0.9, "单目标跟踪系统", fc=C_BLUE, ec=C_BLUE,
        fs=12, bold=True, tc="white")

    cols = [
        (0.4, "小程序用户端", ["注册/登录", "修改密码", "上传视频", "结果回看", "我的记录"]),
        (3.7, "Web后端(管理端)", ["用户增删改查", "重置密码", "任务记录管理", "系统统计", "JWT鉴权"]),
        (7.0, "视觉处理(服务端)", ["CSRT跟踪", "遮挡检测", "重检测恢复", "轨迹/统计输出"]),
    ]
    for x, title, items in cols:
        box(ax, x, 4.7, 2.6, 0.9, title, fc=C_LIGHT, ec=C_BLUE, fs=10.5, bold=True)
        arrow(ax, x + 1.3, 5.9, x + 1.3, 5.65, lw=1.2)
        for i, it in enumerate(items):
            box(ax, x, 4.1 - i * 0.68, 2.6, 0.55, it, fc="white", ec=C_GRAY,
                fs=9.5)
    # 后端连接用户端与视觉/数据库的横向标注
    ax.text(5.0, 0.25, "统一 REST 接口 / MySQL / 文件存储", ha="center",
            fontsize=10, color=C_ORANGE, style="italic")
    save(fig, "fig_tree_功能结构图.png")


# ---------------------------------------------------------------- 小程序原型（PIL）
def mini_mockup(name, title, rows, bottom_note=""):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 420, 860
    img = Image.new("RGB", (W, H), "#f0f2f5")
    d = ImageDraw.Draw(img)
    f_title = ImageFont.truetype("msyh.ttc", 30)
    f_text = ImageFont.truetype("msyh.ttc", 22)
    f_small = ImageFont.truetype("msyh.ttc", 18)
    # 状态栏+导航
    d.rectangle([0, 0, W, 110], fill="#2a5298")
    d.text((150, 45), title, font=f_title, fill="white")
    y = 150
    for item in rows:
        kind = item[0]
        if kind == "field":
            d.rounded_rectangle([40, y, W - 40, y + 80], radius=14,
                                fill="white", outline="#d9d9d9")
            d.text((60, y + 24), item[1], font=f_text, fill="#999")
            y += 100
        elif kind == "btn":
            d.rounded_rectangle([40, y, W - 40, y + 90], radius=45,
                                fill="#2a5298")
            d.text((W // 2 - len(item[1]) * 13, y + 22), item[1],
                   font=f_text, fill="white")
            y += 110
        elif kind == "video":
            d.rounded_rectangle([40, y, W - 40, y + 260], radius=14,
                                fill="#222222", outline="#888")
            d.text((160, y + 110), item[1], font=f_text, fill="#bbb")
            y += 280
        elif kind == "note":
            d.text((60, y), item[1], font=f_small, fill="#888")
            y += 44
        elif kind == "list":
            for idx, txt in enumerate(item[1]):
                d.rounded_rectangle([40, y, W - 40, y + 110], radius=14,
                                    fill="white")
                d.text((60, y + 14), txt[0], font=f_small, fill="#2a5298")
                d.text((60, y + 44), txt[1], font=f_small, fill="#666")
                y += 130
        elif kind == "box":
            d.rectangle([x0, y, x0 + w, y + h], outline="green", width=4) \
                if False else None
        elif kind == "status":
            d.rounded_rectangle([40, y, W - 40, y + 90], radius=14,
                                fill="#fdf3e3", outline="#f39c12")
            d.text((60, y + 28), item[1], font=f_text, fill="#e67e22")
            y += 110
    if bottom_note:
        d.text((40, H - 60), bottom_note, font=f_small, fill="#bbb")
    img.save(os.path.join(OUT, name))
    print("fig:", name)


def main():
    fig_arch()
    fig_usecase()
    fig_seq()
    fig_state()
    fig_flow()
    fig_gantt()
    fig_er()
    fig_tree()

    mini_mockup("mini_1_登录页原型.png", "登录",
                [("field", "用户名"), ("field", "密码"),
                 ("btn", "登  录"), ("note", "还没有账号？立即注册")],
                bottom_note="小程序界面原型示意（实际运行截图待替换）")
    mini_mockup("mini_2_上传页原型.png", "上传跟踪",
                [("note", "1. 选择要跟踪的视频"),
                 ("video", "点击选择视频"),
                 ("note", "2. 指定跟踪目标"),
                 ("btn", "自动选择目标(画面中央)"),
                 ("btn", "3. 提交处理")],
                bottom_note="小程序界面原型示意（实际运行截图待替换）")
    mini_mockup("mini_3_结果页原型.png", "处理结果",
                [("status", "SUCCESS 处理成功"),
                 ("video", "结果视频(带跟踪框)"),
                 ("note", "处理帧数:420  FPS:97"),
                 ("note", "丢失事件:1次 重新捕获:1次"),
                 ("btn", "查看我的记录")],
                bottom_note="小程序界面原型示意（实际运行截图待替换）")
    print("all figures done ->", OUT)


if __name__ == "__main__":
    main()
