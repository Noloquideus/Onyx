"""
Find command for intelligent file searching.
"""

import re
import os
import fnmatch
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import csv
import click
from dateutil import parser as date_parser


@click.group()
def find():
    """Intelligent file and content search."""
    pass


@find.command()
@click.argument('path', default='.', type=click.Path(exists=True, path_type=Path))
@click.option('--name', '-n', help='Search by filename pattern (supports wildcards)')
@click.option('--regex', '-r', help='Search by filename regex pattern')
@click.option('--size', '-s', help='Search by file size (e.g., >1MB, <500KB, =1.5GB)')
@click.option('--modified', '-m', help='Search by modification time (e.g., >2023-01-01, <7d, =today)')
@click.option('--type', '-t', type=click.Choice(['file', 'dir', 'both']), default='both', help='Search for files, directories, or both')
@click.option('--extension', '-e', multiple=True, help='Filter by file extensions (e.g., .py, .js)')
@click.option('--ignore', '-i', multiple=True, help='Patterns to ignore')
@click.option('--max-depth', '-d', type=int, help='Maximum search depth')
@click.option('--show-hidden', '-a', is_flag=True, help='Include hidden files/directories')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
@click.option('--export', type=click.Path(), help='Export results to file')
@click.option('--limit', '-l', type=int, help='Limit number of results')
def files(path: Path, name: str, regex: str, size: str, modified: str, type: str, 
         extension: tuple, ignore: tuple, max_depth: int, show_hidden: bool,
         output: str, export: str, limit: int):
    """Search for files and directories by various criteria."""
    
    click.echo(f"🔍 Searching in: {path.absolute()}")
    
    # Build search criteria
    criteria = {}
    if name:
        criteria['name'] = name
    if regex:
        criteria['regex'] = regex
    if size:
        criteria['size'] = _parse_size_criteria(size)
    if modified:
        criteria['modified'] = _parse_time_criteria(modified)
    if extension:
        criteria['extensions'] = set(ext if ext.startswith('.') else f'.{ext}' for ext in extension)
    
    ignore_patterns = set(ignore) if ignore else set()
    
    # Display search criteria
    _display_search_criteria(criteria, type, ignore_patterns, max_depth, show_hidden)
    
    try:
        results = _search_files(path, criteria, type, ignore_patterns, max_depth, show_hidden, limit)
        
        if not results:
            click.echo("❌ No files found matching the criteria.")
            return
        
        click.echo(f"\n✅ Found {len(results)} items")
        
        # Output results
        if output == 'table':
            _display_table_results(results)
        elif output == 'json':
            _display_json_results(results)
        elif output == 'csv':
            _display_csv_results(results)
        
        # Export if requested
        if export:
            _export_results(results, export, output)
            click.echo(f"📄 Results exported to: {export}")
            
    except Exception as e:
        click.echo(f"❌ Error during search: {e}", err=True)


@find.command()
@click.argument('path', default='.', type=click.Path(exists=True, path_type=Path))
@click.argument('pattern', required=True)
@click.option('--regex', '-r', is_flag=True, help='Treat pattern as regex')
@click.option('--case-sensitive', '-c', is_flag=True, help='Case sensitive search')
@click.option('--extension', '-e', multiple=True, help='Search only in files with these extensions')
@click.option('--ignore', '-i', multiple=True, help='Patterns to ignore')
@click.option('--context', '-C', type=int, default=0, help='Show N lines of context around matches')
@click.option('--max-depth', '-d', type=int, help='Maximum search depth')
@click.option('--show-hidden', '-a', is_flag=True, help='Include hidden files')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.option('--limit', '-l', type=int, help='Limit number of results')
def content(path: Path, pattern: str, regex: bool, case_sensitive: bool, extension: tuple,
           ignore: tuple, context: int, max_depth: int, show_hidden: bool, 
           output: str, limit: int):
    """Search for text content within files."""
    
    click.echo(f"🔍 Searching for: '{pattern}' in {path.absolute()}")
    
    # Prepare search pattern
    flags = 0 if case_sensitive else re.IGNORECASE
    if regex:
        try:
            search_pattern = re.compile(pattern, flags)
        except re.error as e:
            click.echo(f"❌ Invalid regex pattern: {e}", err=True)
            return
    else:
        # Escape special characters for literal search
        escaped_pattern = re.escape(pattern)
        search_pattern = re.compile(escaped_pattern, flags)
    
    # Filter extensions
    extensions = set(ext if ext.startswith('.') else f'.{ext}' for ext in extension) if extension else None
    ignore_patterns = set(ignore) if ignore else set()
    
    click.echo(f"🎯 Pattern: {pattern} ({'regex' if regex else 'literal'})")
    click.echo(f"🔤 Case sensitive: {case_sensitive}")
    if extensions:
        click.echo(f"📁 Extensions: {', '.join(sorted(extensions))}")
    if context > 0:
        click.echo(f"📝 Context lines: {context}")
    
    try:
        results = _search_content(path, search_pattern, extensions, ignore_patterns, 
                                max_depth, show_hidden, context, limit)
        
        if not results:
            click.echo("❌ No matches found.")
            return
        
        click.echo(f"\n✅ Found {len(results)} matches in {len(set(r['file'] for r in results))} files")
        
        # Output results
        if output == 'table':
            _display_content_results(results, context)
        elif output == 'json':
            click.echo(json.dumps(results, indent=2, default=str))
            
    except Exception as e:
        click.echo(f"❌ Error during content search: {e}", err=True)


def _parse_size_criteria(size_str: str) -> Dict[str, Any]:
    """Parse size criteria like '>1MB', '<500KB', '=1.5GB'."""
    pattern = r'^([><=])(\d+(?:\.\d+)?)(B|KB|MB|GB|TB)?$'
    match = re.match(pattern, size_str.upper())
    
    if not match:
        raise ValueError(f"Invalid size format: {size_str}")
    
    operator, value, unit = match.groups()
    value = float(value)
    
    # Convert to bytes
    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
    unit = unit or 'B'
    size_bytes = int(value * multipliers[unit])
    
    return {'operator': operator, 'size': size_bytes}


def _parse_time_criteria(time_str: str) -> Dict[str, Any]:
    """Parse time criteria like '>2023-01-01', '<7d', '=today'."""
    now = datetime.now()
    
    # Handle relative time (e.g., '7d', '2h', '30m')
    if time_str.lower() == 'today':
        target_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return {'operator': '=', 'time': target_time}
    
    # Check for relative time patterns
    relative_pattern = r'^([><=])(\d+)([hdwmy])$'
    match = re.match(relative_pattern, time_str.lower())
    
    if match:
        operator, value, unit = match.groups()
        value = int(value)
        
        unit_map = {
            'h': 'hours',
            'd': 'days', 
            'w': 'weeks',
            'm': 'days',  # months as 30 days
            'y': 'days'   # years as 365 days
        }
        
        if unit == 'm':
            value *= 30
        elif unit == 'y':
            value *= 365
            
        delta = timedelta(**{unit_map[unit]: value})
        target_time = now - delta
        
        return {'operator': operator, 'time': target_time}
    
    # Handle absolute dates
    operator = time_str[0] if time_str[0] in '><=' else '='
    date_str = time_str[1:] if operator in '><=' else time_str
    
    try:
        target_time = date_parser.parse(date_str)
        return {'operator': operator, 'time': target_time}
    except Exception:
        raise ValueError(f"Invalid time format: {time_str}")


def _search_files(path: Path, criteria: Dict, search_type: str, ignore_patterns: set,
                 max_depth: int, show_hidden: bool, limit: int) -> List[Dict]:
    """Search for files based on criteria."""
    results = []
    current_depth = 0
    
    def _should_ignore(item_path: Path) -> bool:
        """Check if path should be ignored."""
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(item_path.name, pattern):
                return True
        return False
    
    def _matches_criteria(item_path: Path) -> bool:
        """Check if item matches all criteria."""
        try:
            stat = item_path.stat()
            
            # Name criteria
            if 'name' in criteria:
                if not fnmatch.fnmatch(item_path.name, criteria['name']):
                    return False
            
            # Regex criteria
            if 'regex' in criteria:
                if not re.search(criteria['regex'], item_path.name):
                    return False
            
            # Size criteria (only for files)
            if 'size' in criteria and item_path.is_file():
                size_crit = criteria['size']
                file_size = stat.st_size
                
                if size_crit['operator'] == '>':
                    if file_size <= size_crit['size']:
                        return False
                elif size_crit['operator'] == '<':
                    if file_size >= size_crit['size']:
                        return False
                elif size_crit['operator'] == '=':
                    if abs(file_size - size_crit['size']) > size_crit['size'] * 0.1:  # 10% tolerance
                        return False
            
            # Modified time criteria
            if 'modified' in criteria:
                mod_crit = criteria['modified']
                mod_time = datetime.fromtimestamp(stat.st_mtime)
                
                if mod_crit['operator'] == '>':
                    if mod_time <= mod_crit['time']:
                        return False
                elif mod_crit['operator'] == '<':
                    if mod_time >= mod_crit['time']:
                        return False
                elif mod_crit['operator'] == '=':
                    # Same day
                    if mod_time.date() != mod_crit['time'].date():
                        return False
            
            # Extension criteria (only for files)
            if 'extensions' in criteria and item_path.is_file():
                if item_path.suffix.lower() not in criteria['extensions']:
                    return False
            
            return True
            
        except (OSError, PermissionError):
            return False
    
    def _search_recursive(current_path: Path, depth: int):
        """Recursively search directories."""
        if max_depth is not None and depth > max_depth:
            return
        
        if limit and len(results) >= limit:
            return
        
        try:
            for item in current_path.iterdir():
                if limit and len(results) >= limit:
                    break
                
                # Skip hidden files unless requested
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                # Skip ignored patterns
                if _should_ignore(item):
                    continue
                
                # Check type filter
                if search_type == 'file' and not item.is_file():
                    continue
                elif search_type == 'dir' and not item.is_dir():
                    continue
                
                # Check if matches criteria
                if _matches_criteria(item):
                    try:
                        stat = item.stat()
                        results.append({
                            'path': str(item),
                            'name': item.name,
                            'type': 'file' if item.is_file() else 'directory',
                            'size': stat.st_size if item.is_file() else None,
                            'modified': datetime.fromtimestamp(stat.st_mtime),
                            'permissions': oct(stat.st_mode)[-3:],
                        })
                    except (OSError, PermissionError):
                        pass
                
                # Recurse into directories
                if item.is_dir():
                    _search_recursive(item, depth + 1)
                    
        except (OSError, PermissionError):
            pass
    
    _search_recursive(path, 0)
    return results


def _search_content(path: Path, pattern: re.Pattern, extensions: set, ignore_patterns: set,
                   max_depth: int, show_hidden: bool, context: int, limit: int) -> List[Dict]:
    """Search for content within files."""
    results = []
    
    def _should_ignore(item_path: Path) -> bool:
        """Check if path should be ignored."""
        for ignore_pattern in ignore_patterns:
            if fnmatch.fnmatch(item_path.name, ignore_pattern):
                return True
        return False
    
    def _search_file_content(file_path: Path):
        """Search content within a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                if limit and len(results) >= limit:
                    break
                
                match = pattern.search(line)
                if match:
                    result = {
                        'file': str(file_path),
                        'line': line_num,
                        'content': line.rstrip(),
                        'match_start': match.start(),
                        'match_end': match.end(),
                        'match_text': match.group()
                    }
                    
                    # Add context if requested
                    if context > 0:
                        start_line = max(0, line_num - context - 1)
                        end_line = min(len(lines), line_num + context)
                        result['context'] = [
                            {
                                'line': i + start_line + 1,
                                'content': lines[i + start_line].rstrip()
                            }
                            for i in range(end_line - start_line)
                        ]
                    
                    results.append(result)
                    
        except (OSError, PermissionError, UnicodeDecodeError):
            pass
    
    def _search_recursive(current_path: Path, depth: int):
        """Recursively search directories."""
        if max_depth is not None and depth > max_depth:
            return
        
        if limit and len(results) >= limit:
            return
        
        try:
            for item in current_path.iterdir():
                if limit and len(results) >= limit:
                    break
                
                # Skip hidden files unless requested
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                # Skip ignored patterns
                if _should_ignore(item):
                    continue
                
                if item.is_file():
                    # Check extension filter
                    if extensions and item.suffix.lower() not in extensions:
                        continue
                    
                    _search_file_content(item)
                    
                elif item.is_dir():
                    _search_recursive(item, depth + 1)
                    
        except (OSError, PermissionError):
            pass
    
    _search_recursive(path, 0)
    return results


def _display_search_criteria(criteria: Dict, search_type: str, ignore_patterns: set, 
                           max_depth: int, show_hidden: bool):
    """Display search criteria."""
    click.echo("🎯 Search criteria:")
    
    if 'name' in criteria:
        click.echo(f"   📝 Name pattern: {criteria['name']}")
    if 'regex' in criteria:
        click.echo(f"   🔤 Regex pattern: {criteria['regex']}")
    if 'size' in criteria:
        size_crit = criteria['size']
        click.echo(f"   📏 Size: {size_crit['operator']}{_format_bytes(size_crit['size'])}")
    if 'modified' in criteria:
        mod_crit = criteria['modified']
        click.echo(f"   📅 Modified: {mod_crit['operator']}{mod_crit['time'].strftime('%Y-%m-%d %H:%M')}")
    if 'extensions' in criteria:
        click.echo(f"   📁 Extensions: {', '.join(sorted(criteria['extensions']))}")
    
    click.echo(f"   🔍 Type: {search_type}")
    if ignore_patterns:
        click.echo(f"   🚫 Ignore: {', '.join(ignore_patterns)}")
    if max_depth is not None:
        click.echo(f"   📊 Max depth: {max_depth}")
    click.echo(f"   👁️ Hidden files: {'yes' if show_hidden else 'no'}")
    click.echo()


def _display_table_results(results: List[Dict]):
    """Display results in table format."""
    for result in results:
        icon = "📄" if result['type'] == 'file' else "📁"
        size_str = _format_bytes(result['size']) if result['size'] is not None else ""
        mod_time = result['modified'].strftime('%Y-%m-%d %H:%M')
        
        click.echo(f"{icon} {result['name']}")
        click.echo(f"   📍 Path: {result['path']}")
        if result['size'] is not None:
            click.echo(f"   📏 Size: {size_str}")
        click.echo(f"   📅 Modified: {mod_time}")
        click.echo(f"   🔐 Permissions: {result['permissions']}")
        click.echo()


def _display_json_results(results: List[Dict]):
    """Display results in JSON format."""
    click.echo(json.dumps(results, indent=2, default=str))


def _display_csv_results(results: List[Dict]):
    """Display results in CSV format."""
    if not results:
        return
    
    import io
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)
    click.echo(output.getvalue())


def _display_content_results(results: List[Dict], context: int):
    """Display content search results."""
    current_file = None
    
    for result in results:
        if result['file'] != current_file:
            current_file = result['file']
            click.echo(f"\n📄 {current_file}")
            click.echo("─" * 50)
        
        line_num = result['line']
        content = result['content']
        match_start = result['match_start']
        match_end = result['match_end']
        
        # Highlight the match
        highlighted = (
            content[:match_start] + 
            click.style(content[match_start:match_end], fg='yellow', bold=True) +
            content[match_end:]
        )
        
        click.echo(f"{line_num:4d}: {highlighted}")
        
        # Show context if available
        if context > 0 and 'context' in result:
            for ctx in result['context']:
                if ctx['line'] != line_num:  # Don't repeat the match line
                    style = 'dim' if abs(ctx['line'] - line_num) > 1 else None
                    click.echo(f"{ctx['line']:4d}: {ctx['content']}", color=style)


def _export_results(results: List[Dict], export_path: str, format_type: str):
    """Export results to file."""
    export_file = Path(export_path)
    
    if format_type == 'json':
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
    elif format_type == 'csv':
        with open(export_file, 'w', newline='', encoding='utf-8') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)


def _format_bytes(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"
