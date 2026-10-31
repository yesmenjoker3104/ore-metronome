$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location -LiteralPath $projectRoot

$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = (Get-Command python.exe -ErrorAction Stop).Source
}

function Invoke-Python {
    & $pythonPath @args
    if ($LASTEXITCODE -ne 0) {
        throw "python $($args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

Invoke-Python -m pip install -e '.[dev]'
Invoke-Python scripts\make_version_info.py
Invoke-Python scripts\make_icon.py

Invoke-Python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name ore-metronome `
    --icon src\ore_metronome\assets\icon.ico `
    --version-file build\version_info.txt `
    --add-data 'data\app_icon.png;data' `
    --add-data 'src\ore_metronome\infrastructure\update\apply_update.ps1;ore_metronome\infrastructure\update' `
    --add-data 'src\ore_metronome\assets\icons;ore_metronome\assets\icons' `
    launch.py

$builtExecutable = Join-Path $projectRoot 'dist\ore-metronome.exe'
if (-not (Test-Path -LiteralPath $builtExecutable)) {
    throw 'PyInstaller did not create dist\ore-metronome.exe'
}

# 前回の onedir 出力（_internal を含む）が残らないよう、フォルダを作り直して exe だけを入れる。
$appDirectory = Join-Path $projectRoot 'dist\ore-metronome'
if (Test-Path -LiteralPath $appDirectory) {
    Remove-Item -LiteralPath $appDirectory -Recurse -Force
}
New-Item -ItemType Directory -Path $appDirectory | Out-Null
Move-Item -LiteralPath $builtExecutable -Destination $appDirectory

$archiveName = 'ore-metronome-windows-x64.zip'
$archivePath = Join-Path $projectRoot "dist\$archiveName"
$checksumPath = "$archivePath.sha256"
foreach ($path in @($archivePath, $checksumPath)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
    }
}

# zip の先頭フォルダは ore-metronome/ にする（更新処理はこのフォルダを前提にする）。
# .NET Framework の CreateFromDirectory は Windows でもエントリ名に \ を使うため、
# エントリ名を / 区切りに変換して 1 件ずつ追加する。
Add-Type -AssemblyName System.IO.Compression.FileSystem
$distDirectory = Join-Path $projectRoot 'dist'
$archive = [System.IO.Compression.ZipFile]::Open($archivePath, 'Create')
try {
    Get-ChildItem -LiteralPath $appDirectory -Recurse -File | ForEach-Object {
        $relativePath = $_.FullName.Substring($distDirectory.Length + 1).Replace('\', '/')
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $archive,
            $_.FullName,
            $relativePath,
            [System.IO.Compression.CompressionLevel]::Optimal
        )
    }
} finally {
    $archive.Dispose()
}

$hash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath $checksumPath -Value "$hash  $archiveName" -Encoding ASCII

Write-Host "Created $archivePath"
Write-Host "Created $checksumPath"
