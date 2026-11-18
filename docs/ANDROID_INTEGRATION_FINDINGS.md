# Android integration findings

Status: static APK inspection completed; runtime overlay behavior is not yet validated.

## Confirmed from the decoded APK

- Launch activity: `com.rovio.angrybirdstransformers.AngryBirdsTransformersActivity`.
- Rovio activity extends `com.exient.XGS.XGSActivity`.
- `XGSActivity.onCreate()` creates a `SurfaceView` for camera input and a virtual keyboard view, and attaches both using `addContentView()`.
- `ExientGLSurfaceView` extends Android `GLSurfaceView`, configures an EGL context, installs an Exient renderer, and forwards touch events to native input methods.
- The game activity calls `nativeOnCreate()` after the XGS superclass has initialized.

## Integration implications

- `XGSActivity.addContentView()` is a promising Android-side integration point for a floating control panel.
- This is not proof that a new overlay will be visible, correctly layered, touch-safe, or compatible with immersive mode. Those behaviors must be validated in an instrumented build and on-device.
- Avoid intercepting the GL surface's touch events. The floating controls should consume touches only inside their own bounds and allow game input everywhere else.
- FPS selection must be connected to verified native frame pacing / display-refresh behavior. A UI selector alone is not an implementation.
- Graphics controls must be omitted until real engine parameters are identified.

## Next investigation

1. Inspect `com.exient.ExientActivity` to determine how the GL surface is created, attached, and layered.
2. Trace `ExientGLSurfaceView.Renderer` and native frame limiting to identify safe telemetry/control hooks.
3. Prototype a minimal non-invasive overlay and validate lifecycle, immersive mode, touch pass-through, and rendering.
4. Only then wire functional FPS settings and any verified graphics parameters.

## Safety

The working 97-FPS base remains isolated on `backup/97fps-working-2026-11-17`. No APK binary or game assets are included in this report.
