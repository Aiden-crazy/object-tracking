# ============================================================
# build_jar_nomaven.ps1 —— 在没有 Maven 的机器上重新打包后端 jar
#
# 背景：本工程随仓库附带已构建好的 track-server-1.0.0.jar（免 Maven 双击即用）。
#       但如果改了 Java 源码又没装 Maven，就没法重新打包。本脚本解决这个问题。
#
# 原理：Spring Boot fat jar 内部结构固定为
#         BOOT-INF/classes/  应用自己的 .class 与资源（application*.yml、static/**、db/*.sql）
#         BOOT-INF/lib/      44 个依赖 jar
#       于是可以把依赖 jar 解出来当 classpath、用 javac 直接编译源码，
#       再把新的 .class **以及 src/main/resources 下的全部资源**覆盖回 BOOT-INF/classes；
#       依赖 jar 原样不动。
#
# 注意 1：资源必须一起刷新！只更新 .class 的话，改了 admin.html / track.js / application.yml
#         这些文件不会生效（java -jar 运行时是从 jar 内的 classpath 读资源的，不是读源码目录）。
# 注意 2：源码里用了 Lombok。jar 内自带的 lombok-1.18.24 不支持 JDK 21，
#       会抛 NoSuchFieldError: JCTree$JCImport ... 'qualid'，
#       所以这里单独下载一个较新的 Lombok 作为 -processorpath。
#
# 用法：powershell -ExecutionPolicy Bypass -File tools\build_jar_nomaven.ps1
# ============================================================
param(
    [string]$JdkHome = "",          # 可选：JDK 路径，缺省自动探测
    [string]$LombokVersion = "1.18.36"
)

$ErrorActionPreference = 'Stop'

function Find-JdkBin {
    param([string]$Hint)
    if ($Hint) {
        $j = Join-Path $Hint 'bin\javac.exe'
        if (Test-Path $j) { return (Join-Path $Hint 'bin') }
    }
    foreach ($cand in @($env:JAVA_HOME,
                        'D:\Software\jdk-21', 'C:\Program Files\Java\jdk-21',
                        'C:\Program Files\Eclipse Adoptium\jdk-21*')) {
        if (-not $cand) { continue }
        $p = Join-Path $cand 'bin\javac.exe'
        if (Test-Path $p) { return (Join-Path $cand 'bin') }
    }
    $c = Get-Command javac -ErrorAction SilentlyContinue
    if ($c) { return (Split-Path -Parent $c.Source) }
    throw "找不到 javac，请安装 JDK 17+ 或用 -JdkHome 指定"
}

$Tools  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root   = Split-Path -Parent $Tools
$Server = Join-Path $Root '01-代码\server'
$Jar    = Join-Path $Server 'target\track-server-1.0.0.jar'
$SrcDir = Join-Path $Server 'src\main\java'
$Scratch = Join-Path $env:TEMP 'track-jarbuild'
$LombokDir = Join-Path $Tools 'lombok'
$LombokJar = Join-Path $LombokDir "lombok-$LombokVersion.jar"

if (-not (Test-Path $Jar)) { throw "找不到 jar: $Jar（请先确认工程完整）" }
$jdk = Find-JdkBin $JdkHome
Write-Host "[0] JDK: $jdk"

# ---------- 1) 备份原始 jar ----------
$Bak = "$Jar.orig"
if (-not (Test-Path $Bak)) {
    Copy-Item $Jar $Bak
    Write-Host "[1] 已备份原始 jar -> $Bak"
} else {
    Write-Host "[1] 备份已存在: $Bak"
}

# ---------- 2) 准备较新的 Lombok（编译期用，不进产品） ----------
if (-not (Test-Path $LombokJar)) {
    New-Item -ItemType Directory -Path $LombokDir -Force | Out-Null
    $url = "https://repo1.maven.org/maven2/org/projectlombok/lombok/$LombokVersion/lombok-$LombokVersion.jar"
    Write-Host "[2] 下载 Lombok $LombokVersion ..."
    $ProgressPreference = 'SilentlyContinue'
    try {
        Invoke-WebRequest $url -OutFile $LombokJar -UseBasicParsing
    } catch {
        throw "Lombok 下载失败（需要联网一次）: $($_.Exception.Message)"
    }
} else {
    Write-Host "[2] Lombok 已存在: $LombokJar"
}

# ---------- 3) 解出依赖 jar 作 classpath ----------
if (Test-Path $Scratch) { Remove-Item $Scratch -Recurse -Force }
New-Item -ItemType Directory -Path $Scratch | Out-Null
Push-Location $Scratch
& "$jdk\jar.exe" xf $Jar 'BOOT-INF/lib'
Pop-Location
$libs = Get-ChildItem (Join-Path $Scratch 'BOOT-INF\lib') -Filter *.jar
Write-Host "[3] 解出依赖 jar: $($libs.Count) 个"
$cp = ($libs.FullName) -join ';'

# ---------- 4) 编译 + 刷新资源 ----------
$srcs = (Get-ChildItem $SrcDir -Recurse -Filter *.java).FullName
$stage = Join-Path $Scratch 'stage\BOOT-INF\classes'
New-Item -ItemType Directory -Path $stage -Force | Out-Null
Write-Host "[4] 编译 $($srcs.Count) 个源文件 ..."
# -encoding UTF-8 必须：源码含中文注释，缺省按 GBK 读会报错
# -parameters 必须：Spring MVC 的 @PathVariable/@RequestParam 未显式写名字时依赖
#   方法参数名，缺少它会报
#   "Name for argument of type [...] not specified, and parameter name information
#    not found in class file"。Maven 的 spring-boot-starter-parent 默认带该参数。
& "$jdk\javac.exe" -encoding UTF-8 -parameters --release 17 -nowarn `
    -cp $cp -processorpath $LombokJar -d $stage $srcs
if ($LASTEXITCODE -ne 0) { throw "javac 编译失败（退出码 $LASTEXITCODE）" }
Write-Host "    生成 $((Get-ChildItem $stage -Recurse -Filter *.class).Count) 个 class"

# 资源（application*.yml、db/*.sql、static/** 等）一起打包，
# 否则改了前端页面/配置后打出的 jar 仍是旧内容。
$ResDir = Join-Path $Server 'src\main\resources'
$resFiles = Get-ChildItem $ResDir -Recurse -File
foreach ($f in $resFiles) {
    $rel = $f.FullName.Substring($ResDir.Length + 1)
    $dst = Join-Path $stage $rel
    $dstDir = Split-Path -Parent $dst
    if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
    Copy-Item $f.FullName $dst -Force
}
Write-Host "    刷新资源 $($resFiles.Count) 个（含 static 前端页面与 application*.yml）"

# ---------- 5) 覆盖回 jar 并校验 ----------
$tmp = Join-Path $Scratch 'rebuilt.jar'
Copy-Item $Jar $tmp
Push-Location $Scratch
& "$jdk\jar.exe" uf $tmp -C (Join-Path $Scratch 'stage') BOOT-INF
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { throw "jar 更新失败（退出码 $code）" }

$entries = & "$jdk\jar.exe" tf $tmp
foreach ($need in 'BOOT-INF/classes/application.yml',
                 'BOOT-INF/classes/db/schema-h2.sql',
                 'BOOT-INF/classes/static/track.html',
                 'BOOT-INF/classes/static/js/track.js') {
    if (-not ($entries | Where-Object { $_ -like "$need*" })) {
        throw "新 jar 丢了资源: $need"
    }
}
$libCount = ($entries | Where-Object { $_ -match '^BOOT-INF/lib/.*\.jar$' }).Count
Write-Host "[5] 结构校验通过：资源齐全，依赖 jar $libCount 个"

Copy-Item $tmp $Jar -Force
Write-Host "[6] 完成 -> $Jar"
Write-Host ""
Write-Host "    回滚：Copy-Item `"$Bak`" `"$Jar`" -Force"
