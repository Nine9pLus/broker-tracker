<#
.SYNOPSIS
  Register Windows Task Scheduler task for the broker-tracker daily pipeline.

.DESCRIPTION
  Creates a weekly task (Mon-Fri) that runs daily_run.py once at 09:30, then exits.
  Replaces existing task of the same name.

  Run from any shell:
      powershell -ExecutionPolicy Bypass -File .\register_task.ps1

  Remove later with:
      Unregister-ScheduledTask -TaskName 'BrokerTracker_0930' -Confirm:$false
#>

$ErrorActionPreference = 'Stop'

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe   = Join-Path $ScriptDir '.venv\Scripts\python.exe'
$DailyScript = Join-Path $ScriptDir 'daily_run.py'
$EnvFile     = Join-Path $ScriptDir '.env'
$LogDir      = Join-Path $ScriptDir 'logs'
$LogFile     = Join-Path $LogDir 'broker-tracker.log'

if (-not (Test-Path $PythonExe))   { throw "Python venv not found: $PythonExe" }
if (-not (Test-Path $DailyScript)) { throw "daily_run.py not found: $DailyScript" }
if (-not (Test-Path $EnvFile))     { Write-Warning ".env not found at $EnvFile -- script will fail at runtime until you create one." }
if (-not (Test-Path $LogDir))      { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$TaskName = 'BrokerTracker_0930'
$Hour     = 9
$Minute   = 30
$Days     = @('Monday','Tuesday','Wednesday','Thursday','Friday')
$LegacyTaskNames = @('BrokerTracker_1500', 'BrokerTracker_1730')

$cmdLine  = 'set PYTHONIOENCODING=utf-8 && set PYTHONUTF8=1 && "' + $PythonExe + '" "' + $DailyScript + '" >> "' + $LogFile + '" 2>&1'
$argString = '/c ' + $cmdLine

$action = New-ScheduledTaskAction `
    -Execute 'cmd.exe' `
    -Argument $argString `
    -WorkingDirectory $ScriptDir

$triggerTime = Get-Date -Hour $Hour -Minute $Minute -Second 0
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Days -At $triggerTime

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task: $TaskName"
}

foreach ($LegacyTaskName in $LegacyTaskNames) {
    if (Get-ScheduledTask -TaskName $LegacyTaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $LegacyTaskName -Confirm:$false
        Write-Host "Removed legacy task: $LegacyTaskName"
    }
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Description "Run broker-tracker daily pipeline once at $('{0:D2}:{1:D2}' -f $Hour, $Minute) Mon-Fri" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal | Out-Null

Write-Host ("Registered: {0}  ->  {1:D2}:{2:D2}  (Mon-Fri)" -f $TaskName, $Hour, $Minute)
Write-Host ''
Write-Host '=== Done ==='
Write-Host "Logs will append to: $LogFile"
Write-Host ''
Write-Host 'Verify:'
Write-Host "    Get-ScheduledTask -TaskName 'BrokerTracker_*' | Format-Table TaskName, State, @{n='NextRun';e={(Get-ScheduledTaskInfo `$_).NextRunTime}}"
Write-Host ''
Write-Host 'Test-fire immediately:'
Write-Host "    Start-ScheduledTask -TaskName 'BrokerTracker_0930'"
