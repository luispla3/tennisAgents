# Reinicia el servidor web de TennisAgents (libera 8000-8002 y arranca uno nuevo)
$ErrorActionPreference = "SilentlyContinue"

foreach ($port in 8000, 8001, 8002) {
    $pids = Get-NetTCPConnection -LocalPort $port -State Listen |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        Stop-Process -Id $procId -Force
    }
}

Start-Sleep -Seconds 2
Set-Location (Split-Path $PSScriptRoot -Parent)
Write-Host "Iniciando TennisAgents web..."
python -m web.run
