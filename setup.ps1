[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $ProjectRoot

function Stop-Setup([string]$Message) {
    throw $Message
}

function Invoke-Checked([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        Stop-Setup "$Executable $($Arguments -join ' ') failed with exit code $LASTEXITCODE."
    }
}

try {
    Write-Host "Project Alesia setup" -ForegroundColor Cyan
    Write-Host "Checking required tools..."

    $PythonLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    $PythonCommand = $null
    $PythonPrefix = @()
    if ($PythonLauncher) {
        & $PythonLauncher.Source -3.13 --version *> $null
        if ($LASTEXITCODE -eq 0) {
            $PythonCommand = $PythonLauncher.Source
            $PythonPrefix = @("-3.13")
        }
    }
    if (-not $PythonCommand) {
        $Python = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($Python) {
            $PythonCommand = $Python.Source
        }
    }
    if (-not $PythonCommand) {
        Stop-Setup "Python 3.13 or newer was not found. Install Python from https://www.python.org/downloads/ and enable the Python launcher or add Python to PATH, then reopen PowerShell."
    }

    $PythonVersionText = (& $PythonCommand @PythonPrefix --version 2>&1 | Out-String).Trim()
    if ($PythonVersionText -notmatch 'Python\s+(\d+)\.(\d+)\.(\d+)') {
        Stop-Setup "Could not read the Python version from '$PythonVersionText'."
    }
    $PythonVersion = [version]::new([int]$Matches[1], [int]$Matches[2], [int]$Matches[3])
    if ($PythonVersion -lt [version]::new(3, 13, 0)) {
        Stop-Setup "Python 3.13 or newer is required; found $PythonVersionText. Install Python 3.13+ and rerun setup.ps1."
    }

    $Node = Get-Command node.exe -ErrorAction SilentlyContinue
    $Npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $Node -or -not $Npm) {
        Stop-Setup "Node.js and npm were not found. Install Node.js 20.18.1+ or 22.9.0+ from https://nodejs.org/, then reopen PowerShell."
    }
    $NodeVersionText = (& $Node.Source --version | Out-String).Trim()
    if ($NodeVersionText -notmatch '^v?(\d+)\.(\d+)\.(\d+)') {
        Stop-Setup "Could not read the Node.js version from '$NodeVersionText'."
    }
    $NodeMajor = [int]$Matches[1]
    $NodeMinor = [int]$Matches[2]
    $NodePatch = [int]$Matches[3]
    $NodeIsSupported = ($NodeMajor -ge 22 -and ($NodeMajor -gt 22 -or $NodeMinor -gt 9 -or ($NodeMinor -eq 9 -and $NodePatch -ge 0))) -or ($NodeMajor -eq 20 -and ($NodeMinor -gt 18 -or ($NodeMinor -eq 18 -and $NodePatch -ge 1)))
    if (-not $NodeIsSupported) {
        Stop-Setup "Node.js 20.18.1+ or 22.9.0+ is required; found $NodeVersionText. Update Node.js and rerun setup.ps1."
    }

    Write-Host "Python: $PythonVersionText"
    Write-Host "Node.js: $NodeVersionText"

    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        Write-Host "Creating Python virtual environment..."
        Invoke-Checked $PythonCommand ($PythonPrefix + @("-m", "venv", ".venv"))
    }
    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    Write-Host "Installing Python dependencies..."
    Invoke-Checked $VenvPython @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-Checked $VenvPython @("-m", "pip", "install", "-r", "requirements-dev.txt")

    foreach ($Frontend in @("extension", "web")) {
        Write-Host "Installing $Frontend dependencies..."
        Push-Location (Join-Path $ProjectRoot $Frontend)
        try {
            Invoke-Checked $Npm.Source @("ci")
        }
        finally {
            Pop-Location
        }
    }

    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example. Add your API credentials before starting the backend." -ForegroundColor Yellow
    }
    else {
        Write-Host "Keeping existing .env; setup does not overwrite secrets or local settings."
    }

    $WebEnv = Join-Path $ProjectRoot "web\.env.local"
    if (-not (Test-Path $WebEnv)) {
        Set-Content -Path $WebEnv -Value "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" -Encoding UTF8
        Write-Host "Created web/.env.local for the local backend."
    }

    Write-Host ""
    Write-Host "Setup complete." -ForegroundColor Green
    Write-Host "Before first use: set GOOGLE_API_KEY, OPENROUTER_API_KEY, and VTAI_TOKEN in .env. Configure Qdrant in .env and ensure its collection contains your knowledge documents."
    Write-Host "For local Qdrant, install/start Docker Desktop and run the Qdrant command in README.md. For Qdrant Cloud, set QDRANT_URL and QDRANT_API_KEY instead."
    Write-Host "Start the backend and selected interface using the commands in README.md."
}
catch {
    Write-Error $_
    exit 1
}
finally {
    Pop-Location
}
