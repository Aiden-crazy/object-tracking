# 综合实践III《单目标跟踪系统》课程设计 —— 工程与文档说明

> 系统：**单目标跟踪系统的设计与实现**（网页检测端 + 微信小程序 + Web管理端 + Spring Boot + Python/OpenCV）
> 作者：【姓名1】学号【学号1】｜【姓名2】学号【学号2】｜指导教师：罗颂、罗娅、贺筠

---

## ⭐ 在任何电脑上跑通（传给同学/换电脑必读）

把整个文件夹（或从 GitHub `git clone` 后）发给同学，**只需三步**：

1. **装 Python 3.10+**（https://www.python.org/downloads/ ，安装时勾选 *Add python.exe to PATH*）
2. **双击 `启动-网页检测端.bat`**（或 `启动-管理端.bat`）
   > 若中文文件名在你的系统/解压工具中显示异常，请用英文别名脚本：`Start-Detect-Page.bat` / `Start-Admin.bat`
3. 等待窗口提示"服务全部就绪"，**浏览器自动打开**

> 📁 四个启动脚本都在**仓库最外层根目录**（与 README.md 同一层，解压/克隆后即在该文件夹根目录）。

启动脚本会自动完成以下事情（无需手动敲任何命令）：
- ✅ 检查 Python，缺失时尝试 `winget` 自动安装；
- ✅ 按 `01-代码/vision/requirements.txt` **自动安装缺失的 Python 依赖**（opencv/fastapi/imageio-ffmpeg 等）；
- ✅ 检查 Java 17，缺失时**自动下载便携版 Temurin JRE**（约 45MB，仅首次，保存于 `tools\jre`）；
- ✅ 启动视觉服务(9000) + Web 后端(8080)；
- ✅ **数据库使用内嵌 H2**（免安装 MySQL，数据库文件自动生成，重启数据不丢失）；
- ✅ 服务已运行时自动跳过启动，直接打开浏览器。

> 无 Java 环境也能跑：脚本会自动下载便携 JRE；也可以自备任意 Java 17（JDK/JRE 均可）。

### 同学之间快速联调（可选）
把工程跑在一台电脑上，其他同学直接用浏览器访问
`http://<该电脑局域网IP>:8080/track.html` 即可测试（无需各自装环境）。
注意：小程序与网页中的 `127.0.0.1` 需改为该电脑局域网 IP（track.js 用相对路径无需改，
后端默认监听所有网卡；Windows 首次会弹出防火墙询问，请允许）。

---

## 目录结构

```
综设3-单目标跟踪/
├── 启动-网页检测端.bat / Start-Detect-Page.bat   # ★ 双击启动（检测端，自动开浏览器+装依赖）
├── 启动-管理端.bat / Start-Admin.bat             # ★ 双击启动（管理端，英文名为兼容别名）
├── 01-代码/
│   ├── vision/              # 视觉处理模块（Python + OpenCV + FastAPI）
│   │   ├── tracker.py           # 跟踪器核心：CSRT + 遮挡检测/重检测状态机 + 图片定位
│   │   ├── gui_track.py         # 本地交互演示（鼠标框选目标/摄像头）
│   │   ├── api_service.py       # FastAPI 视觉服务（端口 9000，含状态首页）
│   │   ├── make_demo_video.py   # 合成测试视频（--no_wall 生成无遮挡对照视频）
│   │   ├── requirements.txt     # Python 依赖清单（脚本自动安装）
│   │   └── extract_screens.py   # 从结果视频抽取报告截图
│   ├── server/              # Web 后端 Spring Boot 3（端口 8080，默认内嵌 H2）
│   │   ├── sql/init.sql         # （可选 MySQL 版建库脚本）
│   │   ├── src/main/resources/
│   │   │   ├── application.yml           # 默认 profile=h2
│   │   │   ├── application-h2.yml        # 内嵌 H2（默认，免安装）
│   │   │   ├── application-mysql.yml     # 可选 MySQL 8
│   │   │   ├── db/schema-h2.sql          # H2 自动建表（每次启动幂等执行）
│   │   │   └── static/                   # 系统首页/网页检测端/管理端页面
│   │   └── target/track-server-1.0.0.jar # 已构建可执行 jar（跨电脑免构建）
│   └── miniprogram/         # 微信小程序端
├── 02-文档/                  # 课程设计报告 docx + 预览 PDF
├── 03-答辩PPT/               # 答辩 PPT
├── demo/                    # 测试素材与截图/示意图（vision_out 为运行产物不入仓）
│   ├── demo_ball_track.mp4      # 场景B：含遮挡墙的合成视频（遮挡恢复测试）
│   ├── demo_ball_seamless.mp4   # 场景A：同规格无遮挡对照视频
│   └── demo_test_image.png      # 图片素材链路测试图片
├── tools/                   # 生成脚本 + 一键启动 + 回归测试
│   ├── start_all.ps1             # 一键启动逻辑（环境探测/装依赖/起服务）
│   ├── build_jar_nomaven.ps1     # 无 Maven 环境下重新打包 jar
│   ├── regression_test.py        # 全链路接口回归测试（50 项断言，退出码可直接用）
│   ├── gen_report.py 等          # 报告/PPT/示意图生成脚本
├── .gitignore / .gitattributes
└── README.md
```

---

## 手动启动方式（等价于双击脚本，便于调试）

### 第 1 步：安装/校验环境
```bash
# Python 依赖（脚本会自动装，手动时执行）
pip install -r 01-代码/vision/requirements.txt
#   ↑ 注意：跟踪算法基于 CSRT 跟踪器，必须用 opencv-contrib-python（不是 opencv-python）。
#     requirements.txt 已锁定 `opencv-contrib-python>=4.8,<5`：非 contrib 版没有
#     cv2.legacy/CSRT，OpenCV 5.0 起 CSRT 已被彻底移除。
#     （该文件首行的 `# -*- coding: utf-8 -*-` 请勿删除：缺它时中文 Windows 下 pip
#       会按 GBK 解码而报 UnicodeDecodeError。）
# Java 17+（JDK/JRE 均可）；MySQL 不再需要（默认 H2）
```

### 第 2 步：启动视觉服务（9000）
```bash
cd 01-代码/vision
python api_service.py --host 127.0.0.1 --port 9000 --out_dir ../../demo/vision_out
```

### 第 3 步：启动 Web 后端（8080，内嵌 H2）
```bash
cd 01-代码/server
java -jar target/track-server-1.0.0.jar
```
首次启动自动建库建表并创建管理员 **admin / 123456**。

> 改用 MySQL（可选）：先执行 `sql/init.sql`，再
> `java -jar target/track-server-1.0.0.jar --spring.profiles.active=mysql`。

### 第 4 步：打开页面
| 页面 | 地址 |
|---|---|
| 系统首页 | `http://localhost:8080/` |
| **网页检测端** | `http://localhost:8080/track.html`（拖拽/粘贴视频或图片→首帧框选/自动目标→检测→回看） |
| Web 管理端 | `http://localhost:8080/admin.html`（admin / 123456） |
| 视觉状态页 | `http://127.0.0.1:9000/`（含接口文档 /docs） |
| 小程序端 | 微信开发者工具导入 `01-代码/miniprogram` |

---

## 默认账号
| 端 | 账号 | 密码 |
|---|---|---|
| Web 管理端 | admin | 123456 |
| 网页检测端 | webdemo（自动登录体验账号） | 123456 |
| 小程序端 | 需注册 | — |

---

## 提交前必须完成的替换（重要！）

1. **报告 docx** 全文查找替换：`【姓名1】/【学号1】/【姓名2】/【学号2】/【班级】` → 真实信息；
   替换后 Word 中目录右键 **更新域**（F9）。
2. **代码文件头注释**（vision/*.py、server Java、miniprogram js、tools/*.py 等）：
   已标注 `作者：【姓名】 学号：【学号】`，一并替换。
3. **答辩 PPT**：替换封面/分工页占位姓名学号。
4. **小程序界面截图**：报告图3-15~3-17 为界面原型示意，请在微信开发者工具运行后替换。
5. **Git 协作留痕**：报告表2-3 为示例提交记录；本仓库已 `git init` 并完成首次提交，
   团队继续开发时按实际过程提交即可。

---

## Git 使用

```bash
# 本机仓库已初始化并完成首次提交（提交信息见 git log）

# 关联你的 GitHub 远程仓库（先到 github.com 新建空仓库，复制其 URL）
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main
# 之后同学即可：git clone https://github.com/<你的用户名>/<仓库名>.git
```

---

## 系统自测（回归测试，可留作测试证据）

系统启动后（双击 `启动-网页检测端.bat` 即可），在工程根目录执行：

```bash
python tools/regression_test.py
```

脚本会自动走完 50 项端到端断言：视觉服务健康检查、注册/登录/改密/弱口令、
视频两段式流程（提首帧 → 框选 → start → 结果视频）、图片素材流程（→ 结果图片）、
任务归属越权校验（他人任务返回 403）、管理端用户增删查改与统计、视觉服务
prepare/track_local 等。全部通过时退出码为 0，可直接用于答辩演示前的自检：

```
汇总：通过 50 项，失败 0 项
```

> 测局域网上的那台机器：`python tools/regression_test.py --base http://10.100.0.36:8080`
> 视觉模块单独的专项测试（场景A无遮挡/场景B遮挡恢复/图片链路）见报告表4-3，可用
> `python 01-代码/vision/tracker.py --video demo/demo_ball_track.mp4 --out_dir demo/vision_out`
> 与 `--video demo/demo_ball_seamless.mp4` 复现。

---

## 验收自检（对照《综合实践III任务书》）

| 任务书要求 | 本工程对应 | 状态 |
|---|---|---|
| Web 开发（管理端） | server/static admin.html + /api/admin/** | ✅ |
| 移动开发（小程序端） | miniprogram/（6页面） | ✅ |
| 机器视觉（核心处理） | vision/ CSRT跟踪+遮挡重检测 | ✅ |
| 用户管理：注册/改密、删除/重置密码 | t_user + 对应接口 | ✅ |
| 图片/视频的存储与查询 | t_task(media_type VIDEO/IMAGE) + uploads 存储 + /files 访问 + 历史回看 | ✅ |
| 用户提交**图片或者视频** | 两种素材同一链路：视频→结果视频，图片→标注结果图 | ✅ |
| 用户从摄像头画面或视频中**框出目标对象** | 小程序/网页端首帧拖拽框选；本地 gui_track.py 支持 `--video` 与 `--camera 0` | ✅ |
| 提交→服务端处理→结果返回→入库→管理 | 全链路实测通过（tools/regression_test.py 50/50） | ✅ |
| 目标特征提取与识别 | 首帧目标区域灰度模板 + HSV 二维直方图特征模型 | ✅ |
| 遮挡后能再次捕捉继续跟踪 | 实测 丢失1次(第199帧)→自动找回1次(第262帧)→跟踪至结束 | ✅ |
| 界面展示 | 网页检测端 + 管理端 + 小程序 + 视觉GUI | ✅ |
| 命名规范、注释含学号姓名 | 文件头注释（替换占位后生效） | ✅ |
| 团队2人分工 + 版本控制 | 报告2.1 + Git 仓库（已提交） | ✅ |
| 报告每人一份 + 源码 + 答辩PPT | 02-文档/ 03-答辩PPT/ 01-代码/ | ✅ |
| 跨电脑可移植（免MySQL免构建） | H2 内嵌库 + 已打包 jar + 双击脚本自动装依赖 | ✅ |

---

## 常见问题

- **页面打不开 / "崩溃页" / 连接失败**：几乎都是后端服务停止了。双击启动脚本即可自动恢复
  （脚本检测端口，未运行则拉起并打开浏览器）。
- **网页里点"提取首帧"没反应 / 结果视频黑屏**：视频编码问题。浏览器只支持 H.264 等格式，
  本项目结果视频已自动转码 H.264；源视频若无法预览取帧请用 mp4(H.264)（手机拍的通常可以），
  或直接使用"自动目标"检测。依赖 `pip install imageio-ffmpeg`（脚本会自动装）。
- **上传图片会怎样**：图片素材不需要"提首帧"，选好后直接进入框选步骤（图片本身即首帧），
  提交后输出的是一张标注了目标框的结果图片（`*_tracked.jpg`）；此时没有"运动"信息，
  自动目标回退为画面中央区域，建议手动框选。
- **任务列表里能看到别人的任务吗**：不能。`/api/task/{id}` 与 `/api/task/{id}/start`
  都会校验任务归属，访问他人任务返回 403；管理员可在管理端查看全部任务。
- **双击脚本提示 Python/Java 缺失**：脚本会自动安装/下载；若失败请按提示手动安装
  Python 3.10+（勾选 Add to PATH）或 Java 17（adoptium.net），再双击一次。
- **明明装了 Python/Java，脚本却说找不到**：启动脚本已不依赖 PATH，会依次自动探测
  PATH → `py` 启动器 → 注册表 → `JAVA_HOME` → 常见安装目录（含 `D:\Software\...`
  这类自定义路径）。若仍未识别，可手动指定：
  `powershell -ExecutionPolicy Bypass -File tools\start_all.ps1 -PythonPath "D:\...\python.exe" -JavaPath "D:\...\java.exe"`
- **任务失败并提示"无法创建跟踪器"**：OpenCV 装成了非 contrib 版（`import cv2` 正常，
  但没有 CSRT）。修复：
  `pip uninstall -y opencv-python opencv-python-headless` 然后
  `pip install "opencv-contrib-python>=4.8,<5"`；再次运行启动脚本会自动修正。
- **第一次双击脚本 Windows 弹"安全警告"**：点"仍要运行"。
- **同学局域网访问不了**：确认双方同网段、防火墙允许 Java/Python 通信（弹出询问时点允许），
  浏览器访问 `http://<运行电脑IP>:8080/track.html`。
- **文件选择框默认目录是别的文件夹**：系统记忆"上次打开位置"，网页无法指定；直接把视频
  **拖进网页虚线框**最方便。
