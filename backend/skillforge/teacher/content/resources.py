"""Curated further-reading links, shown after a wrong answer.

Only established, publicly available references are listed: official
documentation (Python, scikit-learn), Wikipedia's reference articles,
and an openly published textbook. Every URL here was checked to resolve
when it was added. A resource may target specific concepts (`concepts`);
without that it applies to the whole topic. Topics with no trustworthy
match simply have no entry: the explanation stands on its own.

Shape: topic_id -> [{"title", "url", "publisher", "concepts"?}]
"""

from __future__ import annotations

ALLOWED_HOSTS = (
    "en.wikipedia.org",
    "docs.python.org",
    "scikit-learn.org",
    "christophm.github.io",
)


def _w(title: str, slug: str, concepts: list[str] | None = None) -> dict:
    r = {"title": title, "url": f"https://en.wikipedia.org/wiki/{slug}", "publisher": "Wikipedia"}
    if concepts:
        r["concepts"] = concepts
    return r


def _py(title: str, path: str, concepts: list[str] | None = None) -> dict:
    r = {"title": title, "url": f"https://docs.python.org/3/library/{path}", "publisher": "Python documentation"}
    if concepts:
        r["concepts"] = concepts
    return r


def _sk(title: str, path: str, concepts: list[str] | None = None) -> dict:
    r = {"title": title, "url": f"https://scikit-learn.org/stable/modules/{path}", "publisher": "scikit-learn user guide"}
    if concepts:
        r["concepts"] = concepts
    return r


RESOURCES: dict[str, list[dict]] = {
    # --- VNR: Computer Networks
    "cn-osi-model": [_w("OSI model", "OSI_model")],
    "cn-error-detection": [
        _w("Hamming distance", "Hamming_distance", ["hamming"]),
        _w("Cyclic redundancy check", "Cyclic_redundancy_check", ["crc"]),
        _w("Error detection and correction", "Error_detection_and_correction"),
    ],
    "cn-transport": [
        _w("Transmission Control Protocol", "Transmission_Control_Protocol", ["tcp-udp", "congestion"]),
        _w("User Datagram Protocol", "User_Datagram_Protocol", ["tcp-udp"]),
        _w("Port (computer networking)", "Port_(computer_networking)", ["ports"]),
        _w("TCP congestion control", "TCP_congestion_control", ["congestion"]),
    ],
    # --- VNR: Artificial Intelligence
    "ai-intelligent-agents": [_w("Intelligent agent", "Intelligent_agent")],
    "ai-search-strategies": [
        _w("A* search algorithm", "A*_search_algorithm", ["heuristic"]),
        _w("Breadth-first search", "Breadth-first_search", ["uninformed"]),
        _w("Hill climbing", "Hill_climbing", ["local"]),
    ],
    # --- VNR: Operating Systems
    "os-cpu-scheduling": [_w("Scheduling (computing)", "Scheduling_(computing)")],
    "os-deadlock": [
        _w("Deadlock (computer science)", "Deadlock_(computer_science)"),
        _w("Banker's algorithm", "Banker%27s_algorithm", ["prevention-avoidance"]),
    ],
    # --- VNR: Machine Learning
    "linear-regression": [
        _sk("Linear models", "linear_model.html"),
        _w("Linear regression", "Linear_regression"),
    ],
    "decision-trees": [
        _sk("Decision trees", "tree.html"),
        _w("Entropy (information theory)", "Entropy_(information_theory)", ["splitting-criteria"]),
        _w("Decision tree pruning", "Decision_tree_pruning", ["pruning"]),
    ],
    "bias-variance": [
        _w("Bias–variance tradeoff", "Bias%E2%80%93variance_tradeoff"),
        _sk("Cross-validation", "cross_validation.html", ["validation"]),
        _w("Regularization (mathematics)", "Regularization_(mathematics)", ["regularization"]),
    ],
    # --- VNR: Explainable AI
    "xai-post-hoc": [
        {
            "title": "Interpretable Machine Learning (C. Molnar)",
            "url": "https://christophm.github.io/interpretable-ml-book/",
            "publisher": "Open textbook",
        },
        _sk("Permutation feature importance", "permutation_importance.html", ["feature-importance"]),
    ],
    # --- VNR: Laboratories
    "lab-page-replacement": [_w("Page replacement algorithm", "Page_replacement_algorithm")],
    "mllab-model-training": [
        _sk("Cross-validation", "cross_validation.html", ["holdout", "kfold"]),
        _w("Bootstrapping (statistics)", "Bootstrapping_(statistics)", ["bootstrap"]),
    ],
    # gender-sensitization: no single authoritative reference chosen; explanations stand alone.
    # --- DSA foundations
    "dsa-asymptotic": [
        _w("Big O notation", "Big_O_notation", ["big-o", "bounds"]),
        _w("Time complexity", "Time_complexity"),
        _w("Space complexity", "Space_complexity", ["time-space"]),
    ],
    "dsa-two-pointers": [_w("Prefix sum", "Prefix_sum", ["prefix-sums"])],
    "dsa-linked-lists": [
        _w("Linked list", "Linked_list"),
        _w("Doubly linked list", "Doubly_linked_list", ["doubly"]),
        _w("Cycle detection", "Cycle_detection", ["cycle"]),
    ],
    "dsa-stacks-queues": [
        _w("Stack (abstract data type)", "Stack_(abstract_data_type)", ["stack", "monotonic"]),
        _w("Queue (abstract data type)", "Queue_(abstract_data_type)", ["queue-deque"]),
        _py("collections.deque", "collections.html#collections.deque", ["queue-deque"]),
    ],
    "dsa-hashing": [
        _w("Hash table", "Hash_table", ["hash-table"]),
        _w("Set (abstract data type)", "Set_(abstract_data_type)", ["sets"]),
        _py("collections.Counter", "collections.html#collections.Counter", ["frequency"]),
    ],
    "dsa-searching": [
        _w("Binary search", "Binary_search", ["binary", "boundaries"]),
        _py("bisect: array bisection algorithm", "bisect.html", ["boundaries"]),
        _w("Linear search", "Linear_search", ["linear"]),
    ],
    "dsa-sorting": [
        _w("Merge sort", "Merge_sort", ["merge"]),
        _w("Quicksort", "Quicksort", ["quick"]),
        _w("Insertion sort", "Insertion_sort", ["elementary"]),
        _w("Bubble sort", "Bubble_sort", ["elementary"]),
    ],
    "dsa-recursion": [
        _w("Recursion (computer science)", "Recursion_(computer_science)", ["fundamentals"]),
        _w("Master theorem", "Master_theorem_(analysis_of_algorithms)", ["recurrence"]),
        _w("Backtracking", "Backtracking", ["backtracking"]),
    ],
    "dsa-trees": [
        _w("Tree traversal", "Tree_traversal", ["traversal"]),
        _w("Binary search tree", "Binary_search_tree", ["bst", "height"]),
    ],
    "dsa-heaps": [
        _w("Binary heap", "Binary_heap", ["heap-property", "operations"]),
        _py("heapq: heap queue algorithm", "heapq.html"),
        _w("Priority queue", "Priority_queue", ["priority-queue"]),
    ],
    "dsa-graphs": [
        _w("Adjacency list", "Adjacency_list", ["representation"]),
        _w("Breadth-first search", "Breadth-first_search", ["bfs"]),
        _w("Depth-first search", "Depth-first_search", ["dfs"]),
        _w("Dijkstra's algorithm", "Dijkstra%27s_algorithm", ["bfs"]),
    ],
    "dsa-dp": [
        _w("Dynamic programming", "Dynamic_programming"),
        _w("Memoization", "Memoization", ["memoization"]),
        _w("Longest common subsequence", "Longest_common_subsequence", ["tabulation"]),
    ],
}


def attach(subjects: list[dict]) -> None:
    """Put each topic's resources on the topic dict (validated)."""
    known = set()
    for s in subjects:
        for u in s["units"]:
            for t in u["topics"]:
                known.add(t["id"])
                items = RESOURCES.get(t["id"], [])
                for r in items:
                    assert r["url"].startswith("https://"), r
                    assert r["url"].split("/")[2] in ALLOWED_HOSTS, r
                    for c in r.get("concepts", []):
                        assert c in t["concepts"], (t["id"], c)
                t["resources"] = items
    assert set(RESOURCES) <= known, set(RESOURCES) - known
