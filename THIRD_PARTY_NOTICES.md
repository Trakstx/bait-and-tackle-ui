# Third-party notices

## UI ancestry and assets

This skin is derived from community EverQuest UI components including Rustle UI 2 by deezy, along with components carrying their existing authorship. Preserve notices in the XML and package.

- Rustle UI 2 author thread: https://project1999.com/forums/showthread.php?t=359465
- EQInterface listing: https://www.eqinterface.com/downloads/fileinfo.php?id=6828

This project does not claim ownership of EverQuest or its original assets, or grant new rights to third-party artwork.

## ReShade

Copyright 2014 Patrick Mours. The distribution includes ReShade's redistribution conditions and disclaimer in `ReShade-LICENSE.md`.

## CPython and Tcl/Tk

The release bundles a private CPython 3.14.10 runtime. Its PSF license and incorporated notices are in `payload/BFT_HUD/runtime/LICENSE.txt`. Tcl/Tk notices are retained in the PSF license bundle and Tcl/Tk library archives under `runtime/tcl/`. Preserve these files when redistributing the package.

## CH-chain references

CCHPM and EQTool were researched as behavior/format references. Their source code was not copied into the CH parser.

- https://github.com/Dgc2002/CCHPM
- https://github.com/smasherprog/EqTool/blob/main/README.md

## Native toolchain runtime

The native targets use w64devkit 2.10.0 with static MinGW/GCC runtime linking. Preserve the accompanying MinGW-w64 runtime notice. GCC runtime use is subject to the GCC Runtime Library Exception (version 3.1) and its underlying license; see https://www.gnu.org/licenses/gcc-exception-3.1.html. The compiler is a build-time input, not an installed application.

## Optional recorder

OBS Studio 33.0.1 is an optional hash-pinned download, not bundled in the candidate archive. OBS and its plugins retain their upstream license notices in the downloaded distribution. See https://github.com/obsproject/obs-studio and its COPYING file. Source and build notices for BFT do not replace OBS licensing.
