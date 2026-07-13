# ClusterShell — Copilot instructions

ClusterShell is an event-driven Python library and set of CLIs (`clush`,
`nodeset`/`cluset`, `clubak`) for parallel remote execution and node-set/range
manipulation on HPC clusters. Core library: `lib/ClusterShell/`; CLIs:
`lib/ClusterShell/CLI/`; tests: `tests/`; docs: `doc/`.

License: LGPL-2.1-or-later (core), PSF-2.0 (some components).

## Supported Python versions

- The library (`lib/`) keeps best-effort Python 2.7 support through the 1.10
  series (legacy EL7 HPC); 1.11 drops Python 2 with a floor of Python 3.6 /
  EL8. Do not propose removing a py2 compat path in a 1.10.x change — flag it
  as a 1.11 cleanup instead.
- Tests are Python 3 only, floor Python 3.6 / EL8.

## Hard rules

- Man pages are generated: files under `doc/man/` must never be hand-edited;
  the source is `doc/txt/*.txt` (rst2man).
- Public API compatibility: new constructor/function parameters are appended
  at the end of the signature, never inserted mid-signature.

## Review conduct

- Prioritize correctness and semantic regressions over style.
- Comments in code should be concise: one line preferred, multi-line only to
  explain a complex situation the code cannot self-describe.
- Keep review comments concise and high-signal. Do not comment on
  commit-message formatting or DCO.
