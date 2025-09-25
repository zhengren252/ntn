# NeuroTrade Nexus V1.4 Protocol Audit Script (Clean Version)
# Created for comprehensive system audit and validation

param(
    [string]$LogLevel = "INFO"
)

# Global Configuration
$AuditLog = "audit_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$PassCount = 0
$FailCount = 0
$StartTime = Get-Date

# Logging Function
function Write-AuditLog {
    param(
        [string]$Level,
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] ${Level}: $Message"
    
    Write-Host $logEntry
    Add-Content -Path $AuditLog -Value $logEntry
    
    if ($Level -eq "PASS") {
        $global:PassCount++
    } elseif ($Level -eq "FAIL") {
        $global:FailCount++
    }
}

# Header Function
function Write-Header {
    param([string]$Title)
    
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Blue
    Write-Host "  $Title" -ForegroundColor Blue
    Write-Host "=" * 60 -ForegroundColor Blue
    Write-Host ""
}

# Test Prerequisites
function Test-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    # Check Node.js
    try {
        $nodeVersion = node --version 2>$null
        if ($nodeVersion) {
            Write-AuditLog "PASS" "Node.js available: $nodeVersion"
        } else {
            Write-AuditLog "FAIL" "Node.js not available"
        }
    } catch {
        Write-AuditLog "FAIL" "Node.js check failed"
    }
    
    # Check Python
    try {
        $pythonVersion = python --version 2>$null
        if ($pythonVersion) {
            Write-AuditLog "PASS" "Python available: $pythonVersion"
        } else {
            Write-AuditLog "FAIL" "Python not available"
        }
    } catch {
        Write-AuditLog "FAIL" "Python check failed"
    }
    
    # Check SSH
    try {
        $sshTest = ssh -V 2>&1
        if ($sshTest) {
            Write-AuditLog "PASS" "SSH tool available"
        } else {
            Write-AuditLog "FAIL" "SSH tool not available"
        }
    } catch {
        Write-AuditLog "FAIL" "SSH tool check failed"
    }
}

# Test VM Docker Environment
function Test-VMDockerEnvironment {
    Write-Header "Testing VM Docker Environment"
    
    $vmHost = "192.168.1.7"
    $vmUser = "tjsga"
    
    try {
        # Test SSH Connection
        Write-AuditLog "INFO" "Testing SSH connection to $vmUser@$vmHost"
        $sshTest = ssh -o ConnectTimeout=10 -o BatchMode=yes $vmUser@$vmHost "echo 'connected'" 2>$null
        
        if ($sshTest -eq "connected") {
            Write-AuditLog "PASS" "VM SSH connection successful"
        } else {
            Write-AuditLog "FAIL" "VM SSH connection failed"
            return $false
        }
        
        # Check Docker availability
        Write-AuditLog "INFO" "Checking VM Docker availability"
        $dockerVersion = ssh -o ConnectTimeout=10 $vmUser@$vmHost "docker --version" 2>$null
        
        if ($dockerVersion) {
            Write-AuditLog "PASS" "VM Docker available: $dockerVersion"
        } else {
            Write-AuditLog "FAIL" "VM Docker not available"
            return $false
        }
        
        # Check Docker service status
        Write-AuditLog "INFO" "Checking VM Docker service status"
        $dockerStatus = ssh -o ConnectTimeout=10 $vmUser@$vmHost "systemctl is-active docker" 2>$null
        
        if ($dockerStatus -eq "active") {
            Write-AuditLog "PASS" "VM Docker service is running"
        } else {
            Write-AuditLog "FAIL" "VM Docker service not running: $dockerStatus"
        }
        
        # Check docker-compose availability
        Write-AuditLog "INFO" "Checking VM docker-compose availability"
        $composeVersion = ssh -o ConnectTimeout=10 $vmUser@$vmHost "docker-compose --version" 2>$null
        
        if ($composeVersion) {
            Write-AuditLog "PASS" "VM docker-compose available: $composeVersion"
        } else {
            Write-AuditLog "FAIL" "VM docker-compose not available"
        }
        
        return $true
    } catch {
        Write-AuditLog "FAIL" "VM Docker environment check exception: $($_.Exception.Message)"
        return $false
    }
}

# Module Audit Function
function Invoke-ModuleAudit {
    param([string]$ModulePath)
    
    Write-AuditLog "INFO" "Starting audit for module: $ModulePath"
    
    if (-not (Test-Path $ModulePath)) {
        Write-AuditLog "FAIL" "Module directory $ModulePath does not exist"
        return $false
    }
    
    $moduleResult = $true
    
    try {
        # Check Python files
        $pythonFiles = Get-ChildItem -Path $ModulePath -Filter "*.py" -Recurse -ErrorAction SilentlyContinue
        if ($pythonFiles) {
            Write-AuditLog "INFO" "Python files found, executing Python checks"
            
            # Check requirements.txt
            if (Test-Path "$ModulePath\requirements.txt") {
                Write-AuditLog "PASS" "requirements.txt file exists"
            } else {
                Write-AuditLog "FAIL" "Missing requirements.txt file"
                $moduleResult = $false
            }
        }
        
        # Check Node.js files
        if (Test-Path "$ModulePath\package.json") {
            Write-AuditLog "INFO" "package.json found, executing Node.js checks"
            
            try {
                $packageJson = Get-Content "$ModulePath\package.json" | ConvertFrom-Json
                Write-AuditLog "PASS" "package.json format is valid"
            } catch {
                Write-AuditLog "FAIL" "package.json format is invalid"
                $moduleResult = $false
            }
        }
        
        # Check Dockerfile
        if (Test-Path "$ModulePath\Dockerfile") {
            Write-AuditLog "PASS" "Dockerfile exists"
            
            # Use Select-String for better encoding handling
            $fromInstructions = Select-String -Path "$ModulePath\Dockerfile" -Pattern "^FROM" -ErrorAction SilentlyContinue
            
            if ($fromInstructions) {
                Write-AuditLog "PASS" "Dockerfile contains FROM instruction"
            } else {
                Write-AuditLog "FAIL" "Dockerfile missing FROM instruction"
                $moduleResult = $false
            }
        } else {
            Write-AuditLog "FAIL" "Dockerfile does not exist"
            $moduleResult = $false
        }
    } catch {
        Write-AuditLog "FAIL" "Module audit exception: $($_.Exception.Message)"
        $moduleResult = $false
    }
    
    return $moduleResult
}

# Integration Test Function
function Invoke-IntegrationTest {
    Write-Header "System Integration Validation"
    
    $integrationResult = $true
    $vmHost = "192.168.1.7"
    $vmUser = "tjsga"
    $vmProjectPath = "~/projects"
    
    Write-AuditLog "INFO" "Using VM Docker environment for integration testing"
    
    # Check docker-compose file on VM
    try {
        Write-AuditLog "INFO" "Checking docker-compose file on VM"
        $composeCheck = ssh -o ConnectTimeout=10 $vmUser@$vmHost "test -f $vmProjectPath/docker-compose.prod.yml && echo 'found' || echo 'not_found'" 2>$null
        
        if ($composeCheck -eq "found") {
            Write-AuditLog "PASS" "VM Docker Compose config file exists: docker-compose.prod.yml"
        } else {
            Write-AuditLog "FAIL" "Docker Compose config file not found on VM"
            $integrationResult = $false
        }
    } catch {
        Write-AuditLog "FAIL" "Failed to check VM Docker Compose file: $($_.Exception.Message)"
        $integrationResult = $false
    }
    
    # Check container status on VM
    try {
        Write-AuditLog "INFO" "Checking container status on VM"
        $containerCount = ssh -o ConnectTimeout=10 $vmUser@$vmHost "cd $vmProjectPath && docker ps -q | wc -l" 2>$null
        
        if ([int]$containerCount -gt 0) {
            Write-AuditLog "PASS" "Found $containerCount running containers on VM"
        } else {
            Write-AuditLog "WARN" "No running containers found on VM"
        }
    } catch {
        Write-AuditLog "FAIL" "Failed to check VM container status: $($_.Exception.Message)"
        $integrationResult = $false
    }
    
    return $integrationResult
}

# Generate Final Report
function Write-FinalReport {
    $endTime = Get-Date
    $duration = ($endTime - $StartTime).TotalSeconds
    
    Write-Header "V1.4 Protocol Audit Results Summary"
    
    Write-Host "=== AUDIT SUMMARY ===" -ForegroundColor Cyan
    Write-Host "Audit Start Time: $($StartTime.ToString('yyyy-MM-dd HH:mm:ss'))"
    Write-Host "Audit End Time: $($endTime.ToString('yyyy-MM-dd HH:mm:ss'))"
    Write-Host "Audit Duration: $([math]::Round($duration, 2)) seconds"
    Write-Host "Passed Items: $PassCount" -ForegroundColor Green
    Write-Host "Failed Items: $FailCount" -ForegroundColor Red
    
    $totalChecks = $PassCount + $FailCount
    if ($totalChecks -gt 0) {
        $passRate = [math]::Round(($PassCount / $totalChecks) * 100, 2)
        Write-Host "Pass Rate: $passRate%" -ForegroundColor Yellow
        
        # Log final summary
        Write-AuditLog "INFO" "=== FINAL AUDIT SUMMARY ==="
        Write-AuditLog "INFO" "Total Checks: $totalChecks"
        Write-AuditLog "INFO" "Passed: $PassCount"
        Write-AuditLog "INFO" "Failed: $FailCount"
        Write-AuditLog "INFO" "Pass Rate: $passRate%"
    }
    
    if ($FailCount -eq 0) {
        Write-Host "OVERALL RESULT: PASS - System meets production readiness standards" -ForegroundColor Green
        Write-AuditLog "INFO" "OVERALL RESULT: PASS - System audit completed successfully"
        return $true
    } else {
        Write-Host "OVERALL RESULT: FAIL - System has $FailCount issues that need to be fixed" -ForegroundColor Red
        Write-AuditLog "INFO" "OVERALL RESULT: FAIL - System audit found $FailCount issues"
        return $false
    }
}

# Main Function
function Main {
    Write-Header "NeuroTrade Nexus V1.4 Protocol Audit Started"
    Write-AuditLog "INFO" "Audit start time: $($StartTime.ToString('yyyy-MM-dd HH:mm:ss'))"
    Write-AuditLog "INFO" "Audit log file: $AuditLog"
    
    # Check prerequisites
    Test-Prerequisites
    
    # Check VM Docker environment
    Test-VMDockerEnvironment
    
    # Define module list
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
    
    Write-Header "Module-Level Static Audit"
    
    # Execute module audits
    foreach ($module in $modules) {
        if (Invoke-ModuleAudit $module) {
            Write-AuditLog "PASS" "Module $module audit passed"
        } else {
            Write-AuditLog "FAIL" "Module $module audit failed"
        }
    }
    
    # Execute integration tests
    if (Invoke-IntegrationTest) {
        Write-AuditLog "PASS" "System integration validation passed"
    } else {
        Write-AuditLog "FAIL" "System integration validation failed"
    }
    
    # Generate final report
    $success = Write-FinalReport
    
    Write-AuditLog "INFO" "Audit log saved to: $AuditLog"
    
    if ($success) {
        exit 0
    } else {
        exit 1
    }
}  

# Execute main function
Main