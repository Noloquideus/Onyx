"""
Main CLI entry point for Onyx utilities.
"""

import click
from onyx.commands import tree, count, find, backup, git, net, download, monitor
from onyx.commands.unlock import unlock


@click.group()
@click.version_option(version='0.3.3', prog_name="onyx")
def cli():
    """Onyx - Collection of useful CLI utilities."""
    pass


# Register commands
cli.add_command(tree.tree)
cli.add_command(count.count)
cli.add_command(find.find)
cli.add_command(backup.backup)
cli.add_command(git.git)
cli.add_command(net.net)
cli.add_command(download.download)
cli.add_command(monitor.monitor)
cli.add_command(unlock)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
