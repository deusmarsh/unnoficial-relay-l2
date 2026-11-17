# Architecture map

The official Windows launcher and game run in a project-owned Wine prefix. The
native Mac app displays and controls launcher pages; it does not render the game.

```text
Develop.command / dev -> dev.py
  setup -> bootstrap_setup.py -> Swift setup wizard -> install.py
             pinned downloads -> patched Wine + .NET -> isolated prefix
             official installer (human interaction) -> config.local.json
  run   -> incremental native build -> start_native_frame_relay.py
             run_stock_launcher.py -> official launcher in Wine
             localhost:8088 <-> NativeFrameRelay.swift (launcher frames and input)
             official Play -> game -> Direct3D 9 -> WineD3D -> OpenGL
  check -> offline boundary tests
```

## Ownership

- `dev.py`: developer commands and native build fingerprint. Delegates runtime
  setup and app building; it is not a second installer.
- `bootstrap_setup.py`: source prerequisites and graphical setup launch.
- `SetupWizard.swift`: setup progress, confirmations, cancellation and handoff.
- `install.py`, `dependencies.json`, `prepare_net3132.py`: verified dependency
  acquisition, source builds, .NET preparation, prefix checks and activation.
- `NativeFrameRelay.swift`: Mac windows, live launcher frames, coordinates and input.
- `start_native_frame_relay.py`, `run_stock_launcher.py`: launcher connection and
  prefix-scoped process handling. Port 8088 is local and controls authenticated pages.
- `NativeLauncherWindow.c`, `launcher_window.py`: official WPF window integration.
- `patches/`: Wine synchronization and per-application Mac background behavior.
- `configure_game_window.py`: game window preferences. Game rendering is independent
  of launcher relay frame rate and Chromium switches.
- `AppPaths.swift`, `app_paths.py`: resources versus writable local data.
- `build_bundle.py`, `install_bundle.py`: optional standalone distribution path;
  source contributors do not need to build a DMG.

## Generated and private data

`4gameRelay.app`, `.build/`, `.local/`, `.local-rebuild-*/`, `logs/`,
`config.local.json` and `dist/` are local. The source setup normally keeps its
runtime/prefix under `.local/` and its active config at the checkout root. The
packaged app uses Application Support instead. `dev` clears inherited LINEAGE_*
overrides so it uses this checkout's source paths.

Changing UI sources rebuilds native components. Changing Wine patches requires a
fresh runtime directory, because the existing Wine source tree is already patched.
The source installer validates patch identity instead of silently applying a new
patch on top of an old one. See CONTRIBUTING.md for the supported rebuild path.

For detailed runtime/build behavior read TECHNICAL.md; for patch ancestry read
patches/README.md. Game performance conclusions belong in docs/experiments.md.
