# Third-party notices

Experience Loop's core workflow uses only Python's standard library and does
not depend on another Codex Skill. To make text-based PDF books work without a
separate installation step, the repository includes these pure-Python wheels:

| Package | Version | License | Purpose |
| --- | --- | --- | --- |
| pypdf | 6.14.2 | BSD-3-Clause | Extract PDF text with real page locators |
| typing_extensions | 4.16.0 | PSF-2.0 | Provide the compatibility symbols pypdf imports on Python 3.9/3.10 |

The upstream licenses are preserved under `licenses/`. Every wheel and its
SHA-256 are recorded in `vendor/manifest.json` so releases can verify the
bundled artifacts. Optional encrypted-PDF features may require packages not
bundled here; their absence never disables the main Experience Loop workflow.
