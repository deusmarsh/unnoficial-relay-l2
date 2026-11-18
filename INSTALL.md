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

These instructions apply if you already have the experimental disk image.
The source alpha uses the setup steps above.

1. Open **Lineage II Launcher.dmg**.
2. Drag **Lineage II Launcher.app** to **Applications**.
3. Open the app and click Get Started.
4. Let setup prepare the runtime. Wine packages are downloaded and verified; nothing is compiled on your Mac.
5. The official Inn.games installer opens separately. Review its agreement yourself and install at the default location.
6. Wait for installation to finish. Return to setup and click I've Finished, then Open Launcher. The app reconnects the installed launcher automatically.
7. Sign in and install Lineage II through the official launcher.

You do not need to type commands or install Python, Xcode or Homebrew. If Rosetta is missing, the app offers to open Apple's installation/license prompt in Terminal. Return to setup once Apple finishes.

This preview is ad-hoc signed, not Developer ID signed or notarized. Local execution is distinct from Gatekeeper acceptance of an app downloaded from the internet; normal public distribution still needs signing/notarization.

## Storage and downloads

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

Open the same app from Applications. It starts the official launcher and displays its page. Use Reload if the page gets stuck. If the launcher does not connect, Open Log shows its startup log. Windowed game preferences are applied once before initial launcher input after the game preference file appears.

Use **Lineage II Launcher.app** from Applications, rather than the Windows Inn.games desktop shortcut. That shortcut does not open the Mac interface.

The Mac app keeps launcher services out of Dock and hides the original blank launcher surface after connecting. **Runtime Log** replaces it with a normal Mac window, a short explanation and live output. Closing this console only hides the log. Stopping the Runtime process may also stop the game. Reopen the console from **Show Runtime Log** in the app menu.

Closing the Mac app leaves the official launcher/game running. Quit them before rerunning setup on the same installation.

## Validation boundary

The original environment reached server selection and character-creation screens. A separate source-based clean runtime build passed Windows, .NET-host and mutex checks and opened the publisher's agreement window. The standalone bundle is tested separately from a relocated copy with a new data directory, no original cache and access to the development workspace denied. The manual handoff is the first agreement window: no publisher terms or account login are accepted by automation.

See the [alpha status](README.md#alpha-status) for the current gameplay baseline.
