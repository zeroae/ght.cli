import os

import pytest
from git import Repo, Tree, Actor, Blob

from .action import GHT


@pytest.fixture()
def template(tmpdir):
    repo = Repo.init(os.path.join(tmpdir, "template"))

    with open(os.path.join(repo.working_tree_dir, "unchanged.md"), "w") as f:
        f.write("this remains unchanged")
    repo.index.add(["unchanged.md"])

    with open(os.path.join(repo.working_tree_dir, "template.md"), "w") as f:
        f.write("{{ ght.hello }}")
    repo.index.add(["template.md"])

    charlie = os.path.join(repo.working_tree_dir, "{{ght.a}}", "{{ght.b}}", "{{ght.c}}")
    os.makedirs(os.path.dirname(charlie))
    open(charlie, 'w').close()
    repo.index.add([charlie])

    author = Actor("GHT Author", "author@example.com")
    repo.index.commit("Initial commit", author=author, committer=author)

    return repo


@pytest.fixture()
def ght(tmpdir, template: Repo):
    ght = GHT.init(path=os.path.join(tmpdir, "ght"),
                   template_url=f"file://{template.working_tree_dir}@master",
                   config=dict(
                       ght=dict(
                           hello="Hello World!",
                           a="alpha",
                           b="beta",
                           c="charlie"
                       )
                   ))
    assert not ght.repo.bare

    return ght


@pytest.mark.parametrize("old,new,expected",
                         [("{a}", "alpha", [("{a}", "alpha")]),
                          ("a/{b}", "a/beta", [("a/{b}", "a/beta")]),
                          ("{a}/b", "alpha/b", [("{a}", "alpha")]),
                          ("{a}/{b}", "alpha/beta", [("{a}/{b}", "{a}/beta"),
                                                     ("{a}", "alpha")]),
                          ("{a}/{b}/c", "alpha/beta/c", [("{a}/{b}", "{a}/beta"),
                                                         ("{a}", "alpha")]),
                          ])
def test_mutation_path(old, new, expected):
    l = list(GHT.mutation_path(old, new))
    assert l == expected


def test_git_configure(ght):
    cr = ght.repo.config_reader()
    assert cr.get_value("user", "email") is not None
    assert cr.get_value("user", "name") is not None


def test_iterable_converged():
    from .action import iterable_converged

    foo = "foo"
    bar = "bar"
    foobar = "foobar"

    assert iterable_converged(foo, foo)
    assert not iterable_converged(foo, bar)
    assert not iterable_converged(foo, foobar)
    assert not iterable_converged(foobar, foo)


def test_render_tree_structure(ght):
    ght.render_tree_structure()
    ght.repo.index.commit("[ght]: render tree structure")
    tree: Tree = ght.repo.tree() / "alpha"
    assert tree.type == "tree"


def test_render_tree_content(ght):
    ght.render_tree_content()
    ght.repo.index.commit("[ght]: render tree content")
    b: Blob = ght.repo.tree() / "unchanged.md"
    assert b.type == "blob"
    b: Blob = ght.repo.tree() / "template.md"
    assert b.type == "blob"
    assert "Hello World!" == b.data_stream.read().decode("utf8")


def test_ght_create_jinja2_environment(ght: GHT):
    for template in ght.env.list_templates():
        b = ght.repo.tree() / template
        assert b.type == "blob"


def test_prepare_tree_for_rendering(ght: GHT):
    ght.prepare_tree_for_rendering()
    assert ght.repo.active_branch == ght.repo.heads["ght/master"]


def test_render_tree(ght: GHT):
    ght.render_tree()
