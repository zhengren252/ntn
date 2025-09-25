# NeuroTrade Nexus Deployment Verification Script
# This script verifies the deployment status of NeuroTrade Nexus system on virtual machine
# Includes container status checks, health endpoint validation and log collection

param(
    [string]$VMHost = "192.168.1.20",
    [string]$VMUser = "tjsga",
    [string]$SSHKeyPath = "C:\Users\Administrator\.ssh\id_rsa",
    [string]$ReportPath = "phase2-deployment-verification-report.md"
)

# Logging function
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path "deployment-verification.log" -Value $logMessage
}

# 执行SSH命令函数
function Invoke-SSHCommand {
    param([string]$Command)
    try {
        $result = ssh -o StrictHostKeyChecking=no -i $SSHKeyPath $VMUser@$VMHost $Command 2>&1
        return $result
    }
    catch {
        Write-Log "SSH命令执行失败: $Command" "ERROR"
        return $null
    }
}

# SSH connection test function
function Test-SSHConnection {
    Write-Log "Testing SSH connection to $VMHost..."
    $testResult = Invoke-SSHCommand "echo 'SSH connection successful'"
    if ($testResult -match "SSH connection successful") {
        Write-Log "SSH connection test successful" "SUCCESS"
        return $true
    }
    else {
        Write-Log "SSH connection test failed" "ERROR"
        return $false
    }
}

# Get Docker container status
function Get-ContainerStatus {
    Write-Log "Getting Docker container status..."
    $containerStatus = Invoke-SSHCommand "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    return $containerStatus
}

# 获取容器健康状态
function Get-ContainerHealth {
    Write-Log "检查容器健康状态..."
    $healthStatus = Invoke-SSHCommand "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E '(healthy|unhealthy)'"
    return $healthStatus
}

# Health endpoint check
function Test-HealthEndpoints {
    Write-Log "Performing health endpoint checks..."
    $endpoints = @(
        "http://192.168.1.20:3001/health",  # APIForge
        "http://192.168.1.20:3002/health",  # DataSpider
        "http://192.168.1.20:3003/health",  # ScanPulse
        "http://192.168.1.20:3004/health",  # OptiCore
        "http://192.168.1.20:3005/health",  # TradeGuard
        "http://192.168.1.20:3008/health",  # NeuroHub
        "http://192.168.1.20:3009/health",  # MMS
        "http://192.168.1.20:3010/health",  # ReviewGuard
        "http://192.168.1.20:3011/health",  # ASTS Console
        "http://192.168.1.20:3012/health"   # TACoreService
    )
    
    $healthResults = @()
    foreach ($endpoint in $endpoints) {
        $curlCommand = "curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 $endpoint"
        $statusCode = Invoke-SSHCommand $curlCommand
        $healthResults += [PSCustomObject]@{
            Endpoint = $endpoint
            StatusCode = $statusCode
            Status = if ($statusCode -eq "200") { "Healthy" } else { "Unhealthy" }
        }
    }
    return $healthResults
}

# Collect container logs
function Get-ContainerLogs {
    param([string]$ContainerName, [int]$Lines = 50)
    
    Write-Log "Collecting logs for container $ContainerName..."
    $logs = Invoke-SSHCommand "docker logs --tail $Lines $ContainerName 2>&1"
    return $logs
}

# Generate report
function Generate-Report {
    param(
        [array]$ContainerStatus,
        [array]$HealthResults,
        [hashtable]$ContainerLogs
    )
    
    Write-Log "Generating deployment verification report..."
    
    $report = @"
# NeuroTrade Nexus Phase 2 Deployment Verification Report

## Verification Time
$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## SSH Connection Status
 [OK] SSH key authentication connection successful
- Target Host: $VMHost
- User: $VMUser
- Authentication Method: SSH key

## Docker Container Status

### Container List
```
$($ContainerStatus -join "`n")
```

### Container Count Statistics
- Total Containers: $((Invoke-SSHCommand "docker ps -a | wc -l") - 1)
- Running Containers: $(Invoke-SSHCommand "docker ps | wc -l" | ForEach-Object { [int]$_ - 1 })
- Stopped Containers: $(Invoke-SSHCommand "docker ps -a -f status=exited | wc -l" | ForEach-Object { [int]$_ - 1 })

## Health Endpoint Check Results

| Service Endpoint | Status Code | Health Status |
|------------------|-------------|---------------|
"@
    
    foreach ($result in $HealthResults) {
         $status = if ($result.Status -eq "Healthy") { "[OK]" } else { "[FAIL]" }
         $report += "| $($result.Endpoint) | $($result.StatusCode) | $status $($result.Status) |`n"
     }
    
    $report += @"

## Service Availability Summary
- Healthy Services: $($HealthResults | Where-Object { $_.Status -eq "Healthy" } | Measure-Object | Select-Object -ExpandProperty Count)
- Unhealthy Services: $($HealthResults | Where-Object { $_.Status -eq "Unhealthy" } | Measure-Object | Select-Object -ExpandProperty Count)
- Overall Availability: $(($HealthResults | Where-Object { $_.Status -eq "Healthy" } | Measure-Object | Select-Object -ExpandProperty Count) / $HealthResults.Count * 100)%

## Container Logs Summary

"@
    
    foreach ($containerName in $ContainerLogs.Keys) {
        $report += "### $containerName Logs`n```
$($ContainerLogs[$containerName])`n```

"
    }
    
    $report += @"
## Verification Conclusion

$(if (($HealthResults | Where-Object { $_.Status -eq "Healthy" } | Measure-Object | Select-Object -ExpandProperty Count) -ge 8) {
     "[PASS] Deployment verification passed - Most services running normally"
 } else {
     "[FAIL] Deployment verification failed - Multiple services have issues"
 })

### Recommendations
- Regularly monitor container status
- Check logs of unhealthy services
- Ensure all health endpoints respond normally

---
*Report generation time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")*
"@
    
    # Save report
    $report | Out-File -FilePath $ReportPath -Encoding UTF8
    Write-Log "Verification report saved to: $ReportPath" "SUCCESS"
}

# Main execution flow
function Main {
    Write-Log "Starting NeuroTrade Nexus deployment verification..." "INFO"
    
    # 1. Test SSH connection
    if (-not (Test-SSHConnection)) {
        Write-Log "SSH connection failed, terminating verification" "ERROR"
        return
    }
    
    # 2. Get container status
    $containerStatus = Get-ContainerStatus
    Write-Log "Container status retrieval completed"
    
    # 3. Perform health checks
    $healthResults = Test-HealthEndpoints
    Write-Log "Health endpoint checks completed"
    
    # 4. Get key container logs
    $containerLogs = @{}
    $keyContainers = @("apiforge", "dataspider", "scanpulse", "opticore", "neurohub")
    foreach ($container in $keyContainers) {
        $containerLogs[$container] = Get-ContainerLogs $container
    }
    
    # 5. Generate report
    Generate-Report -ContainerStatus $containerStatus -HealthResults $healthResults -ContainerLogs $containerLogs
    
    Write-Log "Deployment verification completed" "SUCCESS"
}

# Execute main function
Main