"""
Hash command for file hashing and duplicate detection.
"""

from pathlib import Path
from typing import Dict, List, Optional
import hashlib
import fnmatch

import click


class FileHashInfo:
    __slots__ = ("path", "size", "hash")

    def __init__(self, path: Path, size: int, digest: str) -> None:
        self.path = path
        self.size = size
        self.hash = digest


@click.command(name="hash")
@click.argument('path', default='.', type=click.Path(exists=True, path_type=Path))
@click.option('--algo', '-a', type=click.Choice(['md5', 'sha1', 'sha256']), default='sha256',
              help='Hash algorithm to use')
@click.option('--duplicates-only', '--dups-only', is_flag=True,
              help='Show only files that have duplicates')
@click.option('--min-size', type=str, default=None,
              help='Ignore files smaller than this size (e.g., 1KB, 10MB)')
@click.option('--extension', '-e', multiple=True,
              help='Only include files with these extensions (e.g., .py, .txt)')
@click.option('--ignore', '-i', multiple=True,
              help='Ignore files/directories matching these patterns')
@click.option('--show-hidden', is_flag=True,
              help='Include hidden files')
@click.option(
    '--output',
    '-o',
    type=click.Choice(['table', 'json', 'csv']),
    default='table',
    help='Output format (table/json/csv)',
)
def hash_cmd(path: Path,
             algo: str,
             duplicates_only: bool,
             min_size: Optional[str],
             extension: tuple,
             ignore: tuple,
             show_hidden: bool,
             output: str) -> None:
    """
    Calculate file hashes and detect duplicate files.

    PATH: Root directory to scan (default: current directory)
    """

    try:
        min_size_bytes = _parse_size(min_size) if min_size else 0
    except ValueError as e:
        click.echo(f"❌ Invalid --min-size value: {e}", err=True)
        raise SystemExit(1)

    exts = {ext if ext.startswith('.') else f'.{ext}' for ext in extension} if extension else set()
    ignore_patterns = set(ignore) if ignore else set()

    if output == 'table':
        click.echo(f"🔐 Hashing files under: {path.absolute()}")
        click.echo(f"   Algorithm: {algo}")
        if exts:
            click.echo(f"   Extensions: {', '.join(sorted(exts))}")
        if min_size_bytes:
            click.echo(f"   Min size: {_format_size(min_size_bytes)}")
        if ignore_patterns:
            click.echo(f"   Ignore: {', '.join(sorted(ignore_patterns))}")
        if duplicates_only:
            click.echo(f"   Mode: duplicates only")
        click.echo()

    try:
        files = _collect_files(
            root=path,
            exts=exts,
            min_size=min_size_bytes,
            ignore_patterns=ignore_patterns,
            show_hidden=show_hidden,
        )

        if not files:
            click.echo("❌ No files matched the criteria.")
            return

        # Hash and group by digest
        groups: Dict[str, List[FileHashInfo]] = {}
        for fpath, fsize in files:
            digest = _hash_file(fpath, algo)
            if digest is None:
                continue
            info = FileHashInfo(fpath, fsize, digest)
            groups.setdefault(digest, []).append(info)

        # Flatten for output
        rows: List[Dict] = []
        for digest, infos in groups.items():
            if duplicates_only and len(infos) < 2:
                continue
            for info in infos:
                rows.append({
                    'hash': digest,
                    'path': str(info.path),
                    'size': info.size,
                    'size_human': _format_size(info.size),
                    'is_duplicate': len(infos) > 1,
                    'dups_count': len(infos),
                })

        if not rows:
            if duplicates_only:
                click.echo("✅ No duplicate files found.")
            else:
                click.echo("❌ No files matched after hashing.")
            return

        # Sort: duplicates first, then by hash, then by path
        rows.sort(key=lambda r: (not r['is_duplicate'], r['hash'], r['path']))

        if output == 'json':
            import json as _json
            click.echo(_json.dumps(rows, indent=2, ensure_ascii=False))
        elif output == 'csv':
            import csv as _csv
            import sys as _sys
            fieldnames = ['hash', 'path', 'size', 'size_human', 'is_duplicate', 'dups_count']
            writer = _csv.DictWriter(_sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        else:
            _print_table(rows, algo)

    except Exception as e:
        click.echo(f"❌ Error while hashing files: {e}", err=True)


def _collect_files(root: Path,
                   exts: set,
                   min_size: int,
                   ignore_patterns: set,
                   show_hidden: bool) -> List[tuple]:
    """Collect candidate files for hashing."""
    result: List[tuple] = []

    def should_ignore(p: Path) -> bool:
        name = p.name
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(p), pattern):
                return True
        return False

    for item in root.rglob('*'):
        try:
            if not item.is_file():
                continue

            if not show_hidden and item.name.startswith('.'):
                continue

            if should_ignore(item):
                continue

            if exts and item.suffix.lower() not in exts:
                continue

            size = item.stat().st_size
            if size < min_size:
                continue

            result.append((item, size))
        except (OSError, PermissionError):
            continue

    return result


def _hash_file(path: Path, algo: str) -> Optional[str]:
    """Compute hash of a single file."""
    try:
        if algo == 'md5':
            h = hashlib.md5()
        elif algo == 'sha1':
            h = hashlib.sha1()
        else:
            h = hashlib.sha256()

        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError):
        return None


def _parse_size(value: str) -> int:
    """Parse a human-readable size like '10MB' into bytes."""
    value = value.strip().upper()
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
    }
    for unit, factor in units.items():
        if value.endswith(unit):
            num = value[:-len(unit)]
            return int(float(num) * factor)
    # No suffix: assume bytes
    return int(value)


def _format_size(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def _print_table(rows: List[Dict], algo: str) -> None:
    """Pretty-print hash results and duplicates."""
    total_files = len(rows)
    dup_files = sum(1 for r in rows if r['is_duplicate'])
    unique_hashes = len({r['hash'] for r in rows})

    click.echo(f"🔐 Hash results ({algo})")
    click.echo("=" * 60)
    click.echo(f"📁 Files:      {total_files}")
    click.echo(f"🔁 Duplicates: {dup_files}")
    click.echo(f"🔑 Unique hashes: {unique_hashes}")

    if not rows:
        return

    click.echo("\n📄 Files:")
    current_hash = None
    for row in rows:
        marker = "🔁" if row['is_duplicate'] else "  "
        if row['hash'] != current_hash:
            current_hash = row['hash']
            click.echo(f"\n{marker} {row['hash']}")
        click.echo(f"   - {row['path']} ({row['size_human']})")


