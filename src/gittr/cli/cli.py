"""Console script for gittr."""

import collections
import os

import click
from click_plugins import with_plugins
from entrypoints import get_group_named

from gittr.cli.action import GHT
from gittr.cli.utils import stashed_checkout, resolve_repository_path


class OrderedGroup(click.Group):
    """A click group that maintains order.
    ref: https://bit.ly/click-ordered-group
    """

    def __init__(self, name=None, commands=None, **attrs):
        super(OrderedGroup, self).__init__(name, commands, **attrs)
        self.commands = commands or collections.OrderedDict()

    def list_commands(self, ctx):
        return self.commands


@with_plugins(get_group_named("gittr").values())
@click.group(cls=OrderedGroup)
def cli():
    """gittr command-line-interface"""
    return 0


@cli.command("init")
@click.argument("repository", type=str)
@click.argument("refspec", type=str, default="master", metavar="[REFSPEC]")
def init(repository, refspec):
    """Initialize a git project from a ght-template repository.

    \b
    REPOSITORY: A git-url pointing to a ght-repository to use as a template.
    REFSPEC: The git refspec to use. [default: master]

    \b
    This command will:
      - Git-initialize the current working directory
      - Download the ght template configuration file
      - Create the ght/master tracking branch

    \b
    EXAMPLES:
        $ mkdir example
        $ cd example
        $ ght init https://github.com/sodre/ght-pypackage master
    """

    if len(os.listdir(".")) > 0:
        raise click.ClickException("The current directory is not empty, refusing to initialize it.")

    # Setup the GHT Repository
    _ = GHT.init(path=".", template_url=repository, template_ref=refspec)

    return 0


@cli.command("configure")
@click.argument("repo-path", default=".", type=click.Path(file_okay=False, exists=True))
def configure(repo_path):
    """Edit an existing template configuration file

    A git commit is created if the file is modified.
    """

    # Open the repo
    repo_path = resolve_repository_path(repo_path)
    ght = GHT(repo_path, None)

    with stashed_checkout(ght.repo, "ght/master"):
        click.edit(filename=f"{repo_path}/.github/ght.yaml")
        ght.repo.index.add(".github/ght.yaml")
        ght.repo.index.commit("[ght]: Update configuration file.", skip_hooks=True)


@cli.command()
@click.argument("refspec", default="master", metavar="[refspec]")
@click.argument("dest-branch", default="ght/master", metavar="[ght branch]")
def render(refspec, dest_branch):
    """(Re)render the project

    \b
    refspec: The template branch/refspec to use for rendering [default=master]
    ght branch: The destination branch of the rendered results [default=ght/master]
    """
    if not dest_branch.startswith("ght/"):
        raise click.ClickException(
            "Refusing to render the template."
            f"The destination branch `{dest_branch}` does not begin ght/."
        )

    repo_path = resolve_repository_path(".")
    ght = GHT(repo_path=repo_path, template_ref=refspec)

    with stashed_checkout(ght.repo, dest_branch):
        ght.load_config()
        ght.render_tree()

    return 0


@cli.command("approve")
@click.argument("commit", default="ght/master")
def approve(commit):
    """Merge the rendered template from ght/master to master
    """

    repo_path = resolve_repository_path(".")
    ght = GHT(repo_path=repo_path)

    with stashed_checkout(ght.repo, "master"):
        click.echo(ght.repo.git.merge("--no-squash", "--no-ff", commit))
