"""
Tree command for displaying directory structure.
"""

from pathlib import Path
from typing import List, Optional
import fnmatch
import colorama
from datetime import datetime
import click


class TreeDrawer:
    """
    A class to draw a tree structure of files and directories with additional details
    such as modified time, size, and hidden files handling.

    Attributes:
        path (Path): The directory to generate the tree structure from.
        ignored_patterns (set): A list of file patterns to ignore.
        show_files (bool): Flag to show files in the tree.
        show_modified_time (bool): Flag to show last modified time for files and directories.
        show_size (bool): Flag to show the size of files and directories.
        show_hidden (bool): Flag to show hidden files (files starting with a dot).
    """

    __FORK_STRING = colorama.Fore.WHITE + '├──'
    __CORNER_STRING = colorama.Fore.WHITE + '└──'
    __WALL_STRING = colorama.Fore.WHITE + '│  '
    __SPACE_STRING = '   '

    def __init__(
            self,
            path: Path = Path('.'),
            ignored: List[str] = [],
            show_files: bool = True,
            show_modified_time: bool = False,
            show_size: bool = False,
            show_hidden: bool = False,
            max_depth: Optional[int] = None,
    ):
        """
        Initializes the TreeDrawer instance with the given options.

        Args:
            path (Path): The directory to draw the tree structure for (defaults to the current directory).
            ignored (List[str]): List of patterns for files and directories to ignore.
            show_files (bool): Whether to include files in the tree structure (default is True).
            show_modified_time (bool): Whether to show the last modified time of files (default is False).
            show_size (bool): Whether to show the size of files and directories (default is False).
            show_hidden (bool): Whether to show hidden files (default is False).
        """
        self.path = path
        self.show_files = show_files
        self.ignored_patterns = set(ignored)
        self.show_modified_time = show_modified_time
        self.show_size = show_size
        self.show_hidden = show_hidden
        # Root has depth 0, first level entries depth 1, etc.
        self.max_depth = max_depth
        colorama.init(autoreset=True)

    def _is_ignored(self, name: str) -> bool:
        """
        Check if a given file or directory should be ignored based on the ignored patterns.

        Args:
            name (str): The name of the file or directory to check.

        Returns:
            bool: True if the file or directory matches any ignored pattern, False otherwise.
        """
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.ignored_patterns)

    @staticmethod
    def _is_hidden(name: str) -> bool:
        """
        Check if a file or directory is hidden (i.e., starts with a dot).

        Args:
            name (str): The name of the file or directory to check.

        Returns:
            bool: True if the file or directory is hidden, False otherwise.
        """
        return name.startswith('.')

    @staticmethod
    def _get_size(size: int) -> str:
        """
        Convert a file size (in bytes) to a human-readable string.

        Args:
            size (int): The size of the file in bytes.

        Returns:
            str: The size formatted as bytes (B), kilobytes (KB), or megabytes (MB).
        """
        if size < 1024:
            return f'({size} B)'
        elif size < 1024 * 1024:
            return f'({size / 1024:.1f} KB)'
        else:
            return f'({size / (1024 * 1024):.1f} MB)'

    def _get_directory_size(self, path: Path) -> str:
        """
        Calculate the total size of a directory, including all files inside it.

        Args:
            path (Path): The path to the directory.

        Returns:
            str: The total size of the directory.
        """
        total_size = sum(file.stat().st_size for file in path.rglob('*') if file.is_file())
        return self._get_size(total_size)

    def _tree_structure(self, path: Path, prefix: str = '', current_depth: int = 1) -> List[str]:
        """
        Recursively build the tree structure for the specified directory.

        Args:
            path (Path): The current directory to process.
            prefix (str): The prefix to use for each line, indicating tree structure depth.

        Returns:
            List[str]: A list of strings representing the tree structure.
        """
        # Stop if we reached maximum depth
        if self.max_depth is not None and current_depth > self.max_depth:
            return []

        entries = [e for e in path.iterdir() if not self._is_ignored(e.name)]

        if not self.show_files:
            entries = [e for e in entries if e.is_dir()]

        if not self.show_hidden:
            entries = [e for e in entries if not self._is_hidden(e.name)]

        entries.sort(key=lambda x: (x.is_file(), x.name))

        result = []
        for i, entry in enumerate(entries):
            connector = self.__CORNER_STRING if i == len(entries) - 1 else self.__FORK_STRING
            if entry.is_dir():
                modified_time = datetime.fromtimestamp(entry.stat().st_mtime).strftime(
                    '%Y-%m-%d %H:%M') if self.show_modified_time else ''
                size = self._get_directory_size(entry) if self.show_size else ''
                line = f'{prefix}{connector} {colorama.Fore.BLUE}{entry.name}/'
                if modified_time or size:
                    if modified_time:
                        line += f' {colorama.Fore.WHITE}[Modified: {modified_time}]'
                    if size:
                        line += f' {colorama.Fore.WHITE}[Size: {size}]'
            else:
                line = f'{prefix}{connector} {colorama.Fore.GREEN}{entry.name}'

                if self.show_modified_time:
                    modified_time = datetime.fromtimestamp(entry.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                    line += f' {colorama.Fore.WHITE}[Modified: {modified_time}]'

                if self.show_size and entry.is_file():
                    size = self._get_size(entry.stat().st_size)
                    line += f' {colorama.Fore.WHITE}[Size: {size}]'

            result.append(line)

            if entry.is_dir():
                # Recurse into children only if depth limit allows
                child_prefix = prefix + (self.__SPACE_STRING if i == len(entries) - 1 else self.__WALL_STRING)
                result.extend(self._tree_structure(entry, child_prefix, current_depth=current_depth + 1))
        return result

    def draw(self, as_string: bool = True, save_path: Optional[Path] = None) -> str:
        """
        Generate the tree structure for the directory and print/save it.

        Args:
            as_string (bool): Whether to return the result as a string (default is True).
            save_path (Optional[Path]): If provided, the output will be saved to the specified path.

        Returns:
            str: The tree structure output as a string if `as_string` is True.
        """
        if not self.path.is_dir():
            raise ValueError('The specified path is not a directory.')

        root_modified_time = datetime.fromtimestamp(self.path.stat().st_mtime).strftime(
            '%Y-%m-%d %H:%M') if self.show_modified_time else ''
        root_size = self._get_directory_size(self.path) if self.show_size else ''

        result = [colorama.Fore.BLUE + self.path.name + '/']
        if root_modified_time or root_size:
            if root_modified_time:
                result[0] += f' {colorama.Fore.WHITE}[Modified: {root_modified_time}]'
            if root_size:
                result[0] += f' {colorama.Fore.WHITE}[Size: {root_size}]'

        # Children of root start at depth 1
        result.extend(self._tree_structure(self.path, current_depth=1))

        output = '\n'.join(result)
        if save_path:
            save_path = save_path / 'tree_structure.txt'
            with open(save_path, 'w', encoding='utf-8') as file:
                file.write(
                    output.replace(colorama.Fore.BLUE, '').replace(colorama.Fore.GREEN, '').replace(colorama.Fore.WHITE, ''))
            print(f'Tree structure saved to {save_path}')

        if as_string:
            return output
        print(output)
        return ''


@click.command()
@click.argument('path', default='.', type=click.Path(exists=True, path_type=Path))
@click.option('--max-depth', '-d', default=None, type=int, help='Maximum depth to display')
@click.option('--show-hidden', '-a', is_flag=True, help='Show hidden files and directories')
@click.option('--no-files', is_flag=True, help='Show only directories, no files')
@click.option('--show-size', '-s', is_flag=True, help='Show file and directory sizes')
@click.option('--show-time', '-t', is_flag=True, help='Show last modified time')
@click.option('--ignore', '-i', multiple=True, help='Patterns to ignore (e.g., "*.pyc", "__pycache__")')
@click.option('--save', type=click.Path(path_type=Path), help='Save tree to file')
@click.option(
    '--output',
    '-o',
    type=click.Choice(['table', 'json', 'csv']),
    default='table',
    help='Output format (table/json/csv)',
)
def tree(path: Path, max_depth: int, show_hidden: bool, no_files: bool,
         show_size: bool, show_time: bool, ignore: tuple, save: Path, output: str):
    """Display directory structure as a tree.
    
    PATH: Directory path to display (default: current directory)
    """
    
    # Convert ignore tuple to list
    ignore_patterns = list(ignore) if ignore else []
    
    # Create TreeDrawer instance
    drawer = TreeDrawer(
        path=path,
        ignored=ignore_patterns,
        show_files=not no_files,
        show_modified_time=show_time,
        show_size=show_size,
        show_hidden=show_hidden,
        max_depth=max_depth,
    )
    
    try:
        # Generate textual tree once (depth already limited in TreeDrawer)
        tree_text = drawer.draw(as_string=True)

        # Save plain-text tree if requested (no colors)
        if save:
            save_path = save / 'tree_structure.txt'
            with open(save_path, 'w', encoding='utf-8') as file:
                file.write(tree_text.replace(colorama.Fore.BLUE, '').replace(colorama.Fore.GREEN, '').replace(colorama.Fore.WHITE, ''))
            click.echo(f'Tree structure saved to {save_path}')

        # Output in requested format
        if output == 'table':
            click.echo(tree_text)
        else:
            # Build simple structured representation: level + name string per line
            records = []
            for line in tree_text.split('\n'):
                stripped = line.lstrip()
                if not stripped:
                    continue
                # Depth is approximated by count of tree characters
                depth = sum(1 for ch in line if ch in ['├', '└', '│'])
                # Strip ANSI colors
                clean = (line
                         .replace(colorama.Fore.BLUE, '')
                         .replace(colorama.Fore.GREEN, '')
                         .replace(colorama.Fore.WHITE, ''))
                records.append({'depth': depth, 'text': clean})

            if output == 'json':
                import json as _json
                click.echo(_json.dumps(records, indent=2, ensure_ascii=False))
            elif output == 'csv':
                import csv as _csv
                import sys as _sys
                writer = _csv.DictWriter(_sys.stdout, fieldnames=['depth', 'text'])
                writer.writeheader()
                writer.writerows(records)

        # Add summary statistics if show_size is enabled (printed in table mode only)
        if show_size and output == 'table':
            _print_size_summary(path, ignore_patterns, show_hidden)
                
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
    except PermissionError:
        click.echo(f"❌ Permission denied: {path}", err=True)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)


def _print_size_summary(directory: Path, ignore_patterns: list, show_hidden: bool):
    """Print summary statistics for total file sizes."""
    
    def should_ignore(path: Path) -> bool:
        """Check if path should be ignored."""
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(path.name, pattern):
                return True
        return False
    
    def is_hidden(path: Path) -> bool:
        """Check if path is hidden."""
        return path.name.startswith('.')
    
    def get_size_summary(path: Path) -> tuple:
        """Get total size and file count recursively."""
        total_size = 0
        total_files = 0
        total_dirs = 0
        
        try:
            for item in path.rglob('*'):
                # Skip if should be ignored
                if should_ignore(item):
                    continue
                
                # Skip hidden files unless show_hidden is True
                if not show_hidden and is_hidden(item):
                    continue
                
                try:
                    if item.is_file():
                        total_size += item.stat().st_size
                        total_files += 1
                    elif item.is_dir():
                        total_dirs += 1
                except (PermissionError, OSError):
                    continue
                    
        except (PermissionError, OSError):
            pass
            
        return total_size, total_files, total_dirs
    
    def format_size(size_bytes: int) -> str:
        """Format size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    total_size, total_files, total_dirs = get_size_summary(directory)
    
    click.echo("")
    click.echo("📊 " + colorama.Fore.YELLOW + "Summary Statistics:")
    click.echo(colorama.Fore.WHITE + f"   📁 Total directories: {total_dirs}")
    click.echo(colorama.Fore.WHITE + f"   📄 Total files: {total_files}")
    click.echo(colorama.Fore.WHITE + f"   💾 Total size: {format_size(total_size)}")
    
    if total_files > 0:
        avg_size = total_size / total_files
        click.echo(colorama.Fore.WHITE + f"   📈 Average file size: {format_size(avg_size)}")