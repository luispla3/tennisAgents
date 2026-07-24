param(
    [string]$TaskName = "TennisAgents Supervisor",
    [string]$PythonPath = "",
    [switch]$EnableNow
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$isAdministrator = (
    New-Object Security.Principal.WindowsPrincipal(
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdministrator) {
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`"",
        "-TaskName", "`"$TaskName`""
    )
    if ($PythonPath) {
        $arguments += @("-PythonPath", "`"$PythonPath`"")
    }
    if ($EnableNow) {
        $arguments += "-EnableNow"
    }
    $process = Start-Process `
        -FilePath "powershell.exe" `
        -Verb RunAs `
        -ArgumentList ($arguments -join " ") `
        -Wait `
        -PassThru
    exit $process.ExitCode
}

if (-not $PythonPath) {
    $condaPython = Join-Path $env:USERPROFILE "miniconda3\envs\tennisAgents\python.exe"
    if (Test-Path $condaPython) {
        $PythonPath = $condaPython
    } else {
        $PythonPath = (Get-Command python -ErrorAction Stop).Source
    }
}

if (-not (Test-Path $PythonPath)) {
    throw "No se encontró Python en: $PythonPath"
}

& $PythonPath -m ops.supervisor --validate --network --llm
if ($LASTEXITCODE -ne 0) {
    throw "La validación del supervisor falló."
}

$action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "-m ops.supervisor" `
    -WorkingDirectory $root

$startupTrigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -WakeToRun

# Comprueba que SYSTEM puede ejecutar Python, leer el proyecto, acceder a las
# fuentes y completar una petición mínima al LLM sin iniciar procesos.
$validationTaskName = "$TaskName Validation"
$validationAction = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "-m ops.supervisor --validate --network --llm" `
    -WorkingDirectory $root
$validationSettings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 1)
$validationTask = New-ScheduledTask `
    -Action $validationAction `
    -Principal $principal `
    -Settings $validationSettings `
    -Description "Validación temporal del supervisor TennisAgents."

try {
    Register-ScheduledTask `
        -TaskName $validationTaskName `
        -InputObject $validationTask `
        -Force | Out-Null
    Start-ScheduledTask -TaskName $validationTaskName
    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 500
        $validationState = (Get-ScheduledTask -TaskName $validationTaskName).State
    } while ($validationState -eq "Running" -and (Get-Date) -lt $deadline)

    $validationResult = (Get-ScheduledTaskInfo -TaskName $validationTaskName).LastTaskResult
    if ($validationState -eq "Running" -or $validationResult -ne 0) {
        throw "La autoprueba bajo SYSTEM falló (estado=$validationState, resultado=$validationResult)."
    }
} finally {
    Stop-ScheduledTask -TaskName $validationTaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask `
        -TaskName $validationTaskName `
        -Confirm:$false `
        -ErrorAction SilentlyContinue
}

$task = New-ScheduledTask `
    -Action $action `
    -Trigger $startupTrigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Mantiene activas la API y el colector BetfairEnv y los recupera tras reinicios o bloqueos."

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

if ($EnableNow) {
    Enable-ScheduledTask -TaskName $TaskName | Out-Null
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "Tarea instalada, habilitada e iniciada: $TaskName"
} else {
    Disable-ScheduledTask -TaskName $TaskName | Out-Null
    Write-Output "Tarea instalada y desactivada: $TaskName"
}

Get-ScheduledTask -TaskName $TaskName |
    Select-Object TaskName, State, @{Name = "Enabled"; Expression = { $_.Settings.Enabled }}
