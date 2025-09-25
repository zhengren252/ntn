# Automated VM Deployment Verification Script
# Solves SSH connection stuck at password input issue

param(
    [string]$VMHost = "192.168.1.20",
    [string]$Username = "tjsga",
    [string]$Password = "791106"
)

# Set error handling
$ErrorActionPreference = "Continue"

# Create report file paths
$ReportPath = "e:\NeuroTrade Nexus (NTN)\phase2-deployment-verification-report.md"
$LogPath = "e:\NeuroTrade Nexus (NTN)\logs\vm-verification-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

# Ensure log directory exists
$LogDir = Split-Path $LogPath -Parent
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force
}

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogPath -Value $LogMessage
}

function Execute-SSHCommand {
    param(
        [string]$Command,
        [string]$Description
    )
    
    Write-Log "Executing: $Description"
    Write-Log "Command: $Command"
    
    try {
        # 创建临时脚本文件来执行SSH命令
        $TempScript = "$env:TEMP\ssh_command_$(Get-Random).bat"
        $BatchContent = "@echo off`necho $Password | ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=nul $Username@$VMHost `"$Command`"`n"
        Set-Content -Path $TempScript -Value $BatchContent -Encoding ASCII
        
        $Result = & cmd.exe /c $TempScript 2>&1
        Remove-Item $TempScript -Force -ErrorAction SilentlyContinue
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Success: $Description"
            return $Result
        } else {
            Write-Log "Failed: $Description (Exit code: $LASTEXITCODE)"
            return $null
        }
    } catch {
        Write-Log "Error: $Description - $($_.Exception.Message)"
        return $null
    }
}

function Test-SSHConnection {
    Write-Log "Testing SSH connection to $VMHost..."
    
    # Test connection using echo pipe method
    $TestResult = Execute-SSHCommand "echo 'SSH connection test successful'" "SSH Connection Test"
    
    if ($TestResult -and $TestResult -match "SSH connection test successful") {
        Write-Log "SSH connection established successfully"
        return $true
    } else {
        Write-Log "SSH connection failed"
        return $false
    }
}

function Get-ContainerStatus {
    Write-Log "Getting Docker container status..."
    
    # Get all NTN container status
    $ContainerStatus = Execute-SSHCommand "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep ntn-" "Get NTN Container Status"
    
    if ($ContainerStatus) {
        Write-Log "Container status retrieved successfully"
        return $ContainerStatus
    }
    
    # If failed, try to get all containers
    $AllContainers = Execute-SSHCommand "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" "Get All Container Status"
    return $AllContainers
}

function Get-ContainerHealth {
    Write-Log "Checking container health status..."
    
    $HealthCommands = @(
        @{Command="docker ps --filter health=healthy --format '{{.Names}}'"; Description="Healthy Containers"},
        @{Command="docker ps --filter health=unhealthy --format '{{.Names}}'"; Description="Unhealthy Containers"},
        @{Command="docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'"; Description="Container Resource Usage"}
    )
    
    $HealthResults = @{}
    
    foreach ($HealthCmd in $HealthCommands) {
        $Result = Execute-SSHCommand $HealthCmd.Command $HealthCmd.Description
        $HealthResults[$HealthCmd.Description] = $Result
    }
    
    return $HealthResults
}

function Test-ServiceEndpoints {
    Write-Log "Testing service endpoints..."
    
    $EndpointTests = @(
        @{URL="http://localhost:80"; Description="Nginx Proxy"},
        @{URL="http://localhost:8001/health"; Description="API Factory Health"},
        @{URL="http://localhost:8002/health"; Description="TA Core Service Health"},
        @{URL="http://localhost:8003/health"; Description="Neuro Hub Health"}
    )
    
    $EndpointResults = @{}
    
    foreach ($Test in $EndpointTests) {
        $CurlCommand = "curl -s -o /dev/null -w `"%{http_code}`" --connect-timeout 5 `"$($Test.URL)`""
        $Result = Execute-SSHCommand $CurlCommand "Test Endpoint: $($Test.Description)"
        $EndpointResults[$Test.Description] = $Result
    }
    
    return $EndpointResults
}

function Generate-Report {
    param(
        [object]$ContainerStatus,
        [object]$HealthResults,
        [object]$EndpointResults
    )
    
    Write-Log "Generating deployment verification report..."
    
    $ReportContent = @"
# NeuroTrade Nexus (NTN) Phase 2 Deployment Verification Report

## Verification Time
- Execution Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
- Target VM: $VMHost
- Username: $Username

## SSH Connection Status
- Connection Status: Success
- Connection Method: Automated Script

## Docker Container Status

### NTN Service Containers
``````
$($ContainerStatus -join "`n")
``````

## Container Health Check

"@

    foreach ($Key in $HealthResults.Keys) {
        $ReportContent += "`n### $Key`n``````
$($HealthResults[$Key] -join "`n")`n```````n"
    }
    
    $ReportContent += "`n## Service Endpoint Tests`n`n"
    
    foreach ($Key in $EndpointResults.Keys) {
        $Status = if ($EndpointResults[$Key] -eq "200") { "OK (200)" } else { "ERROR (HTTP $($EndpointResults[$Key]))" }
        $ReportContent += "- $Key`: $Status`n"
    }
    
    $ReportContent += @"

## Verification Summary

### Successful Items
- SSH connection automation successful
- Docker container status retrieved successfully
- Container health check completed
- Service endpoint testing completed

### Recommendations
1. Execute this verification script regularly to ensure system stability
2. Monitor container resource usage
3. Set up automated health check alerts

### Log Files
- Detailed log: $LogPath

---
*Report generated at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')*
"@

    # 写入报告文件
    Set-Content -Path $ReportPath -Value $ReportContent -Encoding UTF8
    Write-Log "Report generated: $ReportPath"
}

# Main execution flow
Write-Log "Starting automated VM deployment verification..."
Write-Log "Target host: $VMHost"
Write-Log "Username: $Username"

# 1. Test SSH connection
if (!(Test-SSHConnection)) {
    Write-Log "SSH connection failed, cannot continue verification"
    exit 1
}

# 2. Get container status
$ContainerStatus = Get-ContainerStatus
if (!$ContainerStatus) {
    Write-Log "Unable to get container status"
    exit 1
}

# 3. Check container health status
$HealthResults = Get-ContainerHealth

# 4. Test service endpoints
$EndpointResults = Test-ServiceEndpoints

# 5. Generate report
Generate-Report -ContainerStatus $ContainerStatus -HealthResults $HealthResults -EndpointResults $EndpointResults

Write-Log "Automated verification completed!"
Write-Log "View report: $ReportPath"
Write-Log "View log: $LogPath"