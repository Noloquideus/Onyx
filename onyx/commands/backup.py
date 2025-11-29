"""
Backup command for creating and managing backups.
"""

import os
import shutil
import zipfile
import tarfile
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Optional
from datetime import datetime
import fnmatch
import rich_click as click
from tqdm import tqdm


@click.group()
def backup():
    """Create and manage backups (full and incremental)."""


@backup.command()
@click.argument('source', type=click.Path(exists=True, path_type=Path))
@click.argument('destination', type=click.Path(path_type=Path))
@click.option('--format', '-f', type=click.Choice(['zip', 'tar', 'tar.gz', 'tar.bz2']), default='zip', help='Archive format')
@click.option('--compression', '-c', type=click.Choice(['none', 'fast', 'best']), default='fast', help='Compression level')
@click.option('--exclude', '-e', multiple=True, help='Patterns to exclude (supports wildcards)')
@click.option('--include-hidden', '-a', is_flag=True, help='Include hidden files and directories')
@click.option('--dry-run', '-n', is_flag=True, help='Show what would be backed up without creating archive')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
@click.option('--follow-symlinks', is_flag=True, help='Follow symbolic links')
def create(source: Path, destination: Path, format: str, compression: str, exclude: tuple,
          include_hidden: bool, dry_run: bool, verbose: bool, follow_symlinks: bool):
    """Create a new backup archive from a directory or single file.

    Examples:
      onyx backup create ./project backups/project.zip
      onyx backup create ./data backups/data.tar.gz --compression best
      onyx backup create ./src backups/src.zip -e .git -e __pycache__ --dry-run
    """
    
    click.echo(f"📦 Creating backup from: {source}")
    click.echo(f"🎯 Destination: {destination}")
    click.echo(f"📋 Format: {format}")
    click.echo(f"🗜️ Compression: {compression}")
    
    if exclude:
        click.echo(f"🚫 Excluding: {', '.join(exclude)}")
    
    # Prepare destination
    if not destination.parent.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
    
    # Add appropriate extension if not present
    if not destination.suffix:
        extension_map = {
            'zip': '.zip',
            'tar': '.tar',
            'tar.gz': '.tar.gz',
            'tar.bz2': '.tar.bz2'
        }
        destination = destination.with_suffix(extension_map[format])
    
    try:
        # Collect files to backup
        files_to_backup = _collect_files_for_backup(
            source, exclude, include_hidden, follow_symlinks, verbose
        )
        
        if not files_to_backup:
            click.echo("❌ No files to backup after applying filters.")
            return
        
        total_size = sum(f['size'] for f in files_to_backup if f['type'] == 'file')
        click.echo(f"📊 Files to backup: {len([f for f in files_to_backup if f['type'] == 'file'])}")
        click.echo(f"📁 Directories: {len([f for f in files_to_backup if f['type'] == 'dir'])}")
        click.echo(f"💾 Total size: {_format_bytes(total_size)}")
        
        if dry_run:
            click.echo("\n🔍 Dry run - showing files that would be backed up:")
            for file_info in files_to_backup[:20]:  # Show first 20
                click.echo(f"  {'📁' if file_info['type'] == 'dir' else '📄'} {file_info['relative_path']}")
            if len(files_to_backup) > 20:
                click.echo(f"  ... and {len(files_to_backup) - 20} more files")
            return
        
        # Create the backup
        click.echo(f"\n🚀 Creating backup...")
        
        if format == 'zip':
            _create_zip_backup(source, destination, files_to_backup, compression, verbose)
        else:
            _create_tar_backup(source, destination, files_to_backup, format, compression, verbose)
        
        # Generate backup info
        backup_info = {
            'created': datetime.now().isoformat(),
            'source': str(source),
            'format': format,
            'compression': compression,
            'files_count': len([f for f in files_to_backup if f['type'] == 'file']),
            'dirs_count': len([f for f in files_to_backup if f['type'] == 'dir']),
            'total_size': total_size,
            'archive_size': destination.stat().st_size if destination.exists() else 0,
            'excluded_patterns': list(exclude)
        }
        
        # Save backup info
        info_file = destination.with_suffix(destination.suffix + '.info')
        with open(info_file, 'w') as f:
            json.dump(backup_info, f, indent=2)
        
        final_size = destination.stat().st_size
        compression_ratio = (1 - final_size / total_size) * 100 if total_size > 0 else 0
        
        click.echo(f"\n✅ Backup created successfully!")
        click.echo(f"📄 Archive: {destination}")
        click.echo(f"📊 Archive size: {_format_bytes(final_size)}")
        click.echo(f"🗜️ Compression ratio: {compression_ratio:.1f}%")
        
    except Exception as e:
        click.echo(f"❌ Error creating backup: {e}", err=True)


@backup.command()
@click.argument('source', type=click.Path(exists=True, path_type=Path))
@click.argument('backup_dir', type=click.Path(path_type=Path))
@click.option('--name', '-n', help='Backup set name (default: source directory name)')
@click.option('--exclude', '-e', multiple=True, help='Patterns to exclude')
@click.option('--include-hidden', '-a', is_flag=True, help='Include hidden files')
@click.option('--max-backups', '-m', type=int, default=10, help='Maximum number of backups to keep')
@click.option('--force-full', '-f', is_flag=True, help='Force full backup instead of incremental')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
def incremental(source: Path, backup_dir: Path, name: str, exclude: tuple, include_hidden: bool,
               max_backups: int, force_full: bool, verbose: bool):
    """Create an incremental backup set with change tracking.

    The first run creates a full backup, subsequent runs store only
    changed / new / deleted files and maintain a manifest.

    Examples:
      onyx backup incremental ./project ./backups
      onyx backup incremental ./data ./backups --name data-set --max-backups 5
      onyx backup incremental ./project ./backups -e .git -e __pycache__
    """
    
    backup_name = name or source.name
    backup_set_dir = backup_dir / backup_name
    backup_set_dir.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"📦 Incremental backup: {backup_name}")
    click.echo(f"📁 Source: {source}")
    click.echo(f"🎯 Backup directory: {backup_set_dir}")
    
    try:
        # Load previous backup info
        manifest_file = backup_set_dir / 'manifest.json'
        previous_manifest = {}
        last_backup_num = 0
        
        if manifest_file.exists() and not force_full:
            with open(manifest_file, 'r') as f:
                manifest_data = json.load(f)
                previous_manifest = manifest_data.get('files', {})
                last_backup_num = manifest_data.get('last_backup', 0)
            click.echo(f"📋 Found previous backup #{last_backup_num}")
        else:
            click.echo("🆕 Creating initial full backup")
        
        # Scan current files
        current_files = _scan_files_with_hashes(source, exclude, include_hidden, verbose)
        
        # Determine what needs to be backed up
        backup_type = "full" if not previous_manifest or force_full else "incremental"
        files_to_backup = []
        
        if backup_type == "full":
            files_to_backup = list(current_files.values())
        else:
            # Incremental: only changed or new files
            for file_path, file_info in current_files.items():
                if file_path not in previous_manifest:
                    file_info['change_type'] = 'new'
                    files_to_backup.append(file_info)
                elif file_info['hash'] != previous_manifest[file_path].get('hash'):
                    file_info['change_type'] = 'modified'
                    files_to_backup.append(file_info)
            
            # Find deleted files
            deleted_files = set(previous_manifest.keys()) - set(current_files.keys())
            for deleted_path in deleted_files:
                files_to_backup.append({
                    'path': deleted_path,
                    'change_type': 'deleted',
                    'type': 'deleted'
                })
        
        if not files_to_backup:
            click.echo("✅ No changes detected - backup not needed")
            return
        
        # Create backup
        backup_num = last_backup_num + 1
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{backup_num:03d}_{backup_type}_{timestamp}"
        backup_file = backup_set_dir / f"{backup_name}.zip"
        
        click.echo(f"🚀 Creating {backup_type} backup #{backup_num}")
        click.echo(f"📊 Files to backup: {len([f for f in files_to_backup if f.get('change_type') != 'deleted'])}")
        
        # Create incremental backup archive
        _create_incremental_archive(source, backup_file, files_to_backup, verbose)
        
        # Update manifest
        new_manifest = {
            'version': '1.0',
            'backup_set': backup_name,
            'last_backup': backup_num,
            'created': datetime.now().isoformat(),
            'type': backup_type,
            'files': current_files
        }
        
        with open(manifest_file, 'w') as f:
            json.dump(new_manifest, f, indent=2)
        
        # Cleanup old backups
        _cleanup_old_backups(backup_set_dir, max_backups)
        
        click.echo(f"✅ {backup_type.title()} backup #{backup_num} created successfully!")
        click.echo(f"📄 Archive: {backup_file}")
        
    except Exception as e:
        click.echo(f"❌ Error creating incremental backup: {e}", err=True)


@backup.command()
@click.argument('archive', type=click.Path(exists=True, path_type=Path))
@click.argument('destination', type=click.Path(path_type=Path))
@click.option('--overwrite', '-o', is_flag=True, help='Overwrite existing files')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
def restore(archive: Path, destination: Path, overwrite: bool, verbose: bool):
    """Restore files from a backup archive into a directory.

    Examples:
      onyx backup restore backups/project.zip ./restored
      onyx backup restore backups/data.tar.gz ./data-restored --overwrite
    """
    
    click.echo(f"📦 Restoring from: {archive}")
    click.echo(f"🎯 Destination: {destination}")
    
    try:
        # Create destination directory
        destination.mkdir(parents=True, exist_ok=True)
        
        # Check archive format and restore
        if archive.suffix == '.zip':
            _restore_from_zip(archive, destination, overwrite, verbose)
        elif archive.suffix in ['.tar', '.gz', '.bz2'] or '.tar' in archive.suffixes:
            _restore_from_tar(archive, destination, overwrite, verbose)
        else:
            click.echo(f"❌ Unsupported archive format: {archive.suffix}", err=True)
            return
        
        click.echo("✅ Restore completed successfully!")
        
    except Exception as e:
        click.echo(f"❌ Error restoring backup: {e}", err=True)


@backup.command()
@click.argument('backup_dir', type=click.Path(exists=True, path_type=Path))
def list(backup_dir: Path):
    """List all backup archives and basic metadata in a directory.

    Examples:
      onyx backup list ./backups
    """
    
    click.echo(f"📋 Backups in: {backup_dir}")
    click.echo("=" * 60)
    
    # Find all backup files and info files
    backups = []
    
    for item in backup_dir.rglob('*'):
        if item.is_file():
            if item.suffix in ['.zip', '.tar', '.gz', '.bz2']:
                backup_info = {
                    'file': item,
                    'size': item.stat().st_size,
                    'created': datetime.fromtimestamp(item.stat().st_mtime)
                }
                
                # Try to load additional info
                info_file = item.with_suffix(item.suffix + '.info')
                if info_file.exists():
                    try:
                        with open(info_file, 'r') as f:
                            extra_info = json.load(f)
                            backup_info.update(extra_info)
                    except:
                        pass
                
                backups.append(backup_info)
    
    if not backups:
        click.echo("No backups found.")
        return
    
    # Sort by creation date
    backups.sort(key=lambda x: x['created'], reverse=True)
    
    for backup in backups:
        click.echo(f"📦 {backup['file'].name}")
        click.echo(f"   📅 Created: {backup['created'].strftime('%Y-%m-%d %H:%M:%S')}")
        click.echo(f"   📊 Size: {_format_bytes(backup['size'])}")
        
        if 'files_count' in backup:
            click.echo(f"   📄 Files: {backup['files_count']}")
        if 'format' in backup:
            click.echo(f"   📋 Format: {backup['format']}")
        if 'compression' in backup:
            click.echo(f"   🗜️ Compression: {backup['compression']}")
        
        click.echo()


def _collect_files_for_backup(source: Path, exclude_patterns: tuple, include_hidden: bool, 
                             follow_symlinks: bool, verbose: bool) -> List[Dict]:
    """Collect files and directories for backup."""
    files = []
    exclude_set = set(exclude_patterns)
    
    def should_exclude(path: Path) -> bool:
        """Check if path should be excluded."""
        for pattern in exclude_set:
            if fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(str(path), pattern):
                return True
        return False
    
    def scan_directory(dir_path: Path, relative_to: Path):
        """Recursively scan directory."""
        try:
            for item in dir_path.iterdir():
                if not include_hidden and item.name.startswith('.'):
                    continue
                
                if should_exclude(item):
                    if verbose:
                        click.echo(f"🚫 Excluding: {item}")
                    continue
                
                relative_path = item.relative_to(relative_to)
                
                if item.is_file() or (item.is_symlink() and follow_symlinks):
                    try:
                        stat_info = item.stat()
                        files.append({
                            'path': str(item),
                            'relative_path': str(relative_path),
                            'type': 'file',
                            'size': stat_info.st_size,
                            'modified': datetime.fromtimestamp(stat_info.st_mtime)
                        })
                        
                        if verbose:
                            click.echo(f"📄 Adding file: {relative_path}")
                            
                    except (OSError, PermissionError):
                        if verbose:
                            click.echo(f"⚠️ Cannot access: {item}")
                
                elif item.is_dir() and not item.is_symlink():
                    files.append({
                        'path': str(item),
                        'relative_path': str(relative_path),
                        'type': 'dir',
                        'size': 0,
                        'modified': datetime.fromtimestamp(item.stat().st_mtime)
                    })
                    
                    if verbose:
                        click.echo(f"📁 Adding directory: {relative_path}")
                    
                    scan_directory(item, relative_to)
                    
        except (OSError, PermissionError):
            if verbose:
                click.echo(f"⚠️ Cannot access directory: {dir_path}")
    
    if source.is_file():
        files.append({
            'path': str(source),
            'relative_path': source.name,
            'type': 'file',
            'size': source.stat().st_size,
            'modified': datetime.fromtimestamp(source.stat().st_mtime)
        })
    else:
        scan_directory(source, source.parent)
    
    return files


def _create_zip_backup(source: Path, destination: Path, files: List[Dict], 
                      compression: str, verbose: bool):
    """Create ZIP backup."""
    compression_level_map = {
        'none': zipfile.ZIP_STORED,
        'fast': zipfile.ZIP_DEFLATED,
        'best': zipfile.ZIP_DEFLATED
    }
    
    compresslevel = {'none': 0, 'fast': 3, 'best': 9}[compression]
    
    with zipfile.ZipFile(destination, 'w', compression_level_map[compression], 
                        compresslevel=compresslevel) as zf:
        
        with tqdm(total=len(files), desc="Creating archive", disable=not verbose) as pbar:
            for file_info in files:
                if file_info['type'] == 'file':
                    try:
                        zf.write(file_info['path'], file_info['relative_path'])
                        if verbose:
                            pbar.set_description(f"Adding: {file_info['relative_path'][:30]}...")
                    except (OSError, PermissionError):
                        if verbose:
                            click.echo(f"⚠️ Skipping: {file_info['relative_path']}")
                
                pbar.update(1)


def _create_tar_backup(source: Path, destination: Path, files: List[Dict], 
                      format: str, compression: str, verbose: bool):
    """Create TAR backup."""
    mode_map = {
        'tar': 'w',
        'tar.gz': 'w:gz',
        'tar.bz2': 'w:bz2'
    }
    
    with tarfile.open(destination, mode_map[format]) as tf:
        with tqdm(total=len(files), desc="Creating archive", disable=not verbose) as pbar:
            for file_info in files:
                if file_info['type'] in ['file', 'dir']:
                    try:
                        tf.add(file_info['path'], file_info['relative_path'], recursive=False)
                        if verbose:
                            pbar.set_description(f"Adding: {file_info['relative_path'][:30]}...")
                    except (OSError, PermissionError):
                        if verbose:
                            click.echo(f"⚠️ Skipping: {file_info['relative_path']}")
                
                pbar.update(1)


def _scan_files_with_hashes(source: Path, exclude_patterns: tuple, include_hidden: bool, 
                           verbose: bool) -> Dict[str, Dict]:
    """Scan files and calculate their hashes for incremental backup."""
    files = {}
    exclude_set = set(exclude_patterns)
    
    def should_exclude(path: Path) -> bool:
        """Check if path should be excluded."""
        for pattern in exclude_set:
            if fnmatch.fnmatch(path.name, pattern):
                return True
        return False
    
    def calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except (OSError, PermissionError):
            return ""
    
    def scan_recursive(current_path: Path):
        """Recursively scan directory."""
        try:
            for item in current_path.iterdir():
                if not include_hidden and item.name.startswith('.'):
                    continue
                
                if should_exclude(item):
                    continue
                
                relative_path = str(item.relative_to(source))
                
                if item.is_file():
                    file_hash = calculate_file_hash(item)
                    stat_info = item.stat()
                    
                    files[relative_path] = {
                        'path': str(item),
                        'relative_path': relative_path,
                        'type': 'file',
                        'size': stat_info.st_size,
                        'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        'hash': file_hash
                    }
                    
                    if verbose:
                        click.echo(f"📄 Hashing: {relative_path}")
                
                elif item.is_dir():
                    scan_recursive(item)
                    
        except (OSError, PermissionError):
            pass
    
    scan_recursive(source)
    return files


def _create_incremental_archive(source: Path, backup_file: Path, files: List[Dict], verbose: bool):
    """Create incremental backup archive."""
    with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Create change log
        changes = {
            'new': [],
            'modified': [],
            'deleted': []
        }
        
        files_to_backup = [f for f in files if f.get('change_type') != 'deleted']
        
        with tqdm(total=len(files_to_backup), desc="Creating incremental backup", 
                 disable=not verbose) as pbar:
            
            for file_info in files_to_backup:
                change_type = file_info.get('change_type', 'unknown')
                changes[change_type].append(file_info['relative_path'])
                
                try:
                    zf.write(file_info['path'], file_info['relative_path'])
                    if verbose:
                        pbar.set_description(f"Adding: {file_info['relative_path'][:30]}...")
                except (OSError, PermissionError):
                    if verbose:
                        click.echo(f"⚠️ Skipping: {file_info['relative_path']}")
                
                pbar.update(1)
        
        # Add deleted files to changes
        for file_info in files:
            if file_info.get('change_type') == 'deleted':
                changes['deleted'].append(file_info['path'])
        
        # Write change log to archive
        change_log = json.dumps(changes, indent=2)
        zf.writestr('CHANGES.json', change_log)


def _cleanup_old_backups(backup_dir: Path, max_backups: int):
    """Remove old backup files, keeping only the most recent ones."""
    backup_files = []
    
    for item in backup_dir.iterdir():
        if item.is_file() and item.suffix == '.zip' and 'backup_' in item.name:
            backup_files.append(item)
    
    if len(backup_files) <= max_backups:
        return
    
    # Sort by modification time (newest first)
    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Remove old backups
    for old_backup in backup_files[max_backups:]:
        try:
            old_backup.unlink()
            click.echo(f"🗑️ Removed old backup: {old_backup.name}")
        except OSError:
            pass


def _restore_from_zip(archive: Path, destination: Path, overwrite: bool, verbose: bool):
    """Restore files from ZIP archive."""
    with zipfile.ZipFile(archive, 'r') as zf:
        members = zf.namelist()
        
        with tqdm(total=len(members), desc="Restoring", disable=not verbose) as pbar:
            for member in members:
                dest_path = destination / member
                
                if dest_path.exists() and not overwrite:
                    if verbose:
                        click.echo(f"⏭️ Skipping existing: {member}")
                    pbar.update(1)
                    continue
                
                try:
                    zf.extract(member, destination)
                    if verbose:
                        pbar.set_description(f"Extracting: {member[:30]}...")
                except Exception:
                    if verbose:
                        click.echo(f"⚠️ Failed to extract: {member}")
                
                pbar.update(1)


def _restore_from_tar(archive: Path, destination: Path, overwrite: bool, verbose: bool):
    """Restore files from TAR archive."""
    with tarfile.open(archive, 'r:*') as tf:
        members = tf.getmembers()
        
        with tqdm(total=len(members), desc="Restoring", disable=not verbose) as pbar:
            for member in members:
                dest_path = destination / member.name
                
                if dest_path.exists() and not overwrite:
                    if verbose:
                        click.echo(f"⏭️ Skipping existing: {member.name}")
                    pbar.update(1)
                    continue
                
                try:
                    tf.extract(member, destination)
                    if verbose:
                        pbar.set_description(f"Extracting: {member.name[:30]}...")
                except Exception:
                    if verbose:
                        click.echo(f"⚠️ Failed to extract: {member.name}")
                
                pbar.update(1)


def _format_bytes(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"
