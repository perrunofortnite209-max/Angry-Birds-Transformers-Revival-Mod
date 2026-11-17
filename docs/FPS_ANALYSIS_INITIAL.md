# Informe inicial de FPS — APK 2.42.0

Fecha del análisis: 2026-11-17
Método: inspección estática de solo lectura mediante GitHub Actions.
APK: `com.rovio.angrybirdstransformers-24200.apk`
Tamaño: 130370652 bytes
SHA-256: `ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013`
Validación ZIP: correcta.

## Hallazgos en libABBS.so

Ambas ABI contienen indicios de control de framerate:
- `LowBatteryFPSCap`
- `TARGET_30_FPS`
- `TARGET_60_FPS`
- `Target30FPS`
- `_Z17LimitFPSWithSleepi`
- `CXGSRenderDeviceOGL::SetFrameRateLimiter(EXGSFPSLimit::Enum)`
- `CXGSRenderDeviceOGL::GetFrameRateLimiter()`
- `CApp::GetDesiredFramerate()`
- `CDeviceConfig::GetDesiredFramerate()`

En ARM64 también aparecen símbolos relacionados con:
- `CDeviceConfig::m_bTarget30FPS`
- `CDeviceConfig::m_bTarget60FPS`
- `XGSClampToTargetFPS`

## Interpretación

El binario contiene una ruta explícita para establecer/consultar el limitador de FPS y lógica de configuración de objetivos de 30/60 FPS. Esto es una pista concreta para continuar la ingeniería inversa; todavía no demuestra qué valor se selecciona en ejecución, dónde se decide el límite ni si el motor soporta de forma estable 90/120/144 FPS.

## Próximo análisis necesario

1. Desensamblar ARM64 y ARMv7 de `libABBS.so`.
2. Localizar las implementaciones de `SetFrameRateLimiter`, `GetFrameRateLimiter`, `GetDesiredFramerate` y `LimitFPSWithSleep`.
3. Seguir referencias cruzadas hacia la selección de `EXGSFPSLimit::Enum` y `LowBatteryFPSCap`.
4. Identificar si el límite se aplica también por VSync, configuración de pantalla o frecuencia del dispositivo.
5. Solo después diseñar un parche mínimo y validar estabilidad, tiempos de frame, temperatura y consumo en dispositivos reales.

## Estado

**Análisis inicial completado. APK sin modificar.** No se ha aplicado ningún parche ni se afirma todavía soporte de 144 FPS.
