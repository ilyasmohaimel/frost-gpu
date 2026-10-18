# G513QY reference source

This directory exports the tested AMD/AMD controller, launch routes, session
helpers, shell cleanup hooks, and Qt tray. PCI addresses, Mesa selectors,
`ADP0`, and package-manager checks deliberately describe one laptop.

The export does not run itself. Follow the [build and integration map](../../docs/build.md)
and keep the [recovery path](../../docs/recovery.md) available.
The portable JSON example is used by the inspection tool only.

The main code matches the local tested implementation. The public export
replaces the tray service's personal home path with `%h` and adapts the session
tests to use fixtures by default. Set `FROST_TEST_HARDWARE=1` only on the exact
reference hardware to run its real DRM-node tests. No machine credentials,
account profiles, custom keyboard-shortcut names, forced relogin scripts,
autologin config, or personal desktop entries are included.

Extra dispatcher profiles do not imply support beyond the public app matrix.
Treat the default route set as reference behavior to review, not an invitation
to wrap every executable on a new installation.
