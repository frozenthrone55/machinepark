@echo off
setlocal
set "MP_SELF=%~f0"
title Machinepark - Outlook Classic koppelen
echo.
echo Machinepark wordt gekoppeld aan Outlook Classic...
echo Dit gebeurt alleen voor je eigen Windows-profiel.
echo.
rem machinepark-outlook-installer-temp-ps1-v3
set "MP_PS1=%TEMP%\Machinepark-Outlook-Classic-Setup-%RANDOM%%RANDOM%.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$raw=Get-Content -LiteralPath $env:MP_SELF -Raw; $hit=[regex]::Match($raw,'(?m)^###MACHINEPARK_POWERSHELL###\r?$'); if(-not $hit.Success){throw 'Installatie-inhoud ontbreekt.'}; $payload=$raw.Substring($hit.Index+$hit.Length); [IO.File]::WriteAllText($env:MP_PS1,$payload,(New-Object Text.UTF8Encoding($false)))"
if errorlevel 1 goto :install_failed
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%MP_PS1%"
set "MP_RC=%ERRORLEVEL%"
del /q "%MP_PS1%" >nul 2>&1
set "MP_PS1="
if not "%MP_RC%"=="0" goto :install_failed
exit /b 0

:install_failed
if defined MP_PS1 del /q "%MP_PS1%" >nul 2>&1
echo.
echo De Outlook Classic-koppeling kon niet worden geinstalleerd.
echo Controleer of Windows PowerShell beschikbaar is en probeer opnieuw.
pause
exit /b 1
###MACHINEPARK_POWERSHELL###
$ErrorActionPreference = 'Stop'
try {
    $installDir = Join-Path $env:LOCALAPPDATA 'MachineparkOutlookBridge'
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
    $bridgePath = Join-Path $installDir 'MachineparkOutlookBridge.ps1'

    $bridge = @'
param([string]$ProtocolUrl)
$ErrorActionPreference = 'Stop'
$logDir = Join-Path $env:LOCALAPPDATA 'MachineparkOutlookBridge'
$logPath = Join-Path $logDir 'bridge.log'
try {
    if ([string]::IsNullOrWhiteSpace($ProtocolUrl)) { throw 'Geen Machinepark-aanvraag ontvangen.' }
    $uri = [System.Uri]$ProtocolUrl
    if ($uri.Scheme -ne 'machinepark-outlook') { throw 'Ongeldig Machinepark-protocol.' }

    Add-Type -AssemblyName System.Web
    $query = [System.Web.HttpUtility]::ParseQueryString($uri.Query)
    $fileName = [string]$query['file']
    $subject = [string]$query['subject']
    $body = [string]$query['body']

    if ([string]::IsNullOrWhiteSpace($fileName)) { throw 'PDF-bestandsnaam ontbreekt.' }
    if ([System.IO.Path]::GetFileName($fileName) -ne $fileName) { throw 'Ongeldige PDF-bestandsnaam.' }
    if (-not $fileName.StartsWith('Machinepark_', [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Alleen Machinepark-PDF bestanden zijn toegestaan.' }
    if ([System.IO.Path]::GetExtension($fileName).ToLowerInvariant() -ne '.pdf') { throw 'Alleen PDF-bestanden zijn toegestaan.' }

    $shell = New-Object -ComObject Shell.Application
    $downloadNs = $shell.NameSpace('shell:Downloads')
    if ($null -eq $downloadNs) { throw 'Windows Downloads-map kon niet worden gevonden.' }
    $downloadDir = [string]$downloadNs.Self.Path
    $pdfPath = Join-Path $downloadDir $fileName

    # Machinepark start deze helper direct vanuit de echte klik op Mail PDF.
    # De PDF wordt daarna opgebouwd en gedownload; wacht dus tot het bestand er staat.
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    while ((-not (Test-Path -LiteralPath $pdfPath -PathType Leaf)) -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 250
    }
    if (-not (Test-Path -LiteralPath $pdfPath -PathType Leaf)) { throw ('De PDF werd niet in Downloads gevonden: ' + $fileName) }

    $pdf = Get-Item -LiteralPath $pdfPath
    if ($pdf.Length -le 0) { throw 'De gedownloade PDF is leeg.' }
    if ($pdf.LastWriteTimeUtc -lt [DateTime]::UtcNow.AddMinutes(-10)) { throw 'De gevonden PDF is niet recent genoeg.' }

    $outlook = New-Object -ComObject Outlook.Application
    $mail = $outlook.CreateItem(0)
    if (-not [string]::IsNullOrWhiteSpace($subject)) { $mail.Subject = $subject }
    if (-not [string]::IsNullOrWhiteSpace($body)) { $mail.Body = $body }
    [void]$mail.Attachments.Add($pdf.FullName)
    $mail.Display()
}
catch {
    try {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        Add-Content -LiteralPath $logPath -Value ((Get-Date).ToString('s') + ' ' + $_.Exception.Message)
    } catch {}
    try {
        $ws = New-Object -ComObject WScript.Shell
        [void]$ws.Popup(('Outlook Classic kon niet worden geopend met de PDF als bijlage.' + [Environment]::NewLine + [Environment]::NewLine + $_.Exception.Message), 0, 'Machinepark', 16)
    } catch {}
    exit 1
}
'@

    Set-Content -LiteralPath $bridgePath -Value $bridge -Encoding UTF8

    $protocolRoot = 'HKCU:\Software\Classes\machinepark-outlook'
    New-Item -Path $protocolRoot -Force | Out-Null
    Set-Item -Path $protocolRoot -Value 'URL:Machinepark Outlook Classic'
    New-ItemProperty -Path $protocolRoot -Name 'URL Protocol' -Value '' -PropertyType String -Force | Out-Null

    $iconKey = Join-Path $protocolRoot 'DefaultIcon'
    New-Item -Path $iconKey -Force | Out-Null
    Set-Item -Path $iconKey -Value 'OUTLOOK.EXE,0'

    $commandKey = Join-Path $protocolRoot 'shell\open\command'
    New-Item -Path $commandKey -Force | Out-Null
    $command = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $bridgePath + '" "%1"'
    Set-Item -Path $commandKey -Value $command

    $ws = New-Object -ComObject WScript.Shell
    [void]$ws.Popup(('Machinepark is gekoppeld aan Outlook Classic.' + [Environment]::NewLine + [Environment]::NewLine + 'Je kunt dit venster sluiten en terugkeren naar Machinepark.'), 0, 'Machinepark', 64)
}
catch {
    try {
        $ws = New-Object -ComObject WScript.Shell
        [void]$ws.Popup(('De Outlook Classic-koppeling kon niet worden geinstalleerd.' + [Environment]::NewLine + [Environment]::NewLine + $_.Exception.Message), 0, 'Machinepark', 16)
    } catch {}
    exit 1
}
