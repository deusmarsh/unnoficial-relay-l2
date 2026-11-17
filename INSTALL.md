# Installation

For development from this repository use [Contributing](CONTRIBUTING.md) and
`./dev setup`. The app-preview instructions below describe the separate optional
standalone distribution; a disk image is not required for contributions.

## App preview

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

## After setup

Open the same app from Applications. It starts the official launcher and displays its page. Use Reload if the page gets stuck. If the launcher does not connect, Open Log shows its startup log. Windowed game preferences are applied once before initial launcher input after the game preference file appears.

Use **Lineage II Launcher.app** from Applications, rather than the Windows Inn.games desktop shortcut. That shortcut does not open the Mac interface.

The Mac app keeps launcher services out of Dock and hides the original blank launcher surface after connecting. **Runtime Log** replaces it with a normal Mac window, a short explanation and live output. Closing this console only hides the log. Stopping the Runtime process may also stop the game. Reopen the console from **Show Runtime Log** in the app menu.

Closing the Mac app leaves the official launcher/game running. Quit them before rerunning setup on the same installation.

## Validation boundary

The original environment reached server selection and character-creation screens. A separate source-based clean runtime build passed Windows, .NET-host and mutex checks and opened the publisher's agreement window. The standalone bundle is tested separately from a relocated copy with a new data directory, no original cache and access to the development workspace denied. The manual handoff is the first agreement window: no publisher terms or account login are accepted by automation.

The maintainer now reports successful character creation on the original setup.
World entry and a full fresh game installation on another Mac remain unverified.

## Source build

The source archive is for development. Its Install.command builds the setup app and does need Apple's developer tools. See [Technical notes](TECHNICAL.md). This requirement does not apply to the prebuilt app.
