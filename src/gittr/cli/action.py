import os
from contextlib import contextmanager

import yaml
from platform import release

from gittr.cli.utils import iterable_converged, RestrictedFileSystemLoader
from jinja2 import Environment, Template
from git import Repo, GitConfigParser


class GHT(object):
    repo: Repo
    env: Environment
    config: dict
    template_url: str

    __slots__ = ["repo", "env", "config", "config_path", "template_url"]

    def __init__(self, repo_path, template_url, config_path=None):
        self.repo = Repo(path=repo_path)
        self.template_url = template_url
        self.config_path = config_path or os.path.join(
            self.repo.working_tree_dir, ".github", "ght.yaml"
        )

        self.env = Environment(
            loader=RestrictedFileSystemLoader(self.repo.working_tree_dir),
            extensions=[
                "jinja2.ext.do",
                "jinja2.ext.loopcontrols",
                "jinja2.ext.with_",
                "jinja2_time.TimeExtension",
            ],
        )
        self.configure_author()

    def load_config(self):
        if not os.path.exists(self.config_path):
            raise ValueError(
                f"{self.repo.working_tree_dir} is an invalid GHT repository, "
                "{self.config_path} does not exist."
            )
        with open(self.config_path, "r") as f:
            self.config = yaml.load(f, Loader=yaml.SafeLoader)

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
        git checkout ght/template -- .
        git branch -D ght/template
        git checkout HEAD -- .github/ght.yaml
        """
        self.remove_all()

        with self.fetch_template():
            self.repo.git.checkout("ght/template", "--", ".")

        self.repo.git.checkout("HEAD", "--", ".github/ght.yaml")

    @contextmanager
    def fetch_template(self):
        ght_url, refspec = self.template_url.split("@")
        self.repo.git.fetch(ght_url, "--no-tags", f"{refspec}:ght/template")
        yield
        self.repo.git.branch("-D", "ght/template")

    def remove_all(self):
        """
        Does the equivalent of `git rm -rf .`
        """
        all_blobs = [
            o.path
            for o in self.repo.tree().traverse(
                predicate=lambda i, _: i.type == "blob", branch_first=False
            )
        ]
        for path in all_blobs:
            fs_path = os.path.join(self.repo.working_tree_dir, path)
            os.remove(fs_path)
        self.repo.index.remove(all_blobs)
        all_trees = [
            o.path
            for o in self.repo.tree().traverse(
                predicate=lambda i, _: i.type == "tree", branch_first=False
            )
        ]
        all_trees.reverse()
        for path in all_trees:
            os.rmdir(os.path.join(self.repo.working_tree_dir, path))
        self.repo.index.update()

    def render_ght_conf(self):
        """
        Render the .github/ght.yaml file
        """
        ght_conf_path = os.path.join(self.repo.working_tree_dir, ".github", "ght.yaml")
        with open(ght_conf_path) as f:
            curr_ght_yaml = f.read().splitlines()
        next_ght_yaml = curr_ght_yaml

        converged, index = False, -1
        while not converged:
            curr_ght_yaml = next_ght_yaml[: index + 1] + curr_ght_yaml[index + 1 :]  # noqa: E203
            config = yaml.safe_load("\n".join(curr_ght_yaml))
            next_ght_yaml = [self.env.from_string(line).render(config) for line in curr_ght_yaml]
            converged, index = iterable_converged(curr_ght_yaml, next_ght_yaml)

        with open(ght_conf_path, "w") as f:
            f.write("\n".join(curr_ght_yaml))
        self.repo.index.add(".github/ght.yaml")

    def render_tree(self):
        self.prepare_tree_for_rendering()
        self.render_ght_conf()
        self.load_config()
        self.render_tree_content()
        self.repo.index.commit(f"[ght]: rendered {self.template_url} content", skip_hooks=True)
        self.render_tree_structure()
        self.repo.index.commit(f"[ght]: rendered {self.template_url} structure", skip_hooks=True)

    def render_tree_structure(self):
        """
        Renders the Tree structure in git, by applying `render_ght_obj_name` to each object name.
        """
        objs_to_rename = [
            (o.path, os.path.join(os.path.dirname(o.path), new_name))
            for o in self.repo.tree().traverse(branch_first=False)
            if o.name != (new_name := self.render_ght_obj_name(o.name))
        ]
        objs_to_rename.reverse()

        for old_new in objs_to_rename:
            self.repo.index.move(old_new)
            self.repo.index.update()

    def render_ght_obj_name(self, name):
        if name.endswith(".ght"):
            rv = name[:-4]
        else:
            rv = name
        return self.env.from_string(rv).render(self.config)

    def render_tree_content(self):
        """
        Render all tree content
        """
        paths_to_render = [
            o.path
            for _, o in self.repo.index.iter_blobs()
            if not o.path.startswith(".github/") or o.path.endswith(".ght")
        ]

        for path in paths_to_render:
            template: Template = self.env.get_template(path)
            rendered = template.render(self.config)
            with open(os.path.join(self.repo.working_tree_dir, path), "w") as f:
                f.write(rendered)
            self.repo.index.add(path)

    @classmethod
    def init(cls, path, template_url, config: dict = None):
        """
        Step 1: Initialize the git repo
        Step 2: Write the configuration file to master branch
        Step 3: Get the ght/master branch ready for rendering
        """
        # Step 1: Initialize the git repo
        repo = Repo.init(path)

        ght = cls(repo_path=path, template_url=template_url)

        # Step 2: Write the configuration file to the master branch
        #   if config is a dict, then yaml.dump it
        if config is None:
            # Get the configuration file from the template URL
            with ght.fetch_template():
                repo.git.checkout("ght/template", ".github/ght.yaml")
        elif isinstance(config, dict):
            github_dir = os.path.join(path, ".github")
            os.makedirs(github_dir, exist_ok=True)
            with open(os.path.join(github_dir, "ght.yaml"), "w") as f:
                yaml.dump(config, f)
            repo.index.add(".github/ght.yaml")
        else:
            raise ValueError("config must be None or a dictionary.")
        repo.index.commit("[ght]: Add ght.yaml configuration.", skip_hooks=True)
        ght.load_config()

        # Step 3: Checkout the ght/master branch
        repo.git.checkout("-b", "ght/master", "master")

        return ght


def commit_and_push():
    """
    git commit -m "<something meaningful>"
    git push --set-upstream origin HEAD:${{ github.head_ref }} --force
    """
