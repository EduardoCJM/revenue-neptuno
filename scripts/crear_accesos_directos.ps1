# Crea los accesos directos en el escritorio para Aparthotel Neptuno Costa Adeje:
#   - "Neptuno"        → Neptuno.bat (procesa buzón + abre dashboard en :8502)
#   - "BUZON Neptuno"  → carpeta Excel-Lunes\BUZON (drop zone semanal)

$ErrorActionPreference = "Stop"

$raiz       = Split-Path -Parent $PSScriptRoot
$desktop    = [Environment]::GetFolderPath("Desktop")
$bat        = Join-Path $raiz "Neptuno.bat"
$buzon      = Join-Path $raiz "Excel-Lunes\BUZON"

if (!(Test-Path $bat))   { throw "No existe $bat" }
if (!(Test-Path $buzon)) { throw "No existe $buzon" }

$ws = New-Object -ComObject WScript.Shell

# 1) Acceso directo "Neptuno" -> Neptuno.bat
$lnkNeptuno = $ws.CreateShortcut((Join-Path $desktop "Neptuno.lnk"))
$lnkNeptuno.TargetPath       = $bat
$lnkNeptuno.WorkingDirectory = $raiz
$lnkNeptuno.Description      = "Aparthotel Neptuno Costa Adeje - Procesa el buzón y abre el dashboard"
$lnkNeptuno.IconLocation     = "$env:SystemRoot\System32\imageres.dll,109"
$lnkNeptuno.Save()
Write-Host "OK  $($lnkNeptuno.FullName)"

# 2) Acceso directo "BUZON Neptuno" -> carpeta BUZON
$lnkBuzon = $ws.CreateShortcut((Join-Path $desktop "BUZON Neptuno.lnk"))
$lnkBuzon.TargetPath       = $buzon
$lnkBuzon.WorkingDirectory = $raiz
$lnkBuzon.Description      = "Suelta aquí el Excel Planning de PickUpADR de cada lunes (Aparthotel Neptuno)"
$lnkBuzon.IconLocation     = "$env:SystemRoot\System32\imageres.dll,3"
$lnkBuzon.Save()
Write-Host "OK  $($lnkBuzon.FullName)"

Write-Host ""
Write-Host "Accesos directos creados en el escritorio."
