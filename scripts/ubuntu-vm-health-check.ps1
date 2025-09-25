# Ubuntu虚拟机环境 - NTN系统健康检查脚本 (Windows PowerShell版本)
# 适用于从Windows主机检查Ubuntu 22.04.5虚拟机中的Docker容器

param(
    [string]$VMHost = "192.168.1.19",
    [int]$SSHPort = 22,
    [string]$Username = "tjsga",
    [string]$Password = "791106",
    [switch]$StartContainers,
    [switch]$GenerateReport,
    [switch]$UseVM2
)

# 颜色定义
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    White = "White"
}

# 日志函数
function Write-LogInfo {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Blue
}

function Write-LogSuccess {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Colors.Green
}

function Write-LogWarning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Yellow
}

function Write-LogError {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

# 检查SSH连接
function Test-SSHConnection {
    Write-LogInfo "检查SSH连接到Ubuntu虚拟机..."
    
    # 如果指定使用VM2，切换到第二个IP
    if ($UseVM2) {
        $script:VMHost = "192.168.1.20"
        Write-LogInfo "切换到备用虚拟机: $VMHost"
    }
    
    try {
        # 检查是否安装了SSH客户端
        if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
            Write-LogError "SSH客户端未安装，请安装OpenSSH客户端"
            Write-LogInfo "安装命令: Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0"
            return $false
        }
        
        # 测试网络连通性
        Write-LogInfo "测试网络连通性到 $VMHost..."
        $pingResult = Test-NetConnection -ComputerName $VMHost -Port $SSHPort -WarningAction SilentlyContinue
        
        if (-not $pingResult.TcpTestSucceeded) {
            Write-LogError "无法连接到 $VMHost:$SSHPort"
            return $false
        }
        
        Write-LogSuccess "网络连接正常"
        Write-LogInfo "SSH连接信息: $Username@$VMHost (密码: $Password)"
        
        # 测试SSH连接
        $testResult = ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$Username@$VMHost" -p $SSHPort "echo 'SSH连接成功'" 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            Write-LogSuccess "SSH连接正常"
            return $true
        } else {
            Write-LogError "SSH连接失败，请检查虚拟机状态和认证配置"
            Write-LogInfo "手动连接命令: ssh $Username@$VMHost"
            return $false
        }
    }
    catch {
        Write-LogError "SSH连接测试异常: $($_.Exception.Message)"
        return $false
    }
}

# 在虚拟机中执行命令
function Invoke-VMCommand {
    param(
        [string]$Command,
        [switch]$IgnoreError
    )
    
    try {
        # 使用改进的SSH选项
        $sshOptions = @(
            "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR"
        )
        
        $result = ssh @sshOptions "$Username@$VMHost" -p $SSHPort $Command 2>&1
        
        if ($LASTEXITCODE -ne 0 -and -not $IgnoreError) {
            Write-LogError "命令执行失败: $Command"
            Write-LogError "错误输出: $result"
            return $null
        }
        
        return $result
    }
    catch {
        Write-LogError "命令执行异常: $($_.Exception.Message)"
        return $null
    }
}

# 检查虚拟机Docker环境
function Test-VMDockerEnvironment {
    Write-LogInfo "检查虚拟机Docker环境..."
    
    # 检查Docker是否安装
    $dockerVersion = Invoke-VMCommand "docker --version" -IgnoreError
    if (-not $dockerVersion) {
        Write-LogError "Docker未安装或不可用"
        return $false
    }
    
    # 检查Docker Compose是否安装
    $composeVersion = Invoke-VMCommand "docker-compose --version" -IgnoreError
    if (-not $composeVersion) {
        Write-LogError "Docker Compose未安装或不可用"
        return $false
    }
    
    # 检查Docker服务状态
    $dockerStatus = Invoke-VMCommand "systemctl is-active docker" -IgnoreError
    if ($dockerStatus -ne "active") {
        Write-LogError "Docker服务未运行"
        return $false
    }
    
    # 检查Docker权限
    $dockerTest = Invoke-VMCommand "docker ps" -IgnoreError
    if (-not $dockerTest) {
        Write-LogError "Docker权限不足"
        return $false
    }
    
    Write-LogSuccess "Docker环境检查通过"
    Write-LogInfo "Docker版本: $dockerVersion"
    Write-LogInfo "Docker Compose版本: $composeVersion"
    return $true
}

# 检查虚拟机系统资源
function Test-VMSystemResources {
    Write-LogInfo "检查虚拟机系统资源..."
    
    # 检查内存使用
    $memInfo = Invoke-VMCommand "free -m | awk 'NR==2{printf \"%d %d\", `$2, `$7}'"
    if ($memInfo) {
        $memArray = $memInfo -split " "
        $totalMem = [int]$memArray[0]
        $availableMem = [int]$memArray[1]
        
        Write-LogInfo "内存状态: 总计 ${totalMem}MB, 可用 ${availableMem}MB"
        
        if ($totalMem -lt 8192) {
            Write-LogWarning "系统内存不足8GB"
        }
        
        if ($availableMem -lt 4096) {
            Write-LogWarning "可用内存不足4GB"
        }
    }
    
    # 检查磁盘使用
    $diskUsage = Invoke-VMCommand "df -h . | awk 'NR==2 {print `$5}' | sed 's/%//'"
    if ($diskUsage) {
        $diskPercent = [int]$diskUsage
        Write-LogInfo "磁盘使用率: ${diskPercent}%"
        
        if ($diskPercent -gt 80) {
            Write-LogWarning "磁盘使用率过高: ${diskPercent}%"
        }
    }
    
    Write-LogSuccess "系统资源检查完成"
}

# 启动容器服务
function Start-VMContainers {
    Write-LogInfo "在虚拟机中启动NTN容器服务..."
    
    # 检查docker-compose.prod.yml文件
    $composeFile = Invoke-VMCommand "ls -la docker-compose.prod.yml" -IgnoreError
    if (-not $composeFile) {
        Write-LogError "docker-compose.prod.yml文件不存在"
        return $false
    }
    
    # 清理旧容器
    Write-LogInfo "清理旧容器..."
    Invoke-VMCommand "docker-compose -f docker-compose.prod.yml down --remove-orphans" -IgnoreError
    
    # 清理Docker缓存
    Write-LogInfo "清理Docker缓存..."
    Invoke-VMCommand "docker system prune -f" -IgnoreError
    
    # 启动服务
    Write-LogInfo "构建并启动所有服务..."
    $startResult = Invoke-VMCommand "docker-compose -f docker-compose.prod.yml up --build -d"
    
    if ($LASTEXITCODE -eq 0) {
        Write-LogSuccess "容器启动命令执行成功"
        
        # 等待容器启动
        Write-LogInfo "等待容器启动完成..."
        Start-Sleep -Seconds 30
        return $true
    } else {
        Write-LogError "容器启动失败"
        return $false
    }
}

# 检查容器状态
function Test-VMContainerStatus {
    Write-LogInfo "检查虚拟机中的容器运行状态..."
    
    # 预期的容器列表（按照新的命名规范）
    $expectedContainers = @(
        "ntn-redis-prod",
        "01APIForge",
        "02DataSpider",
        "03ScanPulse",
        "04OptiCore",
        "05-07TradeGuard",
        "08NeuroHub",
        "09MMS",
        "10ReviewGuard-backend",
        "10ReviewGuard-frontend",
        "11ASTS-Console",
        "12TACoreService",
        "13AI-Strategy-Assistant",
        "14Observability-Center",
        "nginx"
    )
    
    # 获取运行中的容器
    $runningContainers = Invoke-VMCommand "docker ps --format '{{.Names}}'"
    $runningList = if ($runningContainers) { $runningContainers -split "`n" } else { @() }
    
    $runningCount = 0
    $healthyCount = 0
    
    Write-Host ""
    Write-Host ("{0,-35} {1,-15} {2,-15}" -f "容器名称", "运行状态", "健康状态") -ForegroundColor White
    Write-Host ("{0,-35} {1,-15} {2,-15}" -f "---", "---", "---") -ForegroundColor White
    
    foreach ($container in $expectedContainers) {
        if ($runningList -contains $container) {
            $status = "运行中"
            $runningCount++
            
            # 检查健康状态
            $health = Invoke-VMCommand "docker inspect --format='{{.State.Health.Status}}' '$container'" -IgnoreError
            
            switch ($health) {
                "healthy" {
                    $healthStatus = "健康"
                    $healthyCount++
                    $color = $Colors.Green
                }
                "unhealthy" {
                    $healthStatus = "不健康"
                    $color = $Colors.Red
                }
                "starting" {
                    $healthStatus = "启动中"
                    $color = $Colors.Yellow
                }
                default {
                    $healthStatus = "无检查"
                    $color = $Colors.White
                }
            }
        } else {
            $status = "未运行"
            $healthStatus = "N/A"
            $color = $Colors.Red
        }
        
        Write-Host ("{0,-35} {1,-15} {2,-15}" -f $container, $status, $healthStatus) -ForegroundColor $color
    }
    
    Write-Host ""
    Write-LogInfo "容器状态统计: $runningCount/$($expectedContainers.Count) 运行中, $healthyCount 健康"
    
    if ($runningCount -eq $expectedContainers.Count) {
        Write-LogSuccess "所有容器都在运行"
        return $true
    } else {
        Write-LogError "有容器未运行"
        return $false
    }
}

# 检查服务健康端点
function Test-VMServiceEndpoints {
    Write-LogInfo "检查虚拟机中的服务健康端点..."
    
    # 等待服务完全启动
    Write-LogInfo "等待服务完全启动..."
    Start-Sleep -Seconds 60
    
    # 健康端点列表（根据docker-compose.prod.yml端口配置）
    $endpoints = @{
        "Redis" = "redis-cli -h localhost -p 6379 ping"
        "API Factory" = "curl -f -s http://localhost:8000/health"
        "Info Crawler" = "curl -f -s http://localhost:8001/health"
        "Scanner" = "curl -f -s http://localhost:8002/health"
        "Strategy Optimizer" = "curl -f -s http://localhost:8003/health"
        "Trade Guard" = "curl -f -s http://localhost:8004/health"
        "Neuro Hub" = "curl -f -s http://localhost:8005/health"
        "MMS" = "curl -f -s http://localhost:8006/health"
        "Review Guard Backend" = "curl -f -s http://localhost:8007/health"
        "ASTS Console Backend" = "curl -f -s http://localhost:8008/health"
        "TACoreService" = "curl -f -s http://localhost:8009/health"
        "AI Strategy Assistant" = "curl -f -s http://localhost:8010/health"
        "Observability Center" = "curl -f -s http://localhost:8011/health"
    }
    
    # 前端端点列表
    $frontendEndpoints = @{
        "Review Guard Frontend" = "curl -f -s -o /dev/null http://localhost:3000"
        "ASTS Console Frontend" = "curl -f -s -o /dev/null http://localhost:3001"
        "Nginx Gateway" = "curl -f -s -o /dev/null http://localhost:80"
        "Nginx HTTPS" = "curl -f -s -o /dev/null -k https://localhost:443"
    }
    
    $healthyServices = 0
    $totalServices = $endpoints.Count + $frontendEndpoints.Count
    
    Write-Host ""
    Write-LogInfo "检查后端服务健康端点..."
    foreach ($service in $endpoints.Keys) {
        $result = Invoke-VMCommand $endpoints[$service] -IgnoreError
        if ($LASTEXITCODE -eq 0) {
            Write-LogSuccess "$service`: 健康"
            $healthyServices++
        } else {
            Write-LogError "$service`: 不健康或无响应"
        }
    }
    
    Write-Host ""
    Write-LogInfo "检查前端服务端点..."
    foreach ($service in $frontendEndpoints.Keys) {
        $result = Invoke-VMCommand $frontendEndpoints[$service] -IgnoreError
        if ($LASTEXITCODE -eq 0) {
            Write-LogSuccess "$service`: 可访问"
            $healthyServices++
        } else {
            Write-LogError "$service`: 不可访问"
        }
    }
    
    Write-Host ""
    Write-LogInfo "服务健康统计: $healthyServices/$totalServices 服务正常"
    
    return ($healthyServices -eq $totalServices)
}

# 生成健康检查报告
function New-HealthReport {
    Write-LogInfo "生成健康检查报告..."
    
    $reportFile = "health-check-report-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
    $reportPath = Join-Path $PWD $reportFile
    
    $report = @()
    $report += "======================================"
    $report += "NTN系统健康检查报告"
    $report += "======================================"
    $report += "检查时间: $(Get-Date)"
    $report += "环境: Ubuntu 22.04.5 虚拟机 + Docker"
    $report += "检查主机: $env:COMPUTERNAME"
    $report += "虚拟机地址: $VMHost`:$SSHPort"
    $report += ""
    
    # 获取虚拟机系统信息
    $ubuntuVersion = Invoke-VMCommand "lsb_release -d | cut -f2" -IgnoreError
    $dockerVersion = Invoke-VMCommand "docker --version" -IgnoreError
    $composeVersion = Invoke-VMCommand "docker-compose --version" -IgnoreError
    $memInfo = Invoke-VMCommand "free -h | awk 'NR==2{printf \"%s/%s\", `$3,`$2}'" -IgnoreError
    $diskInfo = Invoke-VMCommand "df -h . | awk 'NR==2 {print `$5}'" -IgnoreError
    
    $report += "系统信息:"
    $report += "- Ubuntu版本: $ubuntuVersion"
    $report += "- Docker版本: $dockerVersion"
    $report += "- Docker Compose版本: $composeVersion"
    $report += "- 系统内存: $memInfo"
    $report += "- 磁盘使用: $diskInfo"
    $report += ""
    
    # 获取容器状态
    $containerStatus = Invoke-VMCommand "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" -IgnoreError
    $report += "容器状态:"
    $report += $containerStatus
    $report += ""
    
    # 获取健康检查状态
    $healthyContainers = Invoke-VMCommand "docker ps --filter 'health=healthy' --format 'table {{.Names}}\t{{.Status}}'" -IgnoreError
    $report += "健康检查状态:"
    $report += $healthyContainers
    $report += ""
    
    # 获取异常容器
    $unhealthyContainers = Invoke-VMCommand "docker ps --filter 'health=unhealthy' --format 'table {{.Names}}\t{{.Status}}'" -IgnoreError
    $report += "异常容器:"
    $report += $unhealthyContainers
    $report += ""
    
    # 获取资源使用
    $resourceUsage = Invoke-VMCommand "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'" -IgnoreError
    $report += "资源使用:"
    $report += $resourceUsage
    
    # 写入报告文件
    $report | Out-File -FilePath $reportPath -Encoding UTF8
    
    Write-LogSuccess "健康检查报告已生成: $reportPath"
    return $reportPath
}

# 主函数
function Main {
    Write-Host "======================================" -ForegroundColor White
    Write-Host "NTN系统健康检查 - Ubuntu虚拟机版本" -ForegroundColor White
    Write-Host "======================================" -ForegroundColor White
    Write-Host "开始时间: $(Get-Date)" -ForegroundColor White
    Write-Host "虚拟机地址: $VMHost`:$SSHPort" -ForegroundColor White
    Write-Host ""
    
    # 检查SSH连接
    if (-not (Test-SSHConnection)) {
        Write-LogError "无法连接到虚拟机，请检查网络和SSH配置"
        return
    }
    
    # 检查Docker环境
    if (-not (Test-VMDockerEnvironment)) {
        Write-LogError "虚拟机Docker环境检查失败"
        return
    }
    
    # 检查系统资源
    Test-VMSystemResources
    
    # 启动容器（如果指定）
    if ($StartContainers) {
        if (-not (Start-VMContainers)) {
            Write-LogError "容器启动失败"
            return
        }
    }
    
    # 检查容器状态
    $containersOk = Test-VMContainerStatus
    
    # 检查服务端点
    $servicesOk = Test-VMServiceEndpoints
    
    # 生成报告（如果指定）
    if ($GenerateReport) {
        $reportPath = New-HealthReport
    }
    
    Write-Host ""
    if ($containersOk -and $servicesOk) {
        Write-LogSuccess "健康检查完成 - 系统状态良好!"
    } else {
        Write-LogWarning "健康检查完成 - 发现问题，请查看详细信息"
    }
    Write-Host "======================================" -ForegroundColor White
}

# 显示帮助信息
function Show-Help {
    Write-Host "Ubuntu虚拟机NTN系统健康检查脚本" -ForegroundColor Green
    Write-Host ""
    Write-Host "用法:" -ForegroundColor Yellow
    Write-Host "  .\ubuntu-vm-health-check.ps1 [参数]" -ForegroundColor White
    Write-Host ""
    Write-Host "参数:" -ForegroundColor Yellow
    Write-Host "  -VMHost <地址>        虚拟机IP地址或主机名 (默认: localhost)" -ForegroundColor White
    Write-Host "  -SSHPort <端口>       SSH端口 (默认: 22)" -ForegroundColor White
    Write-Host "  -Username <用户名>    SSH用户名 (默认: ubuntu)" -ForegroundColor White
    Write-Host "  -StartContainers      启动容器服务" -ForegroundColor White
    Write-Host "  -GenerateReport       生成详细报告" -ForegroundColor White
    Write-Host "  -Help                 显示此帮助信息" -ForegroundColor White
    Write-Host ""
    Write-Host "示例:" -ForegroundColor Yellow
    Write-Host "  .\ubuntu-vm-health-check.ps1 -VMHost 192.168.1.100 -StartContainers -GenerateReport" -ForegroundColor White
    Write-Host ""
}

# 检查是否请求帮助
if ($args -contains "-Help" -or $args -contains "--help" -or $args -contains "/?") {
    Show-Help
    return
}

# 执行主函数
Main