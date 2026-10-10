"""Curated pattern list and the default mapping from LeetCode topic tags."""

PATTERNS: dict[str, str] = {
    "arrays-hashing": "Arrays & Hashing",
    "two-pointers": "Two Pointers",
    "sliding-window": "Sliding Window",
    "stack": "Stack",
    "monotonic-stack": "Monotonic Stack",
    "binary-search": "Binary Search",
    "linked-list": "Linked List",
    "trees": "Trees",
    "tries": "Tries",
    "heap": "Heap / Priority Queue",
    "backtracking": "Backtracking",
    "graphs": "Graphs (BFS/DFS)",
    "topological-sort": "Topological Sort",
    "union-find": "Union Find",
    "dynamic-programming": "Dynamic Programming",
    "greedy": "Greedy",
    "intervals": "Intervals",
    "prefix-sum": "Prefix Sum",
    "bit-manipulation": "Bit Manipulation",
    "math": "Math & Geometry",
}

TAG_TO_PATTERN: dict[str, str] = {
    "hash-table": "arrays-hashing",
    "two-pointers": "two-pointers",
    "sliding-window": "sliding-window",
    "stack": "stack",
    "monotonic-stack": "monotonic-stack",
    "binary-search": "binary-search",
    "linked-list": "linked-list",
    "tree": "trees",
    "binary-tree": "trees",
    "binary-search-tree": "trees",
    "trie": "tries",
    "heap-priority-queue": "heap",
    "backtracking": "backtracking",
    "graph": "graphs",
    "topological-sort": "topological-sort",
    "union-find": "union-find",
    "dynamic-programming": "dynamic-programming",
    "memoization": "dynamic-programming",
    "greedy": "greedy",
    "line-sweep": "intervals",
    "prefix-sum": "prefix-sum",
    "bit-manipulation": "bit-manipulation",
    "math": "math",
    "geometry": "math",
}

_TREE_TAGS = {"tree", "binary-tree", "binary-search-tree"}
_TRAVERSAL_TAGS = {"breadth-first-search", "depth-first-search"}


def default_patterns(lc_tags: list[str]) -> list[str]:
    tags = set(lc_tags)
    result = {TAG_TO_PATTERN[t] for t in tags if t in TAG_TO_PATTERN}
    # BFS/DFS on a tree is a tree pattern, and BFS on a DP problem (e.g. Coin Change)
    # is an alternative solution, not the core pattern.
    if tags & _TRAVERSAL_TAGS and not tags & (_TREE_TAGS | {"dynamic-programming"}):
        result.add("graphs")
    # Monotonic stack is the more specific pattern.
    if "monotonic-stack" in result:
        result.discard("stack")
    return sorted(result)


def validate(patterns: list[str]) -> list[str]:
    unknown = [p for p in patterns if p not in PATTERNS]
    if unknown:
        raise ValueError(f"unknown patterns: {', '.join(unknown)}")
    return sorted(set(patterns))
