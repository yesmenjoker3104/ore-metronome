param(
    [Parameter(Mandatory = $true)][string]$CurrentApplication,
    [Parameter(Mandatory = $true)][string]$StagedApplication,
    [switch]$SkipLaunch
)

$ErrorActionPreference = 'Stop'
$logPath = Join-Path $env:TEMP 'ore-metronome-update.log'

function Write-Log([string]$Message) {
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -Path $logPath -Value $line -Encoding UTF8
}

$currentPath = [System.IO.Path]::GetFullPath($CurrentApplication).TrimEnd('\')
$stagedPath = [System.IO.Path]::GetFullPath($StagedApplication).TrimEnd('\')
$backupPath = "$currentPath.bak"
$backupName = Split-Path -Leaf $backupPath
$exePath = Join-Path $currentPath 'ore-metronome.exe'

try {
    Write-Log "Update started: staged=$stagedPath target=$currentPath"

    $parentPid = 0
    [void][int]::TryParse($env:ORE_METRONOME_PARENT_PID, [ref]$parentPid)
    if ($parentPid -gt 0) {
        $parent = Get-Process -Id $parentPid -ErrorAction SilentlyContinue
        if ($parent) {
            if (-not $parent.WaitForExit(60000)) {
                throw "Application process $parentPid did not exit in time"
            }
        }
    }

    if (Test-Path -LiteralPath $backupPath) {
        Remove-Item -LiteralPath $backupPath -Recurse -Force
    }
    Rename-Item -LiteralPath $currentPath -NewName $backupName
    Move-Item -LiteralPath $stagedPath -Destination $currentPath

    if (-not (Test-Path -LiteralPath $exePath)) {
        throw "Updated executable not found: $exePath"
    }

    if (-not $SkipLaunch) {
        $process = Start-Process -FilePath $exePath -WorkingDirectory $currentPath -PassThru
        Start-Sleep -Seconds 3
        if ($process.HasExited) {
            throw "Updated application exited early with code $($process.ExitCode)"
        }
    }

    Remove-Item -LiteralPath $backupPath -Recurse -Force -ErrorAction SilentlyContinue
    Write-Log 'Update completed'
    exit 0
}
catch {
    Write-Log "Update failed: $($_.Exception.Message)"
    try {
        if (Test-Path -LiteralPath $backupPath) {
            if (Test-Path -LiteralPath $currentPath) {
                Remove-Item -LiteralPath $currentPath -Recurse -Force
            }
            Rename-Item -LiteralPath $backupPath -NewName (Split-Path -Leaf $currentPath)
            Write-Log 'Previous version restored'
        }
    }
    catch {
        Write-Log "Rollback failed: $($_.Exception.Message)"
    }
    exit 1
}
