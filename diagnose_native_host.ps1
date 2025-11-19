#
# Chrome Tab Reader - Native Host Diagnostic Script
#
# This script diagnoses why the native messaging host isn't starting
#

# Colors for output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "✓ $Message" "Green"
}

function Write-Failure {
    param([string]$Message)
    Write-ColorOutput "✗ $Message" "Red"
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "⚠ $Message" "Yellow"
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput $Message "Cyan"
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Gray
    Write-ColorOutput $Title "White"
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Gray
}

# Main diagnostic
Write-ColorOutput "Chrome Tab Reader - Native Host Diagnostic Tool" "Green"
Write-Host ""

$Issues = @()
$Recommendations = @()

# ===================================================================
# 1. Check Manifest File
# ===================================================================
Write-Section "1. Checking Native Messaging Manifest"

$ManifestDir = Join-Path $env:APPDATA "Google\Chrome\NativeMessagingHosts"
$ManifestFile = Join-Path $ManifestDir "com.chrome_tab_reader.host.json"

if (Test-Path $ManifestFile) {
    Write-Success "Manifest file exists: $ManifestFile"

    # Read and parse manifest
    try {
        $ManifestContent = Get-Content $ManifestFile -Raw | ConvertFrom-Json
        Write-Success "Manifest file is valid JSON"

        Write-Info "  Name: $($ManifestContent.name)"
        Write-Info "  Type: $($ManifestContent.type)"
        Write-Info "  Path: $($ManifestContent.path)"
        Write-Info "  Allowed origins: $($ManifestContent.allowed_origins -join ', ')"

        # Check if path exists
        $BatchPath = $ManifestContent.path -replace '/', '\'
        if (Test-Path $BatchPath) {
            Write-Success "Batch file exists at specified path"
        } else {
            Write-Failure "Batch file NOT found at: $BatchPath"
            $Issues += "Batch file missing"
            $Recommendations += "Re-run install_native_host.ps1 with your extension ID"
        }

    } catch {
        Write-Failure "Failed to parse manifest JSON: $_"
        $Issues += "Invalid manifest JSON"
        $Recommendations += "Re-run install_native_host.ps1 with your extension ID"
    }

} else {
    Write-Failure "Manifest file NOT found: $ManifestFile"
    $Issues += "Manifest file missing"
    $Recommendations += "Run: .\install_native_host.ps1 <extension-id>"
}

# ===================================================================
# 2. Check Batch Wrapper
# ===================================================================
Write-Section "2. Checking Batch Wrapper Script"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WrapperBatFile = Join-Path $ScriptDir "chrome_tab_native_host.bat"

if (Test-Path $WrapperBatFile) {
    Write-Success "Batch wrapper exists: $WrapperBatFile"

    # Display contents
    Write-Info "Batch file contents:"
    $BatchContent = Get-Content $WrapperBatFile
    foreach ($line in $BatchContent) {
        Write-Host "    $line" -ForegroundColor DarkGray
    }

} else {
    Write-Failure "Batch wrapper NOT found: $WrapperBatFile"
    $Issues += "Batch wrapper missing"
    $Recommendations += "Re-run install_native_host.ps1"
}

# ===================================================================
# 3. Check Python Installation
# ===================================================================
Write-Section "3. Checking Python Installation"

try {
    $PythonPath = (Get-Command python -ErrorAction Stop).Source
    $PythonVersion = & python --version 2>&1
    Write-Success "Python found: $PythonPath"
    Write-Info "  Version: $PythonVersion"
} catch {
    Write-Failure "Python not found in PATH"
    $Issues += "Python not accessible"
    $Recommendations += "Ensure Python 3.8+ is installed and in PATH"
}

# ===================================================================
# 4. Check Python Script
# ===================================================================
Write-Section "4. Checking Python Native Host Script"

$NativeHostScript = Join-Path $ScriptDir "chrome_tab_native_host.py"

if (Test-Path $NativeHostScript) {
    Write-Success "Native host script exists: $NativeHostScript"

    # Try to validate syntax
    Write-Info "Testing Python script syntax..."
    try {
        $SyntaxCheck = & python -m py_compile $NativeHostScript 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Python script syntax is valid"
        } else {
            Write-Failure "Python script has syntax errors"
            Write-Host $SyntaxCheck
            $Issues += "Python script syntax error"
        }
    } catch {
        Write-Warning "Could not verify script syntax: $_"
    }

} else {
    Write-Failure "Native host script NOT found: $NativeHostScript"
    $Issues += "Native host script missing"
}

# ===================================================================
# 5. Check Port Conflicts
# ===================================================================
Write-Section "5. Checking for Port Conflicts (Port 8765)"

Write-Info "Checking if port 8765 is in use..."

try {
    $PortCheck = netstat -ano | Select-String ":8765"
    if ($PortCheck) {
        Write-Warning "Port 8765 is in use!"
        Write-Info "Processes using port 8765:"
        foreach ($line in $PortCheck) {
            Write-Host "    $line" -ForegroundColor Yellow

            # Extract PID and get process info
            if ($line -match '\s+(\d+)\s*$') {
                $PID = $matches[1]
                try {
                    $Process = Get-Process -Id $PID -ErrorAction Stop
                    Write-Info "    → Process: $($Process.ProcessName) (PID: $PID)"

                    # Check if it's WSL
                    if ($Process.ProcessName -like "*wsl*" -or $Process.ProcessName -like "*vmem*") {
                        Write-Warning "    → This appears to be WSL-related!"
                        $Issues += "Port 8765 occupied by WSL"
                        $Recommendations += "Stop WSL processes using port 8765, or change BRIDGE_PORT in Python scripts"
                    }
                } catch {
                    Write-Warning "    → Could not get process info for PID $PID"
                }
            }
        }
    } else {
        Write-Success "Port 8765 is available"
    }
} catch {
    Write-Warning "Could not check port status: $_"
}

# Check WSL specifically
Write-Info "Checking WSL status..."
try {
    $WSLStatus = wsl --status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Info "WSL is installed and running"
        Write-Host $WSLStatus

        # Check if WSL has processes on port 8765
        Write-Info "Checking if WSL has processes on port 8765..."
        try {
            $WSLNetstat = wsl -e bash -c "netstat -tuln 2>/dev/null | grep :8765" 2>&1
            if ($WSLNetstat) {
                Write-Warning "WSL has something listening on port 8765!"
                Write-Host $WSLNetstat
                $Issues += "WSL occupying port 8765"
                $Recommendations += "In WSL, run: sudo fuser -k 8765/tcp"
            } else {
                Write-Success "WSL is not using port 8765"
            }
        } catch {
            Write-Info "Could not check WSL netstat (this is OK if WSL doesn't have netstat installed)"
        }
    }
} catch {
    Write-Info "WSL is not installed or not running (this is OK)"
}

# ===================================================================
# 6. Test Manual Execution
# ===================================================================
Write-Section "6. Testing Manual Execution"

Write-Info "Attempting to manually start the native host..."
Write-Warning "The native host expects Chrome to connect via stdin/stdout."
Write-Warning "When run manually, it will appear to hang - this is normal!"
Write-Warning "Press Ctrl+C to stop after a few seconds."
Write-Host ""

Write-Info "To test manually, run one of these commands:"
Write-ColorOutput "  Option 1 (via batch wrapper):" "Cyan"
Write-Host "    $WrapperBatFile"
Write-Host ""
Write-ColorOutput "  Option 2 (direct Python):" "Cyan"
Write-Host "    python `"$NativeHostScript`""
Write-Host ""
Write-Info "If it starts successfully, you should see emergency logs to stderr."
Write-Info "The log file will be at: ~\.chrome-tab-reader\native_host.log"
Write-Host ""

$Response = Read-Host "Do you want to test manual execution now? (y/N)"
if ($Response -eq 'y' -or $Response -eq 'Y') {
    Write-Info "Starting native host... (Press Ctrl+C to stop)"
    Write-Host ""

    try {
        & python "$NativeHostScript" 2>&1
    } catch {
        Write-Info "Stopped (Ctrl+C)"
    }
}

# ===================================================================
# 7. Check Log File
# ===================================================================
Write-Section "7. Checking Log File"

$LogFile = Join-Path $env:USERPROFILE ".chrome-tab-reader\native_host.log"

if (Test-Path $LogFile) {
    Write-Success "Log file exists: $LogFile"

    $LogSize = (Get-Item $LogFile).Length
    Write-Info "  Size: $LogSize bytes"

    if ($LogSize -eq 0) {
        Write-Warning "Log file is EMPTY - native host has never been launched by Chrome!"
        $Issues += "Native host never launched"
        $Recommendations += "Check Chrome's internal page: chrome://extensions/ (ensure extension is enabled)"
        $Recommendations += "Try restarting Chrome completely"
        $Recommendations += "Check Chrome's stderr output if launched from command line"
    } else {
        Write-Success "Log file has content. Last 20 lines:"
        Get-Content $LogFile -Tail 20 | ForEach-Object {
            Write-Host "    $_" -ForegroundColor DarkGray
        }
    }

} else {
    Write-Warning "Log file does not exist yet: $LogFile"
    Write-Info "This is normal if the native host hasn't been launched yet."
}

# ===================================================================
# 8. Chrome Extension Check
# ===================================================================
Write-Section "8. Chrome Extension Verification"

Write-Info "To verify the extension is installed and enabled:"
Write-Host "1. Open Chrome and navigate to: chrome://extensions/"
Write-Host "2. Enable 'Developer mode' (toggle in top right)"
Write-Host "3. Find 'Chrome Tab Reader' extension"
Write-Host "4. Verify it shows as 'Enabled'"
Write-Host "5. Note the Extension ID (should match manifest's allowed_origins)"
Write-Host ""

if (Test-Path $ManifestFile) {
    $Manifest = Get-Content $ManifestFile -Raw | ConvertFrom-Json
    $ExtensionId = $Manifest.allowed_origins[0] -replace 'chrome-extension://|/', ''
    Write-Info "Expected Extension ID: $ExtensionId"
}

Write-Host ""
Write-Info "After verifying the extension, click the extension icon to trigger"
Write-Info "the native host connection. Watch for new entries in the log file."

# ===================================================================
# Summary
# ===================================================================
Write-Section "Diagnostic Summary"

if ($Issues.Count -eq 0) {
    Write-Success "No critical issues found!"
    Write-Info "If the native host still doesn't start, try:"
    Write-Host "  1. Restart Chrome completely (close all windows)"
    Write-Host "  2. Click the extension icon to trigger connection"
    Write-Host "  3. Monitor the log file:"
    Write-Host "     Get-Content ~\.chrome-tab-reader\native_host.log -Wait -Tail 20"
} else {
    Write-Failure "Found $($Issues.Count) issue(s):"
    foreach ($issue in $Issues) {
        Write-Host "  • $issue" -ForegroundColor Red
    }

    Write-Host ""
    Write-ColorOutput "Recommendations:" "Yellow"
    foreach ($rec in $Recommendations | Select-Object -Unique) {
        Write-Host "  → $rec" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-ColorOutput "Additional Debugging:" "Cyan"
Write-Host "  • Check Chrome's native messaging internals: chrome://policy/"
Write-Host "  • Launch Chrome from command line to see stderr output:"
Write-Host "    `"C:\Program Files\Google\Chrome\Application\chrome.exe`" --enable-logging --v=1"
Write-Host "  • Check Windows Event Viewer for application errors"
Write-Host ""
