![banner](static/banner_readme.png)

---

## Onyx CLI

A cross‑platform, multi‑purpose CLI tool (Windows/Linux) for working with files, networking, and repositories. Distributed as ready‑to‑run executables via GitHub Releases.

### Features
- **tree**: advanced directory tree (filters, sizes, dates, hidden files, total size summary)
- **count**: line counter (by extensions, ignore patterns, BFS/DFS, detailed stats)
- **find**: quick global filename search and advanced file/content search (globs, regex, context); uses Everything/locate when available
- **backup**: simple directory backups (archiving, excludes)
- **git**: repository analytics (commits, authors, files, activity)
- **net**: connectivity and diagnostics (ping, traceroute, ports, ip)
- **download**: downloader with progress, resume, size limits, checksum, smart naming
- **monitor**: live CPU/RAM/disk/network monitoring and processes
- **unlock**: release file locks and clear restrictive attributes (Windows/Linux)

---

## Installation

Recommended: download a prebuilt binary from the [Releases](https://github.com/Noloquideus/onyx/releases) page.

- Windows: `onyx-windows.exe` — run from PowerShell or Command Prompt
- Linux: `onyx-linux` — make it executable and run
  ```bash
  chmod +x onyx-linux
  ./onyx-linux --help
  ```

Alternative for development (Poetry):
```bash
poetry install
poetry run onyx --help
```

Local build (PyInstaller):
```bash
poetry run pyinstaller --onefile --name onyx onyx/main.py
# dist/onyx  (Linux)  or  dist/onyx.exe (Windows)
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
onyx unlock --help
```

---

## Updates & Releases
- New versions are published automatically in [Releases](https://github.com/Noloquideus/onyx/releases)
- To update, download the latest executable for your OS

---

## License
MIT License. See `LICENSE`.

