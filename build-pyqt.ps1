param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $venvPython)) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.10 or later, or provide the python.exe path with -Python.' }
}
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Could not install the required packages. Check your internet connection and try again.' }
& $venvPython -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; the build has been stopped.' }
& $venvPython -m PyInstaller --noconfirm --onefile --windowed --name BuryIt --distpath dist --workpath build\buryit --specpath build app.py
if ($LASTEXITCODE -ne 0) { throw 'Could not build the executable.' }
Write-Host 'Ready: dist\BuryIt.exe'
