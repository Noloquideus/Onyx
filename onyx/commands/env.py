"""
Environment / system information command.
"""

import os
import platform
import sys
from pathlib import Path
from typing import Dict, Any

import rich_click as click

from onyx import __version__ as ONYX_VERSION


@click.command(name="env")
@click.option(
    '--output',
    '-o',
    type=click.Choice(['table', 'json']),
    default='table',
    help='Output format (table/json)',
)
@click.option(
    '--no-env',
    is_flag=True,
    help='Do not include full environment variables (only summary)',
)
def env_cmd(output: str, no_env: bool) -> None:
    """Show a snapshot of system / Python / Onyx environment.

    Useful for bug reports and diagnostics.

    Examples:
      onyx env
      onyx env --output json --no-env
    """

    info = _collect_env_info(include_env=not no_env)

    if output == 'json':
        import json as _json
        click.echo(_json.dumps(info, indent=2, default=str))
        return

    # Human-readable table output
    _print_table(info, include_env=not no_env)


def _collect_env_info(include_env: bool) -> Dict[str, Any]:
    """Collect environment and system information."""
    # OS / platform
    uname = platform.uname()
    system = {
        'os': uname.system,
        'node': uname.node,
        'release': uname.release,
        'version': uname.version,
        'machine': uname.machine,
        'processor': uname.processor,
        'platform': sys.platform,
    }

    # Python
    python = {
        'version': platform.python_version(),
        'implementation': platform.python_implementation(),
        'executable': sys.executable,
        'prefix': sys.prefix,
    }

    # Onyx
    onyx = {
        'version': ONYX_VERSION,
        'cwd': str(Path.cwd()),
        'home': str(Path.home()),
    }

    # PATH and key vars
    env_summary = {
        'PATH': os.environ.get('PATH', ''),
        'PYTHONPATH': os.environ.get('PYTHONPATH', ''),
        'VIRTUAL_ENV': os.environ.get('VIRTUAL_ENV', ''),
        'SHELL': os.environ.get('SHELL', '') if os.name != 'nt' else os.environ.get('ComSpec', ''),
    }

    data: Dict[str, Any] = {
        'system': system,
        'python': python,
        'onyx': onyx,
        'env_summary': env_summary,
    }

    if include_env:
        # Full environment as simple dict
        data['env'] = dict(os.environ)

    return data


def _print_table(info: Dict[str, Any], include_env: bool) -> None:
    """Pretty-print environment info for humans."""
    click.echo("🧩 Onyx Environment")
    click.echo("=" * 60)

    system = info['system']
    python = info['python']
    onyx = info['onyx']
    env_summary = info['env_summary']

    click.echo("\n🖥️ System")
    click.echo(f"  OS:        {system['os']} {system['release']} ({system['version']})")
    click.echo(f"  Machine:   {system['machine']}")
    if system.get('processor'):
        click.echo(f"  CPU:       {system['processor']}")
    click.echo(f"  Platform:  {system['platform']}")

    click.echo("\n🐍 Python")
    click.echo(f"  Version:   {python['version']} ({python['implementation']})")
    click.echo(f"  Executable:{python['executable']}")
    click.echo(f"  Prefix:    {python['prefix']}")

    click.echo("\n💎 Onyx")
    click.echo(f"  Version:   {onyx['version']}")
    click.echo(f"  CWD:       {onyx['cwd']}")
    click.echo(f"  Home:      {onyx['home']}")

    click.echo("\n🌐 Env summary")
    for key, value in env_summary.items():
        if value:
            click.echo(f"  {key}: {value}")

    if include_env and 'env' in info:
        click.echo("\n📦 Full environment (key=value):")
        for k in sorted(info['env'].keys()):
            click.echo(f"  {k}={info['env'][k]}")


