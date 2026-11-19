# Installation

## Source alpha

Follow the [quick start](README.md#quick-start) to set up and launch the alpha.
Setup downloads pinned dependencies, builds the Wine patches, and creates an
isolated environment in `.local/`. It writes `config.local.json` automatically.
The wizard continues in its own window after the command returns. Finish the
publisher's installer and return to the wizard to activate the environment.

Repeating setup reuses completed preparation. For a preparation run that stops
before the official installer and activation, use `./dev setup --prepare-only`.
See [Contributing](CONTRIBUTING.md) for rebuilding after changes to Wine patches.

## Standalone app preview

These instructions apply to a separately built experimental disk image. The
`alpha-demo` GitHub release contains a video and historical sources, not a DMG.
The source alpha uses the setup steps above; older app bundles do not automatically
receive later source changes.

1. Open **Lineage II Launcher.dmg**.
2. Drag **Lineage II Launcher.app** to **Applications**.
3. Open the app and click Get Started.
4. Let setup prepare the runtime. Wine packages are downloaded and verified; nothing is compiled on your Mac.
5. The official Inn.games installer opens separately. Review its agreement yourself and install at the default location.
6. Wait for installation to finish. Return to setup and click I've Finished, then Open Launcher. The app reconnects the installed launcher automatically.
7. Sign in and install Lineage II through the official launcher.

You do not need to type commands or install Python, Xcode or Homebrew. If Rosetta is missing, the app offers to open Apple's installation/license prompt in Terminal. Return to setup once Apple finishes.

This preview is ad-hoc signed, not Developer ID signed or notarized. Local execution is distinct from Gatekeeper acceptance of an app downloaded from the internet; normal public distribution still needs signing/notarization.

## Standalone storage and downloads

The app includes its own Python, Microsoft .NET 3.1.32, the prebuilt Wine patch, helper tools, icons and required notices/source for those bundled parts.

The pinned Wine engine and support packages are downloaded from their upstream publishers on first use (about 380 MB). The official launcher installer and game are also obtained from the publisher. No account profile is copied from an existing installation.

Private data is stored in `~/Library/Application Support/Lineage II for macOS`. Preparation uses several GB. The game needs roughly 41 GB separately. Completed downloads are reused after interruption; changed upstream files stop at a hash check.

## Game UI fonts

Setup and launcher startup copy the local macOS supplemental `Arial.ttf` and
`Tahoma.ttf` into the configured Wine prefix as `C:\windows\Fonts\Arial.ttf`
and `C:\windows\Fonts\tahoma.ttf`. The game opens these files directly;
working Wine/GDI font substitution alone does not supply them. Existing files
are kept, including names with different capitalization. Updating the source
and running `./dev run` applies this to an existing configured installation;
restart an already-running game to load the fonts.

No font binaries are shipped or downloaded by this project. If either local
supplemental font is absent, setup/startup reports the missing name and continues;
missing game text may persist. Check the supplemental fonts on that Mac and
restart through this launcher once they are available. See the
[confirmed investigation](docs/experiments.md#missing-native-ui-text--18-november-2026).

## After setup

For source development, use `./dev run`. For a standalone build containing the
current sources, open **Lineage II Launcher.app** from Applications. Direct mode
opens the official Wine window; the Mac handoff app exits after startup. Reopening
the same mode reuses a running launcher and preserves game/download work.

After closing the launcher and finishing active downloads, `./dev run --relay`
selects the screenshot fallback. A packaged app accepts
`open -a "Lineage II Launcher" --args --relay`. Relay mode supplies Reload and
Show Runtime Log; closing that Mac window leaves the official launcher/game running.
Direct-mode runtime logs are stored in the configured data directory. Closing the
official launcher itself may also stop the game. Do not use the Windows Inn.games
desktop shortcut to select a Mac display mode.

Quit the launcher and game before rerunning setup on the same installation.

## Validation boundary

The existing installation reached Gludio, and a later two-file font repair restored
native UI text. Sustained play remains unverified. A separate source-based clean runtime build passed Windows, .NET-host and mutex checks and opened the publisher's agreement window. The standalone bundle is tested separately from a relocated copy with a new data directory, no original cache and access to the development workspace denied. The manual handoff is the first agreement window: no publisher terms or account login are accepted by automation.

See the [alpha status](README.md#alpha-status) for the current gameplay baseline.
