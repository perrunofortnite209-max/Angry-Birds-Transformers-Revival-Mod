# Resultado de desensamblado inicial — APK 2.42.0

Ejecución GitHub Actions: [run #2](https://github.com/perrunofortnite209-max/Angry-Birds-Transformers-Revival-Mod/actions/runs/44168486661)
Estado: completada correctamente.
APK SHA-256: `ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013`

## Confirmado
- El APK se descargó y su integridad ZIP se verificó.
- Se extrajeron y reconocieron las bibliotecas ELF `libABBS.so` para AArch64 (ARM64) y ARM (32-bit).
- El análisis de cadenas detectó nombres de símbolos y literales asociados a FPS, incluidos `SetFrameRateLimiter`, `GetFrameRateLimiter`, `GetDesiredFramerate`, `LimitFPSWithSleep`, `TARGET_30_FPS`, `TARGET_60_FPS` y `LowBatteryFPSCap`.

## Lo que NO se ha podido confirmar
La etapa de `llvm-nm -D` no encontró esos nombres como símbolos dinámicos exportados y el desensamblado por nombre no devolvió cuerpos de funciones. Por tanto, los nombres detectados proceden de cadenas presentes en el binario y no son todavía direcciones o funciones localizadas. Es posible que el binario esté stripped o que los símbolos estén solo como texto.

## Próximo paso técnico
Usar un desensamblador/análisis de referencias cruzadas (por ejemplo Ghidra o Rizin) para:
1. localizar las cadenas FPS en las secciones ELF;
2. encontrar referencias desde código a esas cadenas;
3. reconstruir las funciones y el flujo de selección de límite;
4. comparar ARM64 y ARMv7 antes de diseñar cualquier parche.

**Estado del mod:** APK original sin modificar. No hay parche FPS ni soporte 144 Hz demostrado todavía.
