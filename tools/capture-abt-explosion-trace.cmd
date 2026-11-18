@echo off
setlocal EnableExtensions
set "PKG=com.rovio.angrybirdstransformers"
set "REMOTE_CFG=/data/local/tmp/abt-perfetto-config.pbtxt"
set "REMOTE_TRACE=/data/local/tmp/abt-explosion-trace.pftrace"
set "LOCAL_CFG=%TEMP%\abt-perfetto-config.pbtxt"
set "OUT=%USERPROFILE%\Desktop\abt-explosion-trace.pftrace"
set "REPORT=%USERPROFILE%\Desktop\abt-perfetto-capture-log.txt"

rem Locate adb.exe even when this script is launched by double-click.
set "ADB="
if exist "%~dp0adb.exe" set "ADB=%~dp0adb.exe"
if not defined ADB if exist "%CD%\adb.exe" set "ADB=%CD%\adb.exe"
if not defined ADB if exist "%USERPROFILE%\Documents\platform-tools\adb.exe" set "ADB=%USERPROFILE%\Documents\platform-tools\adb.exe"
if not defined ADB if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" set "ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
if not defined ADB set "ADB=adb"
"%ADB%" version >NUL 2>&1
if errorlevel 1 (
  echo ADB executable not found. Put this CMD beside adb.exe or install Android platform-tools.
  pause
  exit /b 1
)

echo Checking ADB connection...
"%ADB%" get-state >NUL 2>&1
if errorlevel 1 (
  echo Phone not detected. Enable USB debugging and accept the USB prompt.
  pause
  exit /b 1
)

echo Checking Angry Birds Transformers process...
"%ADB%" shell pidof %PKG%
if errorlevel 1 (
  echo Game process not found. Open the game and enter a level first.
  pause
  exit /b 1
)

echo Creating a 30-second Perfetto capture configuration...
(
  echo duration_ms: 30000
  echo buffers { size_kb: 65536 fill_policy: RING_BUFFER }
  echo data_sources {
  echo   config {
  echo     name: "linux.ftrace"
  echo     target_buffer: 0
  echo     ftrace_config {
  echo       atrace_categories: "gfx"
  echo       atrace_categories: "view"
  echo       atrace_categories: "sched"
  echo       atrace_categories: "freq"
  echo       atrace_categories: "idle"
  echo       atrace_categories: "sync"
  echo       atrace_categories: "binder_driver"
  echo       atrace_categories: "wm"
  echo       atrace_categories: "am"
  echo       atrace_categories: "power"
  echo       atrace_categories: "thermal"
  echo       atrace_apps: "%PKG%"
  echo     }
  echo   }
  echo }
  echo data_sources {
  echo   config {
  echo     name: "track_event"
  echo     target_buffer: 0
  echo     track_event_config {
  echo       enabled_categories: "gpu"
  echo       enabled_categories: "gpu.angle"
  echo       enabled_categories: "cc"
  echo       enabled_categories: "viz"
  echo       enabled_categories: "graphics.pipeline"
  echo       enabled_categories: "disabled-by-default-gpu_cmd_queue"
  echo       enabled_categories: "disabled-by-default-display.framedisplayed"
  echo       enabled_categories: "disabled-by-default-cc.debug.scheduler.frames"
  echo     }
  echo   }
  echo }
  echo data_sources {
  echo   config {
  echo     name: "android.surfaceflinger.frametimeline"
  echo     target_buffer: 0
  echo   }
  echo }
) > "%LOCAL_CFG%"

"%ADB%" push "%LOCAL_CFG%" "%REMOTE_CFG%" >NUL
if errorlevel 1 (
  echo Could not copy Perfetto configuration to phone.
  pause
  exit /b 1
)

echo.
echo Starting capture for 30 seconds.
echo Play normally and trigger several large explosions now.
echo Please do not minimize or close the game.
echo.

"%ADB%" shell perfetto --txt -c "%REMOTE_CFG%" -o "%REMOTE_TRACE%" > "%REPORT%" 2>&1
if errorlevel 1 (
  echo.
  echo Perfetto capture failed. See Desktop\abt-perfetto-capture-log.txt
  type "%REPORT%"
  pause
  exit /b 1
)

echo Pulling trace to Desktop...
"%ADB%" pull "%REMOTE_TRACE%" "%OUT%" >> "%REPORT%" 2>&1
if errorlevel 1 (
  echo Could not pull the trace. See Desktop\abt-perfetto-capture-log.txt
  pause
  exit /b 1
)

"%ADB%" shell rm -f "%REMOTE_CFG%" "%REMOTE_TRACE%" >NUL 2>&1
del "%LOCAL_CFG%" >NUL 2>&1

echo.
echo SUCCESS. Trace saved to:
echo %OUT%
echo.
echo Upload abt-explosion-trace.pftrace to the existing GitHub Release named game.
echo Also upload abt-perfetto-capture-log.txt if the capture log reports warnings.
pause
