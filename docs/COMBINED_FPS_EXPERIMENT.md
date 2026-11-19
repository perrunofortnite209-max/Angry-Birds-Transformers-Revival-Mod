# Combined FPS experiment

This branch combines the existing guarded gameplay FPS target edits with the DoPresent secondary sleep-call bypass.

- Target configuration experiment: 144 FPS request.
- Secondary sleep call: replaced with architecture-specific NOP.
- Both ARM64 and ARMv7 native libraries are handled.
- Every PAK entry is hashed and checked unchanged.
- Original APK SHA-256 is enforced before patching.
- This is experimental and does not guarantee 144 FPS or smoother frame pacing.

The APK is built by GitHub Actions from the exact original release APK. The original release and all PAK payloads are left untouched.
