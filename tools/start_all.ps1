# ============================================================
# start_all.ps1 —— 综合实践III《单目标跟踪系统》一键启动（跨电脑可移植版）
# 作者：【姓名】  学号：【学号】  创建时间：2026-07
# 功能：
#   1) 检查 Python，缺失时尝试 winget 自动安装，否则给出指引；
#   2) 按 vision/requirements.txt 自动安装缺失的 Python 依赖（仅装缺的）；
#   3) 检查 Java 17；缺失时自动下载便携版 Temurin JRE 到 tools\jre（仅首次，约 45MB）；
#   4) 启动视觉服务(9000) 与 Web 后端(8080，内嵌 H2 数据库，无需 MySQL)；
#   5) 等待就绪后用默认浏览器打开指定页面。
# 用法：powershell -ExecutionPolicy Bypass -File start_all.ps1 -Open "http://localhost:8080/track.html"
# 参数：-Open 打开的网址；-Quiet 静默(自动化测试用，不暂停不弹浏览器)
# ============================================================
param(
    [string]$Open = "http://localhost:8080/",
    [switch]$Quiet,
    [string]$PythonPath = "",   # 可选：手动指定 python.exe（自动探测失败时使用）
    [string]$JavaPath = ""      # 可选：手动指定 java.exe（自动探测失败时使用）
)

$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "ZongShe3 - Single Object Tracking - Auto Start"

function Write-Step($msg) {
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
}
function Test-Port($port) {
    try {
        $conn = New-Object Net.Sockets.TcpClient
        $iar = $conn.BeginConnect("127.0.0.1", $port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(600)
        if ($ok -and $conn.Connected) { $conn.Close(); return $true }
        $conn.Close(); return $false
    } catch { return $false }
}
function Test-PythonExe($exe) {
    # 校验是否为"真"Python 解释器：
    # WindowsApps 下的 python.exe 只是微软应用商店别名，执行会打开商店而非解释器，必须排除。
    if (-not $exe -or -not (Test-Path $exe)) { return $false }
    if ($exe -like "*\WindowsApps\python*.exe") { return $false }
    try {
        $out = & $exe -c "import sys;print(sys.version_info[0])" 2>$null
        if ($LASTEXITCODE -eq 0 -and ("$out").Trim() -match '^\d+$') { return $true }
    } catch { }
    return $false
}

function Find-Python {
    # 依次尝试：PATH -> py 启动器 -> 注册表 -> 常见安装目录。
    # 目的：即使系统 PATH 未配置（或被人为写坏），也能自动定位 Python。
    foreach ($name in @("python", "python3")) {
        $c = Get-Command $name -ErrorAction SilentlyContinue
        if ($c -and (Test-PythonExe $c.Source)) { return $c.Source }
    }
    $launcher = (Get-Command py -ErrorAction SilentlyContinue).Source
    if ($launcher) {
        try {
            $out = & $launcher -3 -c "import sys;print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and (Test-PythonExe ("$out").Trim())) {
                return ("$out").Trim()
            }
        } catch { }
    }
    # 注册表：python.org 官方安装包会写入（用户级 HKCU / 机器级 HKLM），按版本号从高到低
    foreach ($hive in @("HKCU:\SOFTWARE\Python\PythonCore", "HKLM:\SOFTWARE\Python\PythonCore")) {
        $vers = Get-ChildItem $hive -ErrorAction SilentlyContinue | Sort-Object PSChildName -Descending
        foreach ($v in $vers) {
            $exe = (Get-ItemProperty "$($v.PSPath)\InstallPath" -ErrorAction SilentlyContinue).ExecutablePath
            if (Test-PythonExe $exe) { return $exe }
        }
    }
    # 常见安装目录（含非系统盘自定义安装，如 D:\Software\Python312）
    $roots = @("$env:ProgramFiles", "${env:ProgramFiles(x86)}",
               "$env:LOCALAPPDATA\Programs")
    foreach ($drv in (Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue |
                      Where-Object { $_.Name -match '^[A-Za-z]$' })) {
        $roots += (Join-Path $drv.Root "Software")
        $roots += $drv.Root
    }
    foreach ($r in $roots) {
        if (-not $r -or -not (Test-Path $r)) { continue }
        $cands = Get-ChildItem $r -Directory -ErrorAction SilentlyContinue |
                 Where-Object { $_.Name -match '^(?i)python' } | Sort-Object Name -Descending
        foreach ($c in $cands) {
            if (Test-PythonExe (Join-Path $c.FullName "python.exe")) {
                return (Join-Path $c.FullName "python.exe")
            }
            # 形如 ...\Python\Python312\python.exe
            $sub = Get-ChildItem $c.FullName -Directory -ErrorAction SilentlyContinue |
                   Where-Object { $_.Name -match '^(?i)python' } | Sort-Object Name -Descending
            foreach ($s in $sub) {
                if (Test-PythonExe (Join-Path $s.FullName "python.exe")) {
                    return (Join-Path $s.FullName "python.exe")
                }
            }
        }
    }
    return $null
}

function Get-JavaMajor($exe) {
    # 解析 `java -version` 的主版本号（兼容 1.8.0 与 17.0.x 两种写法），失败返回 0
    try {
        $line = (& $exe -version 2>&1 | Select-Object -First 1)
        if ("$line" -match 'version "(\d+)') {
            $major = [int]$Matches[1]
            if ($major -eq 1 -and "$line" -match 'version "1\.(\d+)') { return [int]$Matches[1] }
            return $major
        }
    } catch { }
    return 0
}

function Test-JavaExe($exe, $minMajor) {
    if (-not $exe -or -not (Test-Path $exe)) { return $false }
    return ((Get-JavaMajor $exe) -ge $minMajor)
}

function Resolve-Java($minMajor) {
    # 依次尝试：项目内便携 JRE -> JAVA_HOME -> PATH -> 注册表 -> 常见安装目录（要求 >= minMajor）
    $local = Join-Path $Tools "jre\bin\java.exe"
    if (Test-JavaExe $local $minMajor) { return $local }

    if ($env:JAVA_HOME) {
        $exe = Join-Path $env:JAVA_HOME "bin\java.exe"
        if (Test-JavaExe $exe $minMajor) { return $exe }
    }
    $c = Get-Command java -ErrorAction SilentlyContinue
    if ($c -and (Test-JavaExe $c.Source $minMajor)) { return $c.Source }

    foreach ($base in @("HKLM:\SOFTWARE\JavaSoft\JDK",
                        "HKLM:\SOFTWARE\JavaSoft\Java Development Kit",
                        "HKLM:\SOFTWARE\JavaSoft\Java Runtime Environment",
                        "HKLM:\SOFTWARE\JavaSoft\JRE")) {
        if (-not (Test-Path $base)) { continue }
        $keys = Get-ChildItem $base -ErrorAction SilentlyContinue | Sort-Object PSChildName -Descending
        foreach ($k in $keys) {
            $home2 = (Get-ItemProperty $k.PSPath -ErrorAction SilentlyContinue).JavaHome
            if ($home2 -and (Test-JavaExe (Join-Path $home2 "bin\java.exe") $minMajor)) {
                return (Join-Path $home2 "bin\java.exe")
            }
        }
    }

    $roots = @("$env:ProgramFiles\Eclipse Adoptium", "$env:ProgramFiles\Java",
               "$env:ProgramFiles\Microsoft", "${env:ProgramFiles(x86)}\Java",
               "$env:LOCALAPPDATA\Programs\Eclipse Adoptium")
    foreach ($drv in (Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue |
                      Where-Object { $_.Name -match '^[A-Za-z]$' })) {
        $roots += (Join-Path $drv.Root "Software")
    }
    foreach ($r in $roots) {
        if (-not $r -or -not (Test-Path $r)) { continue }
        $cands = Get-ChildItem $r -Directory -ErrorAction SilentlyContinue |
                 Where-Object { $_.Name -match '^(?i)(jdk|jre|java)' } | Sort-Object Name -Descending
        foreach ($c in $cands) {
            if (Test-JavaExe (Join-Path $c.FullName "bin\java.exe") $minMajor) {
                return (Join-Path $c.FullName "bin\java.exe")
            }
        }
    }
    return $null
}

# 脚本所在目录(tools\)，工程根目录为其上一级
$Tools = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root  = Split-Path -Parent $Tools
$VisionDir  = Join-Path $Root "01-代码\vision"
$VisionPy   = Join-Path $VisionDir "api_service.py"
$VisionReq  = Join-Path $VisionDir "requirements.txt"
$ServerDir  = Join-Path $Root "01-代码\server"
$JarFile    = Join-Path $ServerDir "target\track-server-1.0.0.jar"
$VisionOut  = Join-Path $Root "demo\vision_out"

Write-Host ""
Write-Host "  *** 综合实践III 单目标跟踪系统 一键启动 ***" -ForegroundColor Green
Write-Host "  工程目录: $Root"

# ---------- 1. Python ----------
Write-Step "第 1 步 / 4：Python 环境"
$py = ""
if ($PythonPath) {
    if (Test-PythonExe $PythonPath) { $py = $PythonPath }
    else { Write-Host "  [警告] -PythonPath 指定的解释器不可用: $PythonPath" -ForegroundColor Yellow }
}
if (-not $py) { $py = Find-Python }
if ($py) {
    Write-Host "  已找到 Python: $py" -ForegroundColor Green
} else {
    Write-Host "  未检测到 Python，尝试 winget 自动安装 ..." -ForegroundColor Yellow
    try {
        winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements | Out-Null
        # 安装后当前进程 PATH 不会自动刷新，需重新读取
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path", "User")
        $py = Find-Python
    } catch { }
    if (-not $py) {
        Write-Host "  [错误] Python 自动安装失败。" -ForegroundColor Red
        Write-Host "  请手动安装 Python 3.10+（https://www.python.org/downloads/），"
        Write-Host "  安装时勾选 Add python.exe to PATH，然后重新运行本脚本。"
        Write-Host "  若已安装但未被识别，可手动指定："
        Write-Host "    powershell -ExecutionPolicy Bypass -File tools\start_all.ps1 -PythonPath `"D:\path\to\python.exe`""
        if (-not $Quiet) { Read-Host "按回车退出" }
        exit 1
    }
}
Write-Host "  Python: $py"
& $py --version 2>&1 | Select-Object -First 1 | ForEach-Object { Write-Host "  $_" }

# ---------- 2. Python 依赖 ----------
Write-Step "第 2 步 / 4：Python 依赖（缺失时自动安装）"
# 注意：CSRT 跟踪器只存在于 opencv-contrib-python（非 contrib 版没有 cv2.legacy），
#       故此处必须装 contrib 版，且不能与 opencv-python 共存（二者共用 cv2 目录会互相覆盖）。
$need = @{
    "cv2" = "opencv-contrib-python>=4.8,<5"; "numpy" = "numpy"; "fastapi" = "fastapi";
    "uvicorn" = "uvicorn"; "multipart" = "python-multipart"; "imageio_ffmpeg" = "imageio-ffmpeg"
}
$missing = @()
foreach ($mod in $need.Keys) {
    & $py -c "import $mod" 2>$null
    if ($LASTEXITCODE -ne 0) { $missing += $need[$mod] }
}
# 关键功能检查：import cv2 成功并不代表能跟踪——必须确认 CSRT 真的可用
& $py -c "import cv2,sys;sys.exit(0 if (hasattr(cv2,'TrackerCSRT_create') or (hasattr(cv2,'legacy') and hasattr(cv2.legacy,'TrackerCSRT_create'))) else 1)" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OpenCV CSRT 跟踪器可用。" -ForegroundColor Green
} else {
    Write-Host "  当前 OpenCV 缺少 CSRT 跟踪器（多为装成了非 contrib 版），正在修正 ..." -ForegroundColor Yellow
    # 先卸载冲突包，避免 opencv-python 与 opencv-contrib-python 互相覆盖
    & $py -m pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless 2>$null | Out-Null
    $missing += "opencv-contrib-python>=4.8,<5"
}
$missing = @($missing | Select-Object -Unique)
if ($missing.Count -gt 0) {
    Write-Host "  正在安装缺失依赖: $($missing -join ', ') ..."
    & $py -m pip install --disable-pip-version-check -q $missing
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [错误] pip 安装失败，请检查网络后重试：" -ForegroundColor Red
        Write-Host "    `"$py`" -m pip install -r `"$VisionReq`""
        if (-not $Quiet) { Read-Host "按回车退出" }
        exit 1
    }
    Write-Host "  依赖安装完成。" -ForegroundColor Green
} else {
    Write-Host "  Python 依赖已全部就绪。" -ForegroundColor Green
}

# ---------- 3. Java ----------
Write-Step "第 3 步 / 4：Java 17（缺失时自动下载便携版）"
$java = ""
if ($JavaPath) {
    if (Test-JavaExe $JavaPath 17) { $java = $JavaPath }
    else { Write-Host "  [警告] -JavaPath 指定的 java 不可用或版本低于 17: $JavaPath" -ForegroundColor Yellow }
}
if (-not $java) { $java = Resolve-Java 17 }
if ($java) {
    Write-Host "  已找到 Java 17+: $java" -ForegroundColor Green
} else {
    Write-Host "  未检测到 Java 17，正在下载便携版 Temurin JRE（约 45MB，仅首次）..." -ForegroundColor Yellow
    $jreZip = Join-Path $Tools "jre17.zip"
    try {
        $url = "https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jre/hotspot/normal/eclipse"
        Invoke-WebRequest -Uri $url -OutFile $jreZip -UseBasicParsing
        $jreDir = Join-Path $Tools "jre"
        if (Test-Path $jreDir) { Remove-Item $jreDir -Recurse -Force }
        Expand-Archive -Path $jreZip -DestinationPath $jreDir -Force
        # 解压目录形如 jre\jdk-17.x+xx\bin\java.exe，上移一层到 jre\bin\java.exe
        $inner = Get-ChildItem $jreDir -Directory | Select-Object -First 1
        if ($inner -and (Test-Path (Join-Path $inner.FullName "bin\java.exe"))) {
            $tmp = Join-Path $Tools "jre_tmp"
            Move-Item $inner.FullName $tmp
            Remove-Item $jreDir -Recurse -Force -ErrorAction SilentlyContinue
            Move-Item $tmp $jreDir
        }
        Remove-Item $jreZip -Force -ErrorAction SilentlyContinue
        $java = Join-Path $jreDir "bin\java.exe"
        Write-Host "  便携版 JRE 就绪: $java" -ForegroundColor Green
    } catch {
        Write-Host "  [错误] JRE 下载失败：$($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  请手动安装 Java 17（https://adoptium.net/）后重新运行本脚本。"
        Write-Host "  若已安装但未被识别，可手动指定："
        Write-Host "    powershell -ExecutionPolicy Bypass -File tools\start_all.ps1 -JavaPath `"D:\path\to\java.exe`""
        if (-not $Quiet) { Read-Host "按回车退出" }
        exit 1
    }
}
Write-Host "  Java: $java"
& $java -version 2>&1 | Select-Object -First 1 | ForEach-Object { Write-Host "  $_" }

# ---------- 4. 启动服务并打开浏览器 ----------
Write-Step "第 4 步 / 4：启动视觉服务(9000) + Web 后端(8080)"
if (-not (Test-Path $JarFile)) {
    Write-Host "  [错误] 未找到后端 jar：$JarFile" -ForegroundColor Red
    Write-Host "  请先构建（需 Maven）：cd `"$ServerDir`" && mvn -DskipTests package"
    if (-not $Quiet) { Read-Host "按回车退出" }
    exit 1
}
if (Test-Port 9000) {
    Write-Host "  视觉服务已在运行（端口 9000），跳过启动。" -ForegroundColor Green
} else {
    Write-Host "  正在启动视觉服务：python api_service.py ..."
    Start-Process -FilePath $py -ArgumentList @(
        $VisionPy, "--host", "127.0.0.1", "--port", "9000", "--out_dir", $VisionOut
    ) -WorkingDirectory $VisionDir -WindowStyle Minimized
    $i = 0
    while (-not (Test-Port 9000) -and $i -lt 40) { Start-Sleep -Seconds 1; $i++ }
    if (Test-Port 9000) { Write-Host "  视觉服务就绪。状态页: http://127.0.0.1:9000/" -ForegroundColor Green }
    else { Write-Host "  [警告] 视觉服务 40 秒内未就绪，请查看其窗口。" -ForegroundColor Yellow }
}
if (Test-Port 8080) {
    Write-Host "  Web 后端已在运行（端口 8080），跳过启动。" -ForegroundColor Green
} else {
    Write-Host "  正在启动 Web 后端：java -jar track-server-1.0.0.jar（内嵌 H2 数据库，无需 MySQL）..."
    Start-Process -FilePath $java -ArgumentList @("-jar", $JarFile) `
        -WorkingDirectory $ServerDir -WindowStyle Minimized
    $i = 0
    while (-not (Test-Port 8080) -and $i -lt 60) { Start-Sleep -Seconds 1; $i++ }
    if (Test-Port 8080) { Write-Host "  Web 后端就绪。" -ForegroundColor Green }
    else { Write-Host "  [警告] Web 后端 60 秒内未就绪，请查看其窗口。" -ForegroundColor Yellow }
}

if (Test-Port 8080) {
    Write-Host ""
    Write-Host "  服务全部就绪："
    Write-Host "    系统首页   http://localhost:8080/"
    Write-Host "    网页检测端 http://localhost:8080/track.html"
    Write-Host "    Web 管理端 http://localhost:8080/admin.html  (admin / 123456)"
    Write-Host "    视觉服务   http://127.0.0.1:9000/            (状态页)"
    if ($Open -and -not $Quiet) {
        Write-Host "  正在打开浏览器: $Open" -ForegroundColor Green
        Start-Process $Open
    }
} else {
    Write-Host "  [错误] Web 后端未就绪，无法打开页面，请查看上方日志。" -ForegroundColor Red
}

if (-not $Quiet) {
    Write-Host ""
    Read-Host "按回车关闭本窗口（服务将继续在后台运行）"
}
