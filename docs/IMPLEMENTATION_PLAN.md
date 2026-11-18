# Implementación completa — Revival Mod

Este documento define el alcance de la rama `feature/full-revival-mod`. La rama `backup/97fps-working-2026-11-17` conserva el estado de código que corresponde a la compilación que el usuario probó y reportó funcionando a aproximadamente 97 FPS (con caídas que no bajan de 70 FPS).

## Reglas de seguridad del proyecto

- No sobrescribir ni borrar la rama de respaldo.
- No reemplazar el APK original alojado en el release privado/de referencia.
- Mantener el perfil gráfico original como predeterminado.
- Cada cambio nativo debe validar hash de entrada, ABI, firma de bytes y bytes esperados antes y después.
- Nunca anunciar 120/144 FPS solo porque un selector permita elegirlos: validar presentación real y frame pacing en dispositivo.
- Si una función no tiene un punto de integración identificado, primero investigar; no inyectar código a ciegas.

## Entregables previstos

### 1. Núcleo de rendimiento
- Conservar el parche que ya produjo el salto observado por el usuario.
- Investigar límites restantes del motor, sincronización, refresco Android y limitadores térmicos/batería.
- Medir frame times (no solo FPS promedio), estabilidad y temperatura.
- Habilitar modos 30/60/90/120/144 únicamente cuando la pantalla y el motor los soporten.
- Mantener un fallback seguro y no forzar modos incompatibles.

### 2. Panel de ajustes en juego
- Botón flotante arrastrable y con posición persistente.
- Panel compacto con selector de FPS, indicador de FPS y perfil gráfico.
- Cerrar/reabrir sin reiniciar el juego.
- No interceptar controles táctiles del juego cuando el panel está cerrado.
- Usar una integración Android/Unity/native validada para esta versión; no asumir que una Activity overlay funcionará dentro de la superficie de renderizado.

### 3. Ajustes gráficos
- Perfiles Original, Equilibrado y Rendimiento.
- Ajustes independientes para resolución/escala, sombras y efectos solo si los parámetros reales del juego pueden modificarse.
- Original será el valor por defecto.
- Si una opción no existe en el motor, no mostrar un control cosmético que no haga nada.

### 4. Bienvenida e identidad
- Pantalla/mensaje de bienvenida solicitado por el usuario.
- Nombre “Angry Birds Transformers Revival Mod”.
- Mantener intactos los recursos y la progresión del juego.
- Usar recursos gráficos originales del proyecto o aportados con permiso; no redistribuir recursos propietarios extraídos.

### 5. Compatibilidad y validación
- Compilar y validar ARM64 y ARMv7 por separado.
- Verificar firma, alineación, integridad del APK y ausencia de cambios fuera de lo previsto.
- Pruebas reales iniciales en el Motorola Edge 70 Fusion del usuario.
- Registrar Android, frecuencia configurada, escena, FPS sostenidos, mínimos, frame times y temperatura.
- Etiquetar como experimental cualquier dispositivo/SoC que no haya sido probado.

## Criterios de aceptación

Una función se considera terminada solo si:
1. El cambio está implementado, no solo descrito en un archivo de configuración.
2. La compilación termina correctamente y los artefactos pasan las verificaciones.
3. El juego inicia y la función responde en un dispositivo real.
4. No se rompe la instalación, la interfaz, la física, el audio ni la progresión.
5. Los resultados y limitaciones quedan documentados.

## Orden de integración

1. Auditar y estabilizar la base de FPS que el usuario ya probó.
2. Identificar el punto de integración Android/UI y construir el panel flotante mínimo.
3. Conectar el selector a parámetros reales del motor y al refresco del sistema.
4. Implementar perfiles gráficos reales.
5. Integrar bienvenida y marca.
6. Ejecutar regresión completa y generar APK final de prueba.

El trabajo se puede desarrollar en paralelo por componentes, pero la APK final se integra y prueba en orden para poder aislar regresiones.
