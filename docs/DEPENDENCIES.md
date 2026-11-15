# Dependency baseline

The candidate uses official, hash-pinned CPython **3.14.10** and the matching PSF Tcl/Tk MSI, extracted read-only. It does not install a system Python or combine old DLLs with a newer interpreter. Runtime tests report OpenSSL 3.5.9, SQLite 3.50.4, Expat 2.9.0, Tcl 9.0.4 and Tk 9.0.4.1. The official Python SPDX records the complete vendor-reported component list, including components whose license field is NOASSERTION. That field is preserved rather than guessed.

- Runtime input URLs and SHA256 pins: `tools/build_runtime.py`.
- Build toolchain, ReShade SDK, frozen asset archive and graphics test fixture: `tools/build-inputs.json`.
- Every packaged payload file: `manifest.json` and `dependency-inventory.json`.
- Exact native sources, flags, compiler/SDK hashes and output hashes: `native-build.json`.
- Official vendor SPDX: `payload/BFT_HUD/runtime/python-runtime.spdx.json`.
- Optional OBS 33.0.1 download: pinned in `src/HUD/recorder.py`; it is not included in the installer. Its archive hash and every extracted vendor file are checked before use. Unknown executable/script additions are rejected.

Python 3.13.17 was considered but superseded: Python 3.13.18 has security fixes and no official Windows installer. The candidate therefore uses the newer supported Windows binary baseline. This does not establish that all third-party components are free of vulnerabilities. Recheck upstream advisories and pins before each release; rebuild, test and review dependency changes rather than downloading an unpinned latest version at startup.

The frozen v0.7.0 seed contributes skin, maps, artwork and ReShade assets. Its old Python runtime and all six custom native binaries are replaced. Inherited asset licensing and P1999 permission remain separate from build integrity.
