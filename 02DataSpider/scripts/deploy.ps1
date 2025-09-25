# 信息源爬虫模组部署脚本
# 支持三环境隔离部署：development/staging/production

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("up", "down", "restart", "logs", "status", "clean")]
    [string]$Action = "up",
    
    [Parameter(Mandatory=$false)]
    [switch]$Build,
    
    [Parameter(Mandatory=$false)]
    [switch]$Force,
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# 设置错误处理
$ErrorActionPreference = "Stop"

# 颜色输出函数
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# 日志函数
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    switch ($Level) {
        "ERROR" { Write-ColorOutput $logMessage "Red" }
        "WARN"  { Write-ColorOutput $logMessage "Yellow" }
        "INFO"  { Write-ColorOutput $logMessage "Green" }
        "DEBUG" { if ($Verbose) { Write-ColorOutput $logMessage "Cyan" } }
        default { Write-ColorOutput $logMessage "White" }
    }
}

# 检查Docker和Docker Compose
function Test-DockerEnvironment {
    Write-Log "检查Docker环境..." "INFO"
    
    try {
        $dockerVersion = docker --version
        Write-Log "Docker版本: $dockerVersion" "DEBUG"
    }
    catch {
        Write-Log "Docker未安装或未启动" "ERROR"
        exit 1
    }
    
    try {
        $composeVersion = docker-compose --version
        Write-Log "Docker Compose版本: $composeVersion" "DEBUG"
    }
    catch {
        Write-Log "Docker Compose未安装" "ERROR"
        exit 1
    }
}

# 设置环境变量
function Set-EnvironmentVariables {
    param([string]$env)
    
    Write-Log "设置环境变量: $env" "INFO"
    
    # 设置基础环境变量
    $env:APP_ENV = $env
    $env:BUILD_TARGET = $env
    
    # 根据环境设置特定变量
    switch ($env) {
        "development" {
            $env:COMPOSE_FILE = "docker-compose.dev.yml"
            $env:COMPOSE_PROJECT_NAME = "ntn-dev"
            $env:DEV_MOUNT_SUFFIX = ""
        }
        "staging" {
            $env:COMPOSE_FILE = "docker-compose.staging.yml"
            $env:COMPOSE_PROJECT_NAME = "ntn-staging"
            $env:DEV_MOUNT_SUFFIX = ":ro"
        }
        "production" {
            $env:COMPOSE_FILE = "docker-compose.prod.yml"
            $env:COMPOSE_PROJECT_NAME = "ntn-prod"
            $env:DEV_MOUNT_SUFFIX = ":ro"
        }
    }
    
    Write-Log "使用配置文件: $($env:COMPOSE_FILE)" "DEBUG"
}

# 检查环境配置文件
function Test-EnvironmentConfig {
    param([string]$env)
    
    $envFile = ".env.$env"
    if (-not (Test-Path $envFile)) {
        Write-Log "环境配置文件不存在: $envFile" "ERROR"
        exit 1
    }
    
    Write-Log "环境配置文件检查通过: $envFile" "DEBUG"
}

# 创建必要目录
function New-RequiredDirectories {
    $directories = @("data", "logs", "temp")
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Log "创建目录: $dir" "DEBUG"
        }
    }
}

# 构建镜像
function Build-Images {
    param([string]$env)
    
    Write-Log "构建Docker镜像..." "INFO"
    
    $buildArgs = @(
        "--build-arg", "BUILD_TARGET=$env",
        "--target", $env
    )
    
    if ($Force) {
        $buildArgs += "--no-cache"
    }
    
    try {
        docker-compose build @buildArgs
        Write-Log "镜像构建完成" "INFO"
    }
    catch {
        Write-Log "镜像构建失败: $($_.Exception.Message)" "ERROR"
        exit 1
    }
}

# 启动服务
function Start-Services {
    param([string]$env)
    
    Write-Log "启动服务..." "INFO"
    
    try {
        if ($Build) {
            docker-compose up -d --build
        }
        else {
            docker-compose up -d
        }
        
        Write-Log "服务启动完成" "INFO"
        
        # 等待服务就绪
        Start-Sleep -Seconds 10
        
        # 检查服务状态
        Show-ServiceStatus
        
    }
    catch {
        Write-Log "服务启动失败: $($_.Exception.Message)" "ERROR"
        exit 1
    }
}

# 停止服务
function Stop-Services {
    Write-Log "停止服务..." "INFO"
    
    try {
        docker-compose down
        Write-Log "服务停止完成" "INFO"
    }
    catch {
        Write-Log "服务停止失败: $($_.Exception.Message)" "ERROR"
        exit 1
    }
}

# 重启服务
function Restart-Services {
    param([string]$env)
    
    Write-Log "重启服务..." "INFO"
    Stop-Services
    Start-Sleep -Seconds 5
    Start-Services $env
}

# 显示日志
function Show-Logs {
    Write-Log "显示服务日志..." "INFO"
    
    try {
        docker-compose logs -f --tail=100
    }
    catch {
        Write-Log "获取日志失败: $($_.Exception.Message)" "ERROR"
    }
}

# 显示服务状态
function Show-ServiceStatus {
    Write-Log "检查服务状态..." "INFO"
    
    try {
        docker-compose ps
        
        # 检查健康状态
        Write-Log "检查健康状态..." "INFO"
        $containers = docker-compose ps -q
        
        foreach ($container in $containers) {
            if ($container) {
                $health = docker inspect --format='{{.State.Health.Status}}' $container 2>$null
                $name = docker inspect --format='{{.Name}}' $container
                
                if ($health) {
                    Write-Log "容器 $name 健康状态: $health" "INFO"
                }
                else {
                    Write-Log "容器 $name 无健康检查配置" "DEBUG"
                }
            }
        }
    }
    catch {
        Write-Log "获取服务状态失败: $($_.Exception.Message)" "ERROR"
    }
}

# 清理资源
function Clear-Resources {
    Write-Log "清理Docker资源..." "INFO"
    
    try {
        # 停止并删除容器
        docker-compose down -v --remove-orphans
        
        if ($Force) {
            # 删除镜像
            Write-Log "删除相关镜像..." "INFO"
            docker images | Select-String "ntn-" | ForEach-Object {
                $imageId = ($_ -split "\s+")[2]
                docker rmi $imageId -f
            }
            
            # 清理未使用的资源
            docker system prune -f
        }
        
        Write-Log "资源清理完成" "INFO"
    }
    catch {
        Write-Log "资源清理失败: $($_.Exception.Message)" "ERROR"
    }
}

# 主函数
function Main {
    Write-Log "=== 信息源爬虫模组部署脚本 ===" "INFO"
    Write-Log "环境: $Environment" "INFO"
    Write-Log "操作: $Action" "INFO"
    
    # 检查Docker环境
    Test-DockerEnvironment
    
    # 设置环境变量
    Set-EnvironmentVariables $Environment
    
    # 检查环境配置
    Test-EnvironmentConfig $Environment
    
    # 创建必要目录
    New-RequiredDirectories
    
    # 执行操作
    switch ($Action) {
        "up" {
            Start-Services $Environment
        }
        "down" {
            Stop-Services
        }
        "restart" {
            Restart-Services $Environment
        }
        "logs" {
            Show-Logs
        }
        "status" {
            Show-ServiceStatus
        }
        "clean" {
            Clear-Resources
        }
        default {
            Write-Log "未知操作: $Action" "ERROR"
            exit 1
        }
    }
    
    Write-Log "=== 部署脚本执行完成 ===" "INFO"
}

# 执行主函数
Main