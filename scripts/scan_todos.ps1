# TODO Scan Script for NeuroTrade Nexus
# Simple version to avoid encoding issues

Write-Host "=== NeuroTrade Nexus TODO Scan Report ===" -ForegroundColor Cyan
Write-Host "Scan Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# Define modules
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

# Statistics
$totalPending = 0
$totalCompleted = 0
$highPriorityPending = 0
$modulesWithTodos = 0

Write-Host "=== Module TODO Files Scan ===" -ForegroundColor Yellow

foreach ($module in $modules) {
    $todoPath = Join-Path $module ".trae\TODO.md"
    $altTodoPath = Join-Path $module "TODO.md"
    
    $todoFile = $null
    if (Test-Path $todoPath) {
        $todoFile = $todoPath
    } elseif (Test-Path $altTodoPath) {
        $todoFile = $altTodoPath
    }
    
    $pendingTasks = 0
    $completedTasks = 0
    $highPriorityTasks = 0
    
    if ($todoFile) {
        $content = Get-Content $todoFile -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($content) {
            foreach ($line in $content) {
                if ($line -match "^\s*-\s*\[\s*\].*") {
                    $pendingTasks++
                    $totalPending++
                    
                    if ($line -match "priority:\s*High") {
                        $highPriorityTasks++
                        $highPriorityPending++
                    }
                } elseif ($line -match "^\s*-\s*\[x\].*") {
                    $completedTasks++
                    $totalCompleted++
                }
            }
        }
        
        if ($pendingTasks -gt 0 -or $completedTasks -gt 0) {
            $modulesWithTodos++
        }
        
        $status = if ($pendingTasks -eq 0) { "[OK]" } elseif ($highPriorityTasks -gt 0) { "[HIGH]" } else { "[PENDING]" }
        
        Write-Host "$status ${module}: Pending $pendingTasks, Completed $completedTasks" -NoNewline
        
        if ($highPriorityTasks -gt 0) {
            Write-Host " (High Priority: $highPriorityTasks)" -ForegroundColor Red -NoNewline
        }
        
        Write-Host ""
    } else {
        Write-Host "[MISSING] ${module}: No TODO file" -ForegroundColor Gray
    }
}

Write-Host ""

# Scan code TODOs
Write-Host "=== Code TODO Comments Scan ===" -ForegroundColor Yellow

$codePatterns = @("TODO", "FIXME", "HACK")
$fileExtensions = @("*.py", "*.js", "*.ts", "*.tsx")

$codeTodoCount = 0
foreach ($pattern in $codePatterns) {
    foreach ($ext in $fileExtensions) {
        $files = Get-ChildItem -Path "." -Filter $ext -Recurse -File | Where-Object {
            $_.FullName -notmatch "node_modules|__pycache__|\.git|dist|build"
        }
        
        foreach ($file in $files) {
            $content = Get-Content $file.FullName -Encoding UTF8 -ErrorAction SilentlyContinue
            if ($content) {
                $lineNumber = 0
                foreach ($line in $content) {
                    $lineNumber++
                    if ($line -match $pattern) {
                        $priority = "Medium"
                        if ($line -match "\[High\]") { $priority = "High" }
                        elseif ($line -match "\[Low\]") { $priority = "Low" }
                        
                        $relativePath = $file.FullName.Replace((Get-Location).Path, ".")
                        Write-Host "[$priority] ${relativePath}:$lineNumber - $($line.Trim())"
                        $codeTodoCount++
                    }
                }
            }
        }
    }
}

if ($codeTodoCount -eq 0) {
    Write-Host "No code TODO comments found" -ForegroundColor Green
}

Write-Host ""

# Summary
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Total Modules: $($modules.Count)"
Write-Host "Modules with TODOs: $modulesWithTodos"
Write-Host "Total Pending Tasks: $totalPending" -ForegroundColor Yellow
Write-Host "High Priority Pending: $highPriorityPending" -ForegroundColor Red
Write-Host "Total Completed Tasks: $totalCompleted" -ForegroundColor Green
Write-Host "Code TODO Comments: $codeTodoCount" -ForegroundColor Magenta

Write-Host ""
Write-Host "=== Recommendations ===" -ForegroundColor Cyan

if ($highPriorityPending -gt 0) {
    Write-Host "[WARNING] Found $highPriorityPending high priority pending tasks" -ForegroundColor Red
}

if ($codeTodoCount -gt 10) {
    Write-Host "[WARNING] Many TODO comments in code ($codeTodoCount), consider cleanup" -ForegroundColor Yellow
}

if ($modulesWithTodos -lt $modules.Count) {
    $missingCount = $modules.Count - $modulesWithTodos
    Write-Host "[INFO] $missingCount modules missing TODO files" -ForegroundColor Blue
}

if ($totalPending -eq 0 -and $codeTodoCount -eq 0) {
    Write-Host "[SUCCESS] All TODO tasks completed!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Scan completed!" -ForegroundColor Green