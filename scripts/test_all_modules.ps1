# NeuroTrade Nexus (NTN) - Batch Module Health Check Script
# Version: 1.0
# Function: Automated testing of all 14 modules health status

param(
    [switch]$ShowDetails,
    [int]$TimeoutSeconds = 30
)

# Error handling settings
$ErrorActionPreference = "Continue"

# Module configuration definitions
$modules = @(
    @{ Name = "APIForge"; Uri = "http://localhost:8000/health"; Port = 8000 },
    @{ Name = "DataSpider"; Uri = "http://localhost:5000/health"; Port = 5000 },
    @{ Name = "ScanPulse"; Uri = "N/A"; Port = "N/A"; Note = "ZMQ only, check container status" },
    @{ Name = "OptiCore"; Uri = "http://localhost:8002/health"; Port = 8002 },
    @{ Name = "TradeGuard"; Uri = "http://localhost:3000/api/health"; Port = 3000 },
    @{ Name = "NeuroHub"; Uri = "http://localhost:8003/health"; Port = 8003 },
    @{ Name = "MMS"; Uri = "http://localhost:8004/health"; Port = 8004 },
    @{ Name = "ReviewGuard"; Uri = "http://localhost:8005/health"; Port = 8005 },
    @{ Name = "ReviewGuardFrontend"; Uri = "http://localhost:3001"; Port = 3001 },
    @{ Name = "ASTSConsole"; Uri = "http://localhost:80/health"; Port = 80 },
    @{ Name = "TACoreService"; Uri = "http://localhost:8006/health"; Port = 8006 },
    @{ Name = "AIStrategyAssistant"; Uri = "http://localhost:8007/health"; Port = 8007 },
    @{ Name = "ObservabilityCenter"; Uri = "http://localhost:3002/health"; Port = 3002 }
)

function Test-SingleModule {
    param(
        [hashtable]$Module,
        [int]$Timeout = 30
    )
    
    if ($Module.Uri -eq "N/A") {
        # For modules without HTTP interface, check Docker container status
        try {
            $containerName = "ntn-" + $Module.Name.ToLower() -replace "scanpulse", "scan-pulse"
            $containerStatus = docker ps --filter "name=$containerName" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-Object -Skip 1
            
            if ($containerStatus) {
                return @{
                    Name = $Module.Name
                    Success = $true
                    Status = "Container Running"
                    Details = $containerStatus
                    Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                }
            } else {
                return @{
                    Name = $Module.Name
                    Success = $false
                    Status = "Container Not Found"
                    Error = "Container $containerName not found or not running"
                    Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                }
            }
        } catch {
            return @{
                Name = $Module.Name
                Success = $false
                Status = "Docker Check Failed"
                Error = $_.Exception.Message
                Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            }
        }
    } else {
        # For modules with HTTP interface, use health check script
        try {
            $scriptPath = Join-Path $PSScriptRoot "test_health_check.ps1"
            
            if ($ShowDetails) {
                $result = & $scriptPath -Uri $Module.Uri -TimeoutSeconds $Timeout -ShowDetails
            } else {
                $result = & $scriptPath -Uri $Module.Uri -TimeoutSeconds $Timeout
            }
            
            if ($LASTEXITCODE -eq 0) {
                $healthData = $result | ConvertFrom-Json
                return @{
                    Name = $Module.Name
                    Success = $true
                    Status = "$($healthData.status_code) $($healthData.status_description)"
                    Uri = $Module.Uri
                    Port = $Module.Port
                    Timestamp = $healthData.timestamp
                }
            } else {
                $errorData = $result | ConvertFrom-Json
                return @{
                    Name = $Module.Name
                    Success = $false
                    Status = "Health Check Failed"
                    Uri = $Module.Uri
                    Port = $Module.Port
                    Error = $errorData.error
                    Timestamp = $errorData.timestamp
                }
            }
        } catch {
            return @{
                Name = $Module.Name
                Success = $false
                Status = "Script Execution Failed"
                Uri = $Module.Uri
                Port = $Module.Port
                Error = $_.Exception.Message
                Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            }
        }
    }
}

# Main execution logic
Write-Host "=== NeuroTrade Nexus (NTN) - Module Health Check ===" -ForegroundColor Cyan
Write-Host "Start Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

$results = @()
$successCount = 0
$failureCount = 0

foreach ($module in $modules) {
    Write-Host "Checking: $($module.Name)" -ForegroundColor Yellow
    
    $result = Test-SingleModule -Module $module -Timeout $TimeoutSeconds
    $results += $result
    
    if ($result.Success) {
        Write-Host "  Success: $($result.Status)" -ForegroundColor Green
        $successCount++
    } else {
        Write-Host "  Failed: $($result.Status): $($result.Error)" -ForegroundColor Red
        $failureCount++
    }
    
    Write-Host ""
}

# Generate summary report
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Total Modules: $($modules.Count)" -ForegroundColor White
Write-Host "Success: $successCount" -ForegroundColor Green
Write-Host "Failed: $failureCount" -ForegroundColor Red
Write-Host "Success Rate: $([math]::Round(($successCount / $modules.Count) * 100, 2))%" -ForegroundColor $(if ($successCount -eq $modules.Count) { 'Green' } else { 'Yellow' })
Write-Host ""

# Save detailed report to file
$reportPath = "E:\NeuroTrade Nexus (NTN)\logs\module_health_report_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').json"
$reportData = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    total_modules = $modules.Count
    success_count = $successCount
    failure_count = $failureCount
    success_rate = [math]::Round(($successCount / $modules.Count) * 100, 2)
    results = $results
}

$reportData | ConvertTo-Json -Depth 4 | Out-File -FilePath $reportPath -Encoding UTF8
Write-Host "Detailed report saved to: $reportPath" -ForegroundColor Gray

# Return appropriate exit code
if ($failureCount -eq 0) {
    Write-Host "All modules health check passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "$failureCount modules health check failed" -ForegroundColor Red
    exit 1
}