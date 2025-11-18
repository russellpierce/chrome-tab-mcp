#
# Chrome Tab Reader - Native Messaging Host Installer (Windows)
#
# This script installs the native messaging host manifest so Chrome can
# communicate with the browser extension via Native Messaging on Windows.
#
# Usage: .\install_native_host.ps1 <extension-id>
#
# Note: You may need to allow script execution first:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#

param(
    [Parameter(Mandatory=$true, Position=0, HelpMessage="Chrome extension ID")]
    [string]$ExtensionId
)

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

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "Error: $Message" "Red"
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput $Message "Cyan"
}

# Script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$NativeHostScript = Join-Path $ScriptDir "chrome_tab_native_host.py"
$WrapperBatFile = Join-Path $ScriptDir "chrome_tab_native_host.bat"

Write-ColorOutput "Chrome Tab Reader - Native Messaging Host Installer (Windows)" "Green"
Write-Host ""

# Validate extension ID format (basic check)
if ($ExtensionId -notmatch '^[a-z]{32}$') {
    Write-Error "Invalid extension ID format. Extension IDs should be 32 lowercase letters."
    Write-Host ""
    Write-Host "To find your extension ID:"
    Write-Host "1. Open Chrome and go to chrome://extensions/"
    Write-Host "2. Enable 'Developer mode' in the top right"
    Write-Host "3. Find 'Chrome Tab Reader' and copy the ID"
    Write-Host ""
    exit 1
}

# Check if native host script exists
if (-not (Test-Path $NativeHostScript)) {
    Write-Error "Native host script not found at $NativeHostScript"
    exit 1
}

# Detect Python installation and version
Write-Info "Checking Python installation..."
$PythonCmd = $null
$PythonVersion = $null

# Try 'python' command first
try {
    $PythonCmd = (Get-Command python -ErrorAction Stop).Source
    $PythonVersionOutput = & python --version 2>&1
    if ($PythonVersionOutput -match 'Python (\d+)\.(\d+)\.(\d+)') {
        $MajorVersion = [int]$matches[1]
        $MinorVersion = [int]$matches[2]
        $PythonVersion = "$MajorVersion.$MinorVersion"

        if ($MajorVersion -lt 3 -or ($MajorVersion -eq 3 -and $MinorVersion -lt 8)) {
            Write-Error "Python 3.8 or higher required. Found Python $PythonVersion"
            Write-Host ""
            Write-Host "Please install Python 3.8+ from https://www.python.org/downloads/"
            exit 1
        }
    }
} catch {
    # Try 'python3' command
    try {
        $PythonCmd = (Get-Command python3 -ErrorAction Stop).Source
        $PythonVersionOutput = & python3 --version 2>&1
        if ($PythonVersionOutput -match 'Python (\d+)\.(\d+)\.(\d+)') {
            $MajorVersion = [int]$matches[1]
            $MinorVersion = [int]$matches[2]
            $PythonVersion = "$MajorVersion.$MinorVersion"

            if ($MajorVersion -lt 3 -or ($MajorVersion -eq 3 -and $MinorVersion -lt 8)) {
                Write-Error "Python 3.8 or higher required. Found Python $PythonVersion"
                Write-Host ""
                Write-Host "Please install Python 3.8+ from https://www.python.org/downloads/"
                exit 1
            }
        }
    } catch {
        Write-Error "Python not found in PATH"
        Write-Host ""
        Write-Host "Please install Python 3.8+ from https://www.python.org/downloads/"
        Write-Host "Make sure to check 'Add Python to PATH' during installation."
        exit 1
    }
}

Write-Success "Found Python $PythonVersion at $PythonCmd"

# Create batch wrapper script
# This wrapper is needed because Windows doesn't support shebang (#!) lines
Write-Info "Creating batch wrapper script..."
$WrapperContent = @"
@echo off
REM Chrome Tab Reader Native Messaging Host Wrapper
REM This script invokes the Python native host script
`"$PythonCmd`" "%~dp0chrome_tab_native_host.py" %*
"@

Set-Content -Path $WrapperBatFile -Value $WrapperContent -Encoding ASCII
Write-Success "Created wrapper script at $WrapperBatFile"

# Create manifest directory
$ManifestDir = Join-Path $env:APPDATA "Google\Chrome\NativeMessagingHosts"
if (-not (Test-Path $ManifestDir)) {
    New-Item -ItemType Directory -Path $ManifestDir -Force | Out-Null
    Write-Success "Created manifest directory"
} else {
    Write-Success "Manifest directory exists"
}

Write-Info "Manifest directory: $ManifestDir"

# Create manifest file
$ManifestFile = Join-Path $ManifestDir "com.chrome_tab_reader.host.json"

# Use forward slashes for paths in JSON (Chrome accepts both on Windows)
$WrapperBatPath = $WrapperBatFile -replace '\\', '/'

$Manifest = @{
    name = "com.chrome_tab_reader.host"
    description = "Chrome Tab Reader Native Messaging Host"
    path = $WrapperBatPath
    type = "stdio"
    allowed_origins = @(
        "chrome-extension://$ExtensionId/"
    )
}

$Manifest | ConvertTo-Json -Depth 10 | Set-Content -Path $ManifestFile -Encoding UTF8
Write-Success "Created native messaging host manifest"
Write-Info "   Location: $ManifestFile"
Write-Host ""

Write-ColorOutput "Installation complete!" "Green"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Reload the Chrome extension (chrome://extensions/)"
Write-Host "2. Open the extension popup - it should connect to the native host"
Write-Host "3. Check the native host log for connection status:"
Write-Host "   Get-Content ~\.chrome-tab-reader\native_host.log -Wait -Tail 20"
Write-Host ""
Write-Host "To test the setup, try using the MCP server to extract a Chrome tab."
Write-Host ""
