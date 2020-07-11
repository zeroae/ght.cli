from contextlib import contextmanager
from itertools import zip_longest

import click
from jinja2 import FileSystemLoader, TemplateNotFound


def iterable_converged(left, right):
    """
    Returns True, None if the two iterables generate identical, False, index otherwise.
    The index indicates the first position where the iterables differ
    """
    for i, (l_item, r_item) in enumerate(zip_longest(left, right)):
        if l_item != r_item:
            return False, i
    return True, None


class RestrictedFileSystemLoader(FileSystemLoader):
    def get_source(self, environment, template):
        self._ensure_not_unsafe_github(template)
        self._ensure_not_git(template)

        return super().get_source(environment, template)

    def list_templates(self):
        def only_safe(template):
            try:
                self._ensure_not_git(template)
                self._ensure_not_unsafe_github(template)
                return True
            except TemplateNotFound:
                return False

        return filter(only_safe, super().list_templates())

    @staticmethod
    def _ensure_not_unsafe_github(template):
        if template.startswith(".github/") and not (
            template.endswith(".ght") or template.endswith(".j2")
        ):
            raise TemplateNotFound(
                f"Templates under the .github/ folder must end in .ght or j2: {template}"
            )

    @staticmethod
    def _ensure_not_git(template):
        if template.startswith(".git/"):
            raise TemplateNotFound(f"The .git folder is not a valid path for templates: {template}")


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
