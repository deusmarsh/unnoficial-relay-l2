# Deferred custom icons

Custom icons are disabled by default in source development. `./dev setup`,
`./dev run` and CI do not compile `build_icons.swift`, run `iconutil`, generate
Windows ICO files or apply artwork to the Wine runtime. Source window helpers
also omit the optional custom icon argument. macOS can show its default app icon;
existing Wine/game icons are not removed.

The original artwork code remains in `build_icons.swift`. The optional builder
path is retained with a comment in `build_native_frame_relay.py`:

```sh
python3 build_native_frame_relay.py --relay-only --with-icons
```

This is an explicit opt-in, not a required contributor step. Applying the runtime
icon separately uses `configure_runtime_icon.py` after generating the icons.
The separate standalone bundle builder still opts into artwork because it packages
those assets. Revisit that optional distribution path when packaging work resumes.

In the maintainer's restricted execution environment `iconutil` rejected valid
iconsets but worked when allowed normal system access. That is not evidence of an
artwork defect, and it is not a reason to make icon creation a development prerequisite.
