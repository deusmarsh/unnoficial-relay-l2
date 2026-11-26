# Third-party components

Original relay, installer scripts, tests and geometric icons: MIT. The MIT grant excludes third-party code, patches, downloaded binaries and game assets.

## Wine

Wine is LGPL-2.1-or-later, copyright its upstream contributors. The synchronization backport and macOS background-mode patch in `patches/` is provided under those terms. See `patches/README.md`, `licenses/WINE-LICENSE` and `licenses/WINE-COPYING.LIB` for provenance and license text. The setup script builds the modified module locally; the source release contains no Wine runtime binary.

Wine runtime packages are downloaded from Sikarugir-App/Engines and Gcenx/macOS_Wine_builds. Their separate upstream sources, components, notices and license obligations remain applicable:
- https://github.com/Sikarugir-App/Engines
- https://github.com/Gcenx/macOS_Wine_builds
- https://github.com/wine-mirror/wine

## Build tools and Microsoft runtime

LLVM-MinGW and GNU Bison are downloaded from their upstream releases and used locally. Their bundled notices remain in the extracted directories. Microsoft .NET 3.1.32 is downloaded from Microsoft; its distribution terms and notices remain applicable. It is a legacy runtime required by this launcher experiment, not a supported modern .NET configuration.
- https://github.com/mstorsjo/llvm-mingw
- https://www.gnu.org/software/bison/
- https://dotnet.microsoft.com/en-us/download/dotnet/3.1

## Game and launcher

Lineage II and publisher assets belong to their respective rightsholders, including NC Corporation and Innova. No game client, launcher binary, account profile or publisher artwork is included in this source release. The setup script downloads the official installer directly from the publisher and leaves its terms, account login and game installation to the user.

This is an unofficial project without endorsement. The open-source license does not grant rights to publisher assets, trademarks or services, and does not establish compliance with game or launcher terms.
- https://eu.4game.com/legal/lineage2/21/
- https://eu.4game.com/legal/4game/8/

## Standalone app payload

The prebuilt app additionally embeds CPython from python-build-standalone, the official .NET 3.1.32 archive, the locally built Wine synchronization and macOS-driver modules and original helper executables. CPython and its dependency licenses/build metadata are copied from the corresponding pinned full distribution into Resources/Licenses. .NET's LICENSE.txt and ThirdPartyNotices.txt are retained there as well.

The shipped Wine modules are accompanied by its Wine 10 source archive, our patches and build recipe under Resources/Source, with LGPL text in Resources/Licenses. The full Wine engine/support packages are not rehosted in the app: users download them directly from their upstream providers during setup.

Python distribution: https://github.com/astral-sh/python-build-standalone/releases/tag/20261110 . Its licenses apply to Python and dependencies, not to game content. Local ad-hoc signing changes signatures but does not change those license grants.

The standalone app includes apple-codesign (rcodesign) 0.29.0 for local ad-hoc signing of the downloaded runtime, avoiding a dependency on Xcode's codesign_allocate. Its bundled COPYING notice and the corresponding apple-platform-rs source archive are included in Resources/Licenses and Resources/Source. This tool does not provide a Developer ID identity or notarize the app.

Local game fonts: setup/startup uses Arial and Tahoma already present in the
Mac's system supplemental font directory, copying absent files only into the
configured local Wine prefix. This repository and its source/app packages do not
include those font binaries or grant a license to redistribute them. Their
existing license terms apply.

## ISRG Root X1 certificate

`certificates/isrg-root-x1.pem` is the complete public ISRG Root X1 certificate
from https://letsencrypt.org/certs/isrgrootx1.pem, issued by Internet Security
Research Group. Source and certificate details: https://letsencrypt.org/certificates/ .
The certificate is retained in full; it is not original MIT-licensed project code.
Its SHA-256 DER fingerprint is
`96BCEC06264976F37460779ACF28C5A7CFE8A3C0AAE11A8FFCEE05C0BDDF08C6`.
It supplements the updater's local CA file without changing OS trust stores or
disabling certificate verification.

## Metal source setup

The default source setup additionally downloads Highball Wine 11.0 from
https://github.com/gauthierpiarrette/highball-engine/releases/tag/engine-wine-11.0-20261114T185735Z-fiber-mirror-switch
and mtld3d v0.15.5 from https://github.com/athei/mtld3d/releases/tag/v0.15.5 .
The matching CrossOver 26.3.0 open-source archive comes from
https://media.codeweavers.com/pub/crossover/source/crossover-sources-26.3.0.tar.gz .
The Wine-derived kernel is built locally with the existing LGPL synchronization
patches. Highball's downloaded engine, frameworks and notices are retained locally.
The source release does not redistribute their runtime binaries.

mtld3d is copyright 2026 Alexander Theissen under the zlib license; its notice is
retained in licenses/MTLD3D-LICENSE and in the downloaded renderer archive.
Its source is https://github.com/athei/mtld3d . All three downloads are hash-pinned
in dependencies.json. The older Sikarugir inputs remain for legacy standalone builds.

## x87sidecar

Source setup downloads x87sidecar v1.9.1 from its official
release, with pinned archive and executable SHA-256. It is not embedded in this
source archive. Upstream: https://github.com/athei/x87sidecar.
MIT license; copyright (c) 2025 Lifeisawful. The upstream notice is retained in
[licenses/X87SIDECAR-LICENSE](licenses/X87SIDECAR-LICENSE).
Game artwork in screenshots and video excerpts belongs to its respective owners.

## Downstream mtld3d material arithmetic patch

`patches/mtld3d-zero-multiply.patch` is a plainly marked local alteration of
mtld3d v0.15.5 by Alexander Theissen. The upstream zlib notice is retained in
`licenses/MTLD3D-LICENSE`. Source setup downloads verified upstream source
and builds locally; no modified runtime or publisher binary is embedded here.
