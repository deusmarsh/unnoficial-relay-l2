# Technical notes

For the supported developer commands start with [Contributing](CONTRIBUTING.md).
Use `./dev setup`, `./dev run`, `./dev doctor`, `./dev check` and `./dev report`.
The lower-level commands below are for targeted investigation.

## Components

- `SetupWizard.swift`: native setup window; runs the Python installer and turns its prompts into buttons.
- `install.py`: downloads, hash checks, local builds, isolated prefix, smoke tests and activation.
- `NativeFrameRelay.swift`: direct launcher handoff and the optional screenshot relay.
- `run_stock_launcher.py`: official runner under the configured Wine host, display selection and safe reuse.
- `launcher_startup.py`, `launcher_connection.py`: local-only, bounded splash recovery.
- `cef-direct-window.txt`: tested direct-window Chromium switches, including `in-process-gpu`.
- `dependencies.json`: pinned URLs and hashes.
- `patches/`: Wine 10 guarded-mutex and background-launcher patches, reference sources and LGPL terms.

The graphical installer and command-line installer use the same backend. Closing setup asks for confirmation, then stops its own process group and build tasks. Completed work is kept; other launcher/game instances are not targeted.

## Manual installation and checks

```sh
python3 install.py --plan
python3 install.py --prepare-only
python3 install.py --work-dir /absolute/path/to/a/new/dedicated-folder
python3 test_installer.py
```

`--prepare-only` does not open the official installer or activate the resulting config. Its private config is saved inside the work directory as `config.prepared.json`.

For an existing compatible installation, copy `config.example.json` to `config.local.json` and fill in the paths, then run:

```sh
python3 build_native_frame_relay.py
python3 start_native_frame_relay.py --check-layout
python3 start_native_frame_relay.py
```

Requires Xcode Command Line Tools and Python 3. The optional WPF window helper needs `mingw_clang` pointing to the x86_64 LLVM-MinGW compiler. Keep its target-specific executable name; do not resolve that compiler symlink manually.

## Runtime and rendering

The tested environment uses Sikarugir Wine 10 with a locally built Wine kernel synchronization backport and support libraries from the pinned Wine development package. The official WPF installer is extracted and prepared with Microsoft .NET Core 3.1.32 while preserving its WindowsDesktop assemblies. This is a legacy, experimental runtime combination.

The default display is the official launcher's direct Wine window. Its Chromium
switches disable GPU rendering/compositing and accelerated video decode, fix scale
at 1, and add `in-process-gpu`. This combination restored the actual launcher
surface in the local test. `Launcher.exe` sets the per-application
`LineageBackgroundApp` value to `N`, allowing normal foreground window controls.
Other launcher helpers retain their background settings. Wine binaries and patches
are unchanged by this launcher improvement.

The official runner enables its diagnostic endpoint on localhost:8088. Direct mode
uses finite startup checks only, without capturing screenshots or forwarding input.
If `/splash` stays loaded after the real `LAUNCHER` bridge is available, startup
reloads it at most once after a grace period. Checks end after approximately 90
seconds plus bounded connection timeouts; the official window stays open if loading
has not finished. Reopening an existing direct launcher neither reloads its page nor
restarts its updater or game. Concurrent startup requests are serialized.

The game still renders separately through Direct3D 9 → WineD3D → OpenGL. No Vulkan,
DXVK, graphics DLL override or game preference change is part of this improvement.
It does not fix the game's rendering errors or stuttering.

After closing the official launcher, `./dev run --relay` selects the legacy native
Mac screenshot display. That mode retains frame/input handling, the hide timer and
Runtime Log. The packaged equivalent is `open -a "Lineage II Launcher" --args --relay`.
The relay hides the original WPF surface; direct mode does not start any relay
controller or its polling/hide timer. Closing the direct official window may stop
the game. Closing a relay window does not stop Wine.

On the first Open Launcher handoff, startup stops only launcher executables in the
configured prefix, then restarts with the selected display flags. It refuses to do
so while `L2.exe` or `4updater.exe` is running. It never kills wineserver, explorer,
process trees or the game. A normal reopen reuses a matching display mode and asks
the user to close an incompatible one. A busy port in another environment is not
used for startup recovery. Publisher desktop shortcuts bypass these settings;
open the Mac launcher instead.

To restore windows hidden or minimized by the helper:

```sh
python3 launcher_window.py --restore
```

## Window preferences and icons

In the optional relay mode, when the game preference file appears, the relay applies bordered 1280×720 defaults on an initial launcher click before forwarding input. It does this once, preserving the original file as `Option.ini.before-windowed.bak`. Existing preferences already backed up by this helper are left alone. The current game path is C:\Games\LineageII EU inside the configured prefix.

Manual application, with the game closed:

```sh
python3 configure_game_window.py
```

Custom icon generation and runtime icon application are disabled in source setup/run.
The generator is retained behind `--with-icons`; see [Deferred icons](docs/deferred-icons.md).
Optional distribution builds can generate original geometric artwork at macOS and Retina icon sizes. The runtime bundle keeps a fallback icon; the WPF helper also assigns a matching launcher-window icon. Wine may supply separate game icons, and Dock caching may require a runtime restart.

## Local data and security

The debugging endpoint can control authenticated launcher pages. Keep it local, do not expose port 8088 and do not run another launcher on the same port. Closing the relay leaves the official launcher/game running. Close them before rerunning setup on that prefix.

`.local/`, `.build/`, `config.local.json`, profiles, downloaded runtimes, game files and logs are private and excluded from the source ZIP. The installer creates a fresh prefix and does not import an existing user's account profile.

## Source packaging

```sh
python3 package_source.py
```

The ZIP uses an explicit file list. Original code/icons are MIT; Wine patches are LGPL-2.1-or-later. The release does not contain runtime or game binaries. See THIRD_PARTY_NOTICES.md for third-party terms.

## Standalone app distribution

The maintainer runs `python3 build_bundle.py` after preparing the source-built runtime. The builder embeds a relocatable ARM Python distribution, .NET runtime archive, stripped Wine kernel and macOS-driver modules, precompiled Windows helpers, icons, source and notices. It does not package a Wine prefix, account, existing config, launcher binary or game installation.

Wine's full engine and support package are fetched from pinned upstream downloads on first launch rather than rehosted without their complete corresponding-source material. The shipped Wine module has its Wine 10 source archive, LGPL text, patches and build recipe included. Python's dependency notices and build metadata are retained from the corresponding full upstream build.

`AppPaths.swift` and `app_paths.py` separate immutable bundle resources from writable Application Support data. No system Python or maintainer compiler is used by the packaged flow. The private `LINEAGE_DATA_DIR` environment override supports clean-room tests without changing the user's normal installation.

The cold test relocates the app and starts with a new data directory and restricted PATH. A child sandbox denies access to the development workspace, Homebrew and developer-tool directories. The test stops at the publisher's agreement for manual review. Embedded binary linkage and signatures are audited before that test.

The generated DMG includes an Applications link and Source.zip. Signing is currently ad-hoc; Developer ID credentials and notarization are separate release requirements, not simulated by local signature verification.

The standalone app includes apple-codesign (rcodesign) 0.29.0 for local ad-hoc signing of the downloaded runtime, avoiding a dependency on Xcode's codesign_allocate. Its bundled COPYING notice and the corresponding apple-platform-rs source archive are included in Resources/Licenses and Resources/Source. This tool does not provide a Developer ID identity or notarize the app.

Launcher images set the canvas aspect ratio. The fixed 44-point toolbar is excluded from proportional resizing, and the initial size follows the captured image rather than an earlier page viewport. Input coordinates use refreshed CSS viewport metrics.

Launcher runs disable the optional Wine crash debugger executable, retaining error output in the local log. Startup retires a leftover winedbg.exe only inside this app's prefix.

The Wine host uses `LSUIElement` and the window helper is built with the Windows GUI subsystem. Both are needed: a console helper or a regular foreground Wine host can briefly create a Dock entry during the five-second window check. Wine can still promote actual application windows to foreground, so this does not promise one Dock entry for the launcher and game.

The Mac driver supports an opt-in per-application `LineageBackgroundApp` setting. The helper configures launcher services for the background; direct startup then sets `Launcher.exe` to `N` so it owns a normal foreground window. Relay mode keeps it at `Y` and the Mac app owns the launcher and Runtime Log windows. The game, Frost and official installer do not opt in. The earlier activation-forwarding workaround has been removed. The Wine module change requires a separate game regression check; the Dock test alone establishes launcher behavior.
