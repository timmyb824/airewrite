# CHANGELOG


## v0.4.0 (2026-02-18)

### Features

- Remove padding from output panel for tighter formatting
  ([`ab3ca57`](https://github.com/timmyb824/airewrite/commit/ab3ca57e342ae8e27bbcafc31878b30944908227))


## v0.3.0 (2026-02-18)

### Continuous Integration

- Add pre-commit configuration with code quality and security hooks
  ([`b23259e`](https://github.com/timmyb824/airewrite/commit/b23259ed0948bbc51100251cc87e307d0d3d42e1))

Add pre-commit config with sourcery, black, isort, conventional commits, secret scanning, and
  standard hooks. Add uv-lock and uv-export hooks for dependency management. Fix import ordering
  across all modules to comply with isort black profile. Generate requirements.txt from uv export.

### Features

- Add help command to interactive session with command reference
  ([`b071749`](https://github.com/timmyb824/airewrite/commit/b071749a4abf0f21c543858bb94ba4adbe961701))

Add :help command that displays all available session commands and their usage. Update interactive
  prompt hint to include :help as first command option.

- Add token usage tracking and cost estimation with spend command
  ([`c80e073`](https://github.com/timmyb824/airewrite/commit/c80e07387b522ff27612ba6cf7914ae2cfbdbd2c))

Add Usage and Result dataclasses to track token consumption, update providers to return usage data,
  store token counts in history events, add --stats flag to display per-request metrics, implement
  spend command to calculate monthly costs from history, and add interactive commands for toggling
  stats and viewing spend


## v0.2.0 (2026-02-18)

### Features

- Use horizontal box style for output panel borders
  ([`9550ff5`](https://github.com/timmyb824/airewrite/commit/9550ff5978292f49812f7160e6a1df89521fafd6))

Change panel border from default box style to HORIZONTALS for cleaner output appearance


## v0.1.0 (2026-02-17)

### Features

- Add color styling to interactive prompt and improve command hints
  ([`fcc2da9`](https://github.com/timmyb824/airewrite/commit/fcc2da903302584375178c44fbaa6b2a87a3def3))

Add styled prompt with cyan headers and magenta commands, list all available commands in hint text,
  and add blank line after config output for better readability


## v0.0.1 (2026-02-17)

### Continuous Integration

- Add continue-on-error flag to code quality checks
  ([`b878b58`](https://github.com/timmyb824/airewrite/commit/b878b58ad255f41989deec5e638f942a712c5f0b))

- Remove if check from lint check
  ([`c3e8a8d`](https://github.com/timmyb824/airewrite/commit/c3e8a8df10e23cce67873c341d3c22c6764a4d3f))
