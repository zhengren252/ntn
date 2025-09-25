# SSH Connection Script for Ubuntu VMs
# Author: NeuroTrade Nexus Team
# Version: 1.0.0

param(
    [string]$VMIndex = "1",
    [string]$Command = "",
    [switch]$Interactive = $false
)

# VM Configuration
$VM1_IP = "192.168.1.19"
$VM2_IP = "192.168.1.20"
$Username = "tjsga"
$Password = "791106"

# Color output function
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Test SSH client
function Test-SSHClient {
    try {
        $sshVersion = ssh -V 2>&1
        Write-ColorOutput "SSH client installed: $sshVersion" "Green"
        return $true
    }
    catch {
        Write-ColorOutput "SSH client not found. Please install OpenSSH client." "Red"
        return $false
    }
}

# Test VM connection
function Test-VMConnection {
    param([string]$IP)
    Write-ColorOutput "Testing connection to $IP..." "Yellow"
    $pingResult = Test-NetConnection -ComputerName $IP -Port 22 -WarningAction SilentlyContinue
    if ($pingResult.TcpTestSucceeded) {
        Write-ColorOutput "Connection OK ($IP:22)" "Green"
        return $true
    } else {
        Write-ColorOutput "Cannot connect to $IP:22" "Red"
        return $false
    }
}

# Main execution
Write-ColorOutput "NeuroTrade Nexus - Ubuntu VM SSH Connection Tool" "Cyan"
Write-ColorOutput "Version: 1.0.0" "Gray"
Write-ColorOutput "" "White"

# Check SSH client
if (-not (Test-SSHClient)) {
    exit 1
}

# Select VM IP
$selectedIP = ""
if ($VMIndex -eq "1") {
    $selectedIP = $VM1_IP
    Write-ColorOutput "Selected VM: Ubuntu-VM-01 ($VM1_IP)" "Green"
} elseif ($VMIndex -eq "2") {
    $selectedIP = $VM2_IP
    Write-ColorOutput "Selected VM: Ubuntu-VM-02 ($VM2_IP)" "Green"
} else {
    Write-ColorOutput "Invalid VM index: $VMIndex. Use 1 or 2." "Red"
    exit 1
}

# Test connection
if (-not (Test-VMConnection -IP $selectedIP)) {
    Write-ColorOutput "Connection test failed. Please check network configuration." "Red"
    exit 1
}

# Execute SSH connection
if ($Interactive -or [string]::IsNullOrEmpty($Command)) {
    Write-ColorOutput "Starting interactive SSH session to $selectedIP..." "Cyan"
    Write-ColorOutput "Password: $Password" "Yellow"
    Write-ColorOutput "Exit command: exit" "Gray"
    ssh "$Username@$selectedIP"
} else {
    Write-ColorOutput "Executing remote command: $Command" "Cyan"
    Write-ColorOutput "Password: $Password" "Yellow"
    ssh -o StrictHostKeyChecking=no "$Username@$selectedIP" "$Command"
}

if ($LASTEXITCODE -eq 0) {
    Write-ColorOutput "SSH operation completed successfully" "Green"
} else {
    Write-ColorOutput "SSH operation failed" "Red"
    exit 1
}