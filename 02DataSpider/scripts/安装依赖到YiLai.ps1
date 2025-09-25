# NeuroTrade Nexus - 模组二依赖安装脚本
# 安装到D:\YiLai\pydeps目录
# 环境标准：Python 3.11 LTS

param(
    [string]$YiLaiDir = "D:\YiLai",
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=== NeuroTrade Nexus 模组二依赖安装脚本 ===" -ForegroundColor Green
Write-Host "目标目录: $YiLaiDir\pydeps" -ForegroundColor Cyan
Write-Host "Python版本要求: 3.11 LTS" -ForegroundColor Cyan

# 检查Python版本
$pythonVersion = python --version 2>&1
Write-Host "当前Python版本: $pythonVersion" -ForegroundColor Yellow

if ($pythonVersion -notmatch "Python 3\.11") {
    Write-Host "警告: 检测到非Python 3.11版本，可能存在兼容性问题" -ForegroundColor Red
}

# 创建目标目录
$targetDir = Join-Path $YiLaiDir "pydeps"
if (-not (Test-Path $targetDir)) {
    Write-Host "创建目录: $targetDir" -ForegroundColor Green
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
} else {
    Write-Host "目录已存在: $targetDir" -ForegroundColor Yellow
    if ($Force) {
        Write-Host "强制模式：清理现有依赖..." -ForegroundColor Red
        Remove-Item -Path "$targetDir\*" -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# 检查requirements.txt
$requirementsFile = "requirements.txt"
if (-not (Test-Path $requirementsFile)) {
    Write-Error "未找到requirements.txt文件"
    exit 1
}

Write-Host "开始安装依赖到: $targetDir" -ForegroundColor Green

try {
    # 使用--only-binary=:all:强制使用预编译轮子，避免源码构建
    python -m pip install --only-binary=:all: --target="$targetDir" --upgrade --no-deps -r $requirementsFile

    Write-Host "依赖安装完成！" -ForegroundColor Green
    
    # 显示安装统计
    $installedPackages = Get-ChildItem -Path $targetDir -Directory | Measure-Object
    Write-Host "已安装包数量: $($installedPackages.Count)" -ForegroundColor Cyan
    
    # 验证关键依赖
    $criticalDeps = @("flask", "zmq", "scrapy", "redis", "numpy", "pandas")
    Write-Host "验证关键依赖..." -ForegroundColor Yellow
    
    foreach ($dep in $criticalDeps) {
        $depPath = Get-ChildItem -Path $targetDir -Directory -Name "*$dep*" | Select-Object -First 1
        if ($depPath) {
            Write-Host "✓ $dep -> $depPath" -ForegroundColor Green
        } else {
            Write-Host "✗ 未找到: $dep" -ForegroundColor Red
        }
    }
    
} catch {
    Write-Error "依赖安装失败: $($_.Exception.Message)"
    Write-Host "建议检查:" -ForegroundColor Red
    Write-Host "1. Python版本是否为3.11" -ForegroundColor Red
    Write-Host "2. 网络连接是否正常" -ForegroundColor Red
    Write-Host "3. 磁盘空间是否充足" -ForegroundColor Red
    exit 1
}

Write-Host "=== 安装完成 ===" -ForegroundColor Green
Write-Host "请确保应用入口已配置sys.path.insert(0, '$targetDir')" -ForegroundColor Cyan