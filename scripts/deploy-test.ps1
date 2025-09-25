# AI Trading System V1.2 - Deployment Test Script
# Used to verify one-click startup command and container health status
# Corresponds to test plan phase 2: System deployment and Docker containerization health check

param(
    [switch]$SkipBuild,
    [switch]$Verbose,
    [int]$HealthCheckTimeout = 300
)

# Set error handling
$ErrorActionPreference = "Stop"

# Color output functions
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success { param([string]$Message) Write-ColorOutput $Message "Green" }
function Write-Warning { param([string]$Message) Write-ColorOutput $Message "Yellow" }
function Write-Error { param([string]$Message) Write-ColorOutput $Message "Red" }
function Write-Info { param([string]$Message) Write-ColorOutput $Message "Cyan" }

# Test result recording
$TestResults = @{
    "DEPLOY-01" = @{ "Status" = "PENDING"; "Description" = "One-click system startup" }
    "DEPLOY-02" = @{ "Status" = "PENDING"; "Description" = "Verify all container running status" }
    "DEPLOY-03" = @{ "Status" = "PENDING"; "Description" = "Verify all container health status" }
}

# Expected service list
$ExpectedServices = @(
    "ntn-redis-prod",
    "ntn-api-factory-prod",
    "ntn-info-crawler-prod",
    "ntn-scanner-prod",
    "ntn-strategy-optimizer-prod",
    "ntn-trade-guard-prod",
    "ntn-neuro-hub-prod",
    "ntn-mms-prod",
    "ntn-review-guard-backend-prod",
    "ntn-review-guard-frontend-prod",
    "ntn-asts-console-prod",
    "ntn-tacore-service-prod",
    "ntn-ai-strategy-assistant-prod",
    "ntn-observability-center-prod",
    "ntn-nginx-prod"
)

# Services requiring health checks
$HealthCheckServices = @(
    "ntn-redis-prod",
    "ntn-api-factory-prod",
    "ntn-info-crawler-prod",
    "ntn-scanner-prod",
    "ntn-strategy-optimizer-prod",
    "ntn-trade-guard-prod",
    "ntn-neuro-hub-prod",
    "ntn-mms-prod",
    "ntn-review-guard-backend-prod",
    "ntn-review-guard-frontend-prod",
    "ntn-asts-console-prod",
    "ntn-tacore-service-prod",
    "ntn-ai-strategy-assistant-prod",
    "ntn-observability-center-prod",
    "ntn-nginx-prod"
)

function Test-DockerCompose {
    Write-Info "Checking if Docker Compose is available..."
    try {
        $version = docker-compose --version
        Write-Success "Docker Compose version: $version"
        return $true
    }
    catch {
        Write-Error "Docker Compose is not installed or available"
        return $false
    }
}

function Test-DockerDaemon {
    Write-Info "Checking if Docker daemon is running..."
    try {
        docker info | Out-Null
        Write-Success "Docker daemon is running normally"
        return $true
    }
    catch {
        Write-Error "Docker daemon is not running"
        return $false
    }
}

function Stop-ExistingContainers {
    Write-Info "Stopping existing containers..."
    try {
        docker-compose -f docker-compose.prod.yml down --remove-orphans
        Write-Success "Existing containers stopped"
    }
    catch {
        Write-Warning "Warning when stopping containers: $($_.Exception.Message)"
    }
}

function Start-System {
    Write-Info "=== Executing test step DEPLOY-01: One-click system startup ==="
    
    try {
        $buildFlag = if ($SkipBuild) { "" } else { "--build" }
        $command = "docker-compose -f docker-compose.prod.yml up $buildFlag -d"
        
        Write-Info "Executing command: $command"
        
        if ($SkipBuild) {
            docker-compose -f docker-compose.prod.yml up -d
        } else {
            docker-compose -f docker-compose.prod.yml up --build -d
        }
        
        $TestResults["DEPLOY-01"]["Status"] = "PASSED"
        Write-Success "✓ DEPLOY-01: One-click startup command executed successfully"
        return $true
    }
    catch {
        $TestResults["DEPLOY-01"]["Status"] = "FAILED"
        $TestResults["DEPLOY-01"]["Error"] = $_.Exception.Message
        Write-Error "✗ DEPLOY-01: One-click startup command failed: $($_.Exception.Message)"
        return $false
    }
}

function Test-ContainerStatus {
    Write-Info "=== Executing test step DEPLOY-02: Verify all container running status ==="
    
    try {
        # Wait for containers to start
        Write-Info "Waiting for containers to start..."
        Start-Sleep -Seconds 30
        
        # Get container status
        $psOutput = docker-compose -f docker-compose.prod.yml ps
        
        if (-not $psOutput) {
            throw "Unable to get container status information"
        }
        
        $runningContainers = @()
        $failedContainers = @()
        
        # Parse docker-compose ps output
        $lines = $psOutput -split "`n" | Where-Object { $_ -match "ntn-.*-prod" }
        
        foreach ($line in $lines) {
            if ($line -match "(ntn-[^\s]+)\s+.*\s+(Up|running|healthy)" -or $line -match "(ntn-[^\s]+).*Up") {
                $containerName = $matches[1]
                $runningContainers += $containerName
                
                if ($Verbose) {
                    Write-Info "Container: $containerName, Status: Running"
                }
            }
            elseif ($line -match "(ntn-[^\s]+)\s+.*\s+([^\s]+)" -and $line -notmatch "Up") {
                $containerName = $matches[1]
                $status = $matches[2]
                $failedContainers += @{ "Name" = $containerName; "Status" = $status }
                
                if ($Verbose) {
                    Write-Info "Container: $containerName, Status: $status"
                }
            }
        }
        
        # Check if all expected services are running
        $missingServices = @()
        foreach ($expectedService in $ExpectedServices) {
            if ($runningContainers -notcontains $expectedService) {
                $missingServices += $expectedService
            }
        }
        
        if ($failedContainers.Count -eq 0 -and $missingServices.Count -eq 0) {
            $TestResults["DEPLOY-02"]["Status"] = "PASSED"
            Write-Success "✓ DEPLOY-02: All $($runningContainers.Count) containers are running"
            
            if ($Verbose) {
                Write-Info "Running containers:"
                $runningContainers | ForEach-Object { Write-Info "  - $_" }
            }
            
            return $true
        } else {
            $TestResults["DEPLOY-02"]["Status"] = "FAILED"
            $errorMsg = ""
            
            if ($failedContainers.Count -gt 0) {
                $errorMsg += "Failed containers: $($failedContainers | ForEach-Object { "$($_.Name)($($_.Status))" } | Join-String ', '). "
            }
            
            if ($missingServices.Count -gt 0) {
                $errorMsg += "Missing services: $($missingServices -join ', ')"
            }
            
            $TestResults["DEPLOY-02"]["Error"] = $errorMsg
            Write-Error "✗ DEPLOY-02: $errorMsg"
            return $false
        }
    }
    catch {
        $TestResults["DEPLOY-02"]["Status"] = "FAILED"
        $TestResults["DEPLOY-02"]["Error"] = $_.Exception.Message
        Write-Error "✗ DEPLOY-02: Failed to verify container status: $($_.Exception.Message)"
        return $false
    }
}

function Test-ContainerHealth {
    Write-Info "=== Executing test step DEPLOY-03: Verify all container health status ==="
    
    try {
        Write-Info "Waiting for health checks to complete (max wait time: $HealthCheckTimeout seconds)..."
        
        $healthyContainers = @()
        $unhealthyContainers = @()
        $startTime = Get-Date
        
        do {
            $healthyContainers = @()
            $unhealthyContainers = @()
            
            foreach ($serviceName in $HealthCheckServices) {
                try {
                    $healthStatus = docker inspect $serviceName --format='{{.State.Health.Status}}' 2>$null
                    
                    if ($healthStatus -eq "healthy" -or $healthStatus -eq "") {
                        # Empty string means no health check configured, consider as healthy
                        if ($healthStatus -eq "") {
                            # For containers without health check, check if running
                            $isRunning = docker inspect $serviceName --format='{{.State.Running}}' 2>$null
                            if ($isRunning -eq "true") {
                                $healthyContainers += $serviceName
                            } else {
                                $unhealthyContainers += @{ "Name" = $serviceName; "Status" = "not running" }
                            }
                        } else {
                            $healthyContainers += $serviceName
                        }
                    } else {
                        $unhealthyContainers += @{ "Name" = $serviceName; "Status" = $healthStatus }
                    }
                }
                catch {
                    $unhealthyContainers += @{ "Name" = $serviceName; "Status" = "check failed" }
                }
            }
            
            $elapsedTime = (Get-Date) - $startTime
            
            if ($Verbose) {
                Write-Info "Health check progress: $($healthyContainers.Count)/$($HealthCheckServices.Count) (elapsed: $([math]::Round($elapsedTime.TotalSeconds))s)"
            }
            
            if ($unhealthyContainers.Count -eq 0) {
                break
            }
            
            Start-Sleep -Seconds 10
            
        } while ($elapsedTime.TotalSeconds -lt $HealthCheckTimeout)
        
        if ($unhealthyContainers.Count -eq 0) {
            $TestResults["DEPLOY-03"]["Status"] = "PASSED"
            Write-Success "✓ DEPLOY-03: All $($healthyContainers.Count) containers passed health checks"
            
            if ($Verbose) {
                Write-Info "Healthy containers:"
                $healthyContainers | ForEach-Object { Write-Info "  - $_" }
            }
            
            return $true
        } else {
            $TestResults["DEPLOY-03"]["Status"] = "FAILED"
            $errorMsg = "Unhealthy containers: $($unhealthyContainers | ForEach-Object { "$($_.Name)($($_.Status))" } | Join-String ', ')"
            $TestResults["DEPLOY-03"]["Error"] = $errorMsg
            Write-Error "✗ DEPLOY-03: $errorMsg"
            
            # Show detailed container logs
            Write-Info "Getting logs for failed containers..."
            foreach ($container in $unhealthyContainers) {
                Write-Warning "=== $($container.Name) logs ==="
                try {
                    docker logs --tail 20 $container.Name
                }
                catch {
                    Write-Error "Cannot get logs for $($container.Name)"
                }
            }
            
            return $false
        }
    }
    catch {
        $TestResults["DEPLOY-03"]["Status"] = "FAILED"
        $TestResults["DEPLOY-03"]["Error"] = $_.Exception.Message
        Write-Error "✗ DEPLOY-03: Failed to verify container health status: $($_.Exception.Message)"
        return $false
    }
}

function Show-TestSummary {
    Write-Info "`n=== Test Results Summary ==="
    
    $passedTests = 0
    $failedTests = 0
    
    foreach ($testId in $TestResults.Keys) {
        $result = $TestResults[$testId]
        $status = $result.Status
        $description = $result.Description
        
        if ($status -eq "PASSED") {
            Write-Success "✓ $testId`: $description"
            $passedTests++
        } elseif ($status -eq "FAILED") {
            Write-Error "✗ $testId`: $description"
            if ($result.Error) {
                Write-Error "  Error: $($result.Error)"
            }
            $failedTests++
        } else {
            Write-Warning "⚠ $testId`: $description (not executed)"
        }
    }
    
    Write-Info "`nTotal: $($passedTests + $failedTests) tests, $passedTests passed, $failedTests failed"
    
    if ($failedTests -eq 0) {
        Write-Success "`n🎉 All tests passed! System deployed and running normally."
        Write-Info "`nSystem can be accessed via the following URLs:"
        Write-Info "  - Main Frontend: http://localhost:3000"
        Write-Info "  - API Factory: http://localhost:8000"
        Write-Info "  - Nginx Proxy: http://localhost:80"
        Write-Info "  - Monitoring Dashboard: http://localhost:3005"
        Write-Info "  - Grafana: http://localhost:3006"
        return $true
    } else {
        Write-Error "`n❌ Some tests failed, please check the error messages above and fix the issues."
        return $false
    }
}

function Save-TestReport {
    $reportPath = "test-results-$(Get-Date -Format 'yyyyMMdd-HHmmss').json"
    $TestResults | ConvertTo-Json -Depth 3 | Out-File -FilePath $reportPath -Encoding UTF8
    Write-Info "Test report saved to: $reportPath"
}

# Main execution flow
function Main {
    Write-Info "=== AI Trading System V1.2 - Deployment Test Started ==="
    Write-Info "Test time: $(Get-Date)"
    Write-Info "Test parameters: SkipBuild=$SkipBuild, Verbose=$Verbose, HealthCheckTimeout=$HealthCheckTimeout"
    
    # Pre-checks
    if (-not (Test-DockerCompose)) { exit 1 }
    if (-not (Test-DockerDaemon)) { exit 1 }
    
    # Clean up existing containers
    Stop-ExistingContainers
    
    # Execute test steps
    $step1Success = Start-System
    $step2Success = $false
    $step3Success = $false
    
    if ($step1Success) {
        $step2Success = Test-ContainerStatus
        
        if ($step2Success) {
            $step3Success = Test-ContainerHealth
        }
    }
    
    # Show test summary
    $allTestsPassed = Show-TestSummary
    
    # Save test report
    Save-TestReport
    
    # Return appropriate exit code
    if ($allTestsPassed) {
        Write-Success "`nDeployment test completed, system running normally!"
        exit 0
    } else {
        Write-Error "`nDeployment test failed, please check errors and retry."
        exit 1
    }
}

# Execute main function
Main