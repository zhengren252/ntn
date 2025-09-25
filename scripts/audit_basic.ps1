# NeuroTrade Nexus V1.4 协议审计脚本 (基础版)

$StartTime = Get-Date
$PassCount = 0
$FailCount = 0

Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  NeuroTrade Nexus V1.4 协议审计开始" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

# 检查前置条件
Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  检查前置条件" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

# 检查curl
$curlTest = Get-Command curl -ErrorAction SilentlyContinue
if ($curlTest) {
    Write-Host "[PASS] curl工具可用" -ForegroundColor Green
    $PassCount++
} else {
    Write-Host "[FAIL] curl工具不可用" -ForegroundColor Red
    $FailCount++
}

# 检查Node.js
$nodeTest = Get-Command node -ErrorAction SilentlyContinue
if ($nodeTest) {
    $nodeVersion = node --version
    Write-Host "[PASS] Node.js可用: $nodeVersion" -ForegroundColor Green
    $PassCount++
} else {
    Write-Host "[FAIL] Node.js不可用" -ForegroundColor Red
    $FailCount++
}

# 检查SSH
$sshTest = Get-Command ssh -ErrorAction SilentlyContinue
if ($sshTest) {
    Write-Host "[PASS] SSH工具可用" -ForegroundColor Green
    $PassCount++
} else {
    Write-Host "[FAIL] SSH工具不可用" -ForegroundColor Red
    $FailCount++
}

# 检查虚拟机Docker环境
Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  检查虚拟机Docker环境" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

$vmHost = "192.168.1.7"
$vmUser = "tjsga"

Write-Host "[INFO] 测试虚拟机SSH连接: $vmUser@$vmHost" -ForegroundColor Cyan

# 测试SSH连接 - 简化版本
$sshResult = ssh -o ConnectTimeout=10 -o BatchMode=yes $vmUser@$vmHost "echo connected" 2>$null
if ($sshResult -eq "connected") {
    Write-Host "[PASS] 虚拟机SSH连接成功" -ForegroundColor Green
    $PassCount++
    
    # 检查Docker
    $dockerVersion = ssh -o ConnectTimeout=10 $vmUser@$vmHost "docker --version" 2>$null
    if ($dockerVersion) {
        Write-Host "[PASS] 虚拟机Docker可用: $dockerVersion" -ForegroundColor Green
        $PassCount++
    } else {
        Write-Host "[FAIL] 虚拟机Docker不可用" -ForegroundColor Red
        $FailCount++
    }
    
    # 检查Docker服务
    $dockerStatus = ssh -o ConnectTimeout=10 $vmUser@$vmHost "systemctl is-active docker" 2>$null
    if ($dockerStatus -eq "active") {
        Write-Host "[PASS] 虚拟机Docker服务运行中" -ForegroundColor Green
        $PassCount++
    } else {
        Write-Host "[FAIL] 虚拟机Docker服务未运行" -ForegroundColor Red
        $FailCount++
    }
    
} else {
    Write-Host "[FAIL] 虚拟机SSH连接失败" -ForegroundColor Red
    $FailCount++
}

# 模块审计
Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  模块级静态审计" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

$modules = @(
    "01APIForge",
    "02DataSpider", 
    "03ScanPulse",
    "04OptiCore",
    "05-07TradeGuard",
    "08NeuroHub",
    "09MMS",
    "10ReviewGuard",
    "11ASTS Console",
    "12TACoreService",
    "13AI Strategy Assistant",
    "14Observability Center"
)

foreach ($module in $modules) {
    Write-Host "[INFO] 审计模块: $module" -ForegroundColor Cyan
    
    if (Test-Path $module) {
        # 检查Dockerfile
        if (Test-Path "$module\Dockerfile") {
            Write-Host "[PASS] $module - Dockerfile存在" -ForegroundColor Green
            $PassCount++
        } else {
            Write-Host "[FAIL] $module - Dockerfile不存在" -ForegroundColor Red
            $FailCount++
        }
        
        # 检查package.json
        if (Test-Path "$module\package.json") {
            Write-Host "[PASS] $module - package.json存在" -ForegroundColor Green
            $PassCount++
        }
        
        # 检查requirements.txt
        if (Test-Path "$module\requirements.txt") {
            Write-Host "[PASS] $module - requirements.txt存在" -ForegroundColor Green
            $PassCount++
        }
        
    } else {
        Write-Host "[FAIL] 模块目录 $module 不存在" -ForegroundColor Red
        $FailCount++
    }
}

# 集成测试
Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  系统集成验证" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

$vmProjectPath = "~/projects"

# 检查虚拟机上的docker-compose文件
Write-Host "[INFO] 检查虚拟机docker-compose文件" -ForegroundColor Cyan
$composeCheck = ssh -o ConnectTimeout=10 $vmUser@$vmHost "test -f $vmProjectPath/docker-compose.prod.yml; echo `$?" 2>$null

if ($composeCheck -eq "0") {
    Write-Host "[PASS] 虚拟机Docker Compose配置文件存在" -ForegroundColor Green
    $PassCount++
} else {
    Write-Host "[FAIL] 虚拟机上未找到Docker Compose配置文件" -ForegroundColor Red
    $FailCount++
}

# 检查容器状态
Write-Host "[INFO] 检查虚拟机容器状态" -ForegroundColor Cyan
$containerCount = ssh -o ConnectTimeout=10 $vmUser@$vmHost "cd $vmProjectPath; docker ps -q | wc -l" 2>$null

if ($containerCount -and [int]$containerCount -gt 0) {
    Write-Host "[PASS] 虚拟机上发现 $containerCount 个运行中的容器" -ForegroundColor Green
    $PassCount++
} else {
    Write-Host "[WARN] 虚拟机上未发现运行中的容器" -ForegroundColor Yellow
}

# 生成最终报告
Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  V1.4协议审计结果摘要" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

$endTime = Get-Date
$duration = ($endTime - $StartTime).TotalSeconds

Write-Host "=== AUDIT SUMMARY ===" -ForegroundColor Cyan
Write-Host "审计开始时间: $($StartTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Host "审计结束时间: $($endTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Host "审计持续时间: $([math]::Round($duration, 2))秒"
Write-Host "通过项目数: $PassCount" -ForegroundColor Green
Write-Host "失败项目数: $FailCount" -ForegroundColor Red

$totalChecks = $PassCount + $FailCount
if ($totalChecks -gt 0) {
    $passRate = [math]::Round(($PassCount / $totalChecks) * 100, 2)
    Write-Host "通过率: $passRate%" -ForegroundColor Yellow
}

if ($FailCount -eq 0) {
    Write-Host "OVERALL RESULT: PASS - 系统达到生产就绪标准" -ForegroundColor Green
    exit 0
} else {
    Write-Host "OVERALL RESULT: FAIL - 系统存在 $FailCount 个问题需要修复" -ForegroundColor Red
    exit 1
}