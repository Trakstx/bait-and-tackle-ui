@echo off
setlocal
set "BFT_PACKAGE_ROOT=%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -Command "$ErrorActionPreference='Stop'; $root=[IO.Path]::GetFullPath($env:BFT_PACKAGE_ROOT); $payload=Join-Path $root 'payload'; $m=Get-Content -LiteralPath (Join-Path $root 'manifest.json') -Raw | ConvertFrom-Json; foreach($p in $m.files.PSObject.Properties){$f=[IO.Path]::GetFullPath((Join-Path $payload $p.Name)); if(-not $f.StartsWith($payload+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Unsafe manifest path'}; if((Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash -ne $p.Value){throw ('Package verification failed: '+$p.Name)}}; & (Join-Path $payload 'BFT_HUD/runtime/python.exe') -B (Join-Path $root 'install.py'); exit $LASTEXITCODE"
if errorlevel 1 pause
