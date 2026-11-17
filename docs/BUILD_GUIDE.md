# Guía de herramientas y flujo local

## Requisitos de investigación

Para inspeccionar el APK de forma local:

- Android SDK Build Tools (incluye `aapt` y `apksigner`).
- Android SDK Command-line Tools (incluye `apkanalyzer`, según la instalación).
- Java Runtime compatible con las herramientas que se utilicen.
- JADX para inspección de DEX cuando corresponda.
- Apktool para examinar recursos y manifiesto compilado.
- Ghidra u otra herramienta de análisis estático para bibliotecas nativas ARM.
- Un dispositivo de pruebas o emulador compatible.

No todos estos componentes son necesarios para ejecutar los dos scripts de este repositorio.

## Inspeccionar el APK

Linux/macOS/Git Bash:

```bash
bash tools/inspect-apk.sh /ruta/al/archivo.apk
```

El script informa el SHA-256, metadatos del manifiesto si hay una herramienta disponible y las ABI nativas incluidas.

## Verificar una firma

```bash
bash tools/verify-apk.sh /ruta/al/archivo.apk
```

Una APK modificada debe firmarse antes de instalarse. Una clave de desarrollo no equivale a la firma de distribución original.

## Flujo de trabajo previsto

1. Copiar el APK base a una carpeta privada fuera del repositorio.
2. Calcular y registrar su SHA-256.
3. Inspeccionar manifiesto, DEX, recursos y bibliotecas sin modificarlos.
4. Crear un informe reproducible con versión, ABI y hallazgos.
5. Diseñar un parche mínimo y específico para esa versión.
6. Aplicar el parche a una copia de trabajo, conservando intacto el original.
7. Verificar estructura, firma, instalación y ejecución.
8. Medir el comportamiento en dispositivos reales.
9. Publicar solo el código propio y el parche diferencial permitido.

## Importante

- No sobrescribas el APK original.
- No asumas que offsets nativos son iguales entre ARM64, ARMv7 o versiones distintas.
- No compartas claves privadas de firma.
- No subas APKs originales, recursos del juego ni bibliotecas propietarias.
- Una APK recompilada puede perder la firma original y no instalarse como actualización sobre la versión oficial.
- Los scripts de este repositorio solo inspeccionan; no modifican ni desbloquean FPS.
