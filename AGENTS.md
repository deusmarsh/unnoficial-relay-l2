# Working on unnoficial-relay-l2

Unofficial macOS relay and source installer for the official Lineage II EU launcher.
Start here; read only the task-relevant documentation and source below. You do not
need the maintainer's chat history. Instructions and commands are shared with humans.

## Commands

- `./dev setup`: open the source setup wizard; download pinned dependencies, build
  patched Wine and prepare a separate prefix. Requires Apple Silicon, macOS 13+,
  Apple Command Line Tools, Rosetta, space and network. Human installer/login steps remain.
- `./dev run`: rebuild changed native components and launch from this checkout.
- `./dev doctor`: diagnose the local runtime without launching the game.
- `./dev check`: portable offline tests; no Wine, account or graphical session required.
- `./dev report`: source hashes and system versions only; no raw logs or config.
- `./dev setup --work-dir .local-rebuild-1`: prepare a NEW dedicated runtime after
  changing Wine patches. Never delete an old prefix to make a rebuild pass.

## Find the right code

| Task | Start with | Additional reading |
| --- | --- | --- |
| Launcher interface/input | NativeFrameRelay.swift, run_stock_launcher.py, launcher_startup.py | docs/architecture.md |
| Source setup/dependencies | install.py, bootstrap_setup.py, dependencies.json | TECHNICAL.md |
| Wine synchronization or Mac driver | patches/, GuardedMutexProbe.c, install.py | patches/README.md, docs/experiments.md |
| Game rendering/performance | configure_game_window.py, run_stock_launcher.py | docs/architecture.md, docs/experiments.md |
| Developer workflow | dev.py, test_dev.py, package_source.py | CONTRIBUTING.md |
| Standalone distribution only | build_bundle.py, install_bundle.py | INSTALL.md, THIRD_PARTY_NOTICES.md |

## Working on a change

- Start with the reported behavior and the expected result. Inspect the relevant
  code and reproduce the issue when possible. Mark unverified causes as hypotheses.
- Keep the diff focused on the issue. Explain any new dependency and update the
  instructions when commands or setup behavior change.
- For a bug fix, add a regression check when it can capture the reported failure.
  For rendering or performance work, record comparable before-and-after evidence.
- Report what you ran and what remains unverified. Ask a person to handle publisher
  agreements, account sign-in, and gameplay checks.

## Boundaries and validation

- Preserve separation: direct Wine display is the launcher default; relay frames
  are a fallback for launcher UI. The game renders separately
  through mtld3d/Metal in new source setups with Wine audio output disabled.
  Older configured installations retain WineD3D/OpenGL. A faster relay is not evidence of faster game rendering.
- Keep runtime changes inside the configured project prefix. Do not kill all Wine
  processes, edit another installation or silently switch the active environment.
- Source setup and packaged setup share concepts but have different build paths.
  Do not require a DMG or packaged runtime for source development.
- Dependencies remain pinned with verified hashes; do not bypass failed checks.
- Never commit config.local.json, prefixes, game/publisher files, account profiles,
  raw logs, downloaded runtimes, .app bundles, caches or private filesystem paths.
- Original code is MIT; Wine-derived patches retain LGPL terms and provenance.
- Run `./dev check` for code changes. Swift/UI changes also require a native build
  (`./dev run`, or `python3 build_native_frame_relay.py --relay-only` for build only).
  Runtime/graphics changes additionally need the corresponding manual game scenario.
- Use .github/pull_request_template.md. State what was actually checked and what
  could not be checked. Passing offline tests does not establish game compatibility.
- Record useful experiments with environment, exact change, baseline, result and
  limitations in docs/experiments.md. Do not present hypotheses as fixes.
- When adding distributable files, update package_source.FILES and run ./dev check.

Custom icon generation is deferred and disabled in source setup/run and CI.
The code is retained; see [Deferred icons](docs/deferred-icons.md).
