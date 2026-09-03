param(
    [ValidateSet("apply", "status")]
    [string]$Action = "apply",
    [string]$SchemeGuid = "381b4222-f694-41f0-9685-ff5bb260df2e" # Equilibrado
)

$ErrorActionPreference = "Stop"
$isAdministrator = (
    New-Object Security.Principal.WindowsPrincipal(
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($Action -eq "apply" -and -not $isAdministrator) {
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`"",
        "-Action", $Action,
        "-SchemeGuid", $SchemeGuid
    )
    $process = Start-Process `
        -FilePath "powershell.exe" `
        -Verb RunAs `
        -ArgumentList ($arguments -join " ") `
        -Wait `
        -PassThru
    exit $process.ExitCode
}

function Get-PowerIndex {
    param(
        [string]$Subgroup,
        [string]$Setting
    )
    $output = powercfg /query SCHEME_CURRENT $Subgroup $Setting 2>$null
    if (-not $output) {
        return $null
    }
    $ac = ($output | Select-String -Pattern "corriente alterna actual:\s+0x([0-9a-fA-F]+)" | Select-Object -First 1)
    $dc = ($output | Select-String -Pattern "corriente continua actual:\s+0x([0-9a-fA-F]+)" | Select-Object -First 1)
    if (-not $ac) {
        $ac = ($output | Select-String -Pattern "Current AC Power Setting Index:\s+0x([0-9a-fA-F]+)" | Select-Object -First 1)
    }
    if (-not $dc) {
        $dc = ($output | Select-String -Pattern "Current DC Power Setting Index:\s+0x([0-9a-fA-F]+)" | Select-Object -First 1)
    }
    return [pscustomobject]@{
        AC = if ($ac) { [Convert]::ToInt64($ac.Matches[0].Groups[1].Value, 16) } else { $null }
        DC = if ($dc) { [Convert]::ToInt64($dc.Matches[0].Groups[1].Value, 16) } else { $null }
    }
}

function Show-Status {
    $active = (powercfg /GETACTIVESCHEME)
    $standby = Get-PowerIndex -Subgroup "SUB_SLEEP" -Setting "STANDBYIDLE"
    $hibernate = Get-PowerIndex -Subgroup "SUB_SLEEP" -Setting "HIBERNATEIDLE"
    $hybrid = Get-PowerIndex -Subgroup "SUB_SLEEP" -Setting "HYBRIDSLEEP"
    $wake = Get-PowerIndex -Subgroup "SUB_SLEEP" -Setting "RTCWAKE"
    $lid = Get-PowerIndex -Subgroup "SUB_BUTTONS" -Setting "LIDACTION"
    [pscustomobject]@{
        ActiveScheme   = ($active -replace ".*\((.+)\).*", '$1').Trim()
        StandbyAC_sec  = $standby.AC
        StandbyDC_sec  = $standby.DC
        HibernateAC_sec = $hibernate.AC
        HibernateDC_sec = $hibernate.DC
        HybridSleepAC  = $hybrid.AC
        HybridSleepDC  = $hybrid.DC
        WakeTimersAC   = $wake.AC
        LidCloseAC     = $lid.AC
        LidCloseDC     = $lid.DC
    }
}

if ($Action -eq "status") {
    Show-Status | Format-List
    exit 0
}

Write-Output "Aplicando perfil always-on para TennisAgents..."

# Preferir Equilibrado (u otro GUID pasado) si existe; si no, dejar el actual.
$schemes = powercfg /list
if ($schemes -match $SchemeGuid) {
    powercfg /SETACTIVE $SchemeGuid | Out-Null
    Write-Output "Plan activo: $SchemeGuid"
} else {
    Write-Output "Plan $SchemeGuid no encontrado; se ajusta el plan actual."
}

# Suspender / hibernar: nunca en AC y DC.
powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 0
powercfg /change hibernate-timeout-ac 0
powercfg /change hibernate-timeout-dc 0
powercfg /change monitor-timeout-ac 20
powercfg /change monitor-timeout-dc 10

powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP STANDBYIDLE 0
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP STANDBYIDLE 0
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLE 0
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLE 0
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP HYBRIDSLEEP 0
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP HYBRIDSLEEP 0
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1

# Tapa / botón: no suspender (0 = No hacer nada) si el setting existe.
try {
    powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
    powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
} catch {
    Write-Output "LIDACTION no disponible en este equipo (ignorado)."
}

powercfg /SETACTIVE SCHEME_CURRENT | Out-Null
powercfg /hibernate off

Write-Output "Configuración aplicada."
Show-Status | Format-List
