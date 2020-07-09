from gittr.cli.utils import iterable_converged


def test_iterable_converged():
    foo = "foo"
    bar = "bar"
    foobar = "foobar"

    assert iterable_converged(foo, foo)[0]
    assert not iterable_converged(foo, bar)[0]
    assert not iterable_converged(foo, foobar)[0]
    assert not iterable_converged(foobar, foo)[0]
