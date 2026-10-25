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

# The PyInstaller bootloader can keep the old exe locked for a moment after the app exits.
function Remove-BackupExe {
    $deadline = (Get-Date).AddSeconds(30)
    while (Test-Path -LiteralPath $backupExePath) {
        try {
            Remove-Item -LiteralPath $backupExePath -Force
        }
        catch {
            if ((Get-Date) -ge $deadline) {
                Write-Log "Backup left in place: $($_.Exception.Message)"
                return
            }
            Start-Sleep -Milliseconds 500
        }
    }
}

$currentPath = [System.IO.Path]::GetFullPath($CurrentApplication).TrimEnd('\')
$stagedPath = [System.IO.Path]::GetFullPath($StagedApplication).TrimEnd('\')
$exeName = 'ore-metronome.exe'
$exePath = Join-Path $currentPath $exeName
$backupExePath = Join-Path $currentPath "$exeName.bak"
$backupExeName = Split-Path -Leaf $backupExePath
$stagedExePath = Join-Path $stagedPath $exeName

try {
    Write-Log "Update started: staged=$stagedExePath target=$exePath"

    if (-not (Test-Path -LiteralPath $stagedExePath)) {
        throw "Updated executable not found: $stagedExePath"
    }

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

    if (Test-Path -LiteralPath $backupExePath) {
        Remove-Item -LiteralPath $backupExePath -Force
    }

    # The exe may stay locked briefly after the parent exits (PyInstaller bootloader),
    # so retry the rename for a while before giving up.
    if (Test-Path -LiteralPath $exePath) {
        $deadline = (Get-Date).AddSeconds(60)
        while ($true) {
            try {
                Rename-Item -LiteralPath $exePath -NewName $backupExeName
                break
            }
            catch {
                if ((Get-Date) -ge $deadline) {
                    throw
                }
                Start-Sleep -Milliseconds 500
            }
        }
    }
    Move-Item -LiteralPath $stagedExePath -Destination $exePath

    if (-not $SkipLaunch) {
        $process = Start-Process -FilePath $exePath -WorkingDirectory $currentPath -PassThru
        Start-Sleep -Seconds 3
        if ($process.HasExited) {
            throw "Updated application exited early with code $($process.ExitCode)"
        }
    }

    Remove-BackupExe
    Write-Log 'Update completed'
    exit 0
}
catch {
    Write-Log "Update failed: $($_.Exception.Message)"
    try {
        if (Test-Path -LiteralPath $backupExePath) {
            if (Test-Path -LiteralPath $exePath) {
                Remove-Item -LiteralPath $exePath -Force
            }
            Rename-Item -LiteralPath $backupExePath -NewName $exeName
            Write-Log 'Previous version restored'
        }
    }
    catch {
        Write-Log "Rollback failed: $($_.Exception.Message)"
    }
    exit 1
}
