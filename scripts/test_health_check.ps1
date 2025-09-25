# NeuroTrade Nexus (NTN) - 健康检查脚本
# 版本: 1.0
# 功能: 自动化模组健康状态检测，避免交互式提示

param(
    [Parameter(Mandatory=$true)]
    [string]$Uri,
    [int]$TimeoutSeconds = 30,
    [switch]$ShowDetails
)

# 错误处理设置
$ErrorActionPreference = "Stop"

function Test-ModuleHealth {
    param(
        [string]$TestUri,
        [int]$Timeout = 30
    )
    
    try {
        if ($ShowDetails) {
            Write-Host "Testing: $TestUri" -ForegroundColor Yellow
        }
        
        # Use non-interactive Invoke-WebRequest
        $response = Invoke-WebRequest -Uri $TestUri -Method GET -TimeoutSec $Timeout -UseBasicParsing -ErrorAction Stop
        
        $result = @{
            Uri = $TestUri
            StatusCode = $response.StatusCode
            StatusDescription = $response.StatusDescription
            Success = $true
            Content = $response.Content
            ResponseTime = (Get-Date)
        }
        
        if ($ShowDetails) {
            Write-Host "Success: $($response.StatusCode) $($response.StatusDescription)" -ForegroundColor Green
        }
        
        return $result
        
    } catch {
        $result = @{
            Uri = $TestUri
            StatusCode = $null
            StatusDescription = $null
            Success = $false
            Error = $_.Exception.Message
            ResponseTime = (Get-Date)
        }
        
        if ($ShowDetails) {
            Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
        }
        
        return $result
    }
}

# 主执行逻辑
try {
    Write-Host "Starting health check: $Uri" -ForegroundColor Cyan
    
    $result = Test-ModuleHealth -TestUri $Uri -Timeout $TimeoutSeconds
    
    if ($result.Success) {
        Write-Host "Health check passed" -ForegroundColor Green
        
        # 输出结果
        $output = @{
            timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            uri = $result.Uri
            status_code = $result.StatusCode
            status_description = $result.StatusDescription
            success = $result.Success
        }
        
        $output | ConvertTo-Json -Depth 3
        exit 0
    } else {
        Write-Host "Health check failed" -ForegroundColor Red
        
        # 输出错误结果
        $output = @{
            timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            uri = $result.Uri
            success = $result.Success
            error = $result.Error
        }
        
        $output | ConvertTo-Json -Depth 3
        exit 1
    }
    
} catch {
    Write-Host "Script execution failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}