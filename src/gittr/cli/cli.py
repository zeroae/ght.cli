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
@click.argument("repository-path", type=click.Path(exists=False))
@click.argument("template-url")
def init(repository_path, template_url):
    """Initialize a git project from a template url.
    This creates the repository directory,
    initializes the git repository with the gittr tracking branches,
    downloads the gittr template configuration file,
    and opens it for editing.
    """

    # Setup the GHT Repository
    _ = GHT.init(path=repository_path, template_url=template_url)

    return 0


@cli.command("render")
@click.argument("template_url")
def render(template_url):
    """(Re)render an existing project"""

    # Setup the GHT Repository
    ght = GHT(repo_path=".", template_url=template_url)
    ght.load_config()
    ght.fetch_template()
    ght.render_tree()

    return 0
