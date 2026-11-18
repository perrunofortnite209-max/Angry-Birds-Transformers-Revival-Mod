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

## PAK format research and extraction route

External format research identifies the game's archives as Exient XGS PAK containers, with known XPK1/XPK2 variants. The QuickBMS `xpk2.bms` script explicitly lists Angry Birds among supported XPK2 targets, and the public ImHex `xgspak.hexpat` pattern documents header, folder table, file metadata, string-table offsets, payload offsets, and compression variants (raw, zlib, LZ4).

This is a research lead, not yet proof that every PAK in this exact APK uses the same variant. The next pass must inspect the actual magic/version/endian/compression fields from the APK's own PAK headers before choosing an extractor. Do not reimport or modify any PAK until extraction and round-trip integrity are demonstrated on a disposable copy.

Useful public references:
- QuickBMS XPK2 script listing: https://aluigi.altervista.org/bms/xpk2.bms
- ImHex Exient XGS PAK pattern: https://github.com/WerWolv/ImHex-Patterns/blob/master/patterns/xgspak.hexpat
- Community notes mention a custom KPX header and distinguish APK PAKs from OBB archives.

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
