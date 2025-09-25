# ===================================================================
# NeuroTrade Nexus (NTN) - System Audit Script V1.4
# Based on Common Protocol and NTN-DIAGNOSTIC-FIRST-PLAN-V2.4
# ===================================================================

param(
    [ValidateSet("DEBUG", "INFO", "WARN", "ERROR")]
    [string]$LogLevel = "INFO",
    [string]$VmHost = "",
    [string]$VmUser = "",
    [string]$VmProjectPath = "/home/ubuntu/NeuroTrade-Nexus",
    [switch]$SkipIntegrationTest
)

# Global variables
$global:AuditLog = @()
$global:PassCount = 0
$global:FailCount = 0
$global:StartTime = Get-Date

# Logging function
function Write-AuditLog {
    param(
        [string]$Level,
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # Set color based on level
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
        "DEBUG" { 
            if ($LogLevel -eq "DEBUG") { 
                Write-Host $logEntry -ForegroundColor Gray 
            }
        }
        default { Write-Host $logEntry }
    }
    
    $global:AuditLog += $logEntry
}

# Header function
function Write-Header {
    param([string]$Title)
    
    $border = "=" * 60
    Write-Host ""
    Write-Host $border -ForegroundColor Magenta
    Write-Host " $Title" -ForegroundColor Magenta
    Write-Host $border -ForegroundColor Magenta
    Write-Host ""
}

# Network connection test function
function Test-NetworkConnection {
    param(
        [string]$Host,
        [int]$Port,
        [int]$TimeoutSeconds = 3
    )
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connectTask = $tcpClient.ConnectAsync($Host, $Port)
        $timeoutTask = [System.Threading.Tasks.Task]::Delay($TimeoutSeconds * 1000)
        
        $completedTask = [System.Threading.Tasks.Task]::WaitAny(@($connectTask, $timeoutTask))
        
        if ($completedTask -eq 0 -and $tcpClient.Connected) {
            $tcpClient.Close()
            return $true
        } else {
            $tcpClient.Close()
            return $false
        }
    }
    catch {
        return $false
    }
}

# Optimized Invoke-WebRequest function with automatic RI parameter handling
function Invoke-OptimizedWebRequest {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Uri,
        
        [string]$Method = "GET",
        [int]$TimeoutSec = 30,
        [switch]$UseBasicParsing,
        [string]$ErrorAction = "Continue",
        [hashtable]$Headers = @{},
        [string]$Body,
        [string]$ContentType,
        [string]$RI  # Request Identifier parameter
    )
    
    # Prepare the base parameters for Invoke-WebRequest
    $webRequestParams = @{
        Uri = $Uri
        Method = $Method
        TimeoutSec = $TimeoutSec
        UseBasicParsing = $UseBasicParsing.IsPresent
        ErrorAction = $ErrorAction
    }
    
    # Auto-generate RI if not provided but needed
    if ([string]::IsNullOrEmpty($RI)) {
        # Check if the endpoint might need an RI parameter based on URL patterns
        if ($Uri -match "(api|health|status|check)" -and $Uri -notmatch "localhost") {
            $RI = "REQ-" + [System.Guid]::NewGuid().ToString().Substring(0, 8).ToUpper()
            Write-AuditLog "INFO" "Auto-generated RI parameter: $RI for $Uri"
        }
    }
    
    # Add RI to headers if present
    if (-not [string]::IsNullOrEmpty($RI)) {
        $Headers["X-Request-ID"] = $RI
        $Headers["Request-ID"] = $RI
        Write-AuditLog "DEBUG" "Added RI parameter to request headers: $RI"
    }
    
    # Add headers if any
    if ($Headers.Count -gt 0) {
        $webRequestParams["Headers"] = $Headers
    }
    
    # Add body if provided
    if (-not [string]::IsNullOrEmpty($Body)) {
        $webRequestParams["Body"] = $Body
    }
    
    # Add content type if provided
    if (-not [string]::IsNullOrEmpty($ContentType)) {
        $webRequestParams["ContentType"] = $ContentType
    }
    
    try {
        # Execute the optimized web request
        $response = Invoke-WebRequest @webRequestParams
        
        # Log successful request with RI if used
        if (-not [string]::IsNullOrEmpty($RI)) {
            Write-AuditLog "DEBUG" "Request completed successfully with RI: $RI, Status: $($response.StatusCode)"
        }
        
        return $response
    }
    catch {
        # Log failed request with RI if used
        if (-not [string]::IsNullOrEmpty($RI)) {
            Write-AuditLog "ERROR" "Request failed with RI: $RI, Error: $($_.Exception.Message)"
        }
        throw
    }
}

# Prerequisites check
function Test-Prerequisites {
    Write-Header "Prerequisites Check"
    
    $prereqResult = $true
    
    # Check Docker
    try {
        $dockerVersion = docker --version 2>$null
        if ($dockerVersion) {
            Write-AuditLog "PASS" "Docker installed: $dockerVersion"
        } else {
            Write-AuditLog "FAIL" "Docker not installed or unavailable"
            $prereqResult = $false
        }
    }
    catch {
        Write-AuditLog "FAIL" "Docker check failed: $($_.Exception.Message)"
        $prereqResult = $false
    }
    
    # Check Python
    try {
        $pythonVersion = python --version 2>$null
        if ($pythonVersion) {
            Write-AuditLog "PASS" "Python installed: $pythonVersion"
        } else {
            Write-AuditLog "WARN" "Python not installed or not in PATH"
        }
    }
    catch {
        Write-AuditLog "WARN" "Python check failed: $($_.Exception.Message)"
    }
    
    # Check Node.js
    try {
        $nodeVersion = node --version 2>$null
        if ($nodeVersion) {
            Write-AuditLog "PASS" "Node.js installed: $nodeVersion"
        } else {
            Write-AuditLog "WARN" "Node.js not installed or not in PATH"
        }
    }
    catch {
        Write-AuditLog "WARN" "Node.js check failed: $($_.Exception.Message)"
    }
    
    return $prereqResult
}

# Module audit
function Invoke-ModuleAudit {
    param([string]$ModulePath)
    
    $moduleResult = $true
    $moduleName = Split-Path $ModulePath -Leaf
    
    Write-AuditLog "INFO" "Starting audit for module: $moduleName"
    
    if (-not (Test-Path $ModulePath)) {
        Write-AuditLog "FAIL" "Module path does not exist: $ModulePath"
        return $false
    }
    
    # Python files check
    $pythonFiles = Get-ChildItem -Path $ModulePath -Filter "*.py" -Recurse -ErrorAction SilentlyContinue
    if ($pythonFiles -and $pythonFiles.Count -gt 0) {
        Write-AuditLog "INFO" "Found $($pythonFiles.Count) Python files"
        
        # Check requirements.txt
        $requirementsFile = Join-Path $ModulePath "requirements.txt"
        if (Test-Path $requirementsFile) {
            Write-AuditLog "PASS" "requirements.txt exists"
        } else {
            Write-AuditLog "WARN" "requirements.txt does not exist"
        }
        
        # Python syntax check
        try {
            foreach ($pyFile in $pythonFiles) {
                $syntaxCheck = python -m py_compile $pyFile.FullName 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-AuditLog "PASS" "Python syntax check passed: $($pyFile.Name)"
                } else {
                    Write-AuditLog "FAIL" "Python syntax error: $($pyFile.Name)"
                    $moduleResult = $false
                }
            }
        }
        catch {
            Write-AuditLog "WARN" "Python syntax check failed: $($_.Exception.Message)"
        }
    }
    
    # Node.js files check
    $packageJsonFile = Join-Path $ModulePath "package.json"
    if (Test-Path $packageJsonFile) {
        Write-AuditLog "PASS" "package.json exists"
        
        try {
            $packageContent = Get-Content $packageJsonFile -Raw | ConvertFrom-Json
            Write-AuditLog "PASS" "package.json format is correct"
            
            # NPM security audit
            Push-Location $ModulePath
            try {
                $auditResult = npm audit --audit-level=high --json 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-AuditLog "PASS" "NPM security audit passed"
                } else {
                    Write-AuditLog "WARN" "NPM security audit found high-severity vulnerabilities"
                }
            }
            catch {
                Write-AuditLog "WARN" "NPM audit execution failed: $($_.Exception.Message)"
            }
            finally {
                Pop-Location
            }
        }
        catch {
            Write-AuditLog "FAIL" "package.json format error: $($_.Exception.Message)"
            $moduleResult = $false
        }
    }
    
    # Dockerfile check
    $dockerFile = Join-Path $ModulePath "Dockerfile"
    if (Test-Path $dockerFile) {
        Write-AuditLog "PASS" "Dockerfile exists"
        
        $dockerContent = Get-Content $dockerFile
        
        # Check FROM instruction
        if ($dockerContent -match "^FROM\s+") {
            Write-AuditLog "PASS" "Dockerfile contains FROM instruction"
        } else {
            Write-AuditLog "FAIL" "Dockerfile missing FROM instruction"
            $moduleResult = $false
        }
        
        # Check EXPOSE instruction
        if ($dockerContent -match "^EXPOSE\s+") {
            Write-AuditLog "PASS" "Dockerfile contains EXPOSE instruction"
        } else {
            Write-AuditLog "WARN" "Dockerfile missing EXPOSE instruction"
        }
        
        # Check latest tag usage
        if ($dockerContent -match ":latest") {
            Write-AuditLog "WARN" "Dockerfile uses latest tag, recommend using specific version"
        }
    } else {
        Write-AuditLog "WARN" "Dockerfile does not exist"
    }
    
    return $moduleResult
}

# Integration test
function Invoke-IntegrationTest {
    Write-Header "Integration Test"
    
    # Check if integration test should be skipped
    if ($SkipIntegrationTest) {
        Write-AuditLog "INFO" "Skipping integration test (used -SkipIntegrationTest parameter)"
        return $true
    }
    
    # Check VM parameters
    if ([string]::IsNullOrEmpty($VmHost) -or [string]::IsNullOrEmpty($VmUser)) {
        Write-AuditLog "WARN" "VM connection parameters not provided (-VmHost and -VmUser), skipping integration test"
        Write-AuditLog "INFO" "Tip: Use -VmHost IP_ADDRESS -VmUser USERNAME parameters to enable integration test"
        return $true
    }
    
    $integrationResult = $true
    $vmHost = $VmHost
    $vmUser = $VmUser
    $vmProjectPath = $VmProjectPath
    
    Write-AuditLog "INFO" "Starting integration test - Target host: $vmHost"
    
    # Define test endpoints
    $endpoints = @(
        @{ Name = "APIForge"; Url = "http://$vmHost:8001/health" },
        @{ Name = "DataSpider"; Url = "http://$vmHost:8002/health" },
        @{ Name = "ScanPulse"; Url = "http://$vmHost:8003/health" },
        @{ Name = "OptiCore"; Url = "http://$vmHost:8004/api/v1/health" },
        @{ Name = "TradeGuard"; Url = "http://$vmHost:8005/health" },
        @{ Name = "NeuroHub"; Url = "http://$vmHost:8008/health" },
        @{ Name = "MMS"; Url = "http://$vmHost:8009/health" },
        @{ Name = "ReviewGuard"; Url = "http://$vmHost:8010/health" },
        @{ Name = "ASTS Console"; Url = "http://$vmHost:3000/health" },
        @{ Name = "TACoreService"; Url = "http://$vmHost:8012/health" },
        @{ Name = "AIStrategyAssistant"; Url = "http://$vmHost:8013/health" },
        @{ Name = "ObservabilityCenter"; Url = "http://$vmHost:3001/health" }
    )
    
    $successCount = 0
    $totalCount = $endpoints.Count
    
    foreach ($endpoint in $endpoints) {
        $uri = [System.Uri]$endpoint.Url
        $hostName = $uri.Host
        $portNumber = $uri.Port
        
        Write-AuditLog "INFO" "Testing endpoint: $($endpoint.Name) - $($endpoint.Url)"
        
        # Perform TCP connection test first
        if (-not (Test-NetworkConnection -Host $hostName -Port $portNumber -TimeoutSeconds 3)) {
            Write-AuditLog "FAIL" "$($endpoint.Name) - TCP connection failed ($hostName`:$portNumber)"
            $integrationResult = $false
            continue
        }
        
        try {
            # Optimized Invoke-WebRequest with automatic RI parameter handling
            $response = Invoke-OptimizedWebRequest -Uri $endpoint.Url -Method GET -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
            
            if ($response.StatusCode -eq 200) {
                Write-AuditLog "PASS" "$($endpoint.Name) - Health check passed (200 OK)"
                $successCount++
            } else {
                Write-AuditLog "FAIL" "$($endpoint.Name) - Health check failed ($($response.StatusCode))"
                $integrationResult = $false
            }
        }
        catch {
            Write-AuditLog "FAIL" "$($endpoint.Name) - Request failed: $($_.Exception.Message)"
            $integrationResult = $false
        }
    }
    
    # Calculate connectivity rate
    $connectivityRate = [math]::Round(($successCount / $totalCount) * 100, 2)
    Write-AuditLog "INFO" "Network connectivity rate: $connectivityRate% ($successCount/$totalCount)"
    
    if ($connectivityRate -ge 80) {
        Write-AuditLog "PASS" "Network connectivity test passed (>= 80%)"
    } else {
        Write-AuditLog "FAIL" "Network connectivity test failed (< 80%)"
        $integrationResult = $false
    }
    
    return $integrationResult
}

# Generate final report
function Write-FinalReport {
    $endTime = Get-Date
    $duration = ($endTime - $global:StartTime).TotalSeconds
    
    Write-Header "V1.4 Protocol Audit Results Summary"
    
    $summary = "=== AUDIT SUMMARY ===`n"
    $summary += "Audit start time: $($global:StartTime.ToString('yyyy-MM-dd HH:mm:ss'))`n"
    $summary += "Audit end time: $($endTime.ToString('yyyy-MM-dd HH:mm:ss'))`n"
    $summary += "Audit duration: $([math]::Round($duration, 2)) seconds`n"
    $summary += "Passed items: $global:PassCount`n"
    $summary += "Failed items: $global:FailCount`n"
    $summary += "Overall status: $(if ($global:FailCount -eq 0) { 'PASS' } else { 'FAIL' })"
    
    if ($global:FailCount -eq 0) {
        Write-Host $summary -ForegroundColor Green
    } else {
        Write-Host $summary -ForegroundColor Red
    }
    
    # Save audit log
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $logFile = "audit_report_$timestamp.log"
    $global:AuditLog | Out-File -FilePath $logFile -Encoding UTF8
    Write-AuditLog "INFO" "Audit log saved to: $logFile"
}

# Main function
function Main {
    Write-Header "NeuroTrade Nexus (NTN) System Audit V1.4"
    
    # Prerequisites check
    $prereqPassed = Test-Prerequisites
    
    if (-not $prereqPassed) {
        Write-AuditLog "ERROR" "Prerequisites check failed, terminating audit"
        Write-FinalReport
        exit 1
    }
    
    # Module list
    $modules = @(
        "01APIForge",
        "02DataSpider", 
        "03ScanPulse",
        "04OptiCore",
        "05TradeGuard",
        "06TradeGuard",
        "07TradeGuard",
        "08NeuroHub",
        "09MMS",
        "10ReviewGuard",
        "11ASTSConsole",
        "12TACoreService",
        "13AIStrategyAssistant",
        "14ObservabilityCenter"
    )
    
    # Execute module-level audit
    Write-Header "Module-level Static Audit"
    foreach ($module in $modules) {
        $modulePath = Join-Path (Get-Location) $module
        Invoke-ModuleAudit -ModulePath $modulePath
    }
    
    # Execute integration test
    Invoke-IntegrationTest
    
    # Generate final report
    Write-FinalReport
    
    # Return exit code
    if ($global:FailCount -eq 0) {
        exit 0
    } else {
        exit 1
    }
}

# Execute main function
Main