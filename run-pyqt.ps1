$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $venvPython)) { throw 'Run build-pyqt.ps1 first.' }
& $venvPython app.py
if ($LASTEXITCODE -ne 0) { throw 'Could not start the app. Install the required packages with build-pyqt.ps1.' }
