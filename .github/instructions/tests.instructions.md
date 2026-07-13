---
applyTo: "tests/**/*.py"
---

# Test review guidance

- Tests are Python 3 only: never suggest Python 2 shims, `basestring`,
  `u"..."` prefixes, or `from __future__` imports here.
- Test floor is Python 3.6 / EL8: no `subprocess.run(capture_output=True)` or
  `text=True`; use `stdout=`/`stderr=PIPE` and `universal_newlines=True`.
- Prefer the helpers in `tests/TLib.py` (`make_temp_file`, `CLI_main`, …) and
  the existing mixins/base classes over new scaffolding.
- When extending an established test pattern, repeat it verbatim rather than
  restyling it — sameness signals same behavior.
- Watch for timing-sensitive tests: sleeps used as synchronization and tight
  timing assertions are a recurring source of CI flakiness.
- The suite runs many cases in one process: flag tests that mutate global
  state (logging configuration, environment variables, cwd) without restoring
  it.
