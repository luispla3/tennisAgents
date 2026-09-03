param(
    [ValidateSet("schedule", "status", "cancel")]
    [string]$Action = "schedule",
    [string]$OffTime = "08:00",
    [string]$OnTime = "15:30",
    [datetime]$Date = (Get-Date).Date.AddDays(1),
    [ValidateSet("hibernate", "sleep")]
    [string]$Mode = "hibernate"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$manageScript = Join-Path $PSScriptRoot "manage_windows_task.ps1"
$offTaskName = "TennisAgents PowerNap Off"
$onTaskName = "TennisAgents PowerNap On"
$helperOff = Join-Path $root ".run\power_nap_off.ps1"
$helperOn = Join-Path $root ".run\power_nap_on.ps1"

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
        "-OffTime", "`"$OffTime`"",
        "-OnTime", "`"$OnTime`"",
        "-Date", "`"$($Date.ToString('yyyy-MM-dd'))`"",
        "-Mode", $Mode
    )
    $process = Start-Process `
        -FilePath "powershell.exe" `
        -Verb RunAs `
        -ArgumentList ($arguments -join " ") `
        -Wait `
        -PassThru
    exit $process.ExitCode
}

function Get-TaskInfoSafe([string]$Name) {
    try {
        $task = Get-ScheduledTask -TaskName $Name -ErrorAction Stop
        $info = Get-ScheduledTaskInfo -TaskName $Name
        return [pscustomobject]@{
            TaskName    = $Name
            State       = $task.State
            Enabled     = $task.Settings.Enabled
            NextRunTime = $info.NextRunTime
            LastRunTime = $info.LastRunTime
            LastResult  = $info.LastTaskResult
            WakeToRun   = $task.Settings.WakeToRun
        }
    } catch {
        return [pscustomobject]@{
            TaskName    = $Name
            State       = "Missing"
            Enabled     = $false
            NextRunTime = $null
            LastRunTime = $null
            LastResult  = $null
            WakeToRun   = $null
        }
    }
}

if ($Action -eq "status") {
    Get-TaskInfoSafe $offTaskName
    Get-TaskInfoSafe $onTaskName
    exit 0
}

if ($Action -eq "cancel") {
    foreach ($name in @($offTaskName, $onTaskName)) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    }
    Remove-Item $helperOff, $helperOn -Force -ErrorAction SilentlyContinue
    Write-Output "PowerNap cancelado (tareas y helpers eliminados)."
    exit 0
}

$offAt = [datetime]::ParseExact(
    ($Date.ToString("yyyy-MM-dd") + " " + $OffTime),
    "yyyy-MM-dd HH:mm",
    [System.Globalization.CultureInfo]::InvariantCulture
)
$onAt = [datetime]::ParseExact(
    ($Date.ToString("yyyy-MM-dd") + " " + $OnTime),
    "yyyy-MM-dd HH:mm",
    [System.Globalization.CultureInfo]::InvariantCulture
)

if ($onAt -le $offAt) {
    throw "OnTime debe ser posterior a OffTime el mismo día."
}
if ($offAt -le (Get-Date).AddMinutes(2)) {
    throw "OffTime ($offAt) es demasiado pronto; elige una hora futura."
}

New-Item -ItemType Directory -Path (Join-Path $root ".run") -Force | Out-Null

# Habilitar hibernación si se pide; si falla, degradar a sleep.
$effectiveMode = $Mode
if ($Mode -eq "hibernate") {
    try {
        powercfg /hibernate on | Out-Null
        $avail = powercfg /a
        if ($avail -match "Hibernar" -and $avail -match "no est") {
            # sigue listada como no disponible
            if ($avail -notmatch "(?m)^\s*Hibernar\s*$") {
                Write-Output "Hibernación no disponible; se usará sleep (S3)."
                $effectiveMode = "sleep"
            }
        }
        $check = powercfg /a
        if ($check -match "No se habilit" -or $check -match "Hibernation has not been enabled") {
            Write-Output "Hibernación no disponible; se usará sleep (S3)."
            $effectiveMode = "sleep"
        } elseif ($check -match "Hibernar\s*$" -or $check -match "(?m)^\s*Hibernate\s*$") {
            $effectiveMode = "hibernate"
        } else {
            # Si aparece bajo "disponibles"
            if ($check -match "disponibles en este sistema:[\s\S]*?Hibernar") {
                $effectiveMode = "hibernate"
            } else {
                Write-Output "Hibernación no disponible; se usará sleep (S3)."
                $effectiveMode = "sleep"
            }
        }
    } catch {
        Write-Output "No se pudo habilitar hibernación; se usará sleep (S3)."
        $effectiveMode = "sleep"
    }
}

# Asegurar wake timers en el plan actual.
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null
powercfg /SETACTIVE SCHEME_CURRENT | Out-Null

$offBody = @"
`$ErrorActionPreference = 'Continue'
`$log = Join-Path '$root' '.run\power_nap.log'
function Write-NapLog(`$msg) {
    `$line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + `$msg
    Add-Content -Path `$log -Value `$line -Encoding UTF8
}
Write-NapLog 'PowerNap OFF start (mode=$effectiveMode)'
try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File '$manageScript' -Action stop
    Write-NapLog 'Supervisor stopped'
} catch {
    Write-NapLog ("Stop supervisor failed: " + `$_.Exception.Message)
}
Start-Sleep -Seconds 5
if ('$effectiveMode' -eq 'hibernate') {
    Write-NapLog 'Hibernating'
    shutdown.exe /h
} else {
    Write-NapLog 'Sleeping (S3)'
    rundll32.exe powrprof.dll,SetSuspendState 0,1,0
}
"@

$onBody = @"
`$ErrorActionPreference = 'Continue'
`$log = Join-Path '$root' '.run\power_nap.log'
function Write-NapLog(`$msg) {
    `$line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + `$msg
    Add-Content -Path `$log -Value `$line -Encoding UTF8
}
Write-NapLog 'PowerNap ON start'
try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File '$manageScript' -Action start
    Write-NapLog 'Supervisor started'
} catch {
    Write-NapLog ("Start supervisor failed: " + `$_.Exception.Message)
}
"@

Set-Content -Path $helperOff -Value $offBody -Encoding UTF8
Set-Content -Path $helperOn -Value $onBody -Encoding UTF8

foreach ($name in @($offTaskName, $onTaskName)) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
}

$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

$offAction = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$helperOff`""
$offTrigger = New-ScheduledTaskTrigger -Once -At $offAt
$offSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask `
    -TaskName $offTaskName `
    -Action $offAction `
    -Trigger $offTrigger `
    -Principal $principal `
    -Settings $offSettings `
    -Description "Detiene TennisAgents y suspende/hiberna el PC (ventana de descanso)." `
    -Force | Out-Null

$onAction = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$helperOn`""
$onTrigger = New-ScheduledTaskTrigger -Once -At $onAt
$onSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask `
    -TaskName $onTaskName `
    -Action $onAction `
    -Trigger $onTrigger `
    -Principal $principal `
    -Settings $onSettings `
    -Description "Despierta el PC y reinicia TennisAgents tras la ventana de descanso." `
    -Force | Out-Null

Write-Output "PowerNap programado."
Write-Output "  Modo efectivo : $effectiveMode"
Write-Output "  Apagar/reposo : $offAt"
Write-Output "  Encender      : $onAt (WakeToRun)"
Write-Output "  Nota: apagado total (shutdown) casi nunca se autoenciende; se usa $effectiveMode."
Get-TaskInfoSafe $offTaskName | Format-List
Get-TaskInfoSafe $onTaskName | Format-List
