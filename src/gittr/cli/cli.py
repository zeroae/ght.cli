"""Console script for gittr."""

from contextlib import contextmanager

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


@cli.command("configure")
@click.argument("repo-path", default=".", type=click.Path(file_okay=False, exists=True))
def configure(repo_path):
    """Edit an existing template configuration file

    A git commit is created if the file is modified.
    """
    import os

    # Find the configuration file up the directory tree
    while not os.path.isfile(f"{repo_path}/.github/ght.yaml"):
        parent_dir = os.path.dirname(repo_path)
        if parent_dir == repo_path:
            raise click.UsageError("Not a gittr repository (or any of the parent directories): .github/ght.yaml")
        repo_path = parent_dir

    # Open the repo
    ght = GHT(repo_path, None)

    # Stash and checkout ght/master, on "fail/exit" pop the stash and
    # come back to the previous branch
    @contextmanager
    def stashed_checkout(repo, branch_name):
        prev_head = repo.head.reference

        prev_stashed_items = len(repo.git.stash("list").splitlines())
        repo.git.stash("push", "--all", "-m", "[ght]: Before editing configuration file.")
        curr_num_stashed_items = len(repo.git.stash("list").splitlines())

        repo.head.reference = repo.heads[branch_name]

        yield

        repo.head.reference = prev_head
        if curr_num_stashed_items - prev_stashed_items > 0:
            repo.git.stash("pop")

    with stashed_checkout(ght.repo, "ght/master"):
        click.edit(filename=f"{repo_path}/.github/ght.yaml")
        ght.repo.index.add(".github/ght.yaml")
        ght.repo.index.commit("[ght]: Update configuration file.", skip_hooks=True)


@cli.command()
@click.argument("template_url")
def render(template_url):
    """(Re)render an existing project"""

    # Setup the GHT Repository
    ght = GHT(repo_path=".", template_url=template_url)
    ght.load_config()
    ght.fetch_template()
    ght.render_tree()

    return 0
