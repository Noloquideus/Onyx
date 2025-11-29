"""
Main CLI entry point for Onyx utilities.

This module wires all subcommands together and configures `rich-click`
for nicer, colorized help output.
"""

import rich_click as click

from onyx.commands import tree, count, find, backup, git, net, download, monitor
from onyx.commands import services
from onyx.commands.unlock import unlock
from onyx.commands.env import env_cmd
from onyx.commands.filehash import hash_cmd


# Global rich-click configuration
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.STYLE_HELPTEXT = "dim"
click.rich_click.STYLE_OPTION = "bold cyan"
click.rich_click.STYLE_SWITCH = "bold green"
click.rich_click.STYLE_METAVAR = "magenta"
click.rich_click.STYLE_USAGE = "bold"
click.rich_click.STYLE_HEADER_TEXT = "bold"
click.rich_click.STYLE_FOOTER_TEXT = "dim"
click.rich_click.MAX_WIDTH = 100


@click.group()
@click.version_option(version="0.5.1", prog_name="onyx")
def cli():
    """[bold]Onyx[/bold] — a toolbox of everyday CLI utilities.

    The top‑level command simply groups subcommands such as:

    - [cyan]tree[/cyan] — pretty directory tree
    - [cyan]find[/cyan] — fast file & content search
    - [cyan]count[/cyan] — line counter for codebases
    - [cyan]backup[/cyan] — incremental and ad‑hoc backups
    - [cyan]git[/cyan] — Git analytics and history stats
    - [cyan]net[/cyan] — networking helpers (ping, traceroute, ports)
    - [cyan]monitor[/cyan] — system and process monitoring
    - [cyan]services[/cyan] — Windows services management

    Examples:
      [dim]# Show all available subcommands[/dim]
      onyx --help

      [dim]# Get help for a specific tool[/dim]
      onyx find --help
      onyx backup create --help
    """


# Register commands
cli.add_command(tree.tree)
cli.add_command(count.count)
cli.add_command(find.find)
cli.add_command(backup.backup)
cli.add_command(git.git)
cli.add_command(net.net)
cli.add_command(download.download)
cli.add_command(monitor.monitor)
cli.add_command(services.services)
cli.add_command(unlock)
cli.add_command(env_cmd)
cli.add_command(hash_cmd)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
