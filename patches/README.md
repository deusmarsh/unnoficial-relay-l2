# Wine patches

- Base: Wine 10.0, `wine-mirror/wine` tag `wine-10.0`.
- Reference: Wine 11.21, `dlls/ntoskrnl.exe/sync.c` and `ntoskrnl.exe.spec`.
- Local adaptation: 16 November 2026. Adds four guarded-mutex acquire/release exports using Wine's existing fast-mutex implementation.
- Guarded-region entry/exit remains unimplemented, as noted in the reference implementation. This is not a claim of complete Windows-kernel or anti-cheat compatibility.
- The credential-free test checks a blocked waiter and 4,000 operations across four threads with no overlap.

These patches adapt Wine code and are **LGPL-2.1-or-later**, not MIT. Original upstream copyright notices remain in the downloaded source; see `licenses/WINE-LICENSE` and `licenses/WINE-COPYING.LIB`.

Sources:
- https://github.com/wine-mirror/wine/tree/wine-10.0
- https://github.com/wine-mirror/wine/blob/wine-11.21/dlls/ntoskrnl.exe/sync.c
- https://github.com/wine-mirror/wine/blob/wine-11.21/dlls/ntoskrnl.exe/ntoskrnl.exe.spec

The installer downloads a pinned Wine source archive, applies the patches and builds the module locally. No modified Wine binary is shipped in the source ZIP. Keep the source, patches and build recipe if you later redistribute a runtime; that redistribution needs its own license-compliance review.

## Background launcher applications

`winemac-background-app.patch` adapts Wine 10's macOS driver. The per-executable `Mac Driver\LineageBackgroundApp` option prevents opted-in services from promoting themselves into Dock applications. It is enabled for Inn.games.exe, Launcher.exe, explorer.exe, CefSharp.BrowserSubprocess.exe and our window helper. L2.exe, Frost and installer dialogs do not opt in. The driver remains LGPL-2.1-or-later; its original copyright notices are retained.

The maintainer builds the Mac driver with `install.build_background_driver`; `build_bundle.py` embeds its stripped binary alongside the synchronization module, with this patch, the pinned Wine 10 source archive and the build recipe. A foreground game launch must be checked separately from the launcher-only Dock test.

## mtld3d-zero-multiply.patch

Downstream alteration of athei/mtld3d v0.15.5 (zlib), not a Wine patch.
Preserves zero contributions in DXSO MUL/MAD with non-finite operands and adds
vertex/pixel emitter regression checks. Applied only by `material_fix.py` to
hash-verified source, then built into a separate runtime copy. See the
[official-client comparison and limits](../docs/experiments/2026-11-21-material-fix/README.md).
