"""Well-known problems per pattern, roughly easiest first, for "try next" suggestions.

Verified against LeetCode: each slug exists and is free to solve.
"""
from typing import NamedTuple


class BankProblem(NamedTuple):
    slug: str
    title: str
    difficulty: str
    lc_number: int

    @property
    def url(self) -> str:
        return f"https://leetcode.com/problems/{self.slug}/"


BANK: dict[str, list[BankProblem]] = {
    "arrays-hashing": [
        BankProblem("contains-duplicate", "Contains Duplicate", "Easy", 217),
        BankProblem("valid-anagram", "Valid Anagram", "Easy", 242),
        BankProblem("two-sum", "Two Sum", "Easy", 1),
        BankProblem("group-anagrams", "Group Anagrams", "Medium", 49),
        BankProblem("top-k-frequent-elements", "Top K Frequent Elements", "Medium", 347),
        BankProblem("product-of-array-except-self", "Product of Array Except Self", "Medium", 238),
        BankProblem("longest-consecutive-sequence", "Longest Consecutive Sequence", "Medium", 128),
    ],
    "two-pointers": [
        BankProblem("valid-palindrome", "Valid Palindrome", "Easy", 125),
        BankProblem("two-sum-ii-input-array-is-sorted", "Two Sum II - Input Array Is Sorted", "Medium", 167),
        BankProblem("3sum", "3Sum", "Medium", 15),
        BankProblem("container-with-most-water", "Container With Most Water", "Medium", 11),
        BankProblem("trapping-rain-water", "Trapping Rain Water", "Hard", 42),
    ],
    "sliding-window": [
        BankProblem("best-time-to-buy-and-sell-stock", "Best Time to Buy and Sell Stock", "Easy", 121),
        BankProblem("longest-substring-without-repeating-characters", "Longest Substring Without Repeating Characters", "Medium", 3),
        BankProblem("longest-repeating-character-replacement", "Longest Repeating Character Replacement", "Medium", 424),
        BankProblem("permutation-in-string", "Permutation in String", "Medium", 567),
        BankProblem("minimum-window-substring", "Minimum Window Substring", "Hard", 76),
        BankProblem("sliding-window-maximum", "Sliding Window Maximum", "Hard", 239),
    ],
    "stack": [
        BankProblem("valid-parentheses", "Valid Parentheses", "Easy", 20),
        BankProblem("min-stack", "Min Stack", "Medium", 155),
        BankProblem("evaluate-reverse-polish-notation", "Evaluate Reverse Polish Notation", "Medium", 150),
        BankProblem("asteroid-collision", "Asteroid Collision", "Medium", 735),
        BankProblem("decode-string", "Decode String", "Medium", 394),
    ],
    "monotonic-stack": [
        BankProblem("next-greater-element-i", "Next Greater Element I", "Easy", 496),
        BankProblem("daily-temperatures", "Daily Temperatures", "Medium", 739),
        BankProblem("online-stock-span", "Online Stock Span", "Medium", 901),
        BankProblem("car-fleet", "Car Fleet", "Medium", 853),
        BankProblem("largest-rectangle-in-histogram", "Largest Rectangle in Histogram", "Hard", 84),
    ],
    "binary-search": [
        BankProblem("binary-search", "Binary Search", "Easy", 704),
        BankProblem("search-a-2d-matrix", "Search a 2D Matrix", "Medium", 74),
        BankProblem("koko-eating-bananas", "Koko Eating Bananas", "Medium", 875),
        BankProblem("find-minimum-in-rotated-sorted-array", "Find Minimum in Rotated Sorted Array", "Medium", 153),
        BankProblem("search-in-rotated-sorted-array", "Search in Rotated Sorted Array", "Medium", 33),
        BankProblem("time-based-key-value-store", "Time Based Key-Value Store", "Medium", 981),
        BankProblem("median-of-two-sorted-arrays", "Median of Two Sorted Arrays", "Hard", 4),
    ],
    "linked-list": [
        BankProblem("reverse-linked-list", "Reverse Linked List", "Easy", 206),
        BankProblem("merge-two-sorted-lists", "Merge Two Sorted Lists", "Easy", 21),
        BankProblem("linked-list-cycle", "Linked List Cycle", "Easy", 141),
        BankProblem("reorder-list", "Reorder List", "Medium", 143),
        BankProblem("remove-nth-node-from-end-of-list", "Remove Nth Node From End of List", "Medium", 19),
        BankProblem("copy-list-with-random-pointer", "Copy List with Random Pointer", "Medium", 138),
        BankProblem("lru-cache", "LRU Cache", "Medium", 146),
        BankProblem("merge-k-sorted-lists", "Merge k Sorted Lists", "Hard", 23),
    ],
    "trees": [
        BankProblem("invert-binary-tree", "Invert Binary Tree", "Easy", 226),
        BankProblem("maximum-depth-of-binary-tree", "Maximum Depth of Binary Tree", "Easy", 104),
        BankProblem("same-tree", "Same Tree", "Easy", 100),
        BankProblem("diameter-of-binary-tree", "Diameter of Binary Tree", "Easy", 543),
        BankProblem("binary-tree-level-order-traversal", "Binary Tree Level Order Traversal", "Medium", 102),
        BankProblem("validate-binary-search-tree", "Validate Binary Search Tree", "Medium", 98),
        BankProblem("kth-smallest-element-in-a-bst", "Kth Smallest Element in a BST", "Medium", 230),
        BankProblem("construct-binary-tree-from-preorder-and-inorder-traversal", "Construct Binary Tree from Preorder and Inorder Traversal", "Medium", 105),
        BankProblem("binary-tree-maximum-path-sum", "Binary Tree Maximum Path Sum", "Hard", 124),
        BankProblem("serialize-and-deserialize-binary-tree", "Serialize and Deserialize Binary Tree", "Hard", 297),
    ],
    "tries": [
        BankProblem("implement-trie-prefix-tree", "Implement Trie (Prefix Tree)", "Medium", 208),
        BankProblem("design-add-and-search-words-data-structure", "Design Add and Search Words Data Structure", "Medium", 211),
        BankProblem("word-search-ii", "Word Search II", "Hard", 212),
    ],
    "heap": [
        BankProblem("kth-largest-element-in-a-stream", "Kth Largest Element in a Stream", "Easy", 703),
        BankProblem("last-stone-weight", "Last Stone Weight", "Easy", 1046),
        BankProblem("k-closest-points-to-origin", "K Closest Points to Origin", "Medium", 973),
        BankProblem("kth-largest-element-in-an-array", "Kth Largest Element in an Array", "Medium", 215),
        BankProblem("task-scheduler", "Task Scheduler", "Medium", 621),
        BankProblem("find-median-from-data-stream", "Find Median from Data Stream", "Hard", 295),
    ],
    "backtracking": [
        BankProblem("subsets", "Subsets", "Medium", 78),
        BankProblem("combination-sum", "Combination Sum", "Medium", 39),
        BankProblem("permutations", "Permutations", "Medium", 46),
        BankProblem("subsets-ii", "Subsets II", "Medium", 90),
        BankProblem("word-search", "Word Search", "Medium", 79),
        BankProblem("palindrome-partitioning", "Palindrome Partitioning", "Medium", 131),
        BankProblem("n-queens", "N-Queens", "Hard", 51),
    ],
    "graphs": [
        BankProblem("number-of-islands", "Number of Islands", "Medium", 200),
        BankProblem("max-area-of-island", "Max Area of Island", "Medium", 695),
        BankProblem("clone-graph", "Clone Graph", "Medium", 133),
        BankProblem("rotting-oranges", "Rotting Oranges", "Medium", 994),
        BankProblem("pacific-atlantic-water-flow", "Pacific Atlantic Water Flow", "Medium", 417),
        BankProblem("surrounded-regions", "Surrounded Regions", "Medium", 130),
        BankProblem("word-ladder", "Word Ladder", "Hard", 127),
    ],
    "topological-sort": [
        BankProblem("course-schedule", "Course Schedule", "Medium", 207),
        BankProblem("course-schedule-ii", "Course Schedule II", "Medium", 210),
        BankProblem("find-all-possible-recipes-from-given-supplies", "Find All Possible Recipes from Given Supplies", "Medium", 2115),
        BankProblem("minimum-height-trees", "Minimum Height Trees", "Medium", 310),
        BankProblem("parallel-courses-iii", "Parallel Courses III", "Hard", 2050),
    ],
    "union-find": [
        BankProblem("number-of-provinces", "Number of Provinces", "Medium", 547),
        BankProblem("redundant-connection", "Redundant Connection", "Medium", 684),
        BankProblem("satisfiability-of-equality-equations", "Satisfiability of Equality Equations", "Medium", 990),
        BankProblem("accounts-merge", "Accounts Merge", "Medium", 721),
        BankProblem("most-stones-removed-with-same-row-or-column", "Most Stones Removed with Same Row or Column", "Medium", 947),
    ],
    "dynamic-programming": [
        BankProblem("climbing-stairs", "Climbing Stairs", "Easy", 70),
        BankProblem("house-robber", "House Robber", "Medium", 198),
        BankProblem("coin-change", "Coin Change", "Medium", 322),
        BankProblem("longest-increasing-subsequence", "Longest Increasing Subsequence", "Medium", 300),
        BankProblem("word-break", "Word Break", "Medium", 139),
        BankProblem("unique-paths", "Unique Paths", "Medium", 62),
        BankProblem("longest-common-subsequence", "Longest Common Subsequence", "Medium", 1143),
        BankProblem("partition-equal-subset-sum", "Partition Equal Subset Sum", "Medium", 416),
        BankProblem("edit-distance", "Edit Distance", "Medium", 72),
    ],
    "greedy": [
        BankProblem("maximum-subarray", "Maximum Subarray", "Medium", 53),
        BankProblem("jump-game", "Jump Game", "Medium", 55),
        BankProblem("jump-game-ii", "Jump Game II", "Medium", 45),
        BankProblem("gas-station", "Gas Station", "Medium", 134),
        BankProblem("hand-of-straights", "Hand of Straights", "Medium", 846),
        BankProblem("partition-labels", "Partition Labels", "Medium", 763),
    ],
    "intervals": [
        BankProblem("merge-intervals", "Merge Intervals", "Medium", 56),
        BankProblem("insert-interval", "Insert Interval", "Medium", 57),
        BankProblem("non-overlapping-intervals", "Non-overlapping Intervals", "Medium", 435),
        BankProblem("minimum-number-of-arrows-to-burst-balloons", "Minimum Number of Arrows to Burst Balloons", "Medium", 452),
        BankProblem("car-pooling", "Car Pooling", "Medium", 1094),
        BankProblem("minimum-interval-to-include-each-query", "Minimum Interval to Include Each Query", "Hard", 1851),
    ],
    "prefix-sum": [
        BankProblem("range-sum-query-immutable", "Range Sum Query - Immutable", "Easy", 303),
        BankProblem("find-pivot-index", "Find Pivot Index", "Easy", 724),
        BankProblem("subarray-sum-equals-k", "Subarray Sum Equals K", "Medium", 560),
        BankProblem("continuous-subarray-sum", "Continuous Subarray Sum", "Medium", 523),
        BankProblem("contiguous-array", "Contiguous Array", "Medium", 525),
    ],
    "bit-manipulation": [
        BankProblem("single-number", "Single Number", "Easy", 136),
        BankProblem("number-of-1-bits", "Number of 1 Bits", "Easy", 191),
        BankProblem("counting-bits", "Counting Bits", "Easy", 338),
        BankProblem("missing-number", "Missing Number", "Easy", 268),
        BankProblem("reverse-bits", "Reverse Bits", "Easy", 190),
        BankProblem("sum-of-two-integers", "Sum of Two Integers", "Medium", 371),
    ],
    "math": [
        BankProblem("palindrome-number", "Palindrome Number", "Easy", 9),
        BankProblem("plus-one", "Plus One", "Easy", 66),
        BankProblem("rotate-image", "Rotate Image", "Medium", 48),
        BankProblem("spiral-matrix", "Spiral Matrix", "Medium", 54),
        BankProblem("powx-n", "Pow(x, n)", "Medium", 50),
        BankProblem("multiply-strings", "Multiply Strings", "Medium", 43),
    ],
}
