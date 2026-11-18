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

The successful private diagnostic run inspected the exact APK and confirmed that sampled `.pak` headers begin with `02 4b 50 58` (`version=2`, `KPX` magic). The header fields decode as little-endian values and the version-2 compression field is `1`, which the XGS pattern defines as zlib. For example, `ui_bundles.pak` reports 4 folders, 27 files and a 703-byte content table; `uienv.pak` reports 2 folders and 2 files; `uisplash.pak` reports 5 folders and 19 files. This is strong evidence that these sampled game archives use the XGS version-2 layout with zlib compression. It does not prove every `.pak` or `.manifest` in the APK shares that layout: the manifest has a different leading version byte and must be treated separately. The diagnostics script now decodes and prints these header fields for each `.pak` on subsequent runs. Do not reimport or modify any PAK until extraction and round-trip integrity are demonstrated on a disposable copy.

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

1. Implement a read-only XGS v2/zlib extractor against disposable copies of the exact APK's `.pak` files; validate every extracted entry and archive bounds before using any output.
2. Produce a text-only inventory of `ui_bundles.pak`, `uisplash.pak`, and `uienv.pak` to locate the front-end scene, button resources, atlas and settings-screen definitions.
3. Trace the native references and event handlers for `CWindow_MainSplashScreen`, `CSettingsScreen` and `ShowSettingsScreen`; identify a real native menu extension point for `MOD SETTINGS`.
4. Separately validate the native frame-cap patch against the observed 30–32 FPS original behavior and the user's experimental ~72–97 FPS readings; measure frame pacing rather than assuming the cap patch alone solves performance.
5. Build a private experimental APK only after the patch is verified, then install and test on the Motorola Edge 70 Fusion. Add the one-time welcome notice and settings UI after the native integration point is understood.

## Safety

The working ~97-FPS base remains isolated on `backup/97fps-working-2026-11-17`. The menu button must be part of the original game's main menu; no floating control is desired. The first-launch welcome notice must be shown once and then stay dismissed. No APK binary or game assets are included in this report.
