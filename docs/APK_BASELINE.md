# Línea base técnica del APK

## Archivo examinado

- Nombre recibido: `com.rovio.angrybirdstransformers-24200(1).apk`
- Tamaño: 130,370,652 bytes
- SHA-256: `ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013`
- Paquete: `com.rovio.angrybirdstransformers`
- Version code: `16`
- Version name observada en manifiesto: `2.42.0`
- Versión de tienda en `assets/data/version.xml`: `2.42.0.0`
- Target SDK: `36`

## Bibliotecas nativas detectadas

| ABI | Biblioteca | Tamaño |
|---|---|---:|
| arm64-v8a | `libABBS.so` | 17,894,096 bytes |
| armeabi-v7a | `libABBS.so` | 16,247,044 bytes |
| ambas ABI | `libBeaconSDK.so` | Presente |
| ambas ABI | `libapplovin-native-crash-reporter.so` | Presente |
| ambas ABI | `libc++_shared.so` | Presente |

El nombre `libABBS.so` sugiere que buena parte del motor o la lógica nativa está ahí. No se ha confirmado todavía el motor exacto ni la ubicación de todas las rutinas de renderizado.

## Indicios sobre FPS

En cadenas de texto extraídas de `libABBS.so` se encontraron identificadores como:

- `TARGET_60_FPS`
- `TARGET_30_FPS`
- `Target_30_fps`
- `Target30FPS`
- `LowBatteryFPSCap`
- `Framerate`

También aparecen cadenas asociadas a tiempos de fotograma y registro de FPS.

### Qué se puede concluir

El binario contiene referencias internas a objetivos de 30/60 FPS y a un posible límite relacionado con batería. Esto justifica investigar el sistema de frame pacing del motor.

### Qué NO se puede concluir todavía

- No demuestra por sí solo que el juego esté bloqueado actualmente a 30 o 60 FPS.
- No identifica aún la función que aplica el límite.
- No demuestra que 90, 120 o 144 FPS funcionen.
- No demuestra que la simulación, animaciones, físicas, audio o interfaz sean seguros a tasas superiores.
- No demuestra que todos los dispositivos Android puedan utilizar esos modos.

## Próximas tareas de análisis

1. Desensamblar y mapear las bibliotecas para ARM64 y ARMv7.
2. Identificar referencias cruzadas de las cadenas FPS y llamadas que calculan el intervalo de fotograma.
3. Determinar si el límite se aplica en el motor, en la capa de presentación o mediante configuración.
4. Inspeccionar cómo el juego consulta el modo de pantalla y el estado de ahorro de batería.
5. Diseñar un cambio reversible y comparar el comportamiento original frente al modificado.
6. Validar con mediciones reales antes de anunciar soporte.

## Reproducibilidad

El hash de arriba identifica exactamente el archivo utilizado para esta inspección. Para comparar otra copia, ejecuta `tools/inspect-apk.sh`. Si el hash no coincide, registra la nueva versión como una línea base diferente en vez de asumir que los binarios son idénticos.
