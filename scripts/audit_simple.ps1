# NeuroTrade Nexus V1.4 协议审计脚本 (简化版)

$StartTime = Get-Date
$PassCount = 0
$FailCount = 0

function Write-AuditLog {
    param($Level, $Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    switch ($Level) {
        "PASS" { 
            Write-Host $logEntry -ForegroundColor Green
            $global:PassCount++
        }
        "FAIL" { 
            Write-Host $logEntry -ForegroundColor Red
            $global:FailCount++
        }
        "WARN" { Write-Host $logEntry -ForegroundColor Yellow }
        "INFO" { Write-Host $logEntry -ForegroundColor Cyan }
        default { Write-Host $logEntry }
    }
}

function Write-Header {
    param($Title)
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Blue
    Write-Host "  $Title" -ForegroundColor Blue
    Write-Host "============================================================" -ForegroundColor Blue
    Write-Host ""
}

# 检查前置条件
Write-Header "检查前置条件"

# 检查curl
$curlTest = Get-Command curl -ErrorAction SilentlyContinue
if ($curlTest) {
    Write-AuditLog "PASS" "curl工具可用"
} else {
    Write-AuditLog "FAIL" "curl工具不可用"
}

# 检查Node.js
$nodeTest = Get-Command node -ErrorAction SilentlyContinue
if ($nodeTest) {
    $nodeVersion = node --version
    Write-AuditLog "PASS" "Node.js可用: $nodeVersion"
} else {
    Write-AuditLog "FAIL" "Node.js不可用"
}

# 检查SSH
$sshTest = Get-Command ssh -ErrorAction SilentlyContinue
if ($sshTest) {
    Write-AuditLog "PASS" "SSH工具可用"
} else {
    Write-AuditLog "FAIL" "SSH工具不可用"
}

# 检查虚拟机Docker环境
Write-Header "检查虚拟机Docker环境"

$vmHost = "192.168.1.7"
$vmUser = "tjsga"

Write-AuditLog "INFO" "测试虚拟机SSH连接: $vmUser@$vmHost"

# 测试SSH连接
try {
    $sshResult = ssh -o ConnectTimeout=10 -o BatchMode=yes $vmUser@$vmHost "echo connected" 2>$null
    if ($sshResult -eq "connected") {
        Write-AuditLog "PASS" "虚拟机SSH连接成功"
        
        # 检查Docker
        $dockerVersion = ssh -o ConnectTimeout=10 $vmUser@$vmHost "docker --version" 2>$null
        if ($dockerVersion) {
            Write-AuditLog "PASS" "虚拟机Docker可用: $dockerVersion"
        } else {
            Write-AuditLog "FAIL" "虚拟机Docker不可用"
        }
        
        # 检查Docker服务
        $dockerStatus = ssh -o ConnectTimeout=10 $vmUser@$vmHost "systemctl is-active docker" 2>$null
        if ($dockerStatus -eq "active") {
            Write-AuditLog "PASS" "虚拟机Docker服务运行中"
        } else {
            Write-AuditLog "FAIL" "虚拟机Docker服务未运行"
        }
        
    } else {
        Write-AuditLog "FAIL" "虚拟机SSH连接失败"
    }
} catch {
    Write-AuditLog "FAIL" "虚拟机连接测试异常"
}

# 模块审计
Write-Header "模块级静态审计"

$modules = @(
    "01APIForge",
    "02DataSpider", 
    "03ScanPulse",
    "04OptiCore",
    "05-07TradeGuard",
    "08NeuroHub",
    "09MMS",
    "10ReviewGuard",
    "11ASTSConsole",
    "12TACoreService",
    "13AI Strategy Assistant",
    "14Observability Center"
)

foreach ($module in $modules) {
    Write-AuditLog "INFO" "审计模块: $module"
    
    if (Test-Path $module) {
        # 检查Dockerfile
        if (Test-Path "$module\Dockerfile") {
            Write-AuditLog "PASS" "$module - Dockerfile存在"
        } else {
            Write-AuditLog "FAIL" "$module - Dockerfile不存在"
        }
        
        # 检查package.json
        if (Test-Path "$module\package.json") {
            Write-AuditLog "PASS" "$module - package.json存在"
        }
        
        # 检查requirements.txt
        if (Test-Path "$module\requirements.txt") {
            Write-AuditLog "PASS" "$module - requirements.txt存在"
        }
        
    } else {
        Write-AuditLog "FAIL" "模块目录 $module 不存在"
    }
}

# 集成测试
Write-Header "系统集成验证"

$vmProjectPath = "~/projects"

try {
    # 检查虚拟机上的docker-compose文件
    Write-AuditLog "INFO" "检查虚拟机docker-compose文件"
    $composeCheck = ssh -o ConnectTimeout=10 $vmUser@$vmHost "test -f $vmProjectPath/docker-compose.prod.yml && echo found || echo not_found" 2>$null
    
    if ($composeCheck -eq "found") {
        Write-AuditLog "PASS" "虚拟机Docker Compose配置文件存在"
    } else {
        Write-AuditLog "FAIL" "虚拟机上未找到Docker Compose配置文件"
    }
    
    # 检查容器状态
    Write-AuditLog "INFO" "检查虚拟机容器状态"
    $containerCount = ssh -o ConnectTimeout=10 $vmUser@$vmHost "cd $vmProjectPath && docker ps -q | wc -l" 2>$null
    
    if ($containerCount -and [int]$containerCount -gt 0) {
        Write-AuditLog "PASS" "虚拟机上发现 $containerCount 个运行中的容器"
    } else {
        Write-AuditLog "WARN" "虚拟机上未发现运行中的容器"
    }
    
} catch {
    Write-AuditLog "FAIL" "集成测试异常"
}

# 生成最终报告
Write-Header "V1.4协议审计结果摘要"

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