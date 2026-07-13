---
applyTo: "lib/ClusterShell/**/*.py"
---

# Core library review guidance

- This tree keeps best-effort Python 2.7 support for the 1.10 series: do not
  suggest dropping compat shims, `basestring` fallbacks, or old idioms; if
  something is genuinely py2-only cruft, note it as a 1.11 cleanup.
- Python-version breadcrumb comments (`# Python 2 compat`, `# could use
  removeprefix() in py3.9+`) are intentional markers for future cleanups —
  never flag them as dead code or outdated.
- Reuse existing helpers instead of adding a parallel code path (e.g. route
  caching goes through `_upcall_cache()`). Configuration is validated in
  `GroupResolverConfig`, not in class constructors — library classes fail
  lazily (e.g. `GroupSourceNoUpcall`).
- NodeSet / RangeSet / RangeSetND semantics: flag anything that could silently
  flatten multi-dimensional sets to 1D, drop zero-padding, change
  iteration/sort order, or mishandle the empty set — these are the recurring
  regression classes.
- Remote command output is bytes end-to-end on Python 3: str decoding happens
  only at the display boundary (`CLI/Display.py`). Flag code that decodes
  earlier or mixes str and bytes in MsgTree/Worker paths.
