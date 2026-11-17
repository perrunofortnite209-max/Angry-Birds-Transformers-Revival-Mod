# Plan técnico: FPS y refresco de pantalla

## Dos frecuencias diferentes

- **Refresco de pantalla (Hz):** cuántas veces por segundo el panel puede actualizar la imagen.
- **FPS del juego:** cuántos fotogramas nuevos puede producir y presentar el motor cada segundo.

Una pantalla de 120/144 Hz no garantiza que el juego renderice a 120/144 FPS. Del mismo modo, eliminar una variable de límite no garantiza que el motor, la GPU o la lógica del juego soporten esa velocidad.

## Modos deseados

| Opción del futuro panel | Condición para habilitarla |
|---:|---|
| 30 FPS | Siempre como modo de compatibilidad |
| 60 FPS | Solo si el motor y la estabilidad lo permiten |
| 90 FPS | Solo si Android/pantalla lo admiten y el motor se valida |
| 120 FPS | Solo si Android/pantalla lo admiten y el motor se valida |
| 144 FPS | Solo en dispositivos con modo compatible y pruebas satisfactorias |

El panel debe consultar los modos reales disponibles y no ofrecer una tasa superior al refresco útil de la pantalla. En equipos sin soporte o con problemas de estabilidad, debe elegir un modo inferior.

## Capas que hay que investigar

1. **Lógica del juego:** temporizadores, actualización de entidades, físicas y animaciones.
2. **Motor de renderizado:** objetivo de FPS, intervalo de fotograma y sincronización.
3. **Presentación Android:** superficie, compositor y modo de refresco solicitado.
4. **Sistema:** ahorro de batería, temperatura, restricciones del fabricante y modo de pantalla.
5. **Hardware:** GPU, controlador, resolución y capacidad térmica.

## Diseño del panel futuro

- Botón flotante discreto, movible y ocultable.
- Panel con opción de FPS, sincronización y ajustes de calidad.
- Estado visible: “Disponible”, “No admitido” o “Experimental”.
- Aplicar los cambios en un punto seguro, no durante una operación crítica del juego.
- Botón para restaurar valores predeterminados.
- Persistir preferencias sin alterar archivos de progreso.
- Si un modo falla, volver a 60 o 30 FPS y registrar el error sin cerrar el juego.

## Sincronización

La sincronización vertical y las solicitudes de frecuencia de pantalla no son lo mismo que un desbloqueo de FPS. Se deben probar combinaciones controladas y registrar tearing, stutter y latencia de entrada. No se debe forzar una frecuencia que el panel no admita.

## Criterios de pruebas

Por cada modo registrar:
- FPS medio y mínimo observado.
- Frame time medio y percentiles altos (por ejemplo, p95/p99).
- Frecuencia real reportada por Android.
- Temperatura y throttling durante una sesión prolongada.
- Consumo de batería.
- Errores visuales, física acelerada, animaciones desincronizadas o audio alterado.

## Estado de implementación

Este documento describe el diseño y el proceso de validación. Todavía no se ha modificado el motor ni se ha desbloqueado ningún modo FPS en el APK.
