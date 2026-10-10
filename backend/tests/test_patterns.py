import pytest

from app.patterns import default_patterns, validate


@pytest.mark.parametrize(
    "tags, expected",
    [
        (["array", "stack", "monotonic-stack"], ["monotonic-stack"]),
        (["array", "depth-first-search", "breadth-first-search", "union-find", "matrix"], ["graphs", "union-find"]),
        (["tree", "depth-first-search", "binary-tree"], ["trees"]),
        (["array", "dynamic-programming", "breadth-first-search"], ["dynamic-programming"]),
        (["graph", "topological-sort", "depth-first-search"], ["graphs", "topological-sort"]),
        (["string", "simulation"], []),
    ],
)
def test_default_patterns(tags, expected):
    assert default_patterns(tags) == expected


def test_validate_rejects_unknown():
    assert validate(["trees", "graphs", "trees"]) == ["graphs", "trees"]
    with pytest.raises(ValueError):
        validate(["not-a-pattern"])
