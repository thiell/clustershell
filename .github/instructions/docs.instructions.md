---
applyTo: "doc/**"
---

# Documentation review guidance

- Man pages are generated: `doc/man/man1/*.1` and `doc/man/man5/*.5` must not
  be hand-edited. The source is `doc/txt/*.txt`, regenerated with rst2man (see
  the Makefiles under `doc/man/`). If a man page changes without a matching
  `doc/txt/` change, flag it.
- Do not review regenerated man-page content line by line; only check it is
  consistent with the `doc/txt/` source change.
- Keep the three doc surfaces in sync: a user-facing change should be
  reflected in `doc/txt/`, `doc/sphinx/`, and the man pages together.
- Doc examples must run on Python 3: flag `print` statements, `.next()`, and
  other py2-only idioms, as well as stale cross-references.
