# XGS render-path investigation — Angry Birds Transformers 2.42.0

Date: 2026-11-18  
Branch: `feature/full-revival-mod`  
Original APK SHA-256: `ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013`

## Runtime evidence from the existing Perfetto capture

Trace: `xgs-perfetto-20261118-011114.pftrace`  
Trace SHA-256: `6d650622500d4bfbe672dbc7eda03585b8336068bbe0bf62c2aea656a94ba0ae`

- `GLThread 89` (TID 9800) accumulated 8.661 s of scheduled CPU time over an observed active interval of about 10.93 s.
- `onDrawFrame`: 1,008 calls; median 8.42 ms, p95 15.78 ms, p99 25.04 ms, maximum 83.99 ms.
- 34 calls exceeded 16.67 ms; 21 exceeded 20 ms; 5 exceeded 33.33 ms.
- `eglSwapBuffers`: median 1.09 ms, p95 1.40 ms, maximum 3.99 ms.
- The trace has no native sampled call stacks, no useful GPU timing, no FrameTimeline tables, and no CPU frequency samples. It does not prove which native function or render pass is responsible.

## Static call path confirmed in ARM64 libABBS.so

The original APK was hash-verified and disassembled read-only. Relevant path:

```text
CApp::DoRender
  -> CGame::RenderFrame
       -> CRenderManager::RenderFrame
            -> PrepareFrame
            -> RenderShadowMap
            -> RenderReflectionMap
            -> RenderDepthPass
            -> RenderOpaque
            -> Render1Bit environment / environment objects
            -> RenderAllEffects (particles)
            -> RenderAlpha (smackables / environment objects)
            -> post-process to main render target
  -> CApp::DoPresent
       -> GetDesiredFramerate
       -> LimitFPSWithSleep
       -> platform presentation
```

Important observations:

- `CGame::RenderFrame` has a loop over render/view iterations and calls `CRenderManager::RenderFrame` within that loop. The number of iterations is derived from runtime state; this static finding alone does not establish how many passes execute in the user's scene.
- `CRenderManager::RenderFrame` directly calls shadow-map, reflection-map and depth passes before opaque rendering. The shadow and reflection functions contain early-exit conditions, so their presence in the call sequence does not prove their full workloads run on every frame.
- The same render manager then calls opaque rendering, environment rendering, particle effects, alpha rendering and post-processing.
- `eglSwapBuffers` being short in the trace is consistent with the CPU work occurring earlier in the GL frame callback, but it does not exclude GPU saturation or driver stalls.

## Decision

**No render pass has been disabled and no game binary or game asset has been changed.** Static code does not tell us the runtime cost of each pass. Disabling shadows, reflections, depth, particles or post-processing blindly could break visual effects, lighting, gameplay cues or device compatibility.

The FPS limiter/unlock path remains untouched.

## Next safe optimization step

Obtain per-pass runtime attribution on the same repeatable gameplay scene. Preferred evidence is a trace with native sampled stacks and GPU/frame timeline data where the device permits it. If native sampling is unavailable on the production Android build, compare controlled A/B runs using only documented in-game quality settings, one setting at a time, recording frame-time percentiles and temperature.

Only after a pass or setting is shown to cause the long frames should a reversible, ABI- and APK-hash-guarded change be prepared.
