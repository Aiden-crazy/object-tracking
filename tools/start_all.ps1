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
    [switch]$Quiet
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
function Resolve-Java {
    # 依次尝试：项目内便携 JRE(17) -> 系统 java(要求 17+)
    $local = Join-Path $Tools "jre\bin\java.exe"
    if (Test-Path $local) { return $local }
    $sys = (Get-Command java -ErrorAction SilentlyContinue).Source
    if ($sys) {
        try {
            $verLine = (& $sys -version 2>&1 | Select-Object -First 1)
            if ($verLine -match 'version "(\d+)') {
                $major = [int]$Matches[1]
                if ($major -ge 17) { return $sys }
                Write-Host "  [提示] 系统 Java 版本过低（$verLine），将使用便携版 JRE 17。" -ForegroundColor Yellow
            }
        } catch { }
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
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    Write-Host "  未检测到 Python，尝试 winget 自动安装 ..." -ForegroundColor Yellow
    try {
        winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements | Out-Null
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path", "User")
        $py = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
    } catch {
        Write-Host "  [错误] Python 自动安装失败。" -ForegroundColor Red
        Write-Host "  请手动安装 Python 3.10+（https://www.python.org/downloads/），"
        Write-Host "  安装时勾选 Add python.exe to PATH，然后重新运行本脚本。"
        if (-not $Quiet) { Read-Host "按回车退出" }
        exit 1
    }
}
if (-not $py) { $py = "python" }
Write-Host "  Python: $py"
& $py --version 2>&1 | Select-Object -First 1 | ForEach-Object { Write-Host "  $_" }

# ---------- 2. Python 依赖 ----------
Write-Step "第 2 步 / 4：Python 依赖（缺失时自动安装）"
$need = @{
    "cv2" = "opencv-python"; "numpy" = "numpy"; "fastapi" = "fastapi";
    "uvicorn" = "uvicorn"; "multipart" = "python-multipart"; "imageio_ffmpeg" = "imageio-ffmpeg"
}
$missing = @()
foreach ($mod in $need.Keys) {
    & $py -c "import $mod" 2>$null
    if ($LASTEXITCODE -ne 0) { $missing += $need[$mod] }
}
if ($missing.Count -gt 0) {
    Write-Host "  正在安装缺失依赖: $($missing -join ', ') ..."
    & $py -m pip install --disable-pip-version-check -q $missing
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [错误] pip 安装失败，请检查网络后重试：" -ForegroundColor Red
        Write-Host "    python -m pip install -r `"$VisionReq`""
        if (-not $Quiet) { Read-Host "按回车退出" }
        exit 1
    }
    Write-Host "  依赖安装完成。" -ForegroundColor Green
} else {
    Write-Host "  Python 依赖已全部就绪。" -ForegroundColor Green
}

# ---------- 3. Java ----------
Write-Step "第 3 步 / 4：Java 17（缺失时自动下载便携版）"
$java = Resolve-Java
if (-not $java) {
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
