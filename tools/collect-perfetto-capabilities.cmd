@echo off
setlocal
set "OUT=%USERPROFILE%\Desktop\abt-device-trace-capabilities.txt"

(
  echo Angry Birds Transformers - Perfetto capability report
  echo Generated: %DATE% %TIME%
  echo.
  echo === Device model ===
  adb shell getprop ro.product.model
  echo.
  echo === Android version ===
  adb shell getprop ro.build.version.release
  echo.
  echo === Kernel version ===
  adb shell uname -a
  echo.
  echo === Board platform ===
  adb shell getprop ro.board.platform
  echo.
  echo === GPU renderer ===
  adb shell dumpsys SurfaceFlinger 2^>NUL ^| findstr /i "GLES renderer"
  echo.
  echo === Perfetto data sources ===
  adb shell perfetto --query
  echo.
  echo === Atrace categories ===
  adb shell atrace --list_categories
  echo.
  echo === Available ftrace events ===
  adb shell "if [ -r /sys/kernel/tracing/available_events ]; then cat /sys/kernel/tracing/available_events; elif [ -r /sys/kernel/debug/tracing/available_events ]; then cat /sys/kernel/debug/tracing/available_events; else echo TRACE_EVENTS_UNAVAILABLE; fi"
  echo.
  echo === GPU and synchronization event candidates ===
  adb shell "if [ -r /sys/kernel/tracing/available_events ]; then cat /sys/kernel/tracing/available_events; elif [ -r /sys/kernel/debug/tracing/available_events ]; then cat /sys/kernel/debug/tracing/available_events; fi" 2^>NUL ^| findstr /i "gpu kgsl mali fence sync dma_buf binder sched_blocked_reason sched_wakeup"
) > "%OUT%" 2>&1

if errorlevel 1 (
  echo Collection failed. Check that USB debugging is enabled and adb devices shows your phone.
  pause
  exit /b 1
)

echo.
echo Report saved to:
echo %OUT%
echo.
echo Upload this TXT to the existing GitHub Release named game.
pause
