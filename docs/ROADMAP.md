# Hoja de ruta

## Fase 1 — Base verificable

- [x] Registrar paquete, versión, target SDK, ABI y hash del APK.
- [x] Identificar bibliotecas nativas relevantes.
- [x] Registrar cadenas internas relacionadas con FPS.
- [x] Preparar utilidades de inspección y validación.
- [ ] Reproducir el rendimiento original en al menos un dispositivo ARM64.

## Fase 2 — Ingeniería inversa

- [x] Localizar la pantalla nativa de ajustes `EScreen_FE_Settings`.
- [x] Confirmar que existe una pantalla nativa reutilizable `EScreen_FE_FeatureConfig` con interruptores y guardado para el siguiente inicio.
- [x] Localizar el botón de Feature Config actualmente oculto dentro de la pantalla de ajustes.
- [x] Confirmar que `deviceconfigs.pak` admite reconstrucción reversible y que los perfiles XOX2 pasan la validación cruzada.
- [ ] Confirmar el origen exacto de la configuración global de funciones que consume el motor.
- [ ] Confirmar cómo resuelve el motor el perfil gráfico para dispositivos Android no listados.
- [ ] Diseñar un perfil gráfico optimizado conservador que no modifique el desbloqueo de FPS.
- [ ] Verificar el comportamiento de lectura/escritura del interruptor gráfico en el arranque.

## Fase 3 — Integración Revival Mod

- [ ] Reutilizar la pantalla nativa de configuración y exponerla en Ajustes con el nombre `MOD SETTINGS`.
- [ ] Colocar el control `PARCHE GRÁFICO` junto a los controles de FPS y las demás opciones del mod.
- [ ] Mantener el perfil original como predeterminado y permitir activar/desactivar el perfil optimizado.
- [ ] Conservar los controles de FPS ya existentes y su desbloqueo.
- [ ] Integrar el mensaje de bienvenida en el primer inicio, con opción para cerrarlo.
- [ ] Reemplazar el icono de launcher (adaptativo y heredado) usando el recurso gráfico proporcionado por el usuario.
- [ ] Firmar una compilación de prueba con una clave de desarrollo propia.

## Fase 4 — Pruebas

- [ ] Probar instalación limpia y actualización/reversión.
- [ ] Medir FPS sostenidos, tiempos de fotograma y temperatura con el parche gráfico apagado y encendido.
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
