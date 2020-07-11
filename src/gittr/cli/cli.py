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
    repo_path = resolve_repository_path(repo_path)

    # Open the repo
    ght = GHT(repo_path, None)

    with stashed_checkout(ght.repo, "ght/master"):
        click.edit(filename=f"{repo_path}/.github/ght.yaml")
        ght.repo.index.add(".github/ght.yaml")
        ght.repo.index.commit("[ght]: Update configuration file.", skip_hooks=True)


@contextmanager
def stashed_checkout(repo, branch_name):
    with stashed(repo) as stash:
        with checkout(repo, branch_name) as ref:
            yield stash, ref


@contextmanager
def stashed(repo):
    """A context that stashes all uncommitted/untracked items"""
    prev_stashed_items = len(repo.git.stash("list").splitlines())
    repo.git.stash("push", "--all", "-m", "[ght]: Before editing configuration file.")
    curr_num_stashed_items = len(repo.git.stash("list").splitlines())

    stash_created = curr_num_stashed_items - prev_stashed_items > 0

    yield stash_created

    if stash_created:
        repo.git.stash("pop")


@contextmanager
def checkout(repo, branch_name):
    """Branch checkout context"""
    prev_head = repo.head.ref
    yield repo.heads[branch_name].checkout()
    prev_head.checkout()


def resolve_repository_path(repo_path):
    # Find the configuration file up the directory tree
    import os

    while not os.path.isfile(f"{repo_path}/.github/ght.yaml"):
        parent_dir = os.path.dirname(repo_path)
        if parent_dir == repo_path:
            raise click.UsageError(
                "Not a gittr repository (or any of the parent directories): .github/ght.yaml"
            )
        repo_path = parent_dir
    return repo_path


@cli.command()
@click.argument("template_url")
def render(template_url):
    """(Re)render an existing project"""

    # Setup the GHT Repository
    ght = GHT(repo_path=".", template_url=template_url)
    ght.load_config()
    ght.render_tree()

    return 0


@cli.command("approve")
@click.argument("repo-path", default=".", type=click.Path(file_okay=False, exists=True))
@click.argument("commit", default="ght/master")
def approve(repo_path, commit):
    """Merge the rendered template from ght/master to master
    """

    repo_path = resolve_repository_path(repo_path)
    ght = GHT(repo_path, None)

    with stashed_checkout(ght.repo, "master"):
        click.echo(ght.repo.git.merge("--no-squash", "--no-ff", commit))
