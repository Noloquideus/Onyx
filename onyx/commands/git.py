"""
Git analytics command for repository analysis.
"""

import os
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import click
from git import Repo, InvalidGitRepositoryError
from git.objects import Commit


@click.group()
def git():
    """Git repository analytics and statistics."""
    pass


@git.command()
@click.argument('repo_path', default='.', type=click.Path(exists=True, path_type=Path))
@click.option('--author', '-a', help='Filter by specific author')
@click.option('--since', '-s', help='Since date (YYYY-MM-DD or relative like "1 week ago")')
@click.option('--until', '-u', help='Until date (YYYY-MM-DD)')
@click.option('--branch', '-b', help='Analyze specific branch (default: current branch)')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.option('--limit', '-l', type=int, default=1000, help='Limit number of commits to analyze')
def commits(repo_path: Path, author: str, since: str, until: str, branch: str, 
           output: str, limit: int):
    """Analyze commit statistics and patterns."""
    
    try:
        repo = Repo(repo_path)
        
        if repo.bare:
            click.echo("❌ Cannot analyze bare repository", err=True)
            return
        
        click.echo(f"📊 Analyzing commits in: {repo_path.absolute()}")
        click.echo(f"🔍 Repository: {repo.git_dir}")
        
        # Get branch info
        if branch:
            try:
                current_branch = repo.heads[branch]
            except IndexError:
                click.echo(f"❌ Branch '{branch}' not found", err=True)
                return
        else:
            current_branch = repo.active_branch
            branch = current_branch.name
        
        click.echo(f"🌿 Branch: {branch}")
        
        # Parse date filters
        since_date = _parse_date(since) if since else None
        until_date = _parse_date(until) if until else None
        
        if since_date:
            click.echo(f"📅 Since: {since_date.strftime('%Y-%m-%d')}")
        if until_date:
            click.echo(f"📅 Until: {until_date.strftime('%Y-%m-%d')}")
        if author:
            click.echo(f"👤 Author: {author}")
        
        # Collect commits
        commits_iter = repo.iter_commits(
            rev=current_branch,
            author=author,
            since=since_date,
            until=until_date,
            max_count=limit
        )
        
        commits_data = []
        with click.progressbar(commits_iter, label='Analyzing commits', 
                             length=min(limit, 100)) as bar:
            for commit in bar:
                commits_data.append(_analyze_commit(commit))
        
        if not commits_data:
            click.echo("❌ No commits found matching criteria")
            return
        
        # Analyze statistics
        stats = _calculate_commit_stats(commits_data)
        
        # Output results
        if output == 'table':
            _display_commit_stats(stats, commits_data[:10])  # Show top 10 commits
        elif output == 'json':
            click.echo(json.dumps({
                'statistics': stats,
                'commits': commits_data
            }, indent=2, default=str))
        
    except InvalidGitRepositoryError:
        click.echo("❌ Not a valid Git repository", err=True)
    except Exception as e:
        click.echo(f"❌ Error analyzing commits: {e}", err=True)


@git.command()
@click.argument('repo_path', default='.', type=click.Path(exists=True, path_type=Path))
@click.option('--since', '-s', help='Since date (YYYY-MM-DD or relative)')
@click.option('--until', '-u', help='Until date (YYYY-MM-DD)')
@click.option('--min-commits', '-m', type=int, default=1, help='Minimum commits to include author')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.option('--top', '-t', type=int, default=10, help='Show top N authors')
def authors(repo_path: Path, since: str, until: str, min_commits: int, output: str, top: int):
    """Analyze author statistics and contributions."""
    
    try:
        repo = Repo(repo_path)
        
        click.echo(f"👥 Analyzing authors in: {repo_path.absolute()}")
        
        # Parse date filters
        since_date = _parse_date(since) if since else None
        until_date = _parse_date(until) if until else None
        
        # Collect commits by author
        commits_iter = repo.iter_commits(
            since=since_date,
            until=until_date
        )
        
        author_stats = defaultdict(lambda: {
            'commits': 0,
            'lines_added': 0,
            'lines_deleted': 0,
            'files_changed': set(),
            'first_commit': None,
            'last_commit': None,
            'commit_times': [],
            'commits_by_day': defaultdict(int)
        })
        
        total_commits = 0
        
        with click.progressbar(commits_iter, label='Analyzing authors') as bar:
            for commit in bar:
                author_name = commit.author.name
                author_email = commit.author.email
                author_key = f"{author_name} <{author_email}>"
                
                stats = author_stats[author_key]
                stats['commits'] += 1
                stats['commit_times'].append(commit.committed_datetime)
                
                # Track first and last commits
                if stats['first_commit'] is None or commit.committed_datetime < stats['first_commit']:
                    stats['first_commit'] = commit.committed_datetime
                if stats['last_commit'] is None or commit.committed_datetime > stats['last_commit']:
                    stats['last_commit'] = commit.committed_datetime
                
                # Count commits by day of week
                day_name = commit.committed_datetime.strftime('%A')
                stats['commits_by_day'][day_name] += 1
                
                # Calculate line changes
                try:
                    if commit.parents:
                        diffs = commit.parents[0].diff(commit, create_patch=True)
                        for diff in diffs:
                            if diff.a_path:
                                stats['files_changed'].add(diff.a_path)
                            if diff.b_path:
                                stats['files_changed'].add(diff.b_path)
                            
                            # Count line changes
                            if hasattr(diff, 'diff') and diff.diff:
                                diff_text = diff.diff.decode('utf-8', errors='ignore')
                                lines_added = diff_text.count('\n+') - 1  # Exclude header
                                lines_deleted = diff_text.count('\n-') - 1  # Exclude header
                                stats['lines_added'] += max(0, lines_added)
                                stats['lines_deleted'] += max(0, lines_deleted)
                except Exception:
                    pass  # Skip if diff calculation fails
                
                total_commits += 1
        
        # Filter by minimum commits
        filtered_authors = {
            author: stats for author, stats in author_stats.items()
            if stats['commits'] >= min_commits
        }
        
        if not filtered_authors:
            click.echo("❌ No authors found matching criteria")
            return
        
        # Sort by number of commits
        sorted_authors = sorted(
            filtered_authors.items(),
            key=lambda x: x[1]['commits'],
            reverse=True
        )[:top]
        
        # Prepare output data
        authors_data = []
        for author, stats in sorted_authors:
            # Convert sets to lists for JSON serialization
            stats['files_changed'] = list(stats['files_changed'])
            stats['total_files'] = len(stats['files_changed'])
            
            authors_data.append({
                'author': author,
                'stats': stats
            })
        
        # Output results
        if output == 'table':
            _display_author_stats(authors_data, total_commits)
        elif output == 'json':
            click.echo(json.dumps(authors_data, indent=2, default=str))
        
    except InvalidGitRepositoryError:
        click.echo("❌ Not a valid Git repository", err=True)
    except Exception as e:
        click.echo(f"❌ Error analyzing authors: {e}", err=True)


@git.command()
@click.argument('repo_path', default='.', type=click.Path(exists=True, path_type=Path))
@click.option('--since', '-s', help='Since date (YYYY-MM-DD or relative)')
@click.option('--until', '-u', help='Until date (YYYY-MM-DD)')
@click.option('--file-pattern', '-f', help='Filter files by pattern (e.g., "*.py")')
@click.option('--top', '-t', type=int, default=20, help='Show top N files')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
def files(repo_path: Path, since: str, until: str, file_pattern: str, top: int, output: str):
    """Analyze file change statistics."""
    
    try:
        repo = Repo(repo_path)
        
        click.echo(f"📁 Analyzing file changes in: {repo_path.absolute()}")
        
        # Parse date filters
        since_date = _parse_date(since) if since else None
        until_date = _parse_date(until) if until else None
        
        # Collect file statistics
        file_stats = defaultdict(lambda: {
            'commits': 0,
            'lines_added': 0,
            'lines_deleted': 0,
            'authors': set(),
            'first_change': None,
            'last_change': None
        })
        
        commits_iter = repo.iter_commits(
            since=since_date,
            until=until_date
        )
        
        with click.progressbar(commits_iter, label='Analyzing file changes') as bar:
            for commit in bar:
                try:
                    if commit.parents:
                        diffs = commit.parents[0].diff(commit, create_patch=True)
                        
                        for diff in diffs:
                            file_path = diff.b_path or diff.a_path
                            
                            if not file_path:
                                continue
                            
                            # Apply file pattern filter
                            if file_pattern and not _match_pattern(file_path, file_pattern):
                                continue
                            
                            stats = file_stats[file_path]
                            stats['commits'] += 1
                            stats['authors'].add(commit.author.name)
                            
                            # Track first and last changes
                            if stats['first_change'] is None or commit.committed_datetime < stats['first_change']:
                                stats['first_change'] = commit.committed_datetime
                            if stats['last_change'] is None or commit.committed_datetime > stats['last_change']:
                                stats['last_change'] = commit.committed_datetime
                            
                            # Count line changes
                            if hasattr(diff, 'diff') and diff.diff:
                                diff_text = diff.diff.decode('utf-8', errors='ignore')
                                lines_added = diff_text.count('\n+') - 1
                                lines_deleted = diff_text.count('\n-') - 1
                                stats['lines_added'] += max(0, lines_added)
                                stats['lines_deleted'] += max(0, lines_deleted)
                                
                except Exception:
                    continue
        
        if not file_stats:
            click.echo("❌ No file changes found")
            return
        
        # Sort by number of commits
        sorted_files = sorted(
            file_stats.items(),
            key=lambda x: x[1]['commits'],
            reverse=True
        )[:top]
        
        # Prepare output data
        files_data = []
        for file_path, stats in sorted_files:
            stats['authors'] = list(stats['authors'])
            stats['total_authors'] = len(stats['authors'])
            stats['total_lines_changed'] = stats['lines_added'] + stats['lines_deleted']
            
            files_data.append({
                'file': file_path,
                'stats': stats
            })
        
        # Output results
        if output == 'table':
            _display_file_stats(files_data)
        elif output == 'json':
            click.echo(json.dumps(files_data, indent=2, default=str))
        
    except InvalidGitRepositoryError:
        click.echo("❌ Not a valid Git repository", err=True)
    except Exception as e:
        click.echo(f"❌ Error analyzing files: {e}", err=True)


@git.command()
@click.argument('repo_path', default='.', type=click.Path(exists=True, path_type=Path))
@click.option('--threshold', '-t', type=str, default='10MB', help='Size threshold (e.g., 10MB, 1GB)')
@click.option('--current-only', '-c', is_flag=True, help='Check only current working tree')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
def large_files(repo_path: Path, threshold: str, current_only: bool, output: str):
    """Find large files in repository history."""
    
    try:
        repo = Repo(repo_path)
        
        click.echo(f"🔍 Searching for large files in: {repo_path.absolute()}")
        
        # Parse threshold
        threshold_bytes = _parse_size_threshold(threshold)
        click.echo(f"📏 Size threshold: {threshold}")
        
        large_files = []
        
        if current_only:
            # Check only current working tree
            for item in repo_path.rglob('*'):
                if item.is_file():
                    try:
                        size = item.stat().st_size
                        if size >= threshold_bytes:
                            relative_path = item.relative_to(repo_path)
                            large_files.append({
                                'file': str(relative_path),
                                'size': size,
                                'location': 'working_tree',
                                'commit': None
                            })
                    except (OSError, ValueError):
                        continue
        else:
            # Check entire history
            processed_blobs = set()
            
            with click.progressbar(repo.iter_commits(), label='Scanning history') as bar:
                for commit in bar:
                    try:
                        for item in commit.tree.traverse():
                            if item.type == 'blob' and item.hexsha not in processed_blobs:
                                processed_blobs.add(item.hexsha)
                                
                                if item.size >= threshold_bytes:
                                    large_files.append({
                                        'file': item.path,
                                        'size': item.size,
                                        'location': 'history',
                                        'commit': commit.hexsha[:8],
                                        'commit_date': commit.committed_datetime,
                                        'author': commit.author.name
                                    })
                    except Exception:
                        continue
        
        if not large_files:
            click.echo(f"✅ No files larger than {threshold} found")
            return
        
        # Sort by size
        large_files.sort(key=lambda x: x['size'], reverse=True)
        
        # Output results
        if output == 'table':
            _display_large_files(large_files)
        elif output == 'json':
            click.echo(json.dumps(large_files, indent=2, default=str))
        
    except InvalidGitRepositoryError:
        click.echo("❌ Not a valid Git repository", err=True)
    except Exception as e:
        click.echo(f"❌ Error finding large files: {e}", err=True)


@git.command()
@click.argument('repo_path', default='.', type=click.Path(exists=True, path_type=Path))
@click.option('--period', '-p', type=click.Choice(['day', 'week', 'month']), default='week', help='Activity period')
@click.option('--last', '-l', type=int, default=12, help='Number of periods to show')
@click.option('--author', '-a', help='Filter by specific author')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'chart']), default='table', help='Output format')
def activity(repo_path: Path, period: str, last: int, author: str, output: str):
    """Show repository activity over time."""
    
    try:
        repo = Repo(repo_path)
        
        click.echo(f"📈 Analyzing activity in: {repo_path.absolute()}")
        click.echo(f"📊 Period: {period} (last {last} {period}s)")
        
        if author:
            click.echo(f"👤 Author: {author}")
        
        # Calculate time periods
        now = datetime.now()
        periods = []
        
        for i in range(last):
            if period == 'day':
                end_date = now - timedelta(days=i)
                start_date = end_date - timedelta(days=1)
                period_label = end_date.strftime('%Y-%m-%d')
            elif period == 'week':
                end_date = now - timedelta(weeks=i)
                start_date = end_date - timedelta(weeks=1)
                period_label = f"Week {end_date.strftime('%Y-%W')}"
            elif period == 'month':
                end_date = now.replace(day=1) - timedelta(days=i*30)
                start_date = end_date - timedelta(days=30)
                period_label = end_date.strftime('%Y-%m')
            
            periods.append({
                'label': period_label,
                'start': start_date,
                'end': end_date,
                'commits': 0,
                'lines_added': 0,
                'lines_deleted': 0,
                'files_changed': set(),
                'authors': set()
            })
        
        # Analyze commits by period
        commits_iter = repo.iter_commits(author=author)
        
        with click.progressbar(commits_iter, label='Analyzing activity') as bar:
            for commit in bar:
                commit_date = commit.committed_datetime.replace(tzinfo=None)
                
                # Find matching period
                for period_data in periods:
                    if period_data['start'] <= commit_date <= period_data['end']:
                        period_data['commits'] += 1
                        period_data['authors'].add(commit.author.name)
                        
                        # Calculate line changes
                        try:
                            if commit.parents:
                                diffs = commit.parents[0].diff(commit, create_patch=True)
                                for diff in diffs:
                                    if diff.a_path:
                                        period_data['files_changed'].add(diff.a_path)
                                    if diff.b_path:
                                        period_data['files_changed'].add(diff.b_path)
                                    
                                    if hasattr(diff, 'diff') and diff.diff:
                                        diff_text = diff.diff.decode('utf-8', errors='ignore')
                                        lines_added = diff_text.count('\n+') - 1
                                        lines_deleted = diff_text.count('\n-') - 1
                                        period_data['lines_added'] += max(0, lines_added)
                                        period_data['lines_deleted'] += max(0, lines_deleted)
                        except Exception:
                            pass
                        break
        
        # Convert sets to counts for output
        for period_data in periods:
            period_data['files_changed'] = len(period_data['files_changed'])
            period_data['authors'] = len(period_data['authors'])
        
        # Output results
        if output == 'table':
            _display_activity_stats(periods)
        elif output == 'json':
            click.echo(json.dumps(periods, indent=2, default=str))
        elif output == 'chart':
            _display_activity_chart(periods)
        
    except InvalidGitRepositoryError:
        click.echo("❌ Not a valid Git repository", err=True)
    except Exception as e:
        click.echo(f"❌ Error analyzing activity: {e}", err=True)


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string with support for relative dates."""
    if not date_str:
        return None
    
    # Handle relative dates
    if 'ago' in date_str.lower():
        parts = date_str.lower().split()
        if len(parts) >= 3:
            try:
                amount = int(parts[0])
                unit = parts[1]
                
                if 'day' in unit:
                    return datetime.now() - timedelta(days=amount)
                elif 'week' in unit:
                    return datetime.now() - timedelta(weeks=amount)
                elif 'month' in unit:
                    return datetime.now() - timedelta(days=amount * 30)
                elif 'year' in unit:
                    return datetime.now() - timedelta(days=amount * 365)
            except ValueError:
                pass
    
    # Handle absolute dates
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            click.echo(f"⚠️ Cannot parse date: {date_str}")
            return None


def _parse_size_threshold(size_str: str) -> int:
    """Parse size threshold string to bytes."""
    size_str = size_str.upper()
    
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4
    }
    
    for unit, multiplier in multipliers.items():
        if size_str.endswith(unit):
            try:
                value = float(size_str[:-len(unit)])
                return int(value * multiplier)
            except ValueError:
                break
    
    # Default to bytes if no unit specified
    try:
        return int(size_str)
    except ValueError:
        raise ValueError(f"Invalid size format: {size_str}")


def _match_pattern(file_path: str, pattern: str) -> bool:
    """Check if file path matches pattern."""
    import fnmatch
    return fnmatch.fnmatch(file_path, pattern)


def _analyze_commit(commit: Commit) -> Dict:
    """Analyze a single commit."""
    return {
        'hash': commit.hexsha[:8],
        'author': commit.author.name,
        'email': commit.author.email,
        'date': commit.committed_datetime,
        'message': commit.message.strip(),
        'files_changed': len(commit.stats.files),
        'lines_added': commit.stats.total['insertions'],
        'lines_deleted': commit.stats.total['deletions'],
        'total_lines': commit.stats.total['lines']
    }


def _calculate_commit_stats(commits: List[Dict]) -> Dict:
    """Calculate overall commit statistics."""
    if not commits:
        return {}
    
    total_commits = len(commits)
    total_files = sum(c['files_changed'] for c in commits)
    total_lines_added = sum(c['lines_added'] for c in commits)
    total_lines_deleted = sum(c['lines_deleted'] for c in commits)
    
    # Authors
    authors = Counter(c['author'] for c in commits)
    
    # Time analysis
    dates = [c['date'].date() for c in commits]
    first_commit = min(dates)
    last_commit = max(dates)
    days_active = (last_commit - first_commit).days + 1
    
    # Commits per day of week
    days_of_week = Counter(c['date'].strftime('%A') for c in commits)
    
    # Commits per hour
    hours = Counter(c['date'].hour for c in commits)
    
    return {
        'total_commits': total_commits,
        'total_files_changed': total_files,
        'total_lines_added': total_lines_added,
        'total_lines_deleted': total_lines_deleted,
        'total_lines_changed': total_lines_added + total_lines_deleted,
        'unique_authors': len(authors),
        'most_active_author': authors.most_common(1)[0],
        'period': f"{first_commit} to {last_commit}",
        'days_active': days_active,
        'avg_commits_per_day': round(total_commits / days_active, 2),
        'avg_files_per_commit': round(total_files / total_commits, 2),
        'most_active_day': days_of_week.most_common(1)[0],
        'most_active_hour': hours.most_common(1)[0]
    }


def _display_commit_stats(stats: Dict, recent_commits: List[Dict]):
    """Display commit statistics in table format."""
    click.echo("\n📊 " + "=" * 60)
    click.echo("📊 COMMIT STATISTICS")
    click.echo("📊 " + "=" * 60)
    
    click.echo(f"📈 Total commits: {stats['total_commits']:,}")
    click.echo(f"👥 Unique authors: {stats['unique_authors']}")
    click.echo(f"📁 Total files changed: {stats['total_files_changed']:,}")
    click.echo(f"➕ Lines added: {stats['total_lines_added']:,}")
    click.echo(f"➖ Lines deleted: {stats['total_lines_deleted']:,}")
    click.echo(f"📝 Total line changes: {stats['total_lines_changed']:,}")
    click.echo(f"📅 Period: {stats['period']}")
    click.echo(f"📊 Average commits/day: {stats['avg_commits_per_day']}")
    click.echo(f"📄 Average files/commit: {stats['avg_files_per_commit']}")
    click.echo(f"🏆 Most active author: {stats['most_active_author'][0]} ({stats['most_active_author'][1]} commits)")
    click.echo(f"📅 Most active day: {stats['most_active_day'][0]} ({stats['most_active_day'][1]} commits)")
    click.echo(f"🕐 Most active hour: {stats['most_active_hour'][0]}:00 ({stats['most_active_hour'][1]} commits)")
    
    if recent_commits:
        click.echo(f"\n🔥 Recent commits:")
        click.echo("-" * 60)
        for commit in recent_commits:
            date_str = commit['date'].strftime('%Y-%m-%d %H:%M')
            click.echo(f"{commit['hash']} | {date_str} | {commit['author']}")
            click.echo(f"   📝 {commit['message'][:50]}{'...' if len(commit['message']) > 50 else ''}")
            click.echo(f"   📊 {commit['files_changed']} files, +{commit['lines_added']}/-{commit['lines_deleted']} lines")
            click.echo()


def _display_author_stats(authors_data: List[Dict], total_commits: int):
    """Display author statistics in table format."""
    click.echo("\n👥 " + "=" * 60)
    click.echo("👥 AUTHOR STATISTICS")
    click.echo("👥 " + "=" * 60)
    
    for i, author_data in enumerate(authors_data, 1):
        author = author_data['author']
        stats = author_data['stats']
        
        percentage = (stats['commits'] / total_commits) * 100
        
        click.echo(f"\n{i}. {author}")
        click.echo(f"   📈 Commits: {stats['commits']} ({percentage:.1f}%)")
        click.echo(f"   📁 Files changed: {stats['total_files']}")
        click.echo(f"   ➕ Lines added: {stats['lines_added']:,}")
        click.echo(f"   ➖ Lines deleted: {stats['lines_deleted']:,}")
        
        if stats['first_commit'] and stats['last_commit']:
            period = (stats['last_commit'] - stats['first_commit']).days
            click.echo(f"   📅 Active period: {period} days")
        
        # Most active day
        if stats['commits_by_day']:
            most_active = max(stats['commits_by_day'].items(), key=lambda x: x[1])
            click.echo(f"   📅 Favorite day: {most_active[0]} ({most_active[1]} commits)")


def _display_file_stats(files_data: List[Dict]):
    """Display file statistics in table format."""
    click.echo("\n📁 " + "=" * 60)
    click.echo("📁 FILE CHANGE STATISTICS")
    click.echo("📁 " + "=" * 60)
    
    for i, file_data in enumerate(files_data, 1):
        file_path = file_data['file']
        stats = file_data['stats']
        
        click.echo(f"\n{i}. {file_path}")
        click.echo(f"   📈 Commits: {stats['commits']}")
        click.echo(f"   👥 Authors: {stats['total_authors']}")
        click.echo(f"   ➕ Lines added: {stats['lines_added']:,}")
        click.echo(f"   ➖ Lines deleted: {stats['lines_deleted']:,}")
        click.echo(f"   📝 Total changes: {stats['total_lines_changed']:,}")
        
        if stats['first_change'] and stats['last_change']:
            click.echo(f"   📅 First changed: {stats['first_change'].strftime('%Y-%m-%d')}")
            click.echo(f"   📅 Last changed: {stats['last_change'].strftime('%Y-%m-%d')}")


def _display_large_files(large_files: List[Dict]):
    """Display large files in table format."""
    click.echo("\n💾 " + "=" * 60)
    click.echo("💾 LARGE FILES")
    click.echo("💾 " + "=" * 60)
    
    for i, file_data in enumerate(large_files, 1):
        size_str = _format_bytes(file_data['size'])
        click.echo(f"\n{i}. {file_data['file']}")
        click.echo(f"   📏 Size: {size_str}")
        click.echo(f"   📍 Location: {file_data['location']}")
        
        if file_data.get('commit'):
            click.echo(f"   🔗 Commit: {file_data['commit']}")
            click.echo(f"   👤 Author: {file_data['author']}")
            click.echo(f"   📅 Date: {file_data['commit_date'].strftime('%Y-%m-%d')}")


def _display_activity_stats(periods: List[Dict]):
    """Display activity statistics in table format."""
    click.echo("\n📈 " + "=" * 60)
    click.echo("📈 ACTIVITY STATISTICS")
    click.echo("📈 " + "=" * 60)
    
    for period_data in reversed(periods):  # Show oldest first
        click.echo(f"\n📅 {period_data['label']}")
        click.echo(f"   📈 Commits: {period_data['commits']}")
        click.echo(f"   👥 Authors: {period_data['authors']}")
        click.echo(f"   📁 Files changed: {period_data['files_changed']}")
        click.echo(f"   ➕ Lines added: {period_data['lines_added']:,}")
        click.echo(f"   ➖ Lines deleted: {period_data['lines_deleted']:,}")


def _display_activity_chart(periods: List[Dict]):
    """Display activity as a simple ASCII chart."""
    click.echo("\n📊 ACTIVITY CHART")
    click.echo("=" * 60)
    
    max_commits = max(p['commits'] for p in periods) or 1
    chart_width = 40
    
    for period_data in reversed(periods):
        bar_length = int((period_data['commits'] / max_commits) * chart_width)
        bar = '█' * bar_length + '░' * (chart_width - bar_length)
        
        click.echo(f"{period_data['label'][:12]:>12} |{bar}| {period_data['commits']}")


def _format_bytes(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"
