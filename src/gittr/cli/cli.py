"""Console script for gittr."""

import sys
import click
from click_plugins import with_plugins
from entrypoints import get_group_named
from gittr.cli.action import GHT


@with_plugins(get_group_named("gittr").values())
@click.group()
def cli():
    """gittr command-line-interface"""
    return 0


@cli.command("init")
@click.argument("template_url")
@click.argument("repo_path", type=click.Path(exists=False))
def init(template_url, repo_path):
    """Initialize a git project from a template url.
    This creates the repository directory,
    initializes the git repository with the gittr tracking branches,
    downloads the gittr template configuration file,
    and opens it for editing.
    """

    # Setup the GHT Repository
    GHT.init(path=repo_path, template_url=template_url)

    return 0


@cli.command("render")
@click.argument("template_url")
def render(template_url):
    """(Re)render an existing project"""

    # Setup the GHT Repository
    ght = GHT(repo_path=".", template_url=template_url)
    ght.render_tree()

    return 0
