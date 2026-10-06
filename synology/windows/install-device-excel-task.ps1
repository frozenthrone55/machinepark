$ErrorActionPreference = 'Stop'
$directory = Join-Path $env:LOCALAPPDATA 'MachineparkToestelsynchronisatie'
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$script = Join-Path $directory 'copy-device-excel.ps1'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'copy-device-excel.ps1') -Destination $script -Force
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy RemoteSigned -File "' + $script + '"')
$triggers = @((New-ScheduledTaskTrigger -AtLogOn -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)), (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 3650)))
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 3) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'Machinepark Excelkopie' -Action $action -Trigger $triggers -Principal $principal -Settings $settings -Force | Out-Null
& $script
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw 'Eerste kopie mislukt. Bekijk copy.log.' }
Write-Host 'Taak ingesteld: elke 15 minuten terwijl je bent aangemeld. Logboek:' (Join-Path $directory 'copy.log')
