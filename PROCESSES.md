# Processes and icons

Names below describe the app's processes. Publisher executables keep their original filenames.

| Process | Purpose | User-facing name / icon |
| --- | --- | --- |
| `4gameRelay` | Mac launcher interface, setup and Runtime Log | **Lineage II Launcher** · original Relay icon |
| Bundled `python3` | Setup, launch and window helpers | Background task; no separate Dock icon |
| `wine` / `wineserver` | Windows compatibility runtime and process coordination | Host bundle: **Lineage II Runtime**, original Runtime icon. Wine can use executable artwork for foreground windows; launcher services now opt into background mode |
| `Inn.games.exe` | Official runner; starts the installed launcher | Official launcher component; usually exits after handoff |
| `Launcher.exe` | Official launcher, sign-in and installation | Background service; its blank Wine surface is hidden and its Dock entry is suppressed by the opt-in driver setting |
| `CefSharp.BrowserSubprocess.exe` | Chromium renderer, network and graphics helpers | Background components; several instances are normal |
| `NativeLauncherWindow.exe` | Hides or restores the original launcher surface | Short GUI-subsystem task in a background Wine host; no console window or transient Dock tile expected |
| `explorer.exe`, `services.exe`, `svchost.exe`, `rpcss.exe`, `plugplay.exe`, `winedevice.exe` | Wine system services | Background components; no user controls needed |
| `dotnet.exe` | Runs the official installer during setup | Temporary Runtime process |
| `system/Frost/LineageII.exe`, `frostUpdater.exe` | Frost components present in the earlier game installation; started by Play | Suggested: **Frost**; active processes and icons need verification during a full game launch |
| Lineage II client (`L2.exe` in the tested client) | The game | **Lineage II**; verify its original icon during the game test |
| `L2CefSubProcess.exe`, `AwesomiumProcess.exe` / `awesomium_process.exe` | Embedded browser components present in the earlier game installation | Background helpers; verify which this client actually starts |
| `L2CrashSender.exe` | Game crash reporter, present in the earlier installation | Suggested: **Lineage II Crash Reporter**; only verify if a crash occurs |
| `wineboot.exe`, `cmd.exe`, `reg.exe`, `taskkill.exe`, `GuardedMutexProbe.exe` | Short setup/check/cleanup commands | No persistent Dock icon expected |
| `winedbg.exe` | Wine crash debugger | Disabled for launcher runs; errors remain in Runtime Log |

The current clean installation has reached the login screen. Frost and the game have not yet been launched in this fresh environment, so their process list and icon appearance are not confirmed here. Short-lived setup probes and Windows helper commands can also appear while setup runs.

The Mac app owns the launcher page and Runtime Log. Cmd+L or **Show Runtime Log** reopens the console. Closing it hides the log and keeps Wine running.

## Current Dock behavior

| Component | Expected Dock behavior | Verification |
| --- | --- | --- |
| Native Mac interface | **Lineage II Launcher**, L icon; launcher and Runtime Log windows | Opens and connects locally |
| Official launcher and Wine desktop shell | Background services, no separate Runtime tiles | Local patched-driver test: no foreground Runtime apps |
| Window helper and browser helpers | Background tasks | No repeated Dock tile creation in the helper test |
| Official installer | Separate temporary application while reviewing terms/installing | Manual agreement handoff tested before this driver change |
| Lineage II / Frost | Game application may have its own Dock tile; visible windows keep normal foreground behavior | Needs another full game launch after the driver change |

Background mode is opt-in by executable name in Wine's AppDefaults. Publisher executable files are not renamed or edited. The macOS Wine driver is locally built from the pinned Wine 10 source plus the distributed LGPL patch.
