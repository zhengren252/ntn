# SSH Key Setup Script for VM Authentication
# This script copies the local SSH public key to the remote VM's authorized_keys file

param(
    [string]$VMHost = "192.168.1.20",
    [string]$Username = "tjsga",
    [string]$Password = "791106"
)

# Function to log messages with timestamp
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message"
}

Write-Log "Starting SSH key setup for $Username@$VMHost"

# Get the public key content
$publicKeyPath = "$env:USERPROFILE\.ssh\id_rsa.pub"
if (-not (Test-Path $publicKeyPath)) {
    Write-Log "ERROR: SSH public key not found at $publicKeyPath"
    exit 1
}

$publicKey = Get-Content $publicKeyPath -Raw
Write-Log "Public key loaded from $publicKeyPath"

# Create a temporary script to setup SSH key on remote host
$tempScript = @"
#!/bin/bash
# Create .ssh directory if it doesn't exist
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add the public key to authorized_keys
echo '$publicKey' >> ~/.ssh/authorized_keys

# Set proper permissions
chmod 600 ~/.ssh/authorized_keys

# Remove duplicate entries
sort ~/.ssh/authorized_keys | uniq > ~/.ssh/authorized_keys.tmp
mv ~/.ssh/authorized_keys.tmp ~/.ssh/authorized_keys

echo "SSH key setup completed successfully"
"@

# Save the script to a temporary file
$tempScriptPath = "$env:TEMP\setup_ssh_key.sh"
$tempScript | Out-File -FilePath $tempScriptPath -Encoding UTF8

Write-Log "Temporary script created at $tempScriptPath"

try {
    # Copy the script to remote host and execute it
    Write-Log "Copying setup script to remote host..."
    
    # Use scp to copy the script (with password)
    $scpCommand = "echo '$Password' | scp -o StrictHostKeyChecking=no '$tempScriptPath' $Username@${VMHost}:/tmp/setup_ssh_key.sh"
    Write-Log "Executing: $scpCommand"
    
    # Execute scp command
    $result = cmd /c "echo $Password | scp -o StrictHostKeyChecking=no `"$tempScriptPath`" $Username@${VMHost}:/tmp/setup_ssh_key.sh 2>&1"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Script copied successfully"
        
        # Execute the script on remote host
        Write-Log "Executing setup script on remote host..."
        $sshCommand = "echo '$Password' | ssh -o StrictHostKeyChecking=no $Username@$VMHost 'chmod +x /tmp/setup_ssh_key.sh && /tmp/setup_ssh_key.sh && rm /tmp/setup_ssh_key.sh'"
        
        $result = cmd /c "echo $Password | ssh -o StrictHostKeyChecking=no $Username@$VMHost `"chmod +x /tmp/setup_ssh_key.sh && /tmp/setup_ssh_key.sh && rm /tmp/setup_ssh_key.sh`" 2>&1"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "SSH key setup completed successfully!"
            Write-Log "You should now be able to connect without password using: ssh $Username@$VMHost"
        } else {
            Write-Log "ERROR: Failed to execute setup script on remote host"
            Write-Log "Output: $result"
            exit 1
        }
    } else {
        Write-Log "ERROR: Failed to copy script to remote host"
        Write-Log "Output: $result"
        exit 1
    }
    
} catch {
    Write-Log "ERROR: An exception occurred: $($_.Exception.Message)"
    exit 1
} finally {
    # Clean up temporary file
    if (Test-Path $tempScriptPath) {
        Remove-Item $tempScriptPath -Force
        Write-Log "Temporary script file cleaned up"
    }
}

Write-Log "SSH key setup process completed"