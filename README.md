# Lineage II macOS Relay

An unofficial, experimental macOS relay and Wine setup for the official EU launcher
and Windows game. Built with AI-assisted development and local testing. Not affiliated
with Innova or NCSoft. This repository is open for component changes and experiments;
a packaged app or DMG is not required for development.

## Current status

On the maintainer's tested setup, the official launcher starts, login and game download
work, and the game starts. Server selection and character creation work according to
the maintainer's latest report. Entry into the world and sustained gameplay have not
been established. Stuttering and incorrect textures/model colors remain under investigation.
Earlier tests also observed missing text and a blank dialog; check your own scenario.
A complete fresh installation on another Mac still needs verification.

## Developer quick start

Use an Apple Silicon Mac with macOS 13+, internet, several GB for the runtime and
roughly 41 GB for the game. Apple's Command Line Tools and Rosetta are required;
source setup offers installation prompts if missing.

Fork this repository, clone your fork, then run from its directory:

```sh
./dev setup
# Finish the graphical setup and official installer, then:
./dev run
```

Or double-click **Develop.command** for the same commands in a menu. Setup obtains
pinned dependencies, builds the Wine patches and creates an isolated local prefix.
You complete publisher agreements, login and the game installation yourself.
Do not run `run` until the graphical setup has finished.

After editing sources, `./dev run` rebuilds changed native components automatically.
For checks without installing Wine or the game, use `./dev check` (or `python3 dev.py check`
on another operating system with Python 3.9+).

See [Contributing](CONTRIBUTING.md) for the complete fork → edit → check → pull request
process, runtime rebuilds and manual validation. AI assistants should start with
[AGENTS.md](AGENTS.md). See the [architecture map](docs/architecture.md) to find a component.

## How it works

The official launcher and game run through Wine. A native Mac window displays launcher
pages and forwards input through its local Chromium endpoint. Account login, downloads
and Play remain in the official launcher. The game renders in its own window through
Direct3D 9 → WineD3D → OpenGL, separately from launcher frame streaming.

Closing the relay does not close the official launcher or game. Only one launcher may
use the local debug port 8088; do not expose it to the network.

## Areas for contribution

- Reproduce and improve game stuttering, textures, colors and missing text.
- Verify fresh setup and game-world entry on other Macs.
- Improve launcher display, input and setup reliability.
- Investigate alternative rendering paths with before/after evidence.

Record useful results in [Experiments](docs/experiments.md). See [Technical notes](TECHNICAL.md)
for dependencies and build details, and [Installation](INSTALL.md) for the optional
standalone app workflow. Standalone distribution is a separate experimental path;
Developer ID signing and notarization are incomplete.

## License and local data

Original code and icons: MIT. Wine-derived patches: LGPL-2.1-or-later. Dependencies
retain their own terms; see [third-party notices](THIRD_PARTY_NOTICES.md).
Game files, publisher binaries, accounts and runtime installations are not included.
Local configurations, downloaded dependencies and generated apps stay outside Git.

Custom icon generation is deferred and disabled in source setup/run and CI.
The code is retained; see [Deferred icons](docs/deferred-icons.md).
