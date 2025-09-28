# NeuroTrade Nexus V1.4 Protocol Audit Script

$StartTime = Get-Date
$PassCount = 0
$FailCount = 0

Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  NeuroTrade Nexus V1.4 Protocol Audit Started" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

# Check Prerequisites
Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  Checking Prerequisites" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

# Check curl
$curlTest = Get-Command curl -ErrorAction SilentlyContinue
if ($curlTest) {
    Write-Host "[PASS] curl tool available" -ForegroundColor Green
    $PassCount++
} else {
    Write-Host "[FAIL] curl tool not available" -ForegroundColor Red
    $FailCount++
}

# Check Node.js
$nodeTest = Get-Command node -ErrorAction SilentlyContinue
if ($nodeTest) {
    $nodeVersion = node --version
    Write-Host "[PASS] Node.js available: $nodeVersion" -ForegroundColor Green
    $PassCount++
} else {
    Write-Host "[FAIL] Node.js not available" -ForegroundColor Red
    $FailCount++
}

# Check SSH
$sshTest = Get-Command ssh -ErrorAction SilentlyContinue
if ($sshTest) {
    Write-Host "[PASS] SSH tool available" -ForegroundColor Green
    $PassCount++
} else {
    Write-Host "[FAIL] SSH tool not available" -ForegroundColor Red
    $FailCount++
}

# Check VM Docker Environment
Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  Checking VM Docker Environment" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

$vmHost = "192.168.1.7"
$vmUser = "tjsga"

Write-Host "[INFO] Testing VM SSH connection: $vmUser@$vmHost" -ForegroundColor Cyan

# Test SSH connection
$sshResult = ssh -o ConnectTimeout=10 -o BatchMode=yes $vmUser@$vmHost "echo connected" 2>$null
if ($sshResult -eq "connected") {
    Write-Host "[PASS] VM SSH connection successful" -ForegroundColor Green
    $PassCount++
    
    # Check Docker
    $dockerVersion = ssh -o ConnectTimeout=10 $vmUser@$vmHost "docker --version" 2>$null
    if ($dockerVersion) {
        Write-Host "[PASS] VM Docker available: $dockerVersion" -ForegroundColor Green
        $PassCount++
    } else {
        Write-Host "[FAIL] VM Docker not available" -ForegroundColor Red
        $FailCount++
    }
    
    # Check Docker service
    $dockerStatus = ssh -o ConnectTimeout=10 $vmUser@$vmHost "systemctl is-active docker" 2>$null
    if ($dockerStatus -eq "active") {
        Write-Host "[PASS] VM Docker service running" -ForegroundColor Green
        $PassCount++
    } else {
        Write-Host "[FAIL] VM Docker service not running" -ForegroundColor Red
        $FailCount++
    }
    
} else {
    Write-Host "[FAIL] VM SSH connection failed" -ForegroundColor Red
    $FailCount++
}

# Module Audit
Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  Module Static Audit" -ForegroundColor Blue
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
    "11_ASTS_Console",
    "12TACoreService",
    "13AI Strategy Assistant",
    "14Observability Center"
)

foreach ($module in $modules) {
    Write-Host "[INFO] Auditing module: $module" -ForegroundColor Cyan
    
    if (Test-Path $module) {
        # Check Dockerfile
        if (Test-Path "$module\Dockerfile") {
            Write-Host "[PASS] $module - Dockerfile exists" -ForegroundColor Green
            $PassCount++
        } else {
            Write-Host "[FAIL] $module - Dockerfile missing" -ForegroundColor Red
            $FailCount++
        }
        
        # Check package.json
        if (Test-Path "$module\package.json") {
            Write-Host "[PASS] $module - package.json exists" -ForegroundColor Green
            $PassCount++
        }
        
        # Check requirements.txt
        if (Test-Path "$module\requirements.txt") {
            Write-Host "[PASS] $module - requirements.txt exists" -ForegroundColor Green
            $PassCount++
        }
        
    } else {
        Write-Host "[FAIL] Module directory $module does not exist" -ForegroundColor Red
        $FailCount++
    }
}

# Integration Test
Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  System Integration Verification" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

$vmProjectPath = "~/projects"

# Check docker-compose file on VM
Write-Host "[INFO] Checking VM docker-compose file" -ForegroundColor Cyan
$composeCheck = ssh -o ConnectTimeout=10 $vmUser@$vmHost "test -f $vmProjectPath/docker-compose.prod.yml; echo `$?" 2>$null

if ($composeCheck -eq "0") {
    Write-Host "[PASS] VM Docker Compose config file exists" -ForegroundColor Green
    $PassCount++
} else {
    Write-Host "[FAIL] Docker Compose config file not found on VM" -ForegroundColor Red
    $FailCount++
}

# Check container status
Write-Host "[INFO] Checking VM container status" -ForegroundColor Cyan
$containerCount = ssh -o ConnectTimeout=10 $vmUser@$vmHost "cd $vmProjectPath; docker ps -q | wc -l" 2>$null

if ($containerCount -and [int]$containerCount -gt 0) {
    Write-Host "[PASS] Found $containerCount running containers on VM" -ForegroundColor Green
    $PassCount++
} else {
    Write-Host "[WARN] No running containers found on VM" -ForegroundColor Yellow
}

# Generate Final Report
Write-Host ""
Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  V1.4 Protocol Audit Summary" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue
Write-Host ""

$endTime = Get-Date
$duration = ($endTime - $StartTime).TotalSeconds

Write-Host "=== AUDIT SUMMARY ===" -ForegroundColor Cyan
Write-Host "Audit Start Time: $($StartTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Host "Audit End Time: $($endTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Host "Audit Duration: $([math]::Round($duration, 2)) seconds"
Write-Host "Passed Checks: $PassCount" -ForegroundColor Green
Write-Host "Failed Checks: $FailCount" -ForegroundColor Red

$totalChecks = $PassCount + $FailCount
if ($totalChecks -gt 0) {
    $passRate = [math]::Round(($PassCount / $totalChecks) * 100, 2)
    Write-Host "Pass Rate: $passRate%" -ForegroundColor Yellow
}

if ($FailCount -eq 0) {
    Write-Host "OVERALL RESULT: PASS - System meets production readiness standards" -ForegroundColor Green
    exit 0
} else {
    Write-Host "OVERALL RESULT: FAIL - System has $FailCount issues that need to be fixed" -ForegroundColor Red
    exit 1
}