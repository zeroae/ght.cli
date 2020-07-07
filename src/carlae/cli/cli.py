"""Console script for carlae.cli."""

import sys
import click
from click_plugins import with_plugins
from entrypoints import get_group_named


@with_plugins(get_group_named("carlae.cli").values())
@click.group()
def cli(args=None):
    """carlae command-line-interface"""
    return 0


if __name__ == "__main__":
    sys.exit(cli)  # pragma: no cover