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

        # List all WSL distributions
        $WSLList = wsl -l -q 2>&1 | Where-Object { $_ -match '\S' }
        Write-Info "WSL distributions found: $($WSLList -join ', ')"

        # Try to check each Linux distribution (skip docker-desktop)
        $CheckedAny = $false
        foreach ($distro in $WSLList) {
            $distroName = $distro.Trim()
            if ($distroName -like "docker-desktop*") {
                Write-Info "  Skipping $distroName (Docker WSL backend)"
                continue
            }

            Write-Info "  Checking $distroName for port 8765..."
            try {
                # Try with 'sh' first (more portable than bash)
                $WSLNetstat = wsl -d $distroName -e sh -c "command -v ss >/dev/null 2>&1 && ss -tuln | grep :8765 || (command -v netstat >/dev/null 2>&1 && netstat -tuln | grep :8765) || echo 'no-tools'" 2>&1

                if ($LASTEXITCODE -ne 0 -or $WSLNetstat -match "ERROR" -or $WSLNetstat -match "no-tools") {
                    Write-Info "    → Could not check (ss/netstat not available or sh not found)"
                } elseif ($WSLNetstat -and $WSLNetstat -notmatch "no-tools") {
                    Write-Warning "    → Port 8765 IS in use in $distroName!"
                    Write-Host "    $WSLNetstat" -ForegroundColor Yellow
                    $Issues += "WSL ($distroName) occupying port 8765"
                    $Recommendations += "In WSL ($distroName), run: sudo fuser -k 8765/tcp"
                } else {
                    Write-Success "    → Port 8765 not in use"
                }
                $CheckedAny = $true
            } catch {
                Write-Info "    → Could not check: $_"
            }
        }

        if (-not $CheckedAny) {
            Write-Warning "Could not check any WSL distributions for port usage"
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
# 8. Chrome-Side Debugging (If Log is Empty)
# ===================================================================
if (-not (Test-Path $LogFile) -or (Test-Path $LogFile -and (Get-Item $LogFile).Length -eq 0)) {
    Write-Section "8. Chrome-Side Debugging (Why Isn't Chrome Launching the Host?)"

    Write-Warning "The log file is empty, which means Chrome has NEVER launched the native host."
    Write-Info "This suggests Chrome either:"
    Write-Host "  • Cannot find or read the manifest file"
    Write-Host "  • Cannot execute the batch wrapper"
    Write-Host "  • The extension isn't actually requesting native messaging"
    Write-Host "  • Chrome's native messaging is blocked by policy or permissions"
    Write-Host ""

    Write-ColorOutput "Troubleshooting Steps:" "Yellow"
    Write-Host ""

    Write-ColorOutput "Step 1: Manually test the batch wrapper" "Cyan"
    Write-Host "Run this command to see if the native host starts:"
    Write-Host "  `"$WrapperBatFile`"" -ForegroundColor White
    Write-Host ""
    Write-Host "You should see emergency logs like:"
    Write-Host "  [timestamp] EMERGENCY: Native host starting..."
    Write-Host "  [timestamp] EMERGENCY: Python version: ..."
    Write-Host ""
    Write-Host "If you DON'T see these logs, the batch file can't execute properly."
    Write-Host "Press Ctrl+C to stop after seeing the logs."
    Write-Host ""

    Write-ColorOutput "Step 2: Check Chrome's native messaging status" "Cyan"
    Write-Host "1. Open Chrome and go to: chrome://policy/"
    Write-Host "2. Search for 'NativeMessaging'"
    Write-Host "3. Verify there are no policies blocking native messaging"
    Write-Host ""

    Write-ColorOutput "Step 3: Check extension background service worker" "Cyan"
    Write-Host "1. Go to chrome://extensions/"
    Write-Host "2. Find 'Chrome Tab Reader' and click 'service worker' link"
    Write-Host "3. Open the Console tab"
    Write-Host "4. Click the extension icon in Chrome toolbar"
    Write-Host "5. Look for errors about native messaging in the console"
    Write-Host ""

    Write-ColorOutput "Step 4: Launch Chrome with verbose logging" "Cyan"
    Write-Host "Close ALL Chrome windows, then run:"
    Write-Host '  "C:\Program Files\Google\Chrome\Application\chrome.exe" --enable-logging --v=1 --vmodule=native_messaging_host=3' -ForegroundColor White
    Write-Host ""
    Write-Host "Then try to use the extension. Check for native messaging errors in:"
    Write-Host "  $env:LOCALAPPDATA\Google\Chrome\User Data\chrome_debug.log"
    Write-Host ""

    Write-ColorOutput "Step 5: Verify manifest is readable by Chrome" "Cyan"
    Write-Host "Check manifest permissions:"
    Write-Host "  Get-Acl `"$ManifestFile`" | Format-List"
    Write-Host ""
    Write-Host "Verify manifest content:"
    Write-Host "  Get-Content `"$ManifestFile`" | ConvertFrom-Json | ConvertTo-Json -Depth 10"
    Write-Host ""

    Write-ColorOutput "Step 6: Check if extension is using native messaging" "Cyan"
    Write-Host "The extension must call chrome.runtime.connectNative() to trigger the host."
    Write-Host "Check extension/service_worker.js for the native messaging code."
    Write-Host ""

    Write-ColorOutput "Common Causes:" "Yellow"
    Write-Host "  ✗ Manifest path uses backslashes instead of forward slashes"
    Write-Host "  ✗ Batch file lacks execute permissions"
    Write-Host "  ✗ Python path has spaces and isn't properly quoted"
    Write-Host "  ✗ Extension ID mismatch between extension and manifest"
    Write-Host "  ✗ Extension never calls chrome.runtime.connectNative()"
    Write-Host "  ✗ Chrome policy blocking native messaging"
    Write-Host ""
}

# ===================================================================
# 9. Chrome Extension Check
# ===================================================================
Write-Section "9. Chrome Extension Verification"

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
