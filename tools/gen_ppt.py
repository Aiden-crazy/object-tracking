# -*- coding: utf-8 -*-
"""
gen_ppt.py —— 综合实践III《单目标跟踪系统》答辩 PPT 生成器
作者：【姓名】  学号：【学号】  创建时间：2026-07
运行：python gen_ppt.py   输出：../../03-答辩PPT/综合实践III答辩PPT-单目标跟踪系统.pptx
"""
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Cm, Pt

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FIG = ROOT + "/demo/figures/"
SCR = ROOT + "/demo/screenshots/"
OUT_DIR = ROOT + "/03-答辩PPT"
OUT_FILE = OUT_DIR + "/综合实践III答辩PPT-单目标跟踪系统.pptx"

BLUE = RGBColor(0x2A, 0x52, 0x98)
DARK = RGBColor(0x1F, 0x2D, 0x3D)
GRAY = RGBColor(0x60, 0x6A, 0x76)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xEE, 0xF3, 0xFB)
GREEN = RGBColor(0x27, 0xAE, 0x60)
ORANGE = RGBColor(0xE6, 0x7E, 0x22)

EA = "微软雅黑"


def _set_ea(run):
    rPr = run._r.get_or_add_rPr()
    from pptx.oxml.ns import qn
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        rPr.append(ea)
    ea.set("typeface", EA)


def style_run(run, size=18, bold=False, color=DARK, font=EA):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font
    _set_ea(run)


def add_tb(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Cm(x), Cm(y), Cm(w), Cm(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    return tf


def para(tf, text, size=18, bold=False, color=DARK, align=PP_ALIGN.LEFT,
         bullet=False, space_after=8, first=False, level=0):
    p = tf.paragraphs[0] if first and not tf.paragraphs[0].runs else tf.add_paragraph()
    p.alignment = align
    p.level = level
    p.space_after = Pt(space_after)
    if bullet:
        # 前缀符号模拟项目符号
        text = "▪ " + text
    r = p.add_run()
    r.text = text
    style_run(r, size, bold, color)
    return p


def new_pres():
    prs = Presentation()
    prs.slide_width = Cm(33.867)   # 16:9
    prs.slide_height = Cm(19.05)
    return prs


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def add_rect(slide, x, y, w, h, color):
    from pptx.enum.shapes import MSO_SHAPE
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(x), Cm(y), Cm(w), Cm(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def header(slide, title, idx):
    add_rect(slide, 0, 0, 33.867, 2.1, BLUE)
    add_rect(slide, 0, 2.1, 33.867, 0.12, ORANGE)
    tf = add_tb(slide, 1.2, 0.28, 26, 1.5, MSO_ANCHOR.MIDDLE)
    para(tf, title, size=26, bold=True, color=WHITE, first=True)
    tf2 = add_tb(slide, 30.2, 0.5, 2.6, 1.2)
    para(tf2, "%02d" % idx, size=20, bold=True, color=WHITE,
         align=PP_ALIGN.RIGHT, first=True)


def img(slide, path, x, y, w=None, h=None):
    kw = {}
    if w:
        kw["width"] = Cm(w)
    if h:
        kw["height"] = Cm(h)
    slide.shapes.add_picture(path, Cm(x), Cm(y), **kw)


def body_lines(slide, lines, x=1.5, y=2.8, w=30.8, size=17, gap=10, color=DARK):
    tf = add_tb(slide, x, y, w, 14)
    for i, ln in enumerate(lines):
        if isinstance(ln, tuple):
            t, sz, bd, col = ln
        else:
            t, sz, bd, col = ln, size, False, color
        para(tf, t, size=sz, bold=bd, color=col, bullet=(not bd),
             space_after=gap, first=(i == 0))
    return tf


# ============================ 各页 ============================
def slide_cover(prs, idx):
    s = blank(prs)
    add_rect(s, 0, 0, 33.867, 19.05, BLUE)
    add_rect(s, 0, 12.6, 33.867, 0.1, ORANGE)
    tf = add_tb(s, 2, 3.4, 29.8, 3)
    para(tf, "综合实践III 课程设计答辩", size=20, color=RGBColor(0xBF, 0xD3, 0xF0), first=True)
    para(tf, "单目标跟踪系统的设计与实现", size=44, bold=True, color=WHITE, space_after=16)
    para(tf, "——基于微信小程序 · Spring Boot · OpenCV 的三端联动系统——", size=20, color=RGBColor(0xE8, 0xEE, 0xF8))
    tf2 = add_tb(s, 2, 13.4, 29.8, 4)
    for i, line in enumerate([
        "答辩人：【姓名1】　学号：【学号1】　（组长）",
        "团队成员：【姓名2】　学号：【学号2】",
        "指导教师：罗颂、罗娅、贺筠",
        "班级：【班级】　时间：2026 年 7 月",
    ]):
        para(tf2, line, size=19, color=WHITE, space_after=10, first=(i == 0))


def slide_toc(prs, idx):
    s = blank(prs)
    header(s, "目录 CONTENTS", idx)
    items = [
        "01 课题背景与目标", "02 系统总体架构与流程", "03 需求分析",
        "04 视觉模块设计（核心）", "05 后端 · 管理端 · 数据库",
        "06 小程序端实现", "07 运行效果展示", "08 系统测试",
        "09 项目管理与团队分工", "10 总结与展望",
    ]
    tf = add_tb(s, 3.2, 3.4, 27.4, 12)
    for i, it in enumerate(items):
        col = i // 5
        row = i % 5
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(18)
        r = p.add_run()
        r.text = "  " + it
        style_run(r, 20, bold=False, color=DARK if col == 0 else BLUE)


def slide_bg_goal(prs, idx):
    s = blank(prs)
    header(s, "01 课题背景与目标", idx)
    body_lines(s, [
        ("任务书要求：同时涉及 Web 开发（管理端）+ 移动开发（小程序端）+ 机器视觉（核心），三端联动", 18, True, BLUE),
        ("系统流程：小程序登录 → 提交视频/图片 → 服务端视觉处理 → 结果回存 → Web 端管理", 17, False, DARK),
        ("我们选择视觉场景：单目标跟踪（Python + OpenCV）", 17, True, GREEN),
        ("核心目标：", 17, True, ORANGE),
        ("① 用户在首帧画面上框选目标后持续跟踪并绘制轨迹（也可用自动识别目标）；", 16, False, DARK),
        ("② 目标被短暂遮挡后再次出现时，能自动重新捕捉并继续跟踪（遮挡重检测）；", 16, False, DARK),
        ("③ 跟踪结果（结果视频/结果图片/轨迹/统计）可存储、查询、回看；管理员可管理用户与任务；", 16, False, DARK),
        ("④ 遵循软件工程规范：界面展示、命名注释规范、Git 团队协作、文档与测试齐全。", 16, False, DARK),
    ], size=17)


def slide_arch(prs, idx):
    s = blank(prs)
    header(s, "02 系统总体架构", idx)
    body_lines(s, [
        ("四层架构：表现层（小程序/Web管理端）— 业务服务层（Spring Boot）— 视觉处理层（Python+OpenCV）— 数据层（数据库+文件）", 17, True, BLUE),
        ("视觉处理独立成服务，通过 REST 与后端解耦，便于算法替换与升级", 15, False, GRAY),
    ], size=16, gap=6)
    img(s, FIG + "fig1_1_系统总体架构图.png", 3.0, 5.2, w=27.8)


def slide_flow(prs, idx):
    s = blank(prs)
    header(s, "02 系统流程与技术选型", idx)
    img(s, FIG + "fig1_3_系统处理时序图.png", 1.0, 3.0, w=17.5)
    tf = add_tb(s, 19.6, 3.2, 13.2, 14)
    para(tf, "技术选型", size=19, bold=True, color=BLUE, first=True, space_after=12)
    for t in [
        ("用户端", "微信原生小程序（wx.uploadFile 上传）"),
        ("管理端", "原生单页零构建，随静态资源发布"),
        ("后端", "Spring Boot 3 + MyBatis + JWT + BCrypt"),
        ("视觉", "OpenCV CSRT + 多尺度模板匹配/HSV 重检测 + FastAPI"),
        ("数据", "内嵌 H2（MySQL 兼容，免安装；可切 MySQL 8.0）+ 磁盘文件（/files 映射）"),
        ("协作", "Git 版本控制"),
    ]:
        para(tf, t[0] + "：" + t[1], size=14.5, color=DARK, space_after=10)


def slide_requirement(prs, idx):
    s = blank(prs)
    header(s, "03 需求分析", idx)
    img(s, FIG + "fig1_2_系统用例图.png", 0.8, 3.4, w=17.0)
    tf = add_tb(s, 18.8, 3.4, 14.0, 13)
    para(tf, "功能需求（F-01~F-10）", size=18, bold=True, color=BLUE, first=True, space_after=10)
    for t in [
        "普通用户：注册 / 登录 / 改密 / 上传视频或图片 / 首帧框选 / 结果回看 / 历史记录",
        "管理员：用户查询·新增·删除·重置密码 / 任务管理 / 系统统计",
        "视觉处理：CSRT 跟踪 + 运动目标自动识别 + 遮挡检测 + 自动重检测恢复",
        "非功能：实时性(≥25FPS)、BCrypt+JWT 安全、任务归属校验防越权、异步任务状态机、失败留痕",
    ]:
        para(tf, t, size=14.5, color=DARK, bullet=True, space_after=12)


def slide_vision_design(prs, idx):
    s = blank(prs)
    header(s, "04 视觉模块设计：跟踪器状态机", idx)
    img(s, FIG + "fig3_1_跟踪器状态机图.png", 1.0, 3.2, w=19.5)
    tf = add_tb(s, 21.6, 3.4, 11.4, 14)
    para(tf, "设计要点", size=18, bold=True, color=BLUE, first=True, space_after=10)
    for t in [
        "初始化：目标框（框选/自动识别）→ 灰度模板 + HSV 直方图特征模型",
        "正常跟踪：CSRT 逐帧更新；自动识别用中值背景差运动检测",
        "丢失判定：每5帧直方图相关度校验 + 逐帧越界检查，连续3次/3帧确认（防抖）",
        "搜索恢复：多尺度模板匹配 + 直方图验证，连续2帧命中即恢复",
        "全程输出轨迹 / 状态 / 统计（丢失次数、恢复次数、FPS）；图片素材输出标注结果图",
    ]:
        para(tf, t, size=14, color=DARK, bullet=True, space_after=10)


def slide_vision_flow(prs, idx):
    s = blank(prs)
    header(s, "04 视觉处理流程", idx)
    img(s, FIG + "fig3_2_视觉处理流程图.png", 8.4, 3.2, w=17.0)


def slide_recover(prs, idx):
    s = blank(prs)
    header(s, "04 创新点：遮挡后自动再捕捉", idx)
    body_lines(s, [
        ("痛点：目标被遮挡时，相关滤波模板被背景污染，常规跟踪器“一挡就丢”", 17, True, ORANGE),
        ("方案：TRACKING / SEARCHING 双状态机 + 三重判定", 17, True, BLUE),
    ], size=16, gap=8)
    img(s, SCR + "shot3_目标被遮挡_进入搜索.png", 2.2, 7.0, w=9.2)
    img(s, SCR + "shot4_遮挡后重新捕获_继续跟踪.png", 12.2, 7.0, w=9.2)
    img(s, SCR + "shot5_跟踪至末尾_轨迹完整.png", 22.2, 7.0, w=9.2)
    tf = add_tb(s, 2.2, 15.9, 30, 1.2)
    para(tf, "实测：目标被完全遮挡约0.9秒 → 系统丢失1次（第199帧）→ 自动找回1次（第262帧）→ 继续跟踪至视频结束",
         size=15, bold=True, color=GREEN, align=PP_ALIGN.CENTER, first=True)


def slide_server(prs, idx):
    s = blank(prs)
    header(s, "05 Web后端 · 管理端 · 数据库", idx)
    tf = add_tb(s, 1.5, 3.0, 15.5, 14)
    para(tf, "Web 后端（Spring Boot + MyBatis）", size=18, bold=True, color=BLUE, first=True, space_after=8)
    for t in [
        "统一返回体 {code,msg,data} + JWT 拦截器鉴权",
        "管理端接口强制 ADMIN；任务详情/启动再校验归属（越权返回403）",
        "两段式上传：defer=true 提首帧 → 前端框选 → /start 开始处理",
        "线程池异步：PROCESSING → 调视觉服务 → 结果复制回存 → SUCCESS/FAILED(留痕)",
        "BCrypt 密码加密，密码字段不参与序列化；视频/图片结果按类型落盘",
    ]:
        para(tf, t, size=13.5, color=DARK, bullet=True, space_after=8)
    tf2 = add_tb(s, 18.0, 3.0, 14.8, 14)
    para(tf2, "数据库 zongshe3_track", size=18, bold=True, color=BLUE, first=True, space_after=8)
    for t in [
        "t_user：id/username唯一/password(BCrypt)/role/nickname",
        "t_task：user_id/media_type(VIDEO·IMAGE)/文件路径/bbox/status(PENDING·PROCESSING·SUCCESS·FAILED)/结果路径/stats_json/error_msg",
        "1 用户 : N 任务（级联删除）",
    ]:
        para(tf2, t, size=13.5, color=DARK, bullet=True, space_after=8)
    img(s, FIG + "fig4_1_数据库E-R图.png", 18.0, 9.6, w=14.6)


def slide_mini(prs, idx):
    s = blank(prs)
    header(s, "06 小程序端实现", idx)
    body_lines(s, [
        ("6 个页面：登录 / 注册 / 上传跟踪 / 处理结果 / 我的记录 / 个人中心；tabBar 三入口", 16, True, BLUE),
        ("支持视频与图片素材；小程序无法取视频帧 → 后端提首帧，前端在图片上手指拖拽画框", 15, False, DARK),
        ("显示坐标按“原始尺寸/显示尺寸”换算回素材原始像素，保证所见即所框", 15, False, DARK),
        ("结果页 1.5s 轮询任务状态，完成后播放结果视频（图片素材则展示结果图）与统计", 15, False, DARK),
    ], size=15, gap=6)
    img(s, FIG + "mini_1_登录页原型.png", 3.2, 7.2, w=5.4)
    img(s, FIG + "mini_2_上传页原型.png", 11.2, 7.2, w=5.4)
    img(s, FIG + "mini_3_结果页原型.png", 19.2, 7.2, w=5.4)
    tf = add_tb(s, 24.4, 14.4, 8.6, 1.0)
    para(tf, "（界面原型示意，运行截图见 README 指引）", size=11, color=GRAY, first=True)


def slide_effect_vision(prs, idx):
    s = blank(prs)
    header(s, "07 运行效果（一）：视觉跟踪结果", idx)
    img(s, SCR + "shot1_源视频首帧_目标待框选.png", 1.2, 3.0, w=9.6)
    img(s, SCR + "shot2_跟踪中_简单运动.png", 12.0, 3.0, w=9.6)
    img(s, SCR + "shot3_目标被遮挡_进入搜索.png", 22.8, 3.0, w=9.6)
    img(s, SCR + "shot4_遮挡后重新捕获_继续跟踪.png", 12.0, 11.4, w=9.6)
    tf = add_tb(s, 1.2, 16.4, 31, 1.4)
    para(tf, "合成测试视频 640×480@30fps 420帧：正常跟踪→遮挡丢失(SEARCHING)→自动找回→轨迹完整",
         size=14.5, bold=True, color=BLUE, align=PP_ALIGN.CENTER, first=True)


def slide_effect_webuser(prs, idx):
    s = blank(prs)
    header(s, "07 运行效果（二）：网页检测端", idx)
    body_lines(s, [
        ("浏览器直接打开 /track.html：把视频或图片【拖拽】到网页或 Ctrl+V 粘贴，即可发起检测", 15, True, BLUE),
        ("可提取视频首帧在画布上拖拽框选目标；图片本身即首帧，选好直接框选", 14, False, DARK),
        ("处理完成后自动展示结果视频/结果图片与“丢失/找回/FPS”统计", 14, False, DARK),
    ], size=14, gap=6)
    img(s, SCR + "web_05_网页检测端_拖拽上传.png", 2.0, 6.6, w=14.4)
    img(s, SCR + "web_06_网页检测端_检测结果.png", 17.4, 6.6, w=14.4)
    tf = add_tb(s, 2.0, 16.9, 30, 1.2)
    para(tf, "双击【启动-网页检测端.bat】→ 浏览器自动打开检测页", size=14,
         bold=True, color=GREEN, align=PP_ALIGN.CENTER, first=True)


def slide_effect_web(prs, idx):
    s = blank(prs)
    header(s, "07 运行效果（三）：Web 管理端", idx)
    img(s, SCR + "web_01_登录页.png", 1.0, 3.0, w=9.8)
    img(s, SCR + "web_02_用户管理.png", 11.6, 3.0, w=11.4)
    img(s, SCR + "web_03_任务记录.png", 23.2, 3.0, w=9.6)
    img(s, SCR + "web_04_结果弹窗.png", 11.6, 11.6, w=11.4)
    tf = add_tb(s, 1.0, 16.6, 31, 1.2)
    para(tf, "管理员：统计卡片 / 用户增删改查与重置密码 / 任务记录查询 / 在线播放结果视频",
         size=14.5, bold=True, color=BLUE, align=PP_ALIGN.CENTER, first=True)


def slide_test(prs, idx):
    s = blank(prs)
    header(s, "08 系统测试", idx)
    tf = add_tb(s, 1.5, 3.0, 15.2, 15)
    para(tf, "功能测试（21 项用例全部通过）", size=18, bold=True, color=BLUE, first=True, space_after=8)
    for t in [
        "注册/登录/改密：唯一性、弱口令、错误密码校验 ✓",
        "上传：格式白名单、bbox 校验、异步处理、图片素材链路 ✓",
        "权限：普通用户访问管理端 403；访问他人任务 403 ✓",
        "管理端：用户增删查、重置密码、级联删除、统计 ✓",
        "结果：/files 结果视频可在线播放、结果图片可查看 ✓",
    ]:
        para(tf, t, size=13.5, color=DARK, bullet=True, space_after=8)
    tf2 = add_tb(s, 17.8, 3.0, 15.0, 15)
    para(tf2, "视觉专项测试", size=18, bold=True, color=BLUE, first=True, space_after=8)
    for t in [
        "场景A 无遮挡 420帧：全程跟踪，丢失0次（约104 FPS）✓",
        "场景B 完全遮挡~0.9s：第199帧丢失 → 第262帧自动找回 → 恢复跟踪 ✓",
        "场景C 轨迹完整：恢复后跟踪框回到目标上，末帧仍 TRACKING ✓",
        "图片链路：输出 *_tracked.jpg，media_type=IMAGE ✓",
        "环境：Win11 / JDK21 / H2内嵌库 / Python3.12+OpenCV4.11",
    ]:
        para(tf2, t, size=13.5, color=DARK, bullet=True, space_after=8)


def slide_mgmt(prs, idx):
    s = blank(prs)
    header(s, "09 项目管理与团队分工", idx)
    img(s, FIG + "fig2_1_项目进度甘特图.png", 1.2, 3.2, w=18.6)
    tf = add_tb(s, 20.6, 3.4, 12.2, 14)
    para(tf, "两人团队 · Git 协作", size=18, bold=True, color=BLUE, first=True, space_after=10)
    for t in [
        ("【姓名1·本人】组长：视觉模块 + Web后端 + 集成测试 + 报告", 14, False, DARK),
        ("【姓名2】成员：小程序端 + 管理端页面 + 数据库 + 测试与PPT", 14, False, DARK),
        ("质量保障：命名/注释规范（文件头含学号姓名）、交叉评审、Git 提交留痕、文档同步", 13.5, False, GRAY),
        ("周期：8 周，按里程碑检查进度", 13.5, False, GRAY),
    ]:
        para(tf, t[0], size=t[1], bold=t[2], color=t[3], bullet=True, space_after=12)


def slide_summary(prs, idx):
    s = blank(prs)
    header(s, "10 总结与展望", idx)
    tf = add_tb(s, 2.2, 3.2, 29.4, 13)
    para(tf, "系统特色", size=20, bold=True, color=BLUE, first=True, space_after=10)
    for t in [
        "三端联动、架构解耦：小程序 / Web管理端 / Python视觉服务 / 数据库+文件 完整闭环",
        "遮挡自动重检测：直方图质量校验 + 多尺度模板匹配 + 连续帧确认 → “丢了能找回”",
        "素材完整：视频与图片同一链路处理，两端都支持首帧拖拽框选目标",
        "工程化完整：JWT+角色鉴权+任务归属校验、BCrypt、异步状态机、失败留痕、Git 协作、规范文档",
        "轻量可复现：免深度学习训练、数据库内嵌免安装，普通 PC 双击即用",
    ]:
        para(tf, t, size=16.5, color=DARK, bullet=True, space_after=10)
    para(tf, "展望", size=20, bold=True, color=ORANGE, space_after=10)
    for t in [
        "引入 SiamRPN/ByteTrack 等深度跟踪器 + 在线模板更新，提升长时/形变遮挡鲁棒性",
        "接入 RTSP 摄像头直播流，实现真正实时跟踪",
        "框选交互增强（边角微调手柄）、结果图片一键下载、审计日志、Docker 一键部署",
    ]:
        para(tf, t, size=16.5, color=DARK, bullet=True, space_after=10)


def slide_end(prs):
    s = blank(prs)
    add_rect(s, 0, 0, 33.867, 19.05, BLUE)
    tf = add_tb(s, 2, 6.0, 29.8, 4)
    para(tf, "谢谢聆听 · 敬请指正", size=44, bold=True, color=WHITE,
         align=PP_ALIGN.CENTER, first=True)
    tf2 = add_tb(s, 2, 12.0, 29.8, 2)
    para(tf2, "【姓名1】 · 学号【学号1】　团队：【姓名2】",
         size=20, color=RGBColor(0xCF, 0xDD, 0xF2), align=PP_ALIGN.CENTER, first=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    prs = new_pres()
    n = 1
    slide_cover(prs, n); n += 1
    slide_toc(prs, n); n += 1
    slide_bg_goal(prs, n); n += 1
    slide_arch(prs, n); n += 1
    slide_flow(prs, n); n += 1
    slide_requirement(prs, n); n += 1
    slide_vision_design(prs, n); n += 1
    slide_vision_flow(prs, n); n += 1
    slide_recover(prs, n); n += 1
    slide_server(prs, n); n += 1
    slide_mini(prs, n); n += 1
    slide_effect_vision(prs, n); n += 1
    slide_effect_webuser(prs, n); n += 1
    slide_effect_web(prs, n); n += 1
    slide_test(prs, n); n += 1
    slide_mgmt(prs, n); n += 1
    slide_summary(prs, n); n += 1
    slide_end(prs)
    prs.save(OUT_FILE)
    print("PPT 已生成:", OUT_FILE, os.path.getsize(OUT_FILE), "bytes, slides:", n + 1)


if __name__ == "__main__":
    main()
