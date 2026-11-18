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

## Updater HTTPS trust — 19 November 2026

The pinned official installer and the launcher downloaded during a fresh install
both contained a CA file with GlobalSign certificates but no ISRG Root X1.
The updater explicitly uses its own `rootcert.ca`, with default CA loading off.
A new Wine prefix and registry reproduced certificate verification errors during
installation; the publisher's HTTP fallback allowed installation to finish.
This does not establish the behavior on native Windows.

On an Apple M1 Pro MacBook Pro, macOS 27.0 (26A428), using the existing patched
Wine 10 executable with that fresh prefix, the real `4updater.exe` was then run
against the installed launcher distribution over an explicitly HTTPS URL:

| CA configuration | Exit code | Certificate-error log lines | HTTP request lines |
| --- | ---: | ---: | ---: |
| Original publisher file | 70 | 20 | 0 |
| Original file plus fingerprint-verified ISRG Root X1 | 0 | 0 | 0 |
| PR helper extracting the installed launcher's updater resource and adding X1 | 0 | 0 | 0 |

Counts are matching lines in each network log, not distinct failures. Successful
runs reported the distribution up to date. No game or account session was needed.
Original binaries and SSL verification configuration were unchanged. A separate
probe through the same OpenSSL DLLs also verified the hostname and received HTTP
200. Private raw logs, prefixes and publisher binaries are not published.

The code prepares the updater before installer startup (shared by source and
packaged setup), and before each normal launcher startup. Publisher resource
extraction is lazy: an existing `forgameUpdater/4updater.exe` skips extraction.
Preparation extracts the same local ZIP resource first when needed, then appends
only the pinned root certificate. Existing updater executables are preserved;
repeat runs do not duplicate the certificate. Replaced CA files are repaired at
the next Mac launcher startup. Changes to the publisher ZIP layout require review.

Validation: fresh verified installer preparation through the PR code; real updater
check through the PR helper in the installed fresh prefix; offline regression
suite. A complete packaged app rebuild and a second full interactive install
using the final PR code were not performed. This fixes updater trust, with no
claim about black models, stuttering, disconnects or gameplay stability.

![Official installer in the fresh isolated prefix](updater-clean-installer.png)

First screen captured before the maintainer accepted the publisher agreement.
This screenshot documents the installation context, not the HTTPS result; the
measured results are in the table above.

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
