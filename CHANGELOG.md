# Changelog

All notable changes to this project will be documented in this file.

## [0.5.1] - 2025-11-29

### Changed
- GitHub Actions release notes are now fully in English and reference the Windows-only binary and core commands.
- Fixed release title to use the tag name directly (e.g. "Onyx CLI v0.5.1" instead of "vv0.5.1").

## [0.5.0] - 2025-11-29

### Added
- New `onyx services` command for managing Windows services (list/start/stop/restart) via PowerShell.

### Changed
- Project is now Windows‑only in terms of binaries and release workflow (GitHub Actions builds and publishes only `onyx-windows.exe`).
- README updated to reflect the Windows focus and to document `onyx services` usage.

## [0.4.0] - 2025-11-29

### Added
- New `onyx find` UX: filename search over the whole filesystem by default with `-p` to scope the search.
- Progress bars (via `tqdm`) for all `find` modes: quick search, `find files`, and `find content` (including separate bar for matches when a limit is set).
- System and heavy directory ignore list for `find` (e.g. `Windows`, `Program Files`, `.git`, `node_modules`, `venv`, `__pycache__`, etc.), with an option to include them.

### Changed
- Migrated the entire CLI from `click` to `rich-click` for colorized, more readable help output.
- Reworked help texts for all commands (`tree`, `find`, `count`, `backup`, `git`, `net`, `download`, `monitor`, `env`, `hash`, `unlock`) with clear English descriptions and examples.
- Optimized `find`’s filesystem search to reduce redundant `stat()` calls and improve performance on large trees.

### Fixed
- Minor robustness improvements across commands (error handling, messaging, and option help texts).

