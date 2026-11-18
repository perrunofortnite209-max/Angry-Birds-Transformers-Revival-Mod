# Angry Birds Transformers — Revival Mod

**Edición fan en desarrollo para mejorar la experiencia y la compatibilidad de Angry Birds Transformers en dispositivos Android actuales.**

Revival Mod es un proyecto independiente centrado en la investigación del motor XGS, la optimización de la presentación gráfica y el desarrollo de un panel de configuración integrado en la interfaz original del juego.

> **Estado:** desarrollo e investigación técnica. Las funciones todavía no integradas o verificadas se identifican como planificadas o pendientes.

---

## Desarrollo

El trabajo se realiza sobre la versión Android **2.42.0.0** y prioriza la conservación de la experiencia original.

Las áreas actualmente bajo estudio son:

- Integración de un apartado de configuración propio dentro del menú del juego.
- Control de la frecuencia de fotogramas, sujeto a las capacidades reales del dispositivo y del motor.
- Ajustes de rendimiento y presentación gráfica, manteniendo la calidad visual original como referencia.
- Compatibilidad con distintas arquitecturas Android y plataformas de hardware.
- Verificación de cada modificación antes de incorporarla a una compilación.

## Estado de implementación

| Componente | Estado |
|---|---|
| Análisis del APK base 2.42.0.0 | Completado |
| Inspección de bibliotecas nativas | En investigación |
| Análisis de la interfaz y navegación original | En progreso |
| Integración del panel Revival Mod | En desarrollo |
| Opciones de frecuencia de fotogramas | En investigación |
| Ajustes gráficos y de rendimiento | Pendiente de validación |
| Compilación modificada y pruebas en dispositivos | Pendiente |

El estado se actualizará conforme cada función esté implementada y verificada. Una opción mostrada en el diseño no implica que ya esté disponible en el juego.

## Versión de referencia

| Dato | Información |
|---|---|
| Paquete Android | `com.rovio.angrybirdstransformers` |
| Versión | `2.42.0.0` |
| Version code | `16` |
| Arquitecturas | `arm64-v8a`, `armeabi-v7a` |
| Motor | Exient XGS |

El APK original se utiliza únicamente como referencia de análisis y no se distribuye desde este repositorio.

## Documentación técnica

- [Análisis de la versión base](docs/APK_BASELINE.md)
- [Hoja de ruta del desarrollo](docs/ROADMAP.md)
- [Investigación del sistema de FPS](docs/FPS_TECHNICAL_PLAN.md)
- [Guía de herramientas y compilación](docs/BUILD_GUIDE.md)
- [Laboratorio privado de análisis](docs/PRIVATE_APK_LAB.md)

## Herramientas

El repositorio contiene herramientas de inspección y verificación:

```bash
bash tools/inspect-apk.sh /ruta/al/juego.apk
bash tools/verify-apk.sh /ruta/al/juego.apk
```

Estas utilidades permiten consultar metadatos, arquitecturas y firma del APK. No modifican el juego por sí mismas.

## Aviso legal

Revival Mod es un proyecto fan independiente, no oficial y sin afiliación, respaldo ni patrocinio de Rovio Entertainment, SEGA o sus compañías relacionadas.

Angry Birds Transformers y todos sus nombres, marcas, personajes, diseños, música, código y recursos originales pertenecen a sus respectivos titulares. Este repositorio contiene documentación y herramientas de desarrollo; no pretende redistribuir el juego ni reclamar derechos sobre sus elementos.

Consulta [NOTICE.md](NOTICE.md) antes de utilizar o distribuir cualquier modificación.
