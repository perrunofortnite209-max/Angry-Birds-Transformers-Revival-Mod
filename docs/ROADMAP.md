# Hoja de ruta

## Fase 1 — Base verificable

- [x] Registrar paquete, versión, target SDK, ABI y hash del APK.
- [x] Identificar bibliotecas nativas relevantes.
- [x] Registrar cadenas internas relacionadas con FPS.
- [x] Preparar utilidades de inspección y validación.
- [ ] Reproducir el rendimiento original en al menos un dispositivo ARM64.

## Fase 2 — Ingeniería inversa

- [ ] Mapear funciones de inicialización y renderizado en `libABBS.so`.
- [ ] Localizar el origen de los objetivos de 30 y 60 FPS.
- [ ] Determinar el comportamiento de `LowBatteryFPSCap`.
- [ ] Analizar si el motor separa simulación y renderizado.
- [ ] Documentar offsets por versión y ABI, evitando offsets universales sin validar.

## Fase 3 — Primer prototipo

- [ ] Diseñar un cambio mínimo, reversible y específico de versión.
- [ ] Preparar una configuración de FPS con valores disponibles según el dispositivo.
- [ ] Implementar o integrar el panel flotante solo cuando se conozca un punto de integración estable.
- [ ] Añadir el mensaje de bienvenida solicitado.
- [ ] Mantener los ajustes gráficos originales como predeterminados.
- [ ] Firmar una compilación de prueba con una clave de desarrollo propia.

## Fase 4 — Pruebas

- [ ] Probar instalación limpia y actualización/reversión.
- [ ] Medir FPS sostenidos, tiempos de fotograma y temperatura.
- [ ] Comprobar animaciones, física, colisiones, interfaz, audio y consumo de batería.
- [ ] Probar 30/60/90/120/144 solo en pantallas y dispositivos que anuncien esos modos.
- [ ] Verificar ARM64 y ARMv7 por separado.
- [ ] Registrar modelo, Android, SoC, GPU, frecuencia de pantalla y resultados.

## Fase 5 — Publicación

- [ ] Publicar únicamente código propio, documentación y parches diferenciales permitidos.
- [ ] Añadir hashes y notas de versión a cada parche.
- [ ] Publicar instrucciones de aplicación sobre una copia legítima del APK.
- [ ] No subir el APK original, recursos de Rovio ni bibliotecas propietarias extraídas.
- [ ] Marcar como experimental cualquier combinación de dispositivo no probada.

## Criterio de aceptación de “144 FPS”

No basta con mostrar 144 en el menú. Para anunciar ese modo debe comprobarse que:

1. La pantalla y Android admiten el modo de refresco necesario.
2. El motor presenta fotogramas a esa tasa sin un limitador interno inferior.
3. El juego conserva una simulación correcta.
4. La tasa se mantiene de forma sostenida y no solo en una escena vacía.
5. Se han medido frame times, estabilidad, temperatura y consumo.
