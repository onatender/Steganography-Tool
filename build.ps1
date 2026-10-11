$ErrorActionPreference = 'Stop'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (!(Test-Path -LiteralPath $compiler)) { $compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe' }
$outputDir = Join-Path $PSScriptRoot 'dist'
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
$source = Join-Path $PSScriptRoot 'Program.cs'
& $compiler /nologo /target:winexe /optimize+ /utf8output /reference:System.Drawing.dll /reference:System.Windows.Forms.dll "/out:$outputDir\Steganography.exe" $source
if ($LASTEXITCODE -ne 0) { throw 'Could not compile the app.' }
& $compiler /nologo /target:exe /optimize+ /utf8output /reference:System.Drawing.dll /reference:System.Windows.Forms.dll "/out:$outputDir\Steganography.Tests.exe" $source
if ($LASTEXITCODE -ne 0) { throw 'Could not compile the tests.' }
& "$outputDir\Steganography.Tests.exe" --self-test
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
Write-Host "Ready: $outputDir\Steganography.exe"
