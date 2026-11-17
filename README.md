# Angry Birds Transformers: Revival Mod

**Proyecto fan no oficial para investigar y mejorar la compatibilidad de Angry Birds Transformers en Android moderno.**

> Estado actual: **investigación y planificación técnica**. Todavía no existe un APK modificado ni una función de 144 FPS verificada. Este repositorio registra el análisis de la versión base y prepara un flujo reproducible para desarrollar y probar los cambios sin distribuir archivos originales del juego.

## Objetivos

- Mostrar al iniciar el mensaje de bienvenida **“Angry Birds Transformers Revival Mod”** y el texto **“Bienvenido a mi mod de Angry Birds Transformers con soporte para teléfonos modernos. Desbloqueo FPS hasta 144 Hz. ¡Disfrútalo!”** cuando la función esté implementada.
- Añadir un botón flotante para abrir un panel de ajustes dentro del juego.
- Ofrecer objetivos de 30, 60, 90, 120 y 144 FPS, únicamente cuando el dispositivo, la pantalla y el motor del juego puedan mantenerlos de forma estable.
- Investigar controles de sincronización, límite de FPS y opciones gráficas sin degradar la calidad visual por defecto.
- Probar compatibilidad en distintos fabricantes y SoC: Qualcomm Snapdragon, MediaTek, Samsung Exynos y otros compatibles.
- Mantener el juego original como base y documentar cada cambio verificable.

## Estado del proyecto

| Área | Estado |
|---|---|
| Identificación del APK base 2.42.0.0 | Analizada |
| Inspección inicial de bibliotecas nativas | Parcial |
| Confirmación de dónde se limita realmente el FPS | Pendiente |
| Panel flotante de ajustes | Planificado |
| Menú de selección 30–144 FPS | Planificado |
| Mensaje de bienvenida | Planificado |
| Cambios gráficos | Pendiente de análisis |
| Compilación, firma e instalación de un APK modificado | No realizada |
| Pruebas en dispositivos reales | Pendiente |

Consulta [el análisis del APK](docs/APK_BASELINE.md), [la hoja de ruta](docs/ROADMAP.md) y [el plan técnico de FPS](docs/FPS_TECHNICAL_PLAN.md).

## APK base analizado

- Paquete: `com.rovio.angrybirdstransformers`
- Versión declarada: `2.42.0.0` (metadatos internos de la aplicación: `2.42.0`)
- Version code: `16`
- Target SDK: `36`
- Bibliotecas nativas detectadas: `arm64-v8a` y `armeabi-v7a`
- SHA-256 del archivo base analizado: `ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013`

El APK original no se publica en este repositorio. Cada persona debe aportar una copia que tenga derecho a utilizar.

## Herramientas

Se incluyen utilidades de solo lectura:

- `tools/inspect-apk.sh`: imprime el hash, metadatos Android y bibliotecas ABI de un APK usando Android SDK Build Tools.
- `tools/verify-apk.sh`: verifica la firma de un APK mediante `apksigner`.

Ejemplo:

```bash
bash tools/inspect-apk.sh /ruta/al/juego.apk
bash tools/verify-apk.sh /ruta/al/juego.apk
```

Consulta [la guía de herramientas y compilación](docs/BUILD_GUIDE.md).

## Configuración prevista

El esquema de opciones deseadas está en [config/settings-plan.json](config/settings-plan.json). Es una especificación de diseño, **no un archivo que el juego lea actualmente**.

Los FPS reales dependen de varios límites independientes: frecuencia admitida por la pantalla, modo de refresco del sistema Android, renderizado del motor, sincronización y simulación del juego. Seleccionar “144” en una interfaz no crea soporte real de 144 FPS.

## Alcance y distribución

Este es un proyecto fan no oficial. Angry Birds, Angry Birds Transformers, sus personajes, marcas, código y recursos originales pertenecen a sus respectivos titulares. No se incluyen APKs originales, bibliotecas propietarias, recursos extraídos ni datos del juego. El repositorio debe alojar documentación, herramientas originales y parches diferenciales, no una copia redistribuible del juego.

No se debe instalar un APK modificado si no se confía en su origen o firma. Una compilación modificada normalmente requiere una firma distinta de la original y puede no actualizarse encima de la versión instalada desde una tienda.

## Contribuir / reportar pruebas

Al enviar resultados, indica modelo del dispositivo, versión de Android, SoC/GPU, frecuencia real de pantalla, versión exacta del juego, FPS observados y pasos para reproducir el resultado. No publiques datos personales, tokens ni archivos privados.

Consulta [NOTICE.md](NOTICE.md) para el aviso de propiedad intelectual y carácter no oficial.
