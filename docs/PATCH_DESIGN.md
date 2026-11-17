# Arquitectura propuesta del parche

## Principio

El primer cambio debe ser pequeño y reversible. No conviene sustituir bibliotecas completas ni cambiar varios subsistemas a la vez antes de saber qué función controla el frame pacing.

## Componentes propuestos

### 1. Perfil de dispositivo

Obtener de Android los modos de refresco que realmente anuncia la pantalla. No asumir que todos los fabricantes exponen las mismas tasas ni que el modo solicitado queda activo.

### 2. Controlador de FPS

Traducir la elección del usuario a un objetivo compatible con el motor. El controlador debe distinguir entre tasa solicitada, tasa permitida por el motor y tasa observada.

### 3. Panel de ajustes

Interfaz pequeña superpuesta al juego, con cierre rápido, controles accesibles y restauración de valores predeterminados. Debe evitar interceptar controles esenciales del juego cuando esté cerrado.

### 4. Preferencias

Guardar únicamente opciones propias del mod. No modificar partidas guardadas, compras, identificadores de usuario ni datos de cuenta.

### 5. Telemetría local de pruebas

Mostrar FPS y estado de modo solo para diagnóstico. No enviar datos del dispositivo a servidores externos.

## Orden de integración

1. Determinar cómo se controla actualmente el FPS.
2. Crear un prototipo de cambio de tasa sin interfaz.
3. Validarlo con escenas repetibles.
4. Añadir detección de modos de pantalla.
5. Añadir el panel flotante.
6. Añadir bienvenida y preferencias.
7. Probar opciones gráficas una por una.

## Compatibilidad

Mantener separado el código común y las diferencias por ABI. Cualquier parche nativo debe estar ligado al hash de la biblioteca original y a su versión. Si el hash cambia, detener la aplicación del parche en vez de escribir en un offset desconocido.

## No implementado

Esta es una propuesta de arquitectura; ninguno de estos componentes está integrado en el APK todavía.
