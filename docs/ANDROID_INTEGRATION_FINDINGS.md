# Android integration findings

Status: static APK inspection partially completed; in-game menu integration is not yet implemented or runtime-validated.

## Confirmed from the decoded APK

- Launch activity: `com.rovio.angrybirdstransformers.AngryBirdsTransformersActivity`.
- Rovio activity extends `com.exient.XGS.XGSActivity`.
- `XGSActivity.onCreate()` creates a `SurfaceView` for camera input and a virtual keyboard view, and attaches both using `addContentView()`.
- `ExientGLSurfaceView` extends Android `GLSurfaceView`, configures an EGL context, installs an Exient renderer, and forwards touch events to native input methods.
- The game activity calls `nativeOnCreate()` after the XGS superclass has initialized.

## Additional confirmed engine structure

- `ExientActivity.onCreate()` creates `ExientGLSurfaceView` and installs it as the Activity's entire content view with `Window.setContentView()`.
- `ExientGLSurfaceView$Renderer.onDrawFrame()` calls the native `nativeDrawFrame()` entry point. The main game's frame rendering therefore runs through the native engine path.
- `XGSActivity.onCreate()` adds camera-input and virtual-keyboard views after the GL surface has been installed. Those are auxiliary engine views, not evidence of a native Android main-menu widget system.
- The APK contains `libABBS.so` for ARM64 and ARM32. The actual in-game menu implementation has not yet been mapped to native symbols or assets.

## Native front-end/UI discovery (static string scan)

The ARM64 and ARM32 `libABBS.so` string tables contain matching front-end identifiers, including:

- `CSettingsScreen` and `ShowSettingsScreen`
- `CWindow_PlayButton` and `CWindow_MainSplashScreen`
- `FrontendLoadingScreen` and `DeveloperMenuScreen`
- Multiple `EScreen_FE_*` front-end screen identifiers
- UI resource references such as `UIPAK:textures/uishopscreenatlas.atlas` and `XMLPAK:Parameters/AccessoryShopScreen.xml`

The APK also contains these relevant packed assets:

- `assets/data/ui/ui_bundles.pak`
- `assets/data/ui/ui_additional.pak.manifest`
- `assets/data/uisplash.pak`
- `assets/data/uienv.pak`

These are concrete leads that the game's front-end and settings screens are represented in the native engine/resource system. A string-table hit does not prove a callable API or reveal the scene graph, so no native UI patch has been made yet. Next, inspect the PAK format/manifest and trace the native references and event handlers for the existing front-end settings and main splash screens.

## Integration implications

- The requested UI is a button integrated into the game's existing main menu. A floating Android overlay is explicitly out of scope.
- `XGSActivity.addContentView()` is used by the engine for camera and virtual-keyboard views, but it is not evidence that adding another Android view would place a button inside the game's native menu. Do not use it as a substitute for the requested in-menu button.
- The next investigation must identify the Exient menu/UI scene construction path, its assets/resources and input routing before changing the game UI.
- FPS selection must be connected to verified native frame pacing / display-refresh behavior. A UI selector alone is not an implementation.
- Graphics controls must be omitted until real engine parameters are identified.

## Next investigation

1. Inspect `com.exient.ExientActivity` to determine how the GL surface is created, attached, and layered.
2. Trace `ExientGLSurfaceView.Renderer` and native frame limiting to identify safe telemetry/control hooks.
3. Identify a supported native Exient menu extension point for a `MOD SETTINGS` button and its settings screen.
4. Add a first-launch welcome dialog, persist its dismissal with app-private preferences, and ensure it appears only once.
5. Only then wire functional FPS settings and any verified graphics parameters.

## Safety

The working ~97-FPS base remains isolated on `backup/97fps-working-2026-11-17`. The menu button must be part of the original game's main menu; no floating control is desired. The first-launch welcome notice must be shown once and then stay dismissed. No APK binary or game assets are included in this report.
