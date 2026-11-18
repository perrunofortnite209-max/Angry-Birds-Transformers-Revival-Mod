# Capture native CPU call stacks from XGS on Android (best-effort, read-only).
# Run in PowerShell while the game is open and USB debugging is authorized.
# Usage: .\tools\capture_xgs_native_profile.ps1
# Optional: .\tools\capture_xgs_native_profile.ps1 -DurationSeconds 30

param(
    [ValidateRange(10, 90)]
    [int]$DurationSeconds = 30,
    [string]$Package = "com.rovio.angrybirdstransformers"
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
    throw "ADB no está en PATH. Usa la misma terminal donde ejecutaste capture_xgs_perf.ps1."
}
$devices = & adb devices
$ready = @($devices | Select-String "\tdevice$")
if ($ready.Count -lt 1) {
    throw "No hay un dispositivo ADB autorizado."
}
$gamePid = (& adb shell pidof $Package 2>$null | Out-String).Trim()
if (-not $gamePid) {
    throw "No encuentro el proceso $Package. Abre el juego y vuelve a ejecutar."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$localDir = Join-Path (Get-Location) "xgs-native-profile-$stamp"
New-Item -ItemType Directory -Force -Path $localDir | Out-Null
$remoteData = "/data/local/tmp/xgs-native-$stamp.data"
$remoteReport = "/data/local/tmp/xgs-native-$stamp.txt"
$reportPath = Join-Path $localDir "native-profile-report.txt"
$metaPath = Join-Path $localDir "capture-info.txt"

@(
    "Package: $Package"
    "PID at start: $gamePid"
    "Duration requested: $DurationSeconds seconds"
    "Capture time: $(Get-Date -Format o)"
    "Device:"
    (& adb shell getprop ro.product.manufacturer)
    (& adb shell getprop ro.product.model)
    "Android:"
    (& adb shell getprop ro.build.version.release)
) | Set-Content -Encoding UTF8 $metaPath

Write-Host "Capturando pilas nativas del proceso del juego durante $DurationSeconds segundos."
Write-Host "Juega en la misma zona donde notas las caídas; no cambies los ajustes."

$recordOutput = & adb shell simpleperf record -g --call-graph fp -f 500 --duration $DurationSeconds -p $gamePid -o $remoteData 2>&1
$recordExit = $LASTEXITCODE
$recordOutput | Tee-Object -FilePath (Join-Path $localDir "simpleperf-record.log")
if ($recordExit -ne 0) {
    @(
        ""
        "Simpleperf no pudo grabar el perfil en este dispositivo/build."
        "Código de salida: $recordExit"
        "Salida:"
        ($recordOutput | Out-String)
        ""
        "No se modificó el juego. Posibles causas: permisos de profiling del sistema, build Android o soporte de simpleperf."
    ) | Add-Content -Encoding UTF8 $metaPath
    Write-Warning "Android bloqueó o no soportó la captura nativa. Se guardó el motivo en $localDir."
    Write-Host "Envíame la carpeta/ZIP para revisar el error; no hace falta repetir Perfetto todavía."
    exit 0
}

& adb shell simpleperf report -i $remoteData --sort dso,symbol --children --percent-limit 0.5 2>&1 |
    Tee-Object -FilePath $reportPath
if ($LASTEXITCODE -ne 0) {
    Write-Warning "El perfil se grabó, pero Android no pudo generar el informe simbolizado."
} else {
    Write-Host "Informe nativo generado: $reportPath"
}
& adb pull $remoteData (Join-Path $localDir "native-profile.data") | Out-Null
& adb shell rm -f $remoteData $remoteReport | Out-Null

$zipPath = "$localDir.zip"
Compress-Archive -Path (Join-Path $localDir "*") -DestinationPath $zipPath -Force
Write-Host ""
Write-Host "Listo: $zipPath"
Write-Host "Adjunta ese ZIP aquí. El perfil es de solo lectura y no cambia FPS ni archivos del juego."
