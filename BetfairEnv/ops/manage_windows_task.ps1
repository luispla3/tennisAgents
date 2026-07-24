param(
    [ValidateSet("status", "enable", "disable", "start", "stop", "uninstall")]
    [string]$Action = "status",
    [string]$TaskName = "TennisAgents Supervisor"
)

$ErrorActionPreference = "Stop"
$runDir = Join-Path (Split-Path -Parent $PSScriptRoot) ".run"
$pidFile = Join-Path $runDir "supervisor.pid"
$stopFile = Join-Path $runDir "supervisor.stop"
$isAdministrator = (
    New-Object Security.Principal.WindowsPrincipal(
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($Action -ne "status" -and -not $isAdministrator) {
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`"",
        "-Action", $Action,
        "-TaskName", "`"$TaskName`""
    )
    $process = Start-Process `
        -FilePath "powershell.exe" `
        -Verb RunAs `
        -ArgumentList ($arguments -join " ") `
        -Wait `
        -PassThru
    exit $process.ExitCode
}

function Stop-SupervisorTree {
    if (-not (Test-Path $pidFile)) {
        return
    }
    $supervisorPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($supervisorPid -match "^\d+$") {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$supervisorPid" -ErrorAction SilentlyContinue
        if ($process -and $process.CommandLine -match "ops\.supervisor") {
            New-Item -ItemType Directory -Path $runDir -Force | Out-Null
            Set-Content -Path $stopFile -Value ([DateTime]::UtcNow.ToString("o")) -Encoding UTF8
            $deadline = [DateTime]::UtcNow.AddSeconds(60)
            while ([DateTime]::UtcNow -lt $deadline) {
                $process = Get-Process -Id $supervisorPid -ErrorAction SilentlyContinue
                if (-not $process) {
                    break
                }
                Start-Sleep -Milliseconds 500
            }
            if (Get-Process -Id $supervisorPid -ErrorAction SilentlyContinue) {
                & taskkill /PID $supervisorPid /T /F | Out-Null
            }
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    Remove-Item $stopFile -Force -ErrorAction SilentlyContinue
}

switch ($Action) {
    "enable" {
        Enable-ScheduledTask -TaskName $TaskName | Out-Null
        Write-Output "Tarea habilitada. Arrancará en el próximo inicio o inicio de sesión."
    }
    "disable" {
        Disable-ScheduledTask -TaskName $TaskName | Out-Null
        Write-Output "Tarea deshabilitada. El proceso actual no se ha detenido."
    }
    "start" {
        Enable-ScheduledTask -TaskName $TaskName | Out-Null
        Start-ScheduledTask -TaskName $TaskName
        Write-Output "Supervisor iniciado."
    }
    "stop" {
        Stop-SupervisorTree
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Write-Output "Supervisor, API y colector detenidos."
    }
    "uninstall" {
        Stop-SupervisorTree
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Output "Tarea eliminada."
    }
    default {
        $task = Get-ScheduledTask -TaskName $TaskName
        $info = Get-ScheduledTaskInfo -TaskName $TaskName
        [pscustomobject]@{
            TaskName       = $task.TaskName
            State          = $task.State
            Enabled        = $task.Settings.Enabled
            LastRunTime    = $info.LastRunTime
            LastTaskResult = $info.LastTaskResult
            NextRunTime    = $info.NextRunTime
            SupervisorPid  = if (Test-Path $pidFile) { Get-Content $pidFile } else { $null }
        }
    }
}
