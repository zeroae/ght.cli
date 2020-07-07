"""Console script for gittr."""

import sys
import click
from click_plugins import with_plugins
from entrypoints import get_group_named


@with_plugins(get_group_named("gittr").values())
@click.group()
def cli(args=None):
    """gittr command-line-interface"""
    return 0
