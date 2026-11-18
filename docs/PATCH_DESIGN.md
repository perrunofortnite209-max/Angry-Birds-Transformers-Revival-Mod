# Arquitectura propuesta del parche

## Principio

El primer cambio debe ser pequeño y reversible. No conviene sustituir bibliotecas completas ni cambiar varios subsistemas a la vez antes de saber qué función controla el frame pacing.

## Componentes propuestos

### 1. Perfil de dispositivo

Obtener de Android los modos de refresco que realmente anuncia la pantalla. No asumir que todos los fabricantes exponen las mismas tasas ni que el modo solicitado queda activo.

### 2. Controlador de FPS

Traducir la elección del usuario a un objetivo compatible con el motor. El controlador debe distinguir entre tasa solicitada, tasa permitida por el motor y tasa observada.

### 3. Ajustes dentro del menú original

Añadir la entrada **MOD SETTINGS** a la pantalla nativa `CSettingsScreen`, sin panel flotante ni ventana externa. La opción debe convivir con privacidad, borrado de datos, asistencia, restauración de compras, inicio de sesión, sonido y valoración. No se deben reemplazar ni alterar esos controles.

La pantalla original ya declara enlaces para `Page1`/`Page2`, controles de sonido, ahorro de energía, restauración, asistencia y valoración. La integración debe respetar esa estructura y abrir una página propia del mod mediante una acción que el motor realmente reconozca.

### 4. Preferencias

Guardar únicamente opciones propias del mod. No modificar partidas guardadas, compras, identificadores de usuario ni datos de cuenta.

### 5. Telemetría local de pruebas

Mostrar FPS y estado de modo solo para diagnóstico. No enviar datos del dispositivo a servidores externos.

## Orden de integración

1. Determinar cómo se controla actualmente el FPS.
2. Crear un prototipo de cambio de tasa sin interfaz.
3. Validarlo con escenas repetibles.
4. Añadir detección de modos de pantalla.
5. Integrar MOD SETTINGS en CSettingsScreen y validar su acción de navegación.
6. Añadir bienvenida de primer inicio y preferencias persistentes.
7. Probar opciones gráficas una por una.

## Compatibilidad

Mantener separado el código común y las diferencias por ABI. Cualquier parche nativo debe estar ligado al hash de la biblioteca original y a su versión. Si el hash cambia, detener la aplicación del parche en vez de escribir en un offset desconocido.

## No implementado

Esta es una propuesta de arquitectura; ninguno de estos componentes está integrado en el APK todavía.
