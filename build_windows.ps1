$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $repoRoot '.venv'
$buildPath = Join-Path $repoRoot 'build'
$distPath = Join-Path $repoRoot 'dist'
$portableZip = Join-Path $distPath 'EnableChromeAI-portable.zip'
$releaseDir = Join-Path $distPath 'EnableChromeAI-Release'
$releaseZip = Join-Path $distPath 'EnableChromeAI-Release.zip'
$releaseReadme = Join-Path $repoRoot 'release\Read Me First - Enable Chrome AI.txt'
$licenseFile = Join-Path $repoRoot 'LICENSE'

if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
}

$pythonExe = Join-Path $venvPath 'Scripts\python.exe'

& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install psutil pyinstaller
& $pythonExe -m PyInstaller --noconfirm --clean --onefile --windowed --specpath $buildPath --name EnableChromeAI app.pyw

if (Test-Path $portableZip) {
    Remove-Item -Force $portableZip
}

Compress-Archive -Path (Join-Path $distPath 'EnableChromeAI.exe') -DestinationPath $portableZip

if (Test-Path $releaseDir) {
    Remove-Item -Recurse -Force $releaseDir
}

New-Item -ItemType Directory -Path $releaseDir | Out-Null
Copy-Item -Path (Join-Path $distPath 'EnableChromeAI.exe') -Destination (Join-Path $releaseDir 'EnableChromeAI.exe')
Copy-Item -Path $releaseReadme -Destination (Join-Path $releaseDir 'Read Me First - Enable Chrome AI.txt')
Copy-Item -Path $licenseFile -Destination (Join-Path $releaseDir 'LICENSE.txt')

if (Test-Path $releaseZip) {
    Remove-Item -Force $releaseZip
}

Compress-Archive -Path $releaseDir -DestinationPath $releaseZip

Write-Host "Built executable: $(Join-Path $distPath 'EnableChromeAI.exe')"
Write-Host "Portable package: $portableZip"
Write-Host "Release package: $releaseZip"
