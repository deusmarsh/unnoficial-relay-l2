# Status and experiments

## Confirmed baseline — 17 November 2026

The maintainer reports: the official launcher starts, the game downloads and starts,
server selection works, and a character can be created. Entry into the game world
and sustained gameplay have not been established. Stuttering and incorrect textures
or model colors remain investigation areas; earlier tests also observed missing text
and a blank dialog. Recheck whether those older issues persist in your scenario.

The tested rendering path is Direct3D 9 → WineD3D → OpenGL. DXVK/Metal is not a
verified replacement. Launcher Chromium frame rate does not measure game frame rate.

Existing private diagnostic samples are not bundled or treated as published evidence.
This page records the baseline, not a claim that clean installation works on all Macs.

## Add an experiment

For each useful experiment record:

- Date, source commit, Mac/chip, macOS and runtime/dependency versions.
- Hypothesis and exact source/config change (without private paths or account data).
- Reproduction: scene, settings, duration and measurement method.
- Baseline and changed result; repeatability and possible confounding factors.
- Launcher versus game effects, regressions and checks not performed.
- Conclusion: verified improvement, no observed effect, regression or inconclusive.

Keep unsuccessful experiments when they help avoid repeating work. Do not infer
texture correctness or gameplay compatibility from startup alone.

## Direct launcher display — 18 November 2026

Environment: Apple M1 Pro, 16 GB, macOS 27.0, configured Sikarugir Wine 10
with the existing guarded-mutex and per-application background patches. These
interactive tests preceded this PR; its automated and packaged checks are recorded
in the pull request. No private logs, account data or publisher files are included.

Baseline: the native launcher displayed repeated Chromium screenshots and forwarded
input through CDP. The maintainer reported substantial launcher lag.

Change: show the official Wine window, set only `Launcher.exe`'s
`LineageBackgroundApp` to `N`, and use `disable-gpu`, `disable-gpu-compositing`,
`disable-accelerated-video-decode`, `force-device-scale-factor 1`, `in-process-gpu`.
A stuck startup splash recovered after one reload once the official bridge was
registered. Game updates completed and Play launched the client. A separate local
updater certificate repair was also needed during diagnosis; it is not included in
this performance change and is not attributed to direct display.

Result: the maintainer reported a large improvement in launcher responsiveness;
maximize/restore controls worked normally. This is qualitative same-Mac feedback,
not an instrumented before/after FPS measurement or a clean-install guarantee.
The PR makes this display the default and retains `--relay` as an explicit fallback.

Game boundary: the client reached Gludio but retained severe stalls, damaged model
rendering, missing in-game text and an unreadable dialog. Working Vulkan support
alongside OpenGL did not remove those issues. An isolated DXVK/MoltenVK run showed
about 0.4 FPS on the intro, while a simple D3D9 triangle/font test reached about
120 FPS. That synthetic test does not establish game compatibility. No Vulkan
runtime, DXVK deployment or game rendering change is included here. Further game
performance investigation was deferred.
