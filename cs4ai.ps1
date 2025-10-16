# run.ps1
# Requires Windows PowerShell 5.1+ or PowerShell 7+

[CmdletBinding()]
param(
    # Pass-through args for src/cli.py
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $PassthroughArgs
)

$ErrorActionPreference = 'Stop'

# Absolute paths anchored to this script's location
$scriptRoot = Split-Path -Path $PSCommandPath -Parent
$venvPath   = Join-Path $scriptRoot '.venv'
$activatePs = Join-Path $venvPath 'Scripts\Activate.ps1'
$pythonExe  = Join-Path $venvPath 'Scripts\python.exe'
$cliPath    = Join-Path $scriptRoot 'src\cli.py'

# --- 1) Ensure the venv activator exists; otherwise exit early to stderr
if (-not (Test-Path -LiteralPath $activatePs)) {
    Write-Error "Virtual environment not found: '$activatePs'. Expected a sibling '.venv' next to this script."
    exit 1
}

# Try to activate; if that fails, exit early to stderr
try {
    . $activatePs   # dot-source so the activation modifies the current session
} catch {
    Write-Error "Failed to activate virtual environment at '$venvPath'. $($_.Exception.Message)"
    exit 1
}

# --- 2) Validate python and target script exist (absolute)
if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Error "Python executable not found in venv: '$pythonExe'."
    exit 1
}
if (-not (Test-Path -LiteralPath $cliPath)) {
    Write-Error "CLI script not found: '$cliPath'."
    exit 1
}

# --- 3) Run src/cli.py via the venv's python, passing all args through exactly
& $pythonExe $cliPath @PassthroughArgs
$exitCode = $LASTEXITCODE
exit $exitCode
