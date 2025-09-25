# NeuroTrade Nexus Simple Deployment Verification Script
# This script verifies the deployment status using password authentication

param(
    [string]$VMHost = "192.168.1.20",
    [string]$VMUser = "tjsga",
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

# Execute SSH command with password prompt
function Invoke-SSHCommand {
    param([string]$Command)
    
    Write-Log "Executing command: $Command"
    $result = ssh $VMUser@$VMHost $Command
    return $result
}

# Test SSH connection
function Test-SSHConnection {
    Write-Log "Testing SSH connection to $VMHost..."
    try {
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
    catch {
        Write-Log "SSH connection exception: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Get Docker container status
function Get-ContainerStatus {
    Write-Log "Getting Docker container status..."
    $containerStatus = Invoke-SSHCommand "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    return $containerStatus
}

# Get running containers count
function Get-ContainerCounts {
    Write-Log "Getting container counts..."
    $totalContainers = Invoke-SSHCommand "docker ps -a | wc -l"
    $runningContainers = Invoke-SSHCommand "docker ps | wc -l"
    $stoppedContainers = Invoke-SSHCommand "docker ps -a -f status=exited | wc -l"
    
    return @{
        Total = [int]$totalContainers - 1
        Running = [int]$runningContainers - 1
        Stopped = [int]$stoppedContainers - 1
    }
}

# Test health endpoints
function Test-HealthEndpoints {
    Write-Log "Performing health endpoint checks..."
    
    $endpoints = @{
        "01APIForge" = "http://localhost:3001/health"
        "02DataSpider" = "http://localhost:3002/health"
        "03ScanPulse" = "http://localhost:3003/health"
        "04OptiCore" = "http://localhost:3004/health"
        "05TradeGuard" = "http://localhost:3005/health"
        "06NeuroHub" = "http://localhost:3006/health"
        "07MMS" = "http://localhost:3007/health"
        "08ReviewGuard" = "http://localhost:3008/health"
        "09ASTSConsole" = "http://localhost:3009/health"
        "10TACoreService" = "http://localhost:3010/health"
    }
    
    $healthResults = @()
    
    foreach ($service in $endpoints.Keys) {
        $endpoint = $endpoints[$service]
        try {
            $statusCode = Invoke-SSHCommand "curl -s -o /dev/null -w '%{http_code}' $endpoint"
            $healthResults += @{
                Service = $service
                Endpoint = $endpoint
                StatusCode = $statusCode.Trim()
                Status = if ($statusCode.Trim() -eq "200") { "Healthy" } else { "Unhealthy" }
            }
            Write-Log "Service $service health check completed: HTTP $statusCode"
        }
        catch {
            Write-Log "Service $service health check failed: $($_.Exception.Message)" "ERROR"
            $healthResults += @{
                Service = $service
                Endpoint = $endpoint
                StatusCode = "ERROR"
                Status = "Unhealthy"
            }
        }
    }
    
    return $healthResults
}

# Collect container logs
function Get-ContainerLogs {
    param([string]$ContainerName, [int]$Lines = 20)
    
    Write-Log "Collecting logs for container $ContainerName..."
    try {
        $logs = Invoke-SSHCommand "docker logs --tail $Lines $ContainerName 2>&1"
        return $logs
    }
    catch {
        Write-Log "Failed to collect logs for ${ContainerName}: $($_.Exception.Message)" "ERROR"
        return "Failed to collect logs"
    }
}

# Generate report
function Generate-Report {
    param(
        [string]$ContainerStatus,
        [hashtable]$ContainerCounts,
        [array]$HealthResults,
        [hashtable]$ContainerLogs
    )
    
    Write-Log "Generating deployment verification report..."
    
    $healthyCount = ($HealthResults | Where-Object { $_.Status -eq "Healthy" }).Count
    $totalServices = $HealthResults.Count
    
    $report = @"
# NeuroTrade Nexus Phase 2 Deployment Verification Report

## Verification Time
$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Verification Environment
- **Target Host**: $VMHost
- **SSH User**: $VMUser
- **Authentication Method**: Password
- **Verification Script**: simple-deployment-verification.ps1

## SSH Connection Status
[OK] SSH password authentication connection successful

## Docker Container Status

### Container Count Statistics
- **Total Containers**: $($ContainerCounts.Total)
- **Running Containers**: $($ContainerCounts.Running)
- **Stopped Containers**: $($ContainerCounts.Stopped)

### Container List
```
$ContainerStatus
```

## Health Endpoint Check Results

| Service Name | Endpoint | Status Code | Health Status |
|--------------|----------|-------------|---------------|
"@
    
    foreach ($result in $HealthResults) {
        $status = if ($result.Status -eq "Healthy") { "[OK]" } else { "[FAIL]" }
        $report += "| $($result.Service) | $($result.Endpoint) | $($result.StatusCode) | $status $($result.Status) |`n"
    }
    
    $report += @"

## Service Availability Summary
- **Healthy Services**: $healthyCount
- **Unhealthy Services**: $($totalServices - $healthyCount)
- **Total Services**: $totalServices
- **Overall Availability**: $(if ($totalServices -gt 0) { [math]::Round(($healthyCount / $totalServices) * 100, 2) } else { 0 })%

"@
    
    # Add container logs summary
    if ($ContainerLogs.Count -gt 0) {
        $report += "`n## Container Logs Summary`n`n"
        foreach ($containerName in $ContainerLogs.Keys) {
            $report += "### $containerName Logs`n```
$($ContainerLogs[$containerName])`n```

"
        }
    }
    
    $report += @"
## Verification Conclusion

$(if ($healthyCount -ge 8) {
    "[PASS] Deployment verification passed - Most services running normally"
} else {
    "[FAIL] Deployment verification failed - Multiple services have issues"
})

### Recommendations
- Regularly monitor container status
- Check logs of unhealthy services
- Ensure all health endpoints respond normally
- Verify network connectivity between services

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
    Write-Log "Step 1: Testing SSH connection"
    if (-not (Test-SSHConnection)) {
        Write-Log "SSH connection failed, terminating verification" "ERROR"
        return
    }
    
    # 2. Get container status
    Write-Log "Step 2: Getting container status"
    $containerStatus = Get-ContainerStatus
    $containerCounts = Get-ContainerCounts
    Write-Log "Container status retrieval completed"
    
    # 3. Perform health checks
    Write-Log "Step 3: Performing health checks"
    $healthResults = Test-HealthEndpoints
    Write-Log "Health endpoint checks completed"
    
    # 4. Get key container logs
    Write-Log "Step 4: Collecting key container logs"
    $containerLogs = @{}
    $keyContainers = @("01apiforge", "02dataspider", "06neurohub", "12database")
    foreach ($container in $keyContainers) {
        $containerLogs[$container] = Get-ContainerLogs -ContainerName $container -Lines 20
    }
    
    # 5. Generate report
    Write-Log "Step 5: Generating verification report"
    Generate-Report -ContainerStatus $containerStatus -ContainerCounts $containerCounts -HealthResults $healthResults -ContainerLogs $containerLogs
    
    Write-Log "Deployment verification completed successfully" "SUCCESS"
}

# Execute main function
Main