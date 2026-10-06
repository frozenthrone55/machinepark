$ErrorActionPreference = 'Stop'
$source = 'C:\Users\Kris\OneDrive - Wine & Coffee Lovers BV\General\toestelnummers\koffiemachines inventaris 2025.xlsx'
$directory = '\\192.168.0.200\MachineparkData\toestelsynchronisatie'
$target = Join-Path $directory 'koffiemachines inventaris 2025.xlsx'
$log = Join-Path $PSScriptRoot 'copy.log'
$temp = $null
$stream = $null
try {
    if (!(Test-Path -LiteralPath $directory -PathType Container)) { throw 'NAS-map niet bereikbaar.' }
    # Allow Excel/OneDrive to hold the source open; never change the source file.
    $stream = [IO.File]::Open($source, 'Open', 'Read', 'ReadWrite')
    $memory = New-Object IO.MemoryStream
    try { $stream.CopyTo($memory); $bytes = $memory.ToArray() } finally { $memory.Dispose(); $stream.Dispose(); $stream = $null }
    if ($bytes.Length -eq 0 -or $bytes.Length -gt 33554432) { throw 'Excelbestand leeg of te groot.' }
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $hash = [BitConverter]::ToString($sha.ComputeHash($bytes))
        # Reject a source changing while being copied; retry at next scheduled run.
        if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $hash.Replace('-', '')) { throw 'Bron veranderde tijdens het lezen.' }
        if ((Test-Path -LiteralPath $target) -and (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -eq $hash.Replace('-', '')) { exit 0 }
    } finally { $sha.Dispose() }
    $temp = Join-Path $directory ([Guid]::NewGuid().ToString() + '.tmp')
    [IO.File]::WriteAllBytes($temp, $bytes)
    # Publish a complete file in one rename, so Machinepark cannot read half a copy.
    if (Test-Path -LiteralPath $target) { [IO.File]::Replace($temp, $target, ($temp + '.bak')); Remove-Item -LiteralPath ($temp + '.bak') }
    else { [IO.File]::Move($temp, $target) }
    $temp = $null
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) Kopie bijgewerkt."
} catch {
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) Fout: $($_.Exception.Message)"
    Write-Error $_
    exit 1
} finally {
    if ($stream) { $stream.Dispose() }
    if ($temp -and (Test-Path -LiteralPath $temp)) { Remove-Item -LiteralPath $temp }
}
