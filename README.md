![banner](static/banner_readme.png)

---

## Onyx CLI

A Windows‑first CLI toolbox for working with files, services, networking, and repositories. Distributed as a ready‑to‑run Windows executable via GitHub Releases.

### Features
- **tree**: advanced directory tree (filters, sizes, dates, hidden files, total size summary)
- **count**: line counter (by extensions, ignore patterns, BFS/DFS, detailed stats)
- **find**: quick global filename search and advanced file/content search (globs, regex, context); uses Everything when available
- **backup**: simple directory backups (archiving, excludes)
- **git**: repository analytics (commits, authors, files, activity)
- **net**: connectivity and diagnostics (ping, traceroute, ports, ip)
- **download**: downloader with progress, resume, size limits, checksum, smart naming
- **monitor**: live CPU/RAM/disk/network monitoring and processes
- **services**: list/start/stop/restart Windows services from the CLI
- **unlock**: release file locks and clear restrictive attributes (Windows)
- **env**: environment and system snapshot (OS/Python/Onyx, env vars)
- **hash**: file hashes and duplicate detection (md5/sha1/sha256)

---

## Installation

Recommended: download a prebuilt Windows binary from the [Releases](https://github.com/Noloquideus/onyx/releases) page.

- Windows: `onyx-windows.exe` — run from PowerShell or Command Prompt

Alternative for development (Poetry):
```bash
poetry install
poetry run onyx --help
```

Local build (PyInstaller, Windows):
```bash
poetry run pyinstaller --onefile --name onyx onyx/main.py
# dist/onyx.exe (Windows)
```
Requirements: Python >=3.10,<3.13.

---

## Quick Start

Tree (sizes + modified time, depth limit, JSON/CSV output):
```bash
onyx tree . --show-time --show-hidden             # use --no-files to hide files
onyx tree . --max-depth 2                         # real depth limit (no deep traversal)
onyx tree . --output json > tree.json             # machine-readable tree
```

Count lines only in Python files (table/JSON/CSV):
```bash
onyx count . --extensions .py --show-files
onyx count . --extensions .py --output json > count.json
onyx count . --extensions .py --output csv  > count.csv
```

Quick global filename search (uses Everything/locate if available):
```bash
onyx find git.exe             # search across the whole system
onyx find README.md --path .  # restrict to current folder
```

Find text inside files (clean JSON for scripting):
```bash
onyx find content . "TODO" --extension .py -C 2
onyx find content . "TODO" --extension .py --output json > matches.json
```

Download with progress and smart naming:
```bash
onyx download single "https://example.com/file.zip" -o file.zip
# Google Drive direct: https://drive.google.com/uc?export=download&id=<ID>
```

Monitor system resources (live or JSON/CSV stream):
```bash
onyx monitor system --interval 1 --duration 10
onyx monitor system --interval 1 --duration 10 --output json > metrics.json
```

Manage Windows services:
```bash
onyx services list                       # all services
onyx services list --status Running      # only running services
onyx services start "Spooler"            # start a service
onyx services restart "Spooler"
```

Environment / system snapshot:
```bash
onyx env                      # human-readable summary
onyx env --output json > env.json
onyx env --no-env --output json  # without full env vars
```

Hashing and duplicate detection:
```bash
onyx hash . --algo sha256 --output table
onyx hash . --algo sha256 --duplicates-only --output json > dups.json
onyx hash . --algo sha256 --min-size 1MB --extension .py --output csv > hashes.csv
```

Unlock a file for deletion/modification:
```bash
onyx unlock "C:\path\to\file.txt" --force --recursive
```

---

## Command Help
```bash
onyx --help
onyx tree --help
onyx count --help
onyx find --help
onyx backup --help
onyx git --help
onyx net --help
onyx download --help
onyx monitor --help
onyx services --help
onyx unlock --help
```

---

## Updates & Releases
- New versions are published automatically in [Releases](https://github.com/Noloquideus/onyx/releases)
- To update, download the latest Windows executable

## Changelog
- See [CHANGELOG.md](./CHANGELOG.md) for detailed release notes and version history.

---

## License
MIT License. See `LICENSE`.

