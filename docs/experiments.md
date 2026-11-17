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
