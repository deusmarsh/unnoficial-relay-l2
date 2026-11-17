# Lineage II macOS Relay

[![Source checks](https://github.com/deusmarsh/unnoficial-relay-l2/actions/workflows/check.yml/badge.svg?branch=main)](https://github.com/deusmarsh/unnoficial-relay-l2/actions/workflows/check.yml)

An unofficial source alpha for running the Lineage II EU launcher and Windows
game on Apple Silicon Macs through Wine. Developed with AI assistance and local
testing. Independent of Innova and NCSoft.

[Download the alpha demo (.mov)](https://github.com/deusmarsh/unnoficial-relay-l2/releases/download/alpha-demo/demo.mov)

## Quick start

On an Apple Silicon Mac with macOS 13 or later, clone or download this repository.
Allow several GB for setup and roughly 41 GB for the game. Setup prompts for
Apple's Command Line Tools and Rosetta if needed.

1. Open **Develop.command** and choose **Set up / resume**, or run `./dev setup`.
2. Follow the setup wizard and complete the official publisher's installer.
3. Choose **Run changed sources** or run `./dev run`. Sign in and download the
   game in the official launcher.

See [Installation](INSTALL.md) for setup details and [Contributing](CONTRIBUTING.md)
for editing, rebuilding, and submitting changes.

## Alpha status

| Scenario | Status |
| --- | --- |
| Launcher startup, login, and game download | Worked on the maintainer's Mac |
| Game startup, server selection, and character creation | Worked on the maintainer's Mac |
| Entering the game world and sustained play | Still to be verified |
| Fresh setup through game launch on another Mac | Still to be verified |
| Rendering and performance | Stuttering and incorrect textures or model colors remain. Earlier runs also showed missing text and a blank dialog. |

The GitHub checks cover source tests and the macOS interface build.
See [experiment notes](docs/experiments.md) for the gameplay baseline.

![Lineage II game client at its login screen](docs/alpha-login.jpg)

*Game client during a local alpha run. Screenshot includes artwork from the official game.*

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
for dependencies and build details. Start with [AGENTS.md](AGENTS.md) when working
with an AI assistant.

## License and local data

Original code and icons: MIT. Wine-derived patches: LGPL-2.1-or-later. Dependencies
retain their own terms; see [third-party notices](THIRD_PARTY_NOTICES.md).
Game files, publisher binaries, accounts and runtime installations are not included.
Local configurations, downloaded dependencies and generated apps stay outside Git.

Custom icon generation is deferred and disabled in source setup/run and CI.
The code is retained; see [Deferred icons](docs/deferred-icons.md).
