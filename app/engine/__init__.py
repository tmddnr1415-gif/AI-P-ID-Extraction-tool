"""The Phase 0 detection engine, promoted unchanged from `spike/`.

Every module in this package arrived here by `git mv` from `spike/` with no
edit to its detection logic; `git log --follow` on any of them shows the whole
Phase 0 history.  Two kinds of change were unavoidable and are the only ones:

  * path arguments.  `detect_valves` and `stroke_bootstrap` held the sample
    PDF and the `out/` directory as module constants because they were scripts.
    They now take those as parameters whose defaults are the old constants, so
    the command lines in `spike/README.md` still reproduce the Phase 0 numbers
    byte for byte.

  * nothing else.

The modules keep importing each other by bare name (`import pidcache`) via the
`sys.path` insert each one already had, so `app.pipeline` loads them the same
way rather than as a package - importing them both ways would give two copies
of the module-level `LAYOUT` and the config singleton.
"""
