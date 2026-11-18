# Android XGS device profiles — APK 2.42.0

Source APK SHA-256: `ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013`

The full XOX2 scan decoded 15,770 XML candidates and found Android device configuration records. These are real XGS profiles, not guesses. Android generic profiles inherit their settings from the iOS quality tiers.

## Profile inheritance

| Android profile | Parent | Important resolved values |
|---|---|---|
| `android-generic_low` | `iOS-low` | Shadows off; game reflections 0; 0.7 × 0.4 render scale; VFX 2; bloom/motion blur/god rays off; soft particles off |
| `android-generic_mediumlow` | `iOS-mediumlow` | Shadows on; reflections 0; 0.9 × 0.6 render scale; 1024 shadow map; VFX 3; bloom on; motion blur/god rays off; soft particles off |
| `android-generic_medium` | `iOS-medium` | Shadows on; reflections 1; 0.9 × 0.6 render scale; 1024 shadow map; VFX 3; bloom on; motion blur off; god rays on; soft particles off |
| `android-generic_high` | `iOS-high` | Reflections 2; 1.0 × 0.7 render scale; 2048 shadow map; VFX 5; bloom, motion blur and god rays on; soft particles on |
| `android-generic_extrahigh` | `iOS-extrahigh` | Reflections 3; 1.0 × 1.0 render scale; 3072 shadow map; VFX 5; full post-processing; soft particles on |
| `android-generic-pvr` | `android-generic_low` | Same resolved values as generic low |

## Existing device mappings

- Motorola Nexus 6 and Motorola XT1254 inherit `android-generic_medium`.
- Huawei CLT-L29 inherits `android-generic_extrahigh`.
- Several older Samsung, HTC, LG, Oppo and Sony models map to generic low/medium tiers.

## Important FPS detail

The resolved low, mediumlow, medium and high profiles set `TARGET_30_FPS=true`; extrahigh sets it to false. This is a graphics/device profile field and must not be confused with the separate frame-pacing path already investigated. The existing FPS-unlock work must be preserved.

## Current decision

No profile has been changed yet. The Motorola Edge 70 Fusion is not listed by exact model in these legacy records, so we must confirm the engine's fallback and device matching behavior before replacing any profile. The next automated check maps each profile entry to its original KPX PAK and verifies that the archive can be rebuilt byte-for-byte before any replacement is attempted.

This report describes static configuration values only. It does not claim measured FPS gains or a verified device-specific runtime profile.
