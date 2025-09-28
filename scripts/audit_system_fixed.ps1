# NeuroTrade Nexus V1.4 协议审计脚本 (PowerShell版本)
# 适配虚拟机Docker环境

# 全局变量
$StartTime = Get-Date
$AuditLog = "audit_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$PassCount = 0
$FailCount = 0

# 日志记录函数
function Write-AuditLog {
    param(
        [string]$Level,
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # 控制台输出
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
    
    # 写入日志文件
    Add-Content -Path $AuditLog -Value $logEntry
}

# 标题打印函数
function Write-Header {
    param([string]$Title)
    
    $separator = "=" * 60
    Write-Host ""
    Write-Host $separator -ForegroundColor Blue
    Write-Host "  $Title" -ForegroundColor Blue
    Write-Host $separator -ForegroundColor Blue
    Write-Host ""
}

# 检查前置条件
function Test-Prerequisites {
    Write-Header "检查前置条件"
    
    # 检查curl
    try {
        $curlVersion = curl --version 2>$null
        if ($curlVersion) {
            Write-AuditLog "PASS" "curl工具可用"
        } else {
            Write-AuditLog "FAIL" "curl工具不可用"
        }
    }
    catch {
        Write-AuditLog "FAIL" "curl工具检查失败"
    }
    
    # 检查Node.js
    try {
        $nodeVersion = node --version 2>$null
        if ($nodeVersion) {
            Write-AuditLog "PASS" "Node.js可用: $nodeVersion"
        } else {
            Write-AuditLog "FAIL" "Node.js不可用"
        }
    }
    catch {
        Write-AuditLog "FAIL" "Node.js检查失败"
    }
    
    # 检查Python
    try {
        $pythonVersion = python --version 2>$null
        if ($pythonVersion) {
            Write-AuditLog "PASS" "Python可用: $pythonVersion"
        } else {
            Write-AuditLog "FAIL" "Python不可用"
        }
    }
    catch {
        Write-AuditLog "FAIL" "Python检查失败"
    }
    
    # 检查SSH
    try {
        $sshVersion = ssh -V 2>&1
        if ($sshVersion) {
            Write-AuditLog "PASS" "SSH工具可用"
        } else {
            Write-AuditLog "FAIL" "SSH工具不可用"
        }
    }
    catch {
        Write-AuditLog "FAIL" "SSH工具检查失败"
    }
}

# 检查虚拟机Docker环境
function Test-VMDockerEnvironment {
    Write-Header "检查虚拟机Docker环境"
    
    $vmHost = "192.168.1.7"
    $vmUser = "tjsga"
    
    try {
        # 测试SSH连接
        Write-AuditLog "INFO" "测试虚拟机SSH连接: $vmUser@$vmHost"
        $sshTest = ssh -o ConnectTimeout=10 -o BatchMode=yes $vmUser@$vmHost "echo 'connected'" 2>$null
        
        if ($sshTest -eq "connected") {
            Write-AuditLog "PASS" "虚拟机SSH连接成功"
        } else {
            Write-AuditLog "FAIL" "虚拟机SSH连接失败"
            return $false
        }
        
        # 检查Docker可用性
        Write-AuditLog "INFO" "检查虚拟机Docker可用性"
        $dockerVersion = ssh -o ConnectTimeout=10 $vmUser@$vmHost "docker --version" 2>$null
        
        if ($dockerVersion) {
            Write-AuditLog "PASS" "虚拟机Docker可用: $dockerVersion"
        } else {
            Write-AuditLog "FAIL" "虚拟机Docker不可用"
            return $false
        }
        
        # 检查Docker服务状态
        Write-AuditLog "INFO" "检查虚拟机Docker服务状态"
        $dockerStatus = ssh -o ConnectTimeout=10 $vmUser@$vmHost "systemctl is-active docker" 2>$null
        
        if ($dockerStatus -eq "active") {
            Write-AuditLog "PASS" "虚拟机Docker服务运行中"
        } else {
            Write-AuditLog "FAIL" "虚拟机Docker服务未运行: $dockerStatus"
        }
        
        # 检查docker-compose可用性
        Write-AuditLog "INFO" "检查虚拟机docker-compose可用性"
        $composeVersion = ssh -o ConnectTimeout=10 $vmUser@$vmHost "docker-compose --version" 2>$null
        
        if ($composeVersion) {
            Write-AuditLog "PASS" "虚拟机docker-compose可用: $composeVersion"
        } else {
            Write-AuditLog "FAIL" "虚拟机docker-compose不可用"
        }
        
        return $true
    }
    catch {
        Write-AuditLog "FAIL" "虚拟机Docker环境检查异常: $($_.Exception.Message)"
        return $false
    }
}

# 模块审计函数
function Invoke-ModuleAudit {
    param([string]$ModulePath)
    
    Write-AuditLog "INFO" "开始审计模块: $ModulePath"
    
    if (-not (Test-Path $ModulePath)) {
        Write-AuditLog "FAIL" "模块目录 $ModulePath 不存在"
        return $false
    }
    
    $moduleResult = $true
    
    try {
        # 检查Python文件
        $pythonFiles = Get-ChildItem -Path $ModulePath -Filter "*.py" -Recurse -ErrorAction SilentlyContinue
        if ($pythonFiles) {
            Write-AuditLog "INFO" "发现Python文件，执行Python检查"
            
            # 检查requirements.txt
            if (Test-Path "$ModulePath\requirements.txt") {
                Write-AuditLog "PASS" "requirements.txt文件存在"
            } else {
                Write-AuditLog "FAIL" "缺少requirements.txt文件"
                $moduleResult = $false
            }
        }
        
        # 检查Node.js文件
        if (Test-Path "$ModulePath\package.json") {
            Write-AuditLog "INFO" "发现package.json，执行Node.js检查"
            
            try {
                $packageJson = Get-Content "$ModulePath\package.json" | ConvertFrom-Json
                Write-AuditLog "PASS" "package.json格式有效"
            }
            catch {
                Write-AuditLog "FAIL" "package.json格式无效"
                $moduleResult = $false
            }
        }
        
        # 检查Dockerfile
        if (Test-Path "$ModulePath\Dockerfile") {
            Write-AuditLog "PASS" "Dockerfile存在"
            
            $dockerfileContent = Get-Content "$ModulePath\Dockerfile"
            
            if ($dockerfileContent | Where-Object { $_ -match "^FROM" }) {
                Write-AuditLog "PASS" "Dockerfile包含FROM指令"
            } else {
                Write-AuditLog "FAIL" "Dockerfile缺少FROM指令"
                $moduleResult = $false
            }
        } else {
            Write-AuditLog "FAIL" "Dockerfile不存在"
            $moduleResult = $false
        }
    }
    catch {
        Write-AuditLog "FAIL" "模块审计异常: $($_.Exception.Message)"
        $moduleResult = $false
    }
    
    return $moduleResult
}

# 集成测试函数
function Invoke-IntegrationTest {
    Write-Header "系统集成验证"
    
    $integrationResult = $true
    $vmHost = "192.168.1.7"
    $vmUser = "tjsga"
    $vmProjectPath = "~/projects"
    
    Write-AuditLog "INFO" "使用虚拟机Docker环境进行集成测试"
    
    # 检查虚拟机上的docker-compose文件
    try {
        Write-AuditLog "INFO" "检查虚拟机上的docker-compose文件"
        $composeCheck = ssh -o ConnectTimeout=10 $vmUser@$vmHost "test -f $vmProjectPath/docker-compose.prod.yml; if (`$? -eq 0) { echo 'found' } else { echo 'not_found' }" 2>$null
        
        if ($composeCheck -eq "found") {
            Write-AuditLog "PASS" "虚拟机Docker Compose配置文件存在: docker-compose.prod.yml"
        } else {
            Write-AuditLog "FAIL" "虚拟机上未找到Docker Compose配置文件"
            $integrationResult = $false
        }
    }
    catch {
        Write-AuditLog "FAIL" "检查虚拟机Docker Compose文件失败: $($_.Exception.Message)"
        $integrationResult = $false
    }
    
    # 检查虚拟机上的容器状态
    try {
        Write-AuditLog "INFO" "检查虚拟机上的容器状态"
        $containerCount = ssh -o ConnectTimeout=10 $vmUser@$vmHost "cd $vmProjectPath; docker ps -q | wc -l" 2>$null
        
        if ([int]$containerCount -gt 0) {
            Write-AuditLog "PASS" "虚拟机上发现 $containerCount 个运行中的容器"
        } else {
            Write-AuditLog "WARN" "虚拟机上未发现运行中的容器"
        }
    }
    catch {
        Write-AuditLog "FAIL" "检查虚拟机容器状态失败: $($_.Exception.Message)"
        $integrationResult = $false
    }
    
    return $integrationResult
}

# 生成最终报告
function Write-FinalReport {
    $endTime = Get-Date
    $duration = ($endTime - $StartTime).TotalSeconds
    
    Write-Header "V1.4协议审计结果摘要"
    
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
        return $true
    } else {
        Write-Host "OVERALL RESULT: FAIL - 系统存在 $FailCount 个问题需要修复" -ForegroundColor Red
        return $false
    }
}

# 主函数
function Main {
    Write-Header "NeuroTrade Nexus V1.4 协议审计开始"
    Write-AuditLog "INFO" "审计开始时间: $($StartTime.ToString('yyyy-MM-dd HH:mm:ss'))"
    Write-AuditLog "INFO" "审计日志文件: $AuditLog"
    
    # 检查前置条件
    Test-Prerequisites
    
    # 检查虚拟机Docker环境
    Test-VMDockerEnvironment
    
    # 定义模块列表
    $modules = @(
        "01APIForge",
        "02DataSpider",
        "03ScanPulse",
        "04OptiCore",
        "05-07TradeGuard",
        "08NeuroHub",
        "09MMS",
        "10ReviewGuard",
        "11_ASTS_Console",
        "12TACoreService",
        "13AI Strategy Assistant",
        "14Observability Center"
    )
    
    Write-Header "模块级静态审计"
    
    # 执行模块审计
    foreach ($module in $modules) {
        if (Invoke-ModuleAudit $module) {
            Write-AuditLog "PASS" "模块 $module 审计通过"
        } else {
            Write-AuditLog "FAIL" "模块 $module 审计失败"
        }
    }
    
    # 执行集成测试
    if (Invoke-IntegrationTest) {
        Write-AuditLog "PASS" "系统集成验证通过"
    } else {
        Write-AuditLog "FAIL" "系统集成验证失败"
    }
    
    # 生成最终报告
    $success = Write-FinalReport
    
    if ($success) {
        exit 0
    } else {
        exit 1
    }
}

# 执行主函数
Main