![banner](static/banner_readme.png)

---

## Onyx CLI

A cross‑platform, multi‑purpose CLI tool (Windows/Linux) for working with files, networking, and repositories. Distributed as ready‑to‑run executables via GitHub Releases.

### Features
- **tree**: advanced directory tree (filters, sizes, dates, hidden files, total size summary)
- **count**: line counter (by extensions, ignore patterns, BFS/DFS, detailed stats)
- **find**: search files and file contents (globs, case sensitivity, context)
- **backup**: simple directory backups (archiving, excludes)
- **git**: quick git utilities (stats, status, recent commits)
- **net**: networking helpers (ping, whois, ip, ports)
- **download**: file downloader with progress bar and resume
- **monitor**: live CPU/RAM/disk/network monitoring

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

Show a directory tree with sizes and modification times:
```bash
onyx tree . --show-files --show-size --show-modified-time
```

Count lines only in Python files:
```bash
onyx count . --extensions .py --show-files
```

Find text in files using a glob pattern:
```bash
onyx find . --pattern "*.py" --text "TODO" --ignore ".venv,__pycache__"
```

Download a file with a progress bar:
```bash
onyx download https://example.com/file.zip -o ./file.zip
```

System monitoring:
```bash
onyx monitor system
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
```

---

## Updates & Releases
- New versions are published automatically in [Releases](https://github.com/Noloquideus/onyx/releases)
- To update, download the latest executable for your OS

---

## License
MIT License. See `LICENSE`.

