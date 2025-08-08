# Onyx Deployment Guide

## Preparing for GitHub

### 1. Create a repository on GitHub

1. Go to [GitHub](https://github.com) and create a new repository
2. Name it `onyx` or `onyx-cli`
3. Do NOT initialize with README, .gitignore or license (we already have files)

### 2. Connect local repository to GitHub

```bash
# Add remote (replace YOUR_USERNAME with your username)
git remote add origin https://github.com/YOUR_USERNAME/onyx.git

# Push code and a tag
git push -u origin master
git push origin v0.1.0
```

### 3. Automatic Releases

After pushing a tag, GitHub Actions will automatically:
1. Build executables for Windows and Linux
2. Create a release with downloadable assets
3. Add a detailed release body

### 4. Creating a new release

To create a new release:

1. Bump the version in `pyproject.toml`:
   ```toml
   version = "0.1.1"
   ```

2. Commit and tag:
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to 0.1.1"
   git tag -a v0.1.1 -m "Release version 0.1.1"
   git push origin master
   git push origin v0.1.1
   ```

3. GitHub Actions will automatically create a release with executables

### 5. Release contents

Each release contains:
- `onyx-windows.exe` — Windows
- `onyx-linux` — Linux

### 6. Installation for users

#### Windows
1. Download `onyx-windows.exe`
2. Place it in a folder from PATH (e.g., `C:\Windows\System32\`) or any folder and run by full path
3. Example: `C:\path\to\onyx-windows.exe --help`

#### Linux
1. Download the file
2. Make it executable: `chmod +x onyx-linux`
3. Optionally move to PATH: `sudo mv onyx-linux /usr/local/bin/onyx`
4. Or run by full path: `./onyx-linux --help`

### 7. Verify installation
```bash
# Windows
onyx-windows.exe --help

# Linux
onyx --help
```

## Local build (for development)

### Windows build
```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --name onyx onyx/main.py

# Output in dist/onyx.exe
```

### Linux build
```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --name onyx onyx/main.py

# Output in dist/onyx
```

## Troubleshooting

### GitHub Actions
- Check logs in Actions → Workflows
- Ensure the tag is created correctly: `v0.1.0`
- Ensure all files are committed

### Local build
- Ensure dependencies are installed
- Ensure compatible Python is used (>=3.10,<3.13)

### Installation
- Ensure the file is fully downloaded
- Check permissions (Linux)
- Try running with a full path
