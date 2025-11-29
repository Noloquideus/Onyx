"""
Count command for counting lines in files.
"""

from pathlib import Path
from collections import deque
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
import fnmatch
import rich_click as click


@dataclass
class FileStats:
    """File statistics"""
    path: str
    lines: int
    size_bytes: int


@dataclass
class DirectoryStats:
    """Aggregate directory statistics"""
    total_files: int
    total_lines: int
    total_size_bytes: int
    files: List[FileStats]


class LineCounter:
    """Counts lines in files"""
    
    def __init__(self, extensions: set = None, ignore_empty_lines: bool = False, 
                 ignore_comments: bool = False, ignore_patterns: List[str] = None, 
                 show_hidden: bool = False):
        """
        Args:
            extensions: Set of file extensions to analyze
            ignore_empty_lines: Ignore empty lines
            ignore_comments: Ignore comment lines
            ignore_patterns: List of file/folder ignore patterns
            show_hidden: Include hidden files
        """
        self.ignore_empty_lines = ignore_empty_lines
        self.ignore_comments = ignore_comments
        self.extensions = extensions or set()
        self.ignore_patterns = ignore_patterns or []
        self.show_hidden = show_hidden
    
    def count_lines_in_file(self, file_path: Path) -> int:
        """
        Count lines in a single file
        
        Args:
            file_path: Path to the file
            
        Returns:
            int: Number of lines
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if not self.ignore_empty_lines and not self.ignore_comments:
                return len(lines)
            
            count = 0
            for line in lines:
                stripped = line.strip()
                
                # Skip empty lines if requested
                if self.ignore_empty_lines and not stripped:
                    continue
                
                # Skip comment lines if requested
                if self.ignore_comments and stripped.startswith('#'):
                    continue
                
                count += 1
            
            return count
            
        except Exception:
            return 0
    
    def should_include_file(self, file_path: Path) -> bool:
        """Check whether a file should be included in the analysis"""
        # Check extension if a restricted set is provided
        if self.extensions and file_path.suffix.lower() not in self.extensions:
            return False
        
        # Check hidden files
        if not self.show_hidden and file_path.name.startswith('.'):
            return False
            
        return True
    
    def should_ignore(self, path: Path) -> bool:
        """
        Check whether a file or directory should be ignored
        
        Args:
            path: Path to a file or directory
            
        Returns:
            bool: True if it should be ignored
        """
        path_str = str(path)
        path_name = path.name
        
        for pattern in self.ignore_patterns:
            # Exact name match
            if path_name == pattern:
                return True
            
            # Wildcard pattern match
            if fnmatch.fnmatch(path_name, pattern):
                return True
            
            # Pattern contained in the path
            if pattern in path_str:
                return True
            
            # Extension match
            if pattern.startswith('.') and path_name.endswith(pattern):
                return True
        
        return False
    
    def count_lines_recursive(self, root_path: Path, algorithm: str = "dfs") -> DirectoryStats:
        """
        Count lines using the given algorithm
        
        Args:
            root_path: Root directory to search
            algorithm: 'dfs' or 'bfs'
            
        Returns:
            DirectoryStats: Directory statistics
        """
        if not root_path.exists():
            raise FileNotFoundError(f"Path does not exist: {root_path}")
        
        files_stats = []
        
        if algorithm == "dfs":
            # DFS (Depth-First Search) - stack
            stack = [root_path]
            
            while stack:
                current_path = stack.pop()
                
                # Skip if this path should be ignored (except the root folder)
                if current_path != root_path and self.should_ignore(current_path):
                    continue
                
                try:
                    if current_path.is_file():
                        if self.should_include_file(current_path):
                            lines = self.count_lines_in_file(current_path)
                            size = current_path.stat().st_size
                            
                            files_stats.append(FileStats(
                                path=str(current_path),
                                lines=lines,
                                size_bytes=size
                            ))
                    
                    elif current_path.is_dir():
                        # Push directory contents onto stack (reverse order for correct DFS)
                        try:
                            items = sorted(current_path.iterdir(), reverse=True)
                            # Filter ignored items before pushing
                            filtered_items = [item for item in items if not self.should_ignore(item)]
                            stack.extend(filtered_items)
                        except PermissionError:
                            pass
                            
                except Exception:
                    pass
        else:
            # BFS (Breadth-First Search) - queue
            queue = deque([root_path])
            
            while queue:
                current_path = queue.popleft()
                
                # Skip if this path should be ignored (except the root folder)
                if current_path != root_path and self.should_ignore(current_path):
                    continue
                
                try:
                    if current_path.is_file():
                        if self.should_include_file(current_path):
                            lines = self.count_lines_in_file(current_path)
                            size = current_path.stat().st_size
                            
                            files_stats.append(FileStats(
                                path=str(current_path),
                                lines=lines,
                                size_bytes=size
                            ))
                    
                    elif current_path.is_dir():
                        # Enqueue directory contents
                        try:
                            items = sorted(current_path.iterdir())
                            # Filter ignored items before enqueuing
                            filtered_items = [item for item in items if not self.should_ignore(item)]
                            queue.extend(filtered_items)
                        except PermissionError:
                            pass
                            
                except Exception:
                    pass
        
        return DirectoryStats(
            total_files=len(files_stats),
            total_lines=sum(f.lines for f in files_stats),
            total_size_bytes=sum(f.size_bytes for f in files_stats),
            files=files_stats
        )


def format_size(size_bytes: int) -> str:
    """Форматирует размер в читаемый вид"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


@click.command()
@click.argument('path', default='.', type=click.Path(exists=True, path_type=Path))
@click.option('--extensions', '-e', multiple=True, help='Only include files with these extensions (e.g. .py, .js)')
@click.option('--exclude-empty', '-x', is_flag=True, help='Exclude files with 0 counted lines from statistics')
@click.option('--show-files', '-f', is_flag=True, help='Print per-file line counts in addition to the summary')
@click.option('--exclude-dirs', multiple=True, default=[], help='Directories to exclude (e.g. __pycache__, .git)')
@click.option('--ignore-empty-lines', is_flag=True, help='Skip empty lines when counting')
@click.option('--ignore-comments', is_flag=True, help='Skip comment lines starting with "#"')
@click.option('--algorithm', type=click.Choice(['dfs', 'bfs', 'both']), default='dfs', help='Traversal algorithm to use')
@click.option('--top', type=int, default=10, help='Number of top files by line count to display')
@click.option('--show-hidden', is_flag=True, help='Include hidden files in the analysis')
@click.option(
    '--output',
    '-o',
    type=click.Choice(['table', 'json', 'csv']),
    default='table',
    help='Output format (table/json/csv)',
)
def count(path: Path, extensions: tuple, exclude_empty: bool,
          show_files: bool, exclude_dirs: tuple, ignore_empty_lines: bool,
          ignore_comments: bool, algorithm: str, top: int, show_hidden: bool,
          output: str):
    """Count lines in files under a directory.

    PATH is the root directory to analyze (defaults to current directory).

    Examples:
      onyx count .
      onyx count src --extensions .py .js --ignore-empty-lines --ignore-comments
      onyx count . --exclude-dirs .git __pycache__ --show-files
      onyx count . --algorithm both --output json
    """
    
    # Convert extensions to a set for faster lookup
    if extensions:
        # Ensure extensions start with a dot
        extensions = set(ext if ext.startswith('.') else f'.{ext}' for ext in extensions)
    else:
        extensions = set()
    
    exclude_dirs = set(exclude_dirs) if exclude_dirs else set()
    
    if output == 'table':
        click.echo(f"📊 Analyzing: {path.absolute()}")

        if extensions:
            click.echo(f"🔍 Extensions: {', '.join(sorted(extensions))}")
        else:
            click.echo("🔍 All text files")

        if exclude_dirs:
            click.echo(f"🚫 Excluding directories: {', '.join(sorted(exclude_dirs))}")

        if ignore_empty_lines:
            click.echo("📝 Ignoring empty lines")

        if ignore_comments:
            click.echo("💬 Ignoring comment lines")

        click.echo(f"🔄 Algorithm: {algorithm.upper()}")
        click.echo()
    
    # Create line counter
    counter = LineCounter(
        extensions=extensions,
        ignore_empty_lines=ignore_empty_lines,
        ignore_comments=ignore_comments,
        ignore_patterns=list(exclude_dirs),
        show_hidden=show_hidden
    )
    
    try:
        if algorithm == 'both':
            # Run both algorithms and compare
            stats_dfs = counter.count_lines_recursive(path, "dfs")
            stats_bfs = counter.count_lines_recursive(path, "bfs")

            if output == 'table':
                click.echo("🔍 Running DFS (Depth-First Search)...")
                _print_statistics(stats_dfs, "DFS", show_files, exclude_empty, top, path)
                click.echo("🔍 Running BFS (Breadth-First Search)...")
                _print_statistics(stats_bfs, "BFS", show_files, exclude_empty, top, path)

                # Compare results
                click.echo("\n" + "=" * 60)
                click.echo("⚖️  ALGORITHM COMPARISON")
                click.echo("=" * 60)
                click.echo(f"DFS: {stats_dfs.total_files} files, {stats_dfs.total_lines:,} lines")
                click.echo(f"BFS: {stats_bfs.total_files} files, {stats_bfs.total_lines:,} lines")

                if stats_dfs.total_lines == stats_bfs.total_lines:
                    click.echo("✅ Results are identical (as expected!)")
                else:
                    click.echo("❌ Results differ (possible error)")
            else:
                # For JSON/CSV в режиме both возвращаем оба набора
                _emit_structured_stats(
                    {'DFS': stats_dfs, 'BFS': stats_bfs},
                    base_path=path,
                    exclude_empty=exclude_empty,
                    output=output,
                )

        else:
            stats = counter.count_lines_recursive(path, algorithm)
            if output == 'table':
                _print_statistics(stats, algorithm.upper(), show_files, exclude_empty, top, path)
            else:
                _emit_structured_stats(
                    {algorithm.upper(): stats},
                    base_path=path,
                    exclude_empty=exclude_empty,
                    output=output,
                )
            
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)


def _print_statistics(stats: DirectoryStats, algorithm: str, show_files: bool, 
                     exclude_empty: bool, top: int, base_path: Path):
    """Выводит статистику в красивом виде"""
    
    # Filter out empty files if requested
    files_to_show = stats.files
    if exclude_empty:
        files_to_show = [f for f in stats.files if f.lines > 0]
    
    click.echo("\n" + "=" * 60)
    click.echo(f"📊 RESULTS ({algorithm})")
    click.echo("=" * 60)


def _emit_structured_stats(all_stats: Dict[str, DirectoryStats],
                           base_path: Path,
                           exclude_empty: bool,
                           output: str) -> None:
    """Emit statistics in JSON/CSV formats for scripting usage."""
    import json as _json
    import csv as _csv
    import sys as _sys

    # Prepare structured payload per algorithm
    payload = {}
    for algo_name, stats in all_stats.items():
        files = stats.files
        if exclude_empty:
            files = [f for f in files if f.lines > 0]

        files_data = []
        for f in files:
            rel_path = str(Path(f.path).relative_to(base_path))
            files_data.append({
                'path': rel_path,
                'lines': f.lines,
                'size_bytes': f.size_bytes,
            })

        payload[algo_name] = {
            'total_files': len(files),
            'total_lines': sum(f['lines'] for f in files_data),
            'total_size_bytes': sum(f['size_bytes'] for f in files_data),
            'files': files_data,
        }

    if output == 'json':
        click.echo(_json.dumps(payload, indent=2, ensure_ascii=False))
    elif output == 'csv':
        # Flatten into rows: algorithm,path,lines,size_bytes
        fieldnames = ['algorithm', 'path', 'lines', 'size_bytes']
        writer = _csv.DictWriter(_sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        for algo_name, stats in payload.items():
            for f in stats['files']:
                writer.writerow({
                    'algorithm': algo_name,
                    'path': f['path'],
                    'lines': f['lines'],
                    'size_bytes': f['size_bytes'],
                })
    click.echo(f"📁 Total files: {len(files_to_show)}")
    click.echo(f"📄 Total lines: {sum(f.lines for f in files_to_show):,}")
    click.echo(f"💾 Total size: {format_size(sum(f.size_bytes for f in files_to_show))}")
    
    if files_to_show:
        avg_lines = sum(f.lines for f in files_to_show) / len(files_to_show)
        avg_size = sum(f.size_bytes for f in files_to_show) / len(files_to_show)
        click.echo(f"📈 Average lines per file: {avg_lines:.1f}")
        click.echo(f"📈 Average file size: {format_size(avg_size)}")
    
    # Show individual files if requested
    if show_files and files_to_show:
        click.echo(f"\n📄 Individual files:")
        sorted_files = sorted(files_to_show, key=lambda f: f.lines, reverse=True)
        
        for file_stat in sorted_files:
            relative_path = Path(file_stat.path).relative_to(base_path)
            size_str = format_size(file_stat.size_bytes)
            click.echo(f"  {file_stat.lines:>6} lines | {size_str:>8} | {relative_path}")
    
    # Show top files
    if files_to_show and len(files_to_show) > 1:
        click.echo(f"\n🏆 TOP-{min(top, len(files_to_show))} FILES BY LINE COUNT:")
        click.echo("-" * 60)
        
        top_files = sorted(files_to_show, key=lambda f: f.lines, reverse=True)[:top]
        
        for i, file_stat in enumerate(top_files, 1):
            filename = Path(file_stat.path).name
            size_str = format_size(file_stat.size_bytes)
            click.echo(f"{i:2d}. {filename:<30} {file_stat.lines:>6} lines | {size_str}")
    
    click.echo("=" * 60)