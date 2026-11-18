# Capture XGS runtime performance on an Android device
# Run from Windows PowerShell with USB debugging enabled and the game already open.
# Usage: .\tools\capture_xgs_perf.ps1
# Optional: .\tools\capture_xgs_perf.ps1 -DurationSeconds 60

param(
    [ValidateRange(10, 180)]
    [int]$DurationSeconds = 45,
    [string]$Package = "com.rovio.angrybirdstransformers"
)

$ErrorActionPreference = "Stop"

$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) {
    throw "ADB no está en PATH. Instala Android Platform Tools o agrega adb.exe al PATH."
}

$devices = & adb devices
$ready = @($devices | Select-String "\tdevice$")
if ($ready.Count -lt 1) {
    throw "No hay un dispositivo ADB autorizado. Conecta el teléfono y acepta la depuración USB."
}

$gamePid = (& adb shell pidof $Package 2>$null | Out-String).Trim()
if (-not $gamePid) {
    throw "No encuentro el proceso $Package. Abre el juego y vuelve a ejecutar el script."
}

$remote = "/data/misc/perfetto-traces/xgs-perfetto.pftrace"
$local = Join-Path (Get-Location) ("xgs-perfetto-{0}.pftrace" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

Write-Host "Dispositivo conectado. Proceso del juego: $gamePid"
Write-Host "Iniciando captura Perfetto durante $DurationSeconds segundos."
Write-Host "Durante la captura, juega una partida normal y reproduce las bajadas de FPS."
Write-Host "No cambies los ajustes gráficos ni el límite de FPS durante esta prueba."

& adb shell perfetto -o $remote -t "${DurationSeconds}s" sched freq idle am wm gfx view input
if ($LASTEXITCODE -ne 0) {
    throw "Perfetto no pudo completar la captura. Comprueba que el dispositivo permita ejecutar perfetto."
}

& adb pull $remote $local
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo copiar la traza al PC."
}

Write-Host ""
Write-Host "Captura guardada en: $local"
Write-Host "Envíame ese archivo para revisar tiempos de CPU, planificación y fotogramas."
