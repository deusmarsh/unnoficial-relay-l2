# Contributing

You can change any published component in your fork. A distributable app or DMG
is not required. Small focused pull requests are easiest to review; larger component
replacements are welcome with a clear explanation of the resulting behavior.

## First run on a Mac

Requirements: Apple Silicon, macOS 13+, internet, several GB for runtime preparation
and roughly 41 GB more for the game. The source path uses Apple's Command Line Tools
and Rosetta. Setup offers their installation prompts if missing; finish those yourself.

1. Fork this repository on GitHub and clone your fork. Open its folder in Terminal
   or in your coding assistant. Run all commands below from that folder.
2. Run `./dev setup`, or double-click **Develop.command** and choose **Set up / resume**.
3. Follow the setup window. It downloads checksum-pinned dependencies, builds the
   Wine patches and prepares an isolated prefix in `.local/`. Repeating setup reuses
   completed preparation; changed patches require a new directory (see below).
4. Review the official publisher's installer and complete it yourself. Return to
   setup for activation. Setup backs up the previous local config and keeps the old prefix.
5. Run `./dev run`. Sign in and install the game in the official launcher.

No existing game installation or account profile is included in this repository.
Do not manually fill runtime paths for the normal setup path. `config.example.json`
is for advanced use; the installer writes `config.local.json` automatically.

For preparation without opening the publisher installer or activating a config,
use `./dev setup --prepare-only`. This does not make `./dev run` ready by itself.
The setup command opens a graphical wizard and returns before that wizard completes;
continue there, and wait for its completion before launching another command.

## Edit, run, check

Create a topic branch, for example `git switch -c fix/launcher-input`.
Change the relevant source, then run:

```sh
./dev run
./dev check
```

`run` fingerprints the Swift/UI builder and Windows helper inputs. It rebuilds
changed native components before starting the launcher. Python scripts are loaded
from the checkout on launch. There is no DMG generation or notarization step.
Close and reopen the native launcher after a UI change so the running process uses
the new binary. Closing the relay leaves Wine/game processes alive; close those
explicitly when a task requires a full restart. Only one launcher may use port 8088.

Useful commands:

| Command | Purpose |
| --- | --- |
| `./dev` / Develop.command | Interactive menu |
| `./dev doctor` | Check tools, source runtime provenance and official launcher layout |
| `./dev check` | Offline Python syntax, manifest and boundary tests; works without the game |
| `./dev report` | Write `.build/development-report.json` with source hashes and versions |
| `python3 build_native_frame_relay.py --relay-only` | Build the Mac UI without an installed runtime |

Review reports before sharing. Raw logs can contain account or machine information;
do not attach them wholesale. Automated reports deliberately omit their contents.

## Changing Wine patches

`./dev run` refuses to use a runtime with missing or different patch provenance.
Close the launcher and game, then choose a **new** dedicated directory:

```sh
./dev setup --work-dir .local-rebuild-1
```

If that name was already used with older patches, choose another new name. Setup
builds and activates a fresh environment; the old prefix and its downloaded game
remain intact. The fresh prefix may require another game installation. There is
currently no automatic migration of accounts or game files between prefixes.
This is intentionally explicit: changing Wine patches is not a native UI rebuild.

## What to verify

- Python/setup changes: `./dev check`, plus the affected setup scenario if relevant.
- Swift/interface changes: offline checks, native build, and the affected visual/input scenario.
- Wine or game graphics changes: those checks plus launcher startup and the affected
  in-game scenario on a Mac. Report missing manual coverage rather than claiming success.
- Performance changes: same Mac, scene, settings and measurement method before/after;
  separate launcher frame rate from game frame rate. Record results in docs/experiments.md.

CI runs portable checks and a Mac UI build, including a native check that setup
preserves a selected work directory. To run that optional check locally use
`LINEAGE_TEST_SWIFT=1 ./dev check`. It does not log in, install the game,
accept publisher agreements or verify gameplay.

## Open a pull request

1. Run the relevant checks and review `git diff` and `git status --short`.
2. Commit the focused change and push the branch to **your fork**.
3. On GitHub, open a pull request from that branch into this repository's `main`.
4. Fill in the PR template: problem, resulting behavior, checks, manual results,
   and remaining limitations. Screenshots are useful for visual changes; remove
   account names and unrelated windows first.

Do not include local configs, prefixes, game files, runtime binaries or raw logs.
When adding a source file, add it to `package_source.FILES` so the reviewed source
export stays complete. Keep third-party notices and patch provenance intact.

## Working with AI

Ask your assistant to read AGENTS.md, inspect the relevant source, make the change,
and follow the validation rules above. Codex discovers AGENTS.md automatically;
with other assistants explicitly point them to it if needed. You do not need to
paste this repository's full documentation or the maintainer's conversation history.
Humans still handle account login, publisher agreements and visual game verification.

Custom icon generation is deferred and disabled in source setup/run and CI.
The code is retained; see [Deferred icons](docs/deferred-icons.md).
