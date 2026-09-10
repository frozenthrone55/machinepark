from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
setup_path = ROOT / "machinepark-outlook-classic-setup.cmd"
index = index_path.read_text(encoding="utf-8")

DIRECT_MARKER = 'data-machinepark-build-fix="mail-pdf-direct-v4"'
MARKER = 'machinepark-outlook-classic-bridge-v3'

if DIRECT_MARKER not in index:
    raise SystemExit("Buildvalidatie mislukt: directe Mail PDF ontbreekt voor Outlook Classic-koppeling")

# Eénmalige Windows-installatie. Deze registreert alleen onder HKCU (geen administrator nodig)
# een machinepark-outlook: protocol en bewaart de helper in LocalAppData.
setup_cmd = r'''@echo off
setlocal
set "MP_SELF=%~f0"
title Machinepark - Outlook Classic koppelen
echo.
echo Machinepark wordt gekoppeld aan Outlook Classic...
echo Dit gebeurt alleen voor je eigen Windows-profiel.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$raw=Get-Content -LiteralPath $env:MP_SELF -Raw; $mark='###MACHINEPARK_POWERSHELL###'; $pos=$raw.IndexOf($mark); if($pos -lt 0){throw 'Installatie-inhoud ontbreekt.'}; $payload=$raw.Substring($pos+$mark.Length); Invoke-Expression $payload"
if errorlevel 1 (
  echo.
  echo De Outlook Classic-koppeling kon niet worden geinstalleerd.
  echo Controleer of Windows PowerShell beschikbaar is en probeer opnieuw.
  pause
  exit /b 1
)
exit /b 0
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
'''
setup_path.write_text(setup_cmd, encoding="utf-8", newline="\r\n")

if MARKER not in index:
    start = index.find("  async function shareFile(file, title) {")
    end = index.find("\n  async function directMailPdf(button) {", start)
    if start < 0 or end < 0:
        raise SystemExit("Buildvalidatie mislukt: shareFile-route niet gevonden voor Outlook Classic-koppeling")

    replacement = r'''  // machinepark-outlook-classic-bridge-v3
  function machineparkMailUsesNativeShare() {
    const ua = String(navigator.userAgent || '');
    const uaDataMobile = navigator.userAgentData?.mobile === true;
    const phoneOrAndroid = /Android|iPhone|iPod/i.test(ua);
    const iPad = /iPad/i.test(ua) || (navigator.platform === 'MacIntel' && Number(navigator.maxTouchPoints || 0) > 1);
    return uaDataMobile || phoneOrAndroid || iPad;
  }

  function machineparkIsWindowsDesktop() {
    if (machineparkMailUsesNativeShare()) return false;
    const platform = String(navigator.userAgentData?.platform || navigator.platform || navigator.userAgent || '');
    return /Windows|Win32|Win64/i.test(platform);
  }

  function machineparkOutlookContextTitle(context) {
    if (context?.title) return String(context.title);
    if (context?.kind === 'serviceVisit') return 'Serviceverslag';
    if (context?.kind === 'service') {
      if (context.serviceKind === 'maintenance') return 'Onderhoudsverslag';
      return 'Depannageverslag';
    }
    if (context?.kind === 'device') return 'Toesteldetails';
    return 'Machinepark PDF';
  }

  function machineparkOutlookPendingRequest(context) {
    const title = machineparkOutlookContextTitle(context);
    const now = new Date();
    const pad = value => String(value).padStart(2, '0');
    const stamp = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}-${String(now.getMilliseconds()).padStart(3,'0')}`;
    const fileName = `Machinepark_Outlook_${stamp}.pdf`;
    const subject = `Machinepark - ${title}`;
    const body = `In bijlage vind je de PDF uit Machinepark: ${title}.`;
    const protocol = `machinepark-outlook://compose?file=${encodeURIComponent(fileName)}&subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    return { fileName, title, protocol };
  }

  function machineparkLaunchOutlookPending(request) {
    const anchor = document.createElement('a');
    anchor.href = request.protocol;
    anchor.style.display = 'none';
    anchor.setAttribute('aria-hidden', 'true');
    document.body.appendChild(anchor);
    // Belangrijk: deze click gebeurt synchroon binnen de echte Mail PDF-gebruikersklik.
    // Daardoor mag Chrome/Edge de geregistreerde Windows-protocolhandler starten.
    anchor.click();
    anchor.remove();
  }

  function machineparkDownloadOutlookClassicSetup() {
    const anchor = document.createElement('a');
    anchor.href = new URL('machinepark-outlook-classic-setup.cmd', document.baseURI).href;
    anchor.download = 'machinepark-outlook-classic-setup.cmd';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    notify('Open het gedownloade bestand éénmalig om Outlook Classic te koppelen.');
  }

  function machineparkSyncOutlookClassicSetupCard() {
    if (!machineparkIsWindowsDesktop()) return;
    if (document.getElementById('machineparkOutlookClassicSetupCard')) return;
    const view = document.getElementById('view-settings');
    if (!view) return;
    const grid = view.querySelector('.settings-grid') || view;
    const card = document.createElement('div');
    card.id = 'machineparkOutlookClassicSetupCard';
    card.className = 'settings-card';
    card.innerHTML = `<h4>Outlook Classic</h4><p>Eenmalig koppelen op deze Windows-pc. Daarna opent <strong>Mail PDF</strong> rechtstreeks een nieuw Outlook Classic-bericht met de PDF al als bijlage.</p><div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px"><button type="button" class="btn primary" id="machineparkOutlookClassicSetupBtn">Outlook Classic koppelen</button></div><p class="muted" style="font-size:11px;margin:10px 0 0">Na het downloaden open je het installatiebestand één keer. Er zijn geen administratorrechten nodig.</p>`;
    grid.appendChild(card);
    card.querySelector('#machineparkOutlookClassicSetupBtn')?.addEventListener('click', machineparkDownloadOutlookClassicSetup);
  }

  async function shareFile(file, title) {
    const subject = `Machinepark - ${title}`;
    const text = `In bijlage vind je de PDF uit Machinepark: ${title}.`;
    const shareData = { files:[file], title:subject, text };
    const useNativeShare = machineparkMailUsesNativeShare();
    const canShareFile = typeof navigator.share === 'function' && (typeof navigator.canShare !== 'function' || navigator.canShare(shareData));

    // Mobiel behoudt exact de bestaande deelroute.
    if (useNativeShare && canShareFile) {
      try { await navigator.share(shareData); return; }
      catch (error) {
        if (error?.name === 'AbortError') return;
        console.warn('[Machinepark] Mobiele PDF-deling mislukt; mailprogramma wordt gebruikt.', error);
      }
    }

    // De normale Windows-route wordt al vóór PDF-opbouw gestart in directMailPdf,
    // zodat de browser de Outlook-protocolhandler niet kan blokkeren.
    if (machineparkIsWindowsDesktop()) {
      downloadFile(file);
      notify('PDF gedownload. Outlook Classic kon niet vooraf worden gestart; klik Mail PDF opnieuw.');
      return;
    }

    // Niet-Windows desktop houdt een normale mailto-fallback.
    downloadFile(file);
    const body = `${text}\n\nDe PDF is op je toestel gedownload. Voeg het bestand ${file.name} toe als bijlage.`;
    const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    notify('PDF gedownload. Je standaard mailprogramma wordt geopend.');
    setTimeout(() => { window.location.href = mailto; }, 120);
  }

  queueMicrotask(machineparkSyncOutlookClassicSetupCard);
  const outlookSetupObserver = new MutationObserver(machineparkSyncOutlookClassicSetupCard);
  outlookSetupObserver.observe(document.body, { childList:true, subtree:true });
'''
    index = index[:start] + replacement + index[end:]

    old_busy = "      button.textContent = 'Delen…';"
    new_busy = "      button.textContent = machineparkMailUsesNativeShare() ? 'Delen…' : (machineparkIsWindowsDesktop() ? 'Outlook openen…' : 'Mail openen…');"
    if index.count(old_busy) != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1 Mail PDF statusregel, gevonden {index.count(old_busy)}")
    index = index.replace(old_busy, new_busy, 1)

    # De Outlook-protocolhandler moet vanuit de oorspronkelijke gebruikersklik starten.
    # Daarom bepalen we vooraf een unieke bestandsnaam, starten we Windows direct en
    # bouwen/downloaden we daarna de PDF onder exact die naam.
    create_sig = "  async function createDirectPdf(context) {"
    create_sig_new = "  async function createDirectPdf(context, forcedFilename = '') {"
    if index.count(create_sig) != 1:
        raise SystemExit(f"Buildvalidatie mislukt: createDirectPdf-signatuur verwacht 1x, gevonden {index.count(create_sig)}")
    index = index.replace(create_sig, create_sig_new, 1)

    filename_line = "    const filename = `${safeFilename(`Machinepark_${model.filenameTitle}_${stamp}`)}.pdf`;"
    filename_new = "    const filename = forcedFilename || `${safeFilename(`Machinepark_${model.filenameTitle}_${stamp}`)}.pdf`;"
    if index.count(filename_line) != 1:
        raise SystemExit(f"Buildvalidatie mislukt: directe PDF-bestandsnaam verwacht 1x, gevonden {index.count(filename_line)}")
    index = index.replace(filename_line, filename_new, 1)

    direct_start = index.find("  async function directMailPdf(button) {")
    direct_end = index.find("\n\n  document.addEventListener('click', (event) => {", direct_start)
    if direct_start < 0 or direct_end < 0:
        raise SystemExit("Buildvalidatie mislukt: directMailPdf-blok niet gevonden voor directe Outlook-start")

    direct_replacement = r'''  async function directMailPdf(button) {
    if (!button || button.dataset.directPdfBusy === '1') return;
    const context = getContext(button);
    if (!context) { notify('Er is geen afdrukbare inhoud gevonden.'); return; }

    const original = button.textContent;
    const outlookRequest = machineparkIsWindowsDesktop() ? machineparkOutlookPendingRequest(context) : null;

    // Start Outlook/Windows NU, vóór de eerste await. Dit is nog dezelfde echte klik
    // van de gebruiker en voorkomt dat Chrome/Edge het externe protocol blokkeert.
    if (outlookRequest) {
      try {
        machineparkLaunchOutlookPending(outlookRequest);
      } catch (error) {
        console.error('[Machinepark] Outlook Classic protocol kon niet worden gestart', error);
        notify('Outlook Classic kon niet worden gestart. Koppel Outlook Classic opnieuw via Beheer.');
        return;
      }
    }

    button.dataset.directPdfBusy = '1';
    button.disabled = true;
    button.textContent = 'PDF maken…';
    try {
      const file = await createDirectPdf(context, outlookRequest?.fileName || '');
      if (outlookRequest) {
        button.textContent = 'Outlook openen…';
        downloadFile(file);
        notify('PDF gemaakt. Outlook Classic opent met de PDF als bijlage.');
      } else {
        button.textContent = machineparkMailUsesNativeShare() ? 'Delen…' : 'Mail openen…';
        await shareFile(file, context.title || context.kind);
      }
    } catch (error) {
      console.error('[Machinepark] Directe Mail PDF mislukt', error);
      notify(error?.message || 'De PDF kon niet worden gemaakt.');
    } finally {
      button.disabled = false;
      button.dataset.directPdfBusy = '0';
      button.textContent = original;
    }
  }'''
    index = index[:direct_start] + direct_replacement + index[direct_end:]
    index_path.write_text(index, encoding="utf-8")

required = [
    MARKER,
    'function machineparkMailUsesNativeShare()',
    'function machineparkIsWindowsDesktop()',
    'function machineparkOutlookPendingRequest(context)',
    'function machineparkLaunchOutlookPending(request)',
    'machinepark-outlook://compose?file=',
    'machinepark-outlook-classic-setup.cmd',
    'Outlook Classic koppelen',
    "async function createDirectPdf(context, forcedFilename = '')",
    'forcedFilename || `${safeFilename(',
    'const outlookRequest = machineparkIsWindowsDesktop() ? machineparkOutlookPendingRequest(context) : null;',
    'machineparkLaunchOutlookPending(outlookRequest);',
    "createDirectPdf(context, outlookRequest?.fileName || '')",
    'await navigator.share(shareData)',
    "'Outlook openen…'",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: Outlook Classic-koppeling ontbreekt ({needle})")

setup_required = [
    'HKCU:\\Software\\Classes\\machinepark-outlook',
    'MachineparkOutlookBridge.ps1',
    'New-Object -ComObject Outlook.Application',
    '$mail.Attachments.Add($pdf.FullName)',
    "StartsWith('Machinepark_'",
    "NameSpace('shell:Downloads')",
    'AddSeconds(60)',
]
setup_text = setup_path.read_text(encoding='utf-8')
for needle in setup_required:
    if needle not in setup_text:
        raise SystemExit(f"Buildvalidatie mislukt: Outlook Classic setup ontbreekt ({needle})")

print('[Machinepark] Mail PDF: mobiel blijft delen; Windows start Outlook vanuit de gebruikersklik en voegt daarna de PDF toe')
