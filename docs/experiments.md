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

## Missing native UI text — 18 November 2026

Result: missing native UI text restored in the maintainer's existing installation.
The maintainer signed in and entered Gludio; the reviewed recording shows readable
server selection, character statistics, chat, quest text, Teleport and modal
Reconnect/Exit captions. This resolves the text symptom tracked in issue #3.

### Environment and baseline

Apple M1 Pro MacBook Pro, 16 GB RAM; macOS 27.0 (26A428). Existing standalone
preview runtime, Wine 10-based patched environment, Direct3D 9 → WineD3D → OpenGL.
This was a local repair of that installed runtime, not a clean build from this PR.
The PR is based on source commit `9061f53`; no graphics backend or game settings
were changed for the two-file font trial. The original installed app's precise
source commit was not independently established.

Most button captions and dialog text were invisible, although buttons responded.
Numbers, the unique player nickname at character selection, and some labels
remained visible. Therefore surviving text could not all be explained as static
pictures, nor did its presence prove that the failing native UI path worked.

### Investigation

1. Earlier 32-bit GDI probes created named Arial/Tahoma fonts and nonempty Latin
   and Cyrillic glyph bitmaps. That verified name lookup, not the game's direct
   file access. A later Arial probe still returned a 108-byte glyph bitmap while
   opening the required font file failed.
2. Read-only inspection of one blank native NWindow button found a nonempty `OK`
   caption, visibility enabled and alpha 255. The text was assigned and not
   transparent. Investigation moved from a possible GFx issue to native text.
3. The native font manager had default `FONTID = -1` and zero registered names.
   Its backend retained 57 font requests using
   `C:\windows\Fonts\tahoma.ttf`.
4. Inspection of the built-in initialization path found Arial size 12 loaded from
   the Windows directory plus `\Fonts\Arial.ttf`. The text measurement and draw
   fallback paths select the manager's default font when the input font is
   missing/invalid. Falling back cannot help when that default is also invalid;
   missing glyph textures or zero glyph dimensions skip drawing.
5. Direct file opens of both Windows font paths failed with error 2 (file not
   found), despite working GDI name lookup. The initialization code identifies
   the built-in Arial fallback; it does not prove that this exact registration
   was attempted in every affected session.

### Exact change and observed result

Copied the Mac's existing `/System/Library/Fonts/Supplemental/Arial.ttf` and
`Tahoma.ttf` into this prefix's Windows Fonts directory as `Arial.ttf` and
`tahoma.ttf`, preserving other files. Direct Windows opens then succeeded.
Launched a new client, with no game binary patch, renderer replacement or font
registry edit. The manager then had 57 registered fonts and default ID 1 under
`GAMEDEFAULT`. The maintainer immediately confirmed restored captions.

The subsequent 201-second screen recording also verified text in the game world,
including the previously unreadable dialogs. This establishes a successful local
before/after trial. Both fonts were installed together; their individual
necessity was not isolated. We have not traced each surviving label's renderer.

The source fix now performs the same missing-file preparation after Wine prefix
initialization in both setup paths and before normal launcher startup, so existing
configured prefixes also receive it. Case-insensitive existing filenames are
preserved. Missing macOS source fonts produce a diagnostic rather than a download.
Fonts themselves and private diagnostic logs/recordings are not published.

### Validation and limits

Portable regression checks cover direct destination paths, repeat runs, preserving
existing fonts/casing, missing source diagnostics and refusing a Fonts directory
that redirects writes outside the prefix. Launcher handoff checks exercise the
startup integration. See the PR for the actual check results.

The manual trial validates the two-file repair; the new automated setup paths
have not been followed through a fresh installation and account sign-in. Character
and NPC models can still appear black (issue #2). A later Reconnect dialog and
loading loop remain unresolved: the recording does not establish that opening
Teleport caused the disconnect. Restored text makes that failure readable; it
does not establish stable gameplay or a connection fix.

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
