# Laboratorio privado para el APK original

## Por qué está separado

El repositorio principal es público. **Nunca subas aquí el APK de Rovio**, sus bibliotecas ni una copia modificada que contenga recursos originales. El archivo original analizado mide aproximadamente 130 MB; tampoco debe incluirse en commits normales.

La conexión de GitHub usada para este proyecto permite crear/editar archivos de texto, pero no expone una acción para crear repositorios privados ni para cargar adjuntos binarios. Por eso este flujo queda preparado, pero el repositorio privado y la carga inicial deben hacerse desde la interfaz web de GitHub.

## Preparar el laboratorio privado

1. En GitHub, crea un repositorio nuevo llamado `ABT-Revival-APK-Lab` y selecciona **Private**.
2. Copia al repositorio privado estos elementos de este proyecto: `.github/workflows/inspect-private-apk.yml`, `tools/inspect-apk.sh` y `tools/inspect-native-fps.sh`.
3. En el repositorio privado, crea una Release con la etiqueta `apk-baseline`.
4. Adjunta a esa Release el APK original que tengas derecho a utilizar. No lo adjuntes al repositorio público.
5. Abre **Actions → Inspect private APK (read-only) → Run workflow** y deja la etiqueta `apk-baseline`.
6. Al terminar, descarga el artefacto `abt-private-apk-analysis`. Contiene informes de texto, no el APK original.

## Qué realiza el workflow

- Está condicionado a que el repositorio sea privado; en el repositorio público el trabajo queda omitido.
- Descarga el APK desde una Release del mismo repositorio privado.
- Comprueba la integridad ZIP del APK y calcula SHA-256.
- Busca `libABBS.so` en ARM64 y ARMv7.
- Extrae cadenas relacionadas con FPS para orientar la ingeniería inversa.
- Publica únicamente el informe de texto como artefacto temporal.

## Qué NO realiza

Este flujo es deliberadamente de solo lectura. No desensambla instrucciones nativas, no parchea `libABBS.so`, no recompila, no firma y no promete soporte 144 FPS. Para realizar esos cambios se necesita después un análisis estático/dinámico real de las funciones encontradas y pruebas en un dispositivo.

## Seguridad

- No publiques el APK ni sus bibliotecas en el repositorio público.
- No guardes claves de firma en el repositorio ni en los logs.
- El artefacto de análisis caduca a los 7 días.
- El APK original permanece como adjunto de la Release privada y no se adjunta al resultado del workflow.
