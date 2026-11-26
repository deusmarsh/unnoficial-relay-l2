# Architecture map

The official Windows launcher and game run in a project-owned Wine prefix. The
native Mac app handles setup and starts the official launcher. Direct Wine display
is the default; the screenshot relay remains an explicit fallback. Neither renders the game.

```text
Develop.command / dev -> dev.py
  setup -> bootstrap_setup.py -> Swift setup wizard -> install.py
             pinned downloads -> patched Wine + .NET -> isolated prefix
             official installer (human interaction) -> config.local.json
  run   -> incremental native build -> start_native_frame_relay.py
             run_stock_launcher.py -> official launcher in a direct Wine window
             launcher_startup.py -> bounded splash recovery over localhost:8088
             --relay: localhost:8088 <-> NativeFrameRelay.swift (frames and input)
             official Play -> game -> Direct3D 9 -> mtld3d -> Metal (new setups, x87 audio)
  check -> offline boundary tests
```

## Ownership

- `dev.py`: developer commands and native build fingerprint. Delegates runtime
  setup and app building; it is not a second installer.
- `bootstrap_setup.py`: source prerequisites and graphical setup launch.
- `SetupWizard.swift`: setup progress, confirmations, cancellation and handoff.
- `install.py`, `dependencies.json`, `prepare_net3132.py`: verified dependency
  acquisition, source builds, .NET preparation, prefix checks and activation.
- `metal_runtime.py`, `runtime_environment.py`: pinned Metal runtime build,
  prefix renderer install, configured audio environment and hardware probes.
- `NativeFrameRelay.swift`: direct launch handoff, plus fallback frame windows and input.
- `start_native_frame_relay.py`, `run_stock_launcher.py`: launcher connection and
  prefix-scoped process handling. Port 8088 is local and controls authenticated pages.
- `launcher_startup.py`, `launcher_connection.py`: finite startup checks and one
  bridge-aware splash reload. Existing launcher pages are not reloaded on reopening.
- `cef-direct-window.txt`: tested direct display switches; independent of relay switches.
- `NativeLauncherWindow.c`, `launcher_window.py`: official WPF window integration.
- `patches/`: Wine synchronization and per-application Mac background behavior.
- `prepare_game_fonts.py`: prepares missing physical Arial/Tahoma files from local
  macOS fonts; font binaries are neither shipped nor downloaded.
- `configure_game_window.py`: game window preferences. Game rendering is independent
  of launcher relay frame rate and Chromium switches.
- `AppPaths.swift`, `app_paths.py`: resources versus writable local data.
- `build_bundle.py`, `install_bundle.py`: optional standalone distribution path;
  source contributors do not need to build a DMG.

## Generated and private data

`4gameRelay.app`, `.build/`, `.local/`, `.local-rebuild-*/`, `logs/`,
`config.local.json` and `dist/` are local. The source setup normally keeps its
runtime/prefix under `.local-metal-audio-v2/` and its active config at the checkout root. The
packaged app uses Application Support instead. `dev` clears inherited LINEAGE_*
overrides so it uses this checkout's source paths.

Changing UI sources rebuilds native components. Changing Wine patches requires a
fresh runtime directory, because the existing Wine source tree is already patched.
The source installer validates patch identity instead of silently applying a new
patch on top of an old one. See CONTRIBUTING.md for the supported rebuild path.

For detailed runtime/build behavior read TECHNICAL.md; for patch ancestry read
patches/README.md. Game performance conclusions belong in docs/experiments.md.
