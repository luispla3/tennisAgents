# Reinicia la API de BetfairEnv (una sola instancia en el puerto 8770)
$port = 8770
$pids = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique)

foreach ($pid in $pids) {
    Write-Host "Deteniendo proceso PID $pid en puerto $port..."
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 1
$env:PYTHONPATH = $PSScriptRoot
Set-Location $PSScriptRoot
Write-Host "Iniciando API en http://127.0.0.1:$port ..."
python -m api.server
