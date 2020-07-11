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
@click.argument("template-url", type=str, metavar="repository")
@click.argument("template-ref", type=str, default="master", metavar="[refspec]")
def init(template_url, template_ref):
    """Initialize a git project from a template git url and refspec.

    repository: the git-ght repository to use as a template
    refspec: default value is `master`

    \b
    This command will:
      - Initialize the current working directory as repository with the gittr tracking branch
      - Downloads the gittr template configuration file
    The user can then configure the template with `gittr configure`
    """

    if len(os.listdir(".")) > 0:
        raise click.ClickException("Refusing to initialize in a non-empty directory")

    # Setup the GHT Repository
    _ = GHT.init(path=".", template_url=template_url, template_ref=template_ref)

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
def render(refspec):
    """(Re)render an existing project.

    \b
    refspec: The template branch/refspec to use for rendering [default=master]
    """

    repo_path = resolve_repository_path(".")
    ght = GHT(repo_path=repo_path, template_ref=refspec)

    active_branch_name = ght.repo.active_branch.name
    if not active_branch_name.startswith("ght/"):
        raise click.ClickException(
            "Refusing to render the template."
            f"The active branch `{active_branch_name}` does not begin "
        )
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
