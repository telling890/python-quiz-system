# ============================================================================
#  Python 刷题系统 · 网页版一键启动
#  用法：双击仓库根目录的「启动网页版.bat」（它只是调用本脚本）
#       或者直接在 PowerShell 里跑：powershell -ExecutionPolicy Bypass -File start_web.ps1
#
#  做三件事：
#    1. 前端没构建过 → 自动 npm install + npm run build
#    2. 后端没起来   → 新开一个窗口跑 uvicorn（127.0.0.1:8000）
#    3. 等服务就绪   → 用默认浏览器打开 http://127.0.0.1:8000/
# ============================================================================

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$url = 'http://127.0.0.1:8000/'
$healthUrl = 'http://127.0.0.1:8000/healthz'

function Test-ServerUp {
    try {
        return (Invoke-WebRequest $healthUrl -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200
    } catch {
        return $false
    }
}

function Fail($message) {
    Write-Host ''
    Write-Host "  [错误] $message" -ForegroundColor Red
    Write-Host ''
    exit 1
}

Write-Host ''
Write-Host '  ============================================'
Write-Host '   Python 刷题系统 · 网页版'
Write-Host "   地址: $url  （自动进入新前端）"
Write-Host '   旧版页面: http://127.0.0.1:8000/legacy'
Write-Host '  ============================================'
Write-Host ''

# ---------------------------------------------------------------- 1. 前端产物
$distIndex = Join-Path $frontend 'dist\index.html'
if (Test-Path $distIndex) {
    Write-Host '  [1/3] 前端已构建: frontend\dist'
} else {
    Write-Host '  [1/3] 还没构建前端，先构建一次（第一次要装依赖，约 1~3 分钟）...'
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Fail "没找到 npm。装个 Node.js 18+（https://nodejs.org/）再试，或者直接打开 http://127.0.0.1:8000/legacy 用旧版页面。"
    }
    Push-Location $frontend
    try {
        & npm install --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { Fail 'npm install 失败（看上面的报错）' }
        & npm run build
        if ($LASTEXITCODE -ne 0) { Fail '前端构建失败（看上面的报错）' }
    } finally {
        Pop-Location
    }
}

# ---------------------------------------------------------------- 2. 后端服务
if (Test-ServerUp) {
    Write-Host '  [2/3] 后端已经在跑，不用重启'
} else {
    Write-Host '  [2/3] 启动后端服务（会新开一个窗口，关掉它=停止服务）...'
    if (-not (Test-Path (Join-Path $backend 'app\main.py'))) {
        Fail "没有找到 backend\app\main.py，确认这个脚本放在仓库根目录。"
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $exe = 'py'
        $cmdArgs = @('-3.10', '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000')
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $exe = 'python'
        $cmdArgs = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000')
    } else {
        Fail '没找到 Python。装 Python 3.10+ 再试。'
    }
    Start-Process -FilePath $exe -ArgumentList $cmdArgs -WorkingDirectory $backend | Out-Null
}

# ---------------------------------------------------------------- 3. 等就绪 + 开浏览器
Write-Host '  [3/3] 等待服务就绪...'
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    if (Test-ServerUp) { $ready = $true; break }
    Start-Sleep -Milliseconds 500
}
if (-not $ready) {
    Fail '后端 30 秒内没起来。看那个新开的「后端」窗口里的报错（常见：没装 Python 3.10 / 端口 8000 被占用 / 依赖没装）。'
}

if ($env:QUIZ_NO_BROWSER -eq '1') {
    Write-Host "  服务已就绪（QUIZ_NO_BROWSER=1，没有自动打开浏览器）: $url"
} else {
    Start-Process $url | Out-Null
    Write-Host ''
    Write-Host "  已在浏览器打开: $url" -ForegroundColor Green
}

Write-Host ''
Write-Host '  演示账号 demo_student / demo12345，也可以直接注册。'
Write-Host '  快捷键：刷题页 Ctrl+Enter 判题；自由编程页 Ctrl+S 存草稿。'
Write-Host ''
exit 0
