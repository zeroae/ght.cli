#!/usr/bin/env python3

import os
import sys
from itertools import zip_longest
from platform import release

import yaml
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
from git import Repo, GitConfigParser, Remote, Blob, Object


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
        if template.startswith(".github/") and not (template.endswith(".ght") or template.endswith(".j2")):
            raise TemplateNotFound(f"Templates under the .github/ folder must end in .ght or j2: {template}")

    @staticmethod
    def _ensure_not_git(template):
        if template.startswith(".git/"):
            raise TemplateNotFound(f"The .git folder is not a valid path for templates: {template}")


class GHT(object):
    repo: Repo
    env: Environment
    config: dict
    template_url: str

    __slots__ = ["repo", "env", "config", "template_url"]

    def __init__(self, repo_path, template_url):
        self.repo = Repo(path=repo_path)
        self.template_url = template_url

        if not os.path.exists(ght_conf := os.path.join(self.repo.working_tree_dir, ".github", "ght.yaml")):
            raise ValueError(f"{repo_path} is an invalid GHT repository. No .github/ght.yaml file found.")
        with open(ght_conf, "r") as f:
            self.config = yaml.load(f, Loader=yaml.SafeLoader)

        self.env = Environment(
            loader=RestrictedFileSystemLoader(self.repo.working_tree_dir),
            extensions=[
                "jinja2.ext.do",
                "jinja2.ext.loopcontrols",
                "jinja2.ext.with_",
                "jinja2_time.TimeExtension"
            ]
        )
        self.configure_author()

    def configure_author(self):
        """
        git config --local user.email ""
        git config --local user.name ""
        """
        cw: GitConfigParser
        with self.repo.config_writer() as cw:
            cw.set_value("user", "email", "psodre@gmail.com")
            cw.set_value("user", "name", "Patrick Sodré")
        release()

    def prepare_tree_for_rendering(self):
        """
        git rm -rf .
        git fetch {ght_url} {refspec}:ght/template
        git checkout ght/template -- .
        git checkout HEAD -- .github/ght.yaml
        """

        self.remove_all()

        ght_url, refspec = self.template_url.split("@")
        self.repo.git.fetch(ght_url, f"{refspec}:ght/template")

        self.repo.git.checkout("ght/template", "--", ".")
        self.repo.git.checkout("HEAD", "--", ".github/ght.yaml")

    def remove_all(self):
        """
        Does the equivalent of `git rm -rf .`
        """
        all_blobs = [o.path for o in self.repo.tree().traverse(
            predicate=lambda i, _: i.type == "blob",
            branch_first=False)]
        for path in all_blobs:
            fs_path = os.path.join(self.repo.working_tree_dir, path)
            os.remove(fs_path)
        self.repo.index.remove(all_blobs)
        all_trees = [o.path for o in self.repo.tree().traverse(
            predicate=lambda i, _: i.type == "tree",
            branch_first=False
        )]
        all_trees.reverse()
        for path in all_trees:
            os.rmdir(os.path.join(self.repo.working_tree_dir, path))
        self.repo.index.update()

    def render_tree(self):
        self.prepare_tree_for_rendering()
        self.render_tree_content()
        self.render_tree_structure()
        self.repo.index.commit(f"[ght]: rendered {self.template_url}")

    def render_tree_structure(self):
        """
        Walk through all the blobs, and move them if their names need to be changed.
        """

        def compute_new_path(old_path):
            if old_path.endswith(".ght"):
                rv = old_path[:-4]
            else:
                rv = old_path
            return self.env.from_string(rv).render(self.config)

        def next_blob_to_move():
            try:
                return next((
                    (old_path, new_path)
                    for _, b in self.repo.index.iter_blobs()
                    if ((old_path := b.path) !=
                        (new_path := compute_new_path(old_path)))
                ))
            except StopIteration:
                return None

        while old_to_new := next_blob_to_move():
            for old, new in self.mutation_path(old_to_new[0], old_to_new[1]):
                self.repo.index.move([old, new])
            self.repo.index.update()

    def render_tree_content(self):
        """
        Render all tree content
        """
        for template_name in self.env.list_templates():
            template: Template = self.env.get_template(template_name)
            rendered = template.render(self.config)
            with open(os.path.join(self.repo.working_tree_dir, template_name), "w") as f:
                f.write(rendered)
            self.repo.index.add(template_name)

    @staticmethod
    def mutation_path(old: str, new: str):
        """
        Yields a series tuples that mutates an old path into the new path of same length
        """
        old_arr = old.split(os.path.sep)
        new_arr = new.split(os.path.sep)
        if (len_old_arr := len(old_arr)) != len(new_arr):
            raise ValueError

        new_arr.reverse()
        src_arr = [old_arr[0:len_old_arr - i] for i in range(0, len_old_arr)]
        dst_arr = [src[:-1] + [dst] for src, dst in zip(src_arr, new_arr)]

        return filter(lambda x: x[0] != x[1], zip(
            (os.path.join(*s) for s in src_arr),
            (os.path.join(*d) for d in dst_arr)
        ))

    @classmethod
    def init(cls, path, template_url, config: dict = None):
        repo = Repo.init(path)
        git_url, refspec = template_url.split("@")
        repo.git.fetch(git_url, f"{refspec}:ght/master")
        repo.git.checkout("ght/master")

        if config:
            os.makedirs(github_dir := os.path.join(path, ".github"), exist_ok=True)
            with open(os.path.join(github_dir, 'ght.yaml'), 'w') as f:
                yaml.dump(config, f)
            repo.index.add('.github/ght.yaml')

        repo.index.commit("[ght]: Initial Commit")

        return cls(repo_path=path, template_url=template_url)


def iterable_converged(left, right):
    """
    Returns true of the two iterables generate identical, false otherwise.
    """
    for l, r in zip_longest(left, right):
        if l != r:
            return False
    return True


def file_converged(left_filename: str, right_filename: str):
    """
    Returns true if two files are identical, otherwise false
    """
    with open(left_filename) as left:
        with open(right_filename) as right:
            return iterable_converged(left, right)


def commit_and_push():
    """
    git commit -m "<something meaningful>"
    git push --set-upstream origin HEAD:${{ github.head_ref }} --force
    """


def go():
    # message = sys.argv[1]
    # sender = sys.argv[2]
    ght_url = "https://github.com/sodre/ght-pypackage.git"

    # Setup the GHT Repository
    ght = GHT(repo_path=".", template_url=ght_url)
    ght.render_tree()

    os.system('echo ::set-output name=reply::Hello %s!' % ght_url)
    return 0


if __name__ == "__main__":
    sys.exit(go())
