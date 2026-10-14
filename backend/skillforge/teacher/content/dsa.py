"""Data Structures & Algorithms — a general foundations area (not tied to any
institution or semester).

Twelve core topics carry a reviewed question bank (6 questions each: two per
difficulty level), written for SkillForge. Further topics are listed without
a bank so the remaining coverage stays visible.
"""

from __future__ import annotations

from skillforge.teacher.content._build import concept, lesson, question, subject, topic, unit

SOURCE = "SkillForge question bank, DSA foundations"


def q(qid, difficulty, concept_key, cognitive, prompt, options, answer, explanation, why_wrong=None):
    item = question(qid, difficulty, concept_key, prompt, options, answer, explanation, why_wrong)
    item["cognitive_type"] = cognitive
    item["source"] = SOURCE
    return item


R, U, A, N = "recall", "understand", "apply", "analyze"

ASYMPTOTIC = topic(
    "dsa-asymptotic",
    "Asymptotic Notation: Big-O, Big-Θ, Big-Ω; Time vs Space",
    "How an algorithm's cost grows with input size, and how to state it precisely.",
    level="Beginner",
    lesson=lesson(
        "Asymptotic notation describes how an algorithm's cost grows as its input grows, ignoring constant "
        "factors and small inputs.",
        [
            "Big-O gives an upper bound: f(n) = O(g(n)) if, for large n, f(n) ≤ c·g(n) for some constant c. "
            "Big-Ω gives a lower bound and Big-Θ a tight bound (both at once). Keep the dominant term and drop "
            "constants: 3n² + 5n + 2 is Θ(n²).",
            "Time complexity counts basic operations; space complexity counts the extra memory an algorithm "
            "allocates, including the call stack of a recursion. Nested loops over the same input usually "
            "multiply; loops in sequence add.",
        ],
        [
            "O = upper bound, Ω = lower bound, Θ = tight bound.",
            "Keep the dominant term; drop constant factors.",
            "Recursion depth costs stack space.",
        ],
    ),
    concepts={
        "big-o": concept(
            "Big-O notation",
            "f(n) = O(g(n)) means f(n) ≤ c·g(n) for large n. It is an upper bound on growth: 3n + 7 is O(n).",
        ),
        "bounds": concept(
            "Big-Θ and Big-Ω",
            "Big-Ω is a lower bound and Big-Θ a tight bound (both O and Ω). Merge sort is Θ(n log n) on every "
            "input; insertion sort is O(n²) and Ω(n).",
        ),
        "time-space": concept(
            "Time vs space complexity",
            "Time counts operations as n grows; space counts extra memory, including stack frames that a "
            "recursion keeps alive at the same time.",
        ),
    },
    questions=[
        q("dsa-cx-1", 1, "big-o", R, "What is the Big-O time complexity of 3n² + 5n + 2?",
          ["O(n)", "O(n²)", "O(n³)", "O(1)"], 1,
          "Keep the dominant term and drop the constant: for large n, 3n² outgrows 5n + 2, so the cost is O(n²).",
          {0: "The linear term 5n is dominated by 3n² as n grows."}),
        q("dsa-cx-2", 1, "time-space", U,
          "An algorithm makes a copy of its input array of n elements and otherwise uses a few variables. What "
          "is its auxiliary space complexity?",
          ["O(1)", "O(log n)", "O(n)", "O(n²)"], 2,
          "The copy holds all n elements, so the extra memory grows linearly with n: O(n).",
          {0: "O(1) would mean the extra memory does not grow with n, but the copy holds all n elements."}),
        q("dsa-cx-3", 2, "bounds", U, "Which statement correctly describes Big-Θ?",
          ["It is only an upper bound on growth", "It is only a lower bound on growth",
           "It bounds growth both above and below, up to constant factors", "It describes the average case only"], 2,
          "f(n) = Θ(g(n)) when f is both O(g(n)) and Ω(g(n)): g is a tight bound on f's growth.",
          {0: "That is Big-O.", 1: "That is Big-Ω.",
           3: "O, Ω and Θ describe the growth of a function; each can be applied to the worst, best or "
              "average case."}),
        q("dsa-cx-4", 2, "big-o", A,
          "for i in range(n):\n    for j in range(i, n):\n        total += 1\n\n"
          "What is the time complexity of this code?",
          ["O(n)", "O(n log n)", "O(n²)", "O(2ⁿ)"], 2,
          "The inner loop runs n − i times, so the total is n + (n − 1) + … + 1 = n(n + 1)/2, which is Θ(n²). "
          "Starting j at i halves the work but does not change the growth rate.",
          {1: "Nothing here halves the problem each step, which is where log n comes from."}),
        q("dsa-cx-5", 3, "time-space", N,
          "A recursive function on n calls itself once with n − 1 until n reaches 0, doing constant work per "
          "call and allocating nothing else. What are its time and space complexity?",
          ["O(n) time, O(1) space", "O(n) time, O(n) space", "O(log n) time, O(n) space",
           "O(n²) time, O(1) space"], 1,
          "There are n + 1 calls doing constant work, so time is O(n). Every pending call keeps its stack frame "
          "until the base case returns, so up to n frames are live at once: O(n) space.",
          {0: "It allocates nothing explicitly, but a recursion depth of n keeps n stack frames alive."}),
        q("dsa-cx-6", 3, "bounds", N,
          "Insertion sort takes about n steps on an already sorted array and about n²/2 on a reversed one. "
          "Which description is correct?",
          ["It is Θ(n²) on every input",
           "It is O(n²) and Ω(n): Θ(n) in the best case and Θ(n²) in the worst case",
           "It is Θ(n) because the best case is linear", "It is Θ(n log n)"], 1,
          "The worst case grows as n² and the best case as n, so no single tight bound covers every input: the "
          "running time is O(n²) and Ω(n). Each case on its own has a tight bound.",
          {0: "On sorted input it does only about n comparisons, so it is not Θ(n²) on every input."}),
    ],
)

TWO_POINTERS = topic(
    "dsa-two-pointers",
    "Arrays: Prefix Sums, Two Pointers and Sliding Window",
    "Three linear-time array techniques that replace nested loops.",
    level="Beginner",
    lesson=lesson(
        "Many array problems that look quadratic have linear solutions once you reuse work instead of "
        "recomputing it.",
        [
            "A prefix-sum array P with P[0] = 0 and P[i] = a[0] + … + a[i − 1] answers any range sum a[l..r] as "
            "P[r + 1] − P[l] in O(1) after O(n) preprocessing.",
            "Two pointers move through the data under a rule, for example from both ends of a sorted array. A "
            "sliding window keeps a summary of a[left..right] and updates it as elements enter and leave, so "
            "each element is handled a constant number of times.",
        ],
        [
            "Range sum = P[r + 1] − P[l].",
            "Pointers that never move back give O(n).",
            "Update the window; don't recompute it.",
        ],
    ),
    concepts={
        "prefix-sums": concept(
            "Prefix sums",
            "P[i] stores the sum of the first i elements, so the sum of a[l..r] is P[r + 1] − P[l].",
        ),
        "two-pointers": concept(
            "Two pointers",
            "On a sorted array, start at both ends: move left rightwards when the sum is too small and right "
            "leftwards when it is too large. Each pointer moves at most n times.",
        ),
        "sliding-window": concept(
            "Sliding window",
            "Keep a window [left, right] and update its summary as it slides: add the entering element, remove "
            "the leaving one, in O(1) per step.",
        ),
    },
    questions=[
        q("dsa-tp-1", 1, "prefix-sums", R,
          "With prefix sums P[0] = 0 and P[i] = a[0] + … + a[i − 1], how is the sum of a[l..r] (inclusive) "
          "computed?",
          ["P[r] − P[l]", "P[r + 1] − P[l]", "P[r + 1] − P[l + 1]", "P[r] + P[l]"], 1,
          "P[r + 1] holds a[0..r] and P[l] holds a[0..l − 1]; subtracting leaves exactly a[l..r].",
          {0: "P[r] − P[l] covers a[l..r − 1] and misses a[r].", 2: "That drops a[l] from the range."}),
        q("dsa-tp-2", 1, "sliding-window", U,
          "Why is a sliding window faster than recomputing every window of size k from scratch?",
          ["It sorts the array first",
           "It updates the window's summary using only the element entering and the element leaving",
           "It skips half of the windows", "It uses recursion to share work"], 1,
          "Recomputing costs O(k) per window, O(nk) in total. Sliding adds the new element and removes the old "
          "one in O(1), so all windows take O(n)."),
        q("dsa-tp-3", 2, "two-pointers", A,
          "In a sorted ascending array you look for two numbers summing to a target, with pointers at both "
          "ends. The current sum is smaller than the target. What should you do?",
          ["Move the right pointer left", "Move the left pointer right", "Move both pointers inward",
           "Restart from the middle"], 1,
          "The array is sorted ascending, so moving the left pointer right is the only move that can increase "
          "the sum.",
          {0: "Moving the right pointer left can only decrease the sum, away from the target."}),
        q("dsa-tp-4", 2, "prefix-sums", A,
          "a = [3, 1, 4, 1, 5]. Using prefix sums with P[0] = 0, what is the sum of a[1..3]?",
          ["5", "6", "9", "14"], 1,
          "P = [0, 3, 4, 8, 9, 14], so the sum of a[1..3] is P[4] − P[1] = 9 − 3 = 6, which is 1 + 4 + 1.",
          {2: "9 is P[4], the sum of a[0..3]; you still need to subtract P[1]."}),
        q("dsa-tp-5", 3, "sliding-window", N,
          "You need the length of the longest substring with no repeated characters. Which approach runs in "
          "O(n)?",
          ["Check every substring and test it for repeats", "Sort the string and scan it",
           "Grow a window to the right and shrink it from the left whenever a character repeats, tracking "
           "the window's characters in a set",
           "Binary search on the answer with a full rescan each time"], 2,
          "Each character enters the window once and leaves at most once, so the total work is O(n) with O(1) "
          "set operations. Checking every substring means O(n²) substrings.",
          {1: "Sorting destroys the order that defines a substring."}),
        q("dsa-tp-6", 3, "two-pointers", N,
          "Why is the two-pointer pair-sum scan on a sorted array O(n) rather than O(n²)?",
          ["Each step moves one pointer inward and neither ever moves back, so there are at most n − 1 steps",
           "Sorting already found the pair", "It checks only half of the elements",
           "Each pair is checked twice"], 0,
          "Every iteration moves one pointer towards the other, and pointers never move back, so they meet "
          "after at most n − 1 moves. The pairs that are skipped are ruled out by the sorted order."),
    ],
)

LINKED_LISTS = topic(
    "dsa-linked-lists",
    "Linked Lists: Singly, Doubly and Cycle Detection",
    "Pointer-based sequences, their costs, and detecting a loop.",
    level="Beginner",
    lesson=lesson(
        "A linked list stores elements in nodes that point to each other, rather than side by side in memory.",
        [
            "In a singly linked list each node points to the next one. Inserting or removing after a node you "
            "already hold is O(1), but reaching the k-th element means following k links. A doubly linked list "
            "also stores a pointer to the previous node, so a node can be unlinked in O(1) and the list walked "
            "in both directions.",
            "If a list accidentally loops back on itself, Floyd's algorithm detects it with two pointers: a slow "
            "one moving one step and a fast one moving two. They meet if and only if there is a cycle.",
        ],
        [
            "Access by position is O(k), not O(1).",
            "prev pointers make O(1) removal possible.",
            "Slow and fast pointers detect a cycle in O(1) space.",
        ],
    ),
    concepts={
        "singly": concept(
            "Singly linked lists",
            "Each node holds a value and a next pointer. Reaching the k-th node takes k steps; inserting after "
            "a node you hold is O(1).",
        ),
        "doubly": concept(
            "Doubly linked lists",
            "Each node also points to its predecessor, so you can unlink a node in O(1) by redirecting both "
            "neighbours around it.",
        ),
        "cycle": concept(
            "Cycle detection",
            "Move slow by one and fast by two. Inside a cycle the gap shrinks by one per step, so they meet; "
            "if fast reaches the end, there is no cycle.",
        ),
    },
    questions=[
        q("dsa-ll-1", 1, "singly", R, "What is the time complexity of reaching the k-th element of a singly linked list?",
          ["O(1)", "O(log k)", "O(k)", "O(k²)"], 2,
          "There is no index arithmetic: you must follow k next-pointers from the head.",
          {0: "Constant-time access by index belongs to arrays, which store elements contiguously."}),
        q("dsa-ll-2", 1, "doubly", U, "What does a doubly linked list allow that a singly linked list does not?",
          ["O(1) access by index",
           "Walking backwards, and removing a node you hold in O(1) without searching for its predecessor",
           "Storing values of different types", "Keeping elements sorted automatically"], 1,
          "The prev pointer gives direct access to the predecessor, so the node can be unlinked immediately and "
          "the list can be traversed in either direction."),
        q("dsa-ll-3", 2, "singly", A,
          "def reverse(head):\n    prev = None\n    curr = head\n    while curr:\n        nxt = curr.next\n"
          "        curr.next = prev\n        prev = curr\n        curr = nxt\n    return ???\n\n"
          "What should the function return as the head of the reversed list?",
          ["head", "curr", "prev", "nxt"], 2,
          "When the loop ends, curr is None and prev points at the last node visited, which is now the first "
          "node of the reversed list.",
          {0: "The original head is now the tail; its next pointer is None.", 1: "curr is None when the loop exits."}),
        q("dsa-ll-4", 2, "cycle", U,
          "In Floyd's cycle detection, why must the slow and fast pointers meet if the list has a cycle?",
          ["The fast pointer stops at the start of the cycle",
           "Once both are inside the cycle, the gap between them shrinks by one node every step",
           "The slow pointer moves backwards", "The list must be sorted"], 1,
          "Inside the cycle the fast pointer gains one node per step on the slow pointer, so the distance "
          "between them decreases by one each step and must reach zero."),
        q("dsa-ll-5", 3, "doubly", A,
          "To delete node X from the middle of a doubly linked list, which updates are required?",
          ["X.prev.next = X.next and X.next.prev = X.prev",
           "X.next = None and X.prev = None only",
           "X.prev.prev = X.next and X.next.next = X.prev",
           "X.prev.next = X and X.next.prev = X"], 0,
          "Both neighbours must skip X: the previous node's next and the following node's prev are redirected "
          "around it.",
          {1: "Clearing X's own pointers leaves its neighbours still pointing at X, so it stays in the list."}),
        q("dsa-ll-6", 3, "cycle", N, "Which approach detects a cycle in a linked list using O(1) extra space?",
          ["Store every visited node in a hash set", "Copy the list into an array and sort it",
           "Advance a slow pointer by one and a fast pointer by two until they meet or fast reaches the end",
           "Recursively visit each node and record it in a list"], 2,
          "Floyd's tortoise-and-hare uses only two pointers, whatever the list's length.",
          {0: "A hash set also detects the cycle, but needs O(n) extra memory.",
           3: "Recording visited nodes needs O(n) memory, plus O(n) stack for the recursion."}),
    ],
)

STACKS_QUEUES = topic(
    "dsa-stacks-queues",
    "Stacks, Queues, Deques and the Monotonic Stack",
    "LIFO and FIFO structures and the problems they make simple.",
    level="Beginner",
    lesson=lesson(
        "Stacks and queues restrict where you add and remove items, and that restriction is exactly what many "
        "problems need.",
        [
            "A stack is last-in, first-out: push and pop at the same end in O(1). Bracket matching, undo and "
            "function calls are stack problems. A queue is first-in, first-out: enqueue at the back, dequeue at "
            "the front. A deque supports O(1) operations at both ends.",
            "A monotonic stack keeps its contents in increasing (or decreasing) order by popping anything that "
            "would break the order before pushing. Each element is pushed and popped at most once, so problems "
            "like 'next greater element' take O(n) in total.",
        ],
        [
            "Stack = LIFO; queue = FIFO.",
            "Python: use collections.deque for queues.",
            "Count pops over the whole run, not per iteration.",
        ],
    ),
    concepts={
        "stack": concept(
            "Stacks (LIFO)",
            "The most recently added item comes out first. Push and pop happen at the same end in O(1).",
        ),
        "queue-deque": concept(
            "Queues and deques",
            "A queue serves items in arrival order (FIFO). A deque allows O(1) insertion and removal at both "
            "ends; BFS uses a queue.",
        ),
        "monotonic": concept(
            "Monotonic stack",
            "Pop elements that break the stack's order before pushing. Every element is pushed once and popped "
            "at most once, so the whole scan is O(n).",
        ),
    },
    questions=[
        q("dsa-sq-1", 1, "stack", A,
          "Start with an empty stack: push 1, push 2, push 3, pop, push 4, pop. Which element is now on top?",
          ["1", "2", "3", "4"], 1,
          "After pushing 1, 2, 3 and popping, the stack is [1, 2]. Pushing 4 and popping it leaves [1, 2], so "
          "2 is on top.",
          {2: "3 was popped by the first pop."}),
        q("dsa-sq-2", 1, "queue-deque", R, "Which data structure serves items in first-in, first-out order?",
          ["Stack", "Queue", "Binary search tree", "Max-heap"], 1,
          "A queue removes items in the order they arrived.",
          {0: "A stack is last-in, first-out."}),
        q("dsa-sq-3", 2, "stack", A,
          "A stack-based checker reads the brackets ( [ ) ] from left to right. Where does it detect the error?",
          ["At the first (", "At the [", "At the )", "It reports the string as balanced"], 2,
          "At ), the top of the stack is [, which does not match, so the string is unbalanced at that point.",
          {3: "Brackets must close in the reverse order they opened; [ is still open when ) arrives."}),
        q("dsa-sq-4", 2, "queue-deque", U,
          "Why is Python's list.pop(0) a poor way to dequeue, compared with collections.deque.popleft()?",
          ["pop(0) returns the wrong element",
           "pop(0) shifts every remaining element, costing O(n), while popleft() is O(1)",
           "A deque cannot store integers", "Lists do not allow pop(0)"], 1,
          "A list stores its elements contiguously, so removing the first one moves all the others. A deque is "
          "built for O(1) operations at both ends."),
        q("dsa-sq-5", 3, "monotonic", A,
          "For the array [2, 1, 5, 3], what is the 'next greater element' of each position (−1 if none)?",
          ["[5, 5, −1, −1]", "[1, 5, 3, −1]", "[5, 5, 5, −1]", "[−1, 2, −1, 5]"], 0,
          "2 → 5 and 1 → 5 (the first larger value to the right); nothing after 5 is larger; 3 is last. So "
          "the answer is [5, 5, −1, −1].",
          {2: "3 is smaller than 5, so 5 has no next greater element."}),
        q("dsa-sq-6", 3, "monotonic", N,
          "A monotonic-stack solution has a while loop that pops inside a for loop over n elements. Why is it "
          "still O(n)?",
          ["The while loop runs at most once per iteration",
           "Each element is pushed once and popped at most once, so all pops together number at most n",
           "The input must be sorted", "Stack operations are O(log n)"], 1,
          "Amortized analysis: over the whole run there can be no more pops than pushes, and there are exactly "
          "n pushes.",
          {0: "One iteration can pop many elements; it is the total over all iterations that is bounded."}),
    ],
)

HASHING = topic(
    "dsa-hashing",
    "Hashing: Hash Tables, Sets and Frequency Counting",
    "Average constant-time lookup, and the problems it unlocks.",
    level="Beginner",
    lesson=lesson(
        "A hash table turns a key into a bucket index, so finding a key no longer means searching.",
        [
            "A hash function maps each key to a bucket. With a good function and a table that grows as it "
            "fills, insert, lookup and delete take O(1) on average. Two keys landing in the same bucket is a "
            "collision; it is resolved by chaining or open addressing, and many collisions push the worst case "
            "to O(n).",
            "A hash set answers 'have I seen this?' in O(1) on average. A hash map from item to count turns "
            "duplicate detection, anagram checks and majority votes into a single O(n) pass.",
        ],
        [
            "Average O(1); worst case O(n) under heavy collisions.",
            "Sets for membership, maps for counts.",
            "Python: set, dict and collections.Counter.",
        ],
    ),
    concepts={
        "hash-table": concept(
            "Hash tables",
            "A hash function maps a key to a bucket for average O(1) operations. Collisions share a bucket; "
            "if many keys collide, lookups degrade towards O(n).",
        ),
        "sets": concept(
            "Sets",
            "A hash set stores unique keys with average O(1) membership tests.",
        ),
        "frequency": concept(
            "Frequency counting",
            "Count occurrences with a map from item to count in one O(n) pass, then compare or query the counts.",
        ),
    },
    questions=[
        q("dsa-hs-1", 1, "hash-table", R,
          "What is the average-case time to look up a key in a hash table with a good hash function?",
          ["O(1)", "O(log n)", "O(n)", "O(n log n)"], 0,
          "The hash function points straight at the key's bucket, so on average only a constant number of "
          "entries are examined.",
          {1: "O(log n) is a balanced search tree's lookup cost."}),
        q("dsa-hs-2", 1, "sets", U,
          "You must repeatedly check whether a value has already appeared in a stream. Which structure fits "
          "best?",
          ["An unsorted list searched linearly", "A hash set", "A stack", "A queue"], 1,
          "A hash set answers membership in O(1) on average; a list needs O(n) per check."),
        q("dsa-hs-3", 2, "frequency", A,
          "Two strings of length n are anagrams if they have the same characters with the same counts. What is "
          "the time complexity of checking this with a frequency map?",
          ["O(n)", "O(n log n)", "O(n²)", "O(1)"], 0,
          "Count the characters of one string, subtract for the other, and check every count is zero: a "
          "constant number of linear passes, O(n).",
          {1: "O(n log n) is the cost of the sorting approach, not the frequency map."}),
        q("dsa-hs-4", 2, "hash-table", U, "What is a hash collision?",
          ["Inserting the same key twice", "Two different keys mapping to the same bucket",
           "The table running out of memory", "A lookup returning the wrong value"], 1,
          "Collisions are unavoidable because there are more possible keys than buckets; the table must store "
          "both keys and tell them apart."),
        q("dsa-hs-5", 3, "hash-table", N, "Why can hash-table operations degrade to O(n) in the worst case?",
          ["Hashing a key always takes O(n)",
           "If many keys collide into one bucket, a lookup must scan all of them",
           "The table is re-sorted after every insert", "Deleting shifts every element"], 1,
          "With chaining, one overloaded bucket becomes a list that must be scanned. A good hash function and "
          "resizing keep this rare."),
        q("dsa-hs-6", 3, "frequency", N,
          "Given an array and a target, which approach decides in O(n) whether two distinct elements sum to "
          "the target?",
          ["Sort, then binary-search for each element's partner",
           "For each x, check whether target − x is in a hash set of earlier elements, then add x",
           "Nested loops over all pairs", "Count frequencies and return the most common element"], 1,
          "Each element costs one O(1) lookup and one insert. Looking only among earlier elements guarantees "
          "two distinct positions.",
          {0: "This works but costs O(n log n).", 2: "This works but costs O(n²)."}),
    ],
)

SEARCHING = topic(
    "dsa-searching",
    "Searching: Linear Search and Binary Search",
    "Finding values in unsorted and sorted data, and getting the boundaries right.",
    level="Beginner",
    lesson=lesson(
        "Searching sorted data is dramatically faster than searching unsorted data, because each comparison "
        "can rule out half of what remains.",
        [
            "Linear search checks elements one by one: O(n) in the worst case, and it works on any data. Binary "
            "search compares with the middle of a sorted range and discards the half that cannot contain the "
            "target: O(log n). It needs sorted order and constant-time access by index.",
            "Many problems ask for a boundary: the first position where a condition becomes true. Keep an "
            "invariant such as 'the answer is in [lo, hi]' and move one end each step without ever discarding a "
            "possible answer; off-by-one bugs come from breaking that invariant.",
        ],
        [
            "Binary search needs sorted data and random access.",
            "1,000 elements need at most 10 comparisons.",
            "Never discard mid if mid can be the answer.",
        ],
    ),
    concepts={
        "linear": concept("Linear search", "Check each element in turn: O(n), no ordering required."),
        "binary": concept(
            "Binary search",
            "On sorted data, compare with the middle and keep only the half that can contain the target: "
            "O(log n).",
        ),
        "boundaries": concept(
            "Binary search boundaries",
            "To find the first index where a condition holds, set hi = mid when it holds (mid may be the "
            "answer) and lo = mid + 1 when it does not.",
        ),
    },
    questions=[
        q("dsa-bs-1", 1, "binary", R, "What must be true of an array for binary search to work on it?",
          ["It must be sorted", "It must have an even length", "It must contain distinct values",
           "It must be stored as a linked list"], 0,
          "Binary search decides which half to discard by comparing with the middle element, which is only "
          "valid if the array is sorted.",
          {2: "Duplicates are fine; boundary variants of binary search handle them."}),
        q("dsa-bs-2", 1, "linear", U, "When is linear search the better choice?",
          ["When the data is unsorted and you search it only once",
           "When the data is sorted and searched many times",
           "Never; binary search is always faster", "When a very large array is sorted"], 0,
          "Sorting costs O(n log n), more than a single O(n) scan, so for one search on unsorted data linear "
          "search is cheaper."),
        q("dsa-bs-3", 2, "binary", A,
          "What is the largest number of comparisons binary search needs on a sorted array of 1,000 elements?",
          ["10", "100", "500", "1,000"], 0,
          "Each comparison halves the remaining range: 1,000 → 500 → … → 1 takes ⌊log₂ 1000⌋ + 1 = 10 "
          "comparisons.",
          {2: "500 would be a linear scan of half the array."}),
        q("dsa-bs-4", 2, "binary", U, "Why is binary search on a singly linked list not O(log n)?",
          ["Linked lists cannot be sorted", "Reaching the middle node means walking the list, which is O(n)",
           "Binary search only works on numbers", "Comparing nodes is slower than comparing array elements"], 1,
          "Binary search needs constant-time access to the middle element. A linked list only offers "
          "sequential access, so finding each middle costs linear time."),
        q("dsa-bs-5", 3, "boundaries", A,
          "lo, hi = 0, len(a)\nwhile lo < hi:\n    mid = (lo + hi) // 2\n    if a[mid] >= x:\n        hi = mid\n"
          "    else:\n        lo = mid + 1\nreturn lo\n\nFor a = [1, 3, 3, 5] and x = 3, what does this return?",
          ["0", "1", "2", "3"], 1,
          "It returns the first index whose value is at least x (the lower bound). Tracing: mid 2 → hi 2; "
          "mid 1 → hi 1; mid 0 → lo 1; the loop ends with lo = 1.",
          {2: "Index 2 is the last 3, not the first."}),
        q("dsa-bs-6", 3, "boundaries", N,
          "In the loop above, what goes wrong if hi = mid is changed to hi = mid − 1?",
          ["Nothing; it is equivalent",
           "It can skip the answer, because mid itself may be the first index with a[mid] ≥ x",
           "It becomes O(n)", "It loops forever on every input"], 1,
          "When a[mid] ≥ x, mid is still a candidate, so the search range must keep it. For a = [1, 3] and "
          "x = 3 the modified loop returns 0 instead of 1.",
          {0: "For a = [1, 3] and x = 3 the two versions return different indices."}),
    ],
)

SORTING = topic(
    "dsa-sorting",
    "Sorting: Bubble, Insertion, Merge and Quick Sort",
    "How the classic sorting algorithms work and when each is the right choice.",
    lesson=lesson(
        "Sorting algorithms differ in speed, in extra memory, and in whether equal elements keep their "
        "original order (stability).",
        [
            "Bubble sort repeatedly swaps adjacent elements that are out of order; each pass moves the largest "
            "remaining element to the end. Insertion sort inserts each element into the sorted prefix. Both are "
            "O(n²) in the worst case, but insertion sort is O(n) on nearly sorted input.",
            "Merge sort splits the array, sorts each half and merges them in linear time: Θ(n log n) on every "
            "input, stable, with O(n) extra space. Quicksort partitions around a pivot and sorts each side: "
            "O(n log n) on average and in place, but O(n²) when the pivots are consistently extreme.",
        ],
        [
            "Merge sort: guaranteed n log n, stable, extra space.",
            "Quicksort: fast on average, worst case n².",
            "Insertion sort shines on nearly sorted data.",
        ],
    ),
    concepts={
        "elementary": concept(
            "Bubble and insertion sort",
            "Bubble sort swaps adjacent out-of-order pairs; insertion sort grows a sorted prefix. Both are O(n²) "
            "in the worst case; insertion sort is O(n) on sorted input.",
        ),
        "merge": concept(
            "Merge sort",
            "Divide in half, sort both halves, merge in linear time: Θ(n log n) always, stable, O(n) extra space.",
        ),
        "quick": concept(
            "Quicksort",
            "Partition around a pivot and recurse. Average O(n log n), in place; worst case O(n²) when pivots are "
            "always the smallest or largest element.",
        ),
    },
    questions=[
        q("dsa-so-1", 1, "merge", R, "What is merge sort's worst-case time complexity?",
          ["O(n)", "O(n log n)", "O(n²)", "O(log n)"], 1,
          "There are about log n levels of splitting, and merging all the pieces at one level costs O(n).",
          {2: "O(n²) is the worst case of quicksort, bubble sort and insertion sort, not merge sort."}),
        q("dsa-so-2", 1, "elementary", U, "Which of these sorts is fastest on an array that is already sorted?",
          ["Insertion sort", "Selection sort", "Merge sort", "Heap sort"], 0,
          "Each element is compared once with its predecessor and stays put, so insertion sort does about n "
          "comparisons: O(n).",
          {2: "Merge sort still does Θ(n log n) work on sorted input."}),
        q("dsa-so-3", 2, "quick", U,
          "When does quicksort that always picks the first element as pivot hit its O(n²) worst case?",
          ["On random input", "On already sorted input", "When all elements are distinct", "Never"], 1,
          "On sorted input the first element is the smallest, so each partition puts everything on one side. "
          "The recursion depth becomes n and the work n + (n − 1) + … = Θ(n²)."),
        q("dsa-so-4", 2, "merge", A,
          "How many comparisons does the standard merge make when merging [1, 4, 7] with [2, 3, 9]?",
          ["3", "5", "6", "9"], 1,
          "1 < 2, 2 < 4, 3 < 4, 4 < 9 and 7 < 9: five comparisons. Once the first list is exhausted, 9 is "
          "appended without comparing."),
        q("dsa-so-5", 3, "elementary", A,
          "Bubble sort makes passes over [5, 1, 4, 2, 8], each pass moving the largest remaining element to the "
          "end. What is the array after two passes?",
          ["[1, 4, 2, 5, 8]", "[1, 2, 4, 5, 8]", "[1, 2, 5, 4, 8]", "[5, 1, 4, 2, 8]"], 1,
          "Pass 1 gives [1, 4, 2, 5, 8]; pass 2 swaps 4 and 2, giving [1, 2, 4, 5, 8].",
          {0: "That is the array after the first pass."}),
        q("dsa-so-6", 3, "quick", N,
          "You must sort 10 million records, equal keys must keep their original order, and worst-case time "
          "matters. Which algorithm fits?",
          ["Quicksort", "Merge sort", "Bubble sort", "Insertion sort"], 1,
          "Merge sort is stable and guaranteed Θ(n log n). A typical in-place quicksort is not stable and can "
          "degrade to O(n²).",
          {0: "Quicksort is fast on average but neither stable nor guaranteed n log n."}),
    ],
)

RECURSION = topic(
    "dsa-recursion",
    "Recursion Fundamentals and Backtracking",
    "Base cases, the cost of recursive calls, and searching by trying and undoing choices.",
    lesson=lesson(
        "A recursive function solves a problem by solving smaller instances of the same problem.",
        [
            "Every recursion needs a base case that stops it and a recursive case that moves towards the base "
            "case. Its cost is described by a recurrence: T(n) = T(n − 1) + O(1) is O(n), T(n) = 2T(n/2) + O(n) "
            "is O(n log n), while naive Fibonacci, T(n) = T(n − 1) + T(n − 2), grows exponentially because it "
            "recomputes the same values.",
            "Backtracking builds a solution one choice at a time and undoes the last choice when it cannot lead "
            "to a valid answer. Pruning those dead ends early is what keeps the search practical.",
        ],
        [
            "Base case first; each call must make progress.",
            "Write the recurrence to find the cost.",
            "Backtracking = choose, explore, undo.",
        ],
    ),
    concepts={
        "fundamentals": concept(
            "Base case and recursive case",
            "A base case stops the recursion; the recursive case must move towards it. Without a reachable base "
            "case the calls never end and the stack overflows.",
        ),
        "recurrence": concept(
            "Cost of recursion",
            "Describe the cost with a recurrence: T(n) = 2T(n/2) + O(n) is O(n log n); repeated overlapping "
            "calls, as in naive Fibonacci, make the cost exponential.",
        ),
        "backtracking": concept(
            "Backtracking",
            "Make a choice, explore it, undo it, and try the next. Prune any partial solution that can no longer "
            "become valid.",
        ),
    },
    questions=[
        q("dsa-rc-1", 1, "fundamentals", R, "What happens if a recursive function never reaches a base case?",
          ["It returns 0", "It keeps calling itself until the call stack overflows", "It runs in constant time",
           "The interpreter adds a base case automatically"], 1,
          "Each call pushes a new stack frame; without a base case they accumulate until the stack limit is "
          "reached (in Python, a RecursionError)."),
        q("dsa-rc-2", 1, "fundamentals", A,
          "def f(n):\n    if n == 0:\n        return 0\n    return n + f(n - 1)\n\nWhat does f(4) return?",
          ["4", "6", "10", "24"], 2,
          "Each call adds n to the result of the smaller call until the base case returns 0: "
          "f(4) = 4 + f(3) = 4 + 3 + 2 + 1 + 0 = 10.",
          {3: "24 is 4!, which multiplies instead of adds."}),
        q("dsa-rc-3", 2, "recurrence", U,
          "Why is the naive recursive Fibonacci, fib(n) = fib(n − 1) + fib(n − 2), so slow?",
          ["It uses floating-point numbers",
           "It recomputes the same subproblems many times, so the number of calls grows exponentially",
           "It has no base case", "Recursion is always slower than a loop"], 1,
          "fib(n − 2) is computed inside fib(n − 1) and again directly, and the duplication compounds at every "
          "level. Caching each result (memoization) brings the cost down to O(n)."),
        q("dsa-rc-4", 2, "backtracking", U, "In backtracking, what does pruning mean?",
          ["Deleting part of the input",
           "Abandoning a partial solution as soon as it cannot lead to a valid answer",
           "Sorting the choices alphabetically", "Converting the recursion into a loop"], 1,
          "Pruning cuts off whole subtrees of the search, which is where backtracking saves its time."),
        q("dsa-rc-5", 3, "recurrence", A, "What does the recurrence T(n) = 2T(n/2) + O(n) solve to?",
          ["O(n)", "O(n log n)", "O(n²)", "O(log n)"], 1,
          "There are log n levels and each level does O(n) work in total. This is merge sort's recurrence.",
          {0: "Each of the log n levels costs O(n), so the total is more than linear."}),
        q("dsa-rc-6", 3, "backtracking", N,
          "Generating all subsets of n distinct elements by deciding to include or exclude each element "
          "produces how many subsets?",
          ["n", "n²", "2ⁿ", "n!"], 2,
          "Each element is independently in or out: two choices per element gives 2ⁿ subsets.",
          {3: "n! counts orderings (permutations), not subsets."}),
    ],
)

TREES = topic(
    "dsa-trees",
    "Binary Trees, Binary Search Trees and Traversals",
    "Tree vocabulary, the four traversals, and why a BST's height matters.",
    lesson=lesson(
        "A binary tree gives each node at most two children; a binary search tree adds an ordering rule that "
        "makes searching fast.",
        [
            "Preorder visits a node before its subtrees, inorder between the left and right subtree, postorder "
            "after both; level order visits by depth using a queue. In a binary search tree every key in a "
            "node's left subtree is smaller and every key in its right subtree larger, so an inorder traversal "
            "lists the keys in sorted order.",
            "Depth counts edges from the root down to a node; height counts edges on the longest path down to a "
            "leaf. BST search, insert and delete cost O(h): O(log n) when the tree is balanced, but O(n) when "
            "keys are inserted in sorted order and the tree degenerates into a chain.",
        ],
        [
            "Inorder on a BST = sorted order.",
            "BST operations cost O(height).",
            "Sorted insertions make a plain BST a chain.",
        ],
    ),
    concepts={
        "traversal": concept(
            "Tree traversals",
            "Preorder: node, left, right. Inorder: left, node, right. Postorder: left, right, node. Level order: "
            "by depth, using a queue.",
        ),
        "bst": concept(
            "Binary search trees",
            "Left subtree keys are smaller, right subtree keys larger. Operations cost O(height): O(log n) if "
            "balanced, O(n) if the tree is a chain.",
        ),
        "height": concept(
            "Height and depth",
            "Depth: edges from the root to a node. Height: edges on the longest path from a node down to a leaf. "
            "A tree with n nodes has height at least ⌊log₂ n⌋.",
        ),
    },
    questions=[
        q("dsa-tr-1", 1, "traversal", R, "Which traversal of a binary search tree visits its keys in sorted order?",
          ["Preorder", "Inorder", "Postorder", "Level order"], 1,
          "Inorder visits the left subtree (smaller keys), then the node, then the right subtree (larger keys)."),
        q("dsa-tr-2", 1, "height", R, "Measuring depth in edges, what is the depth of the root node?",
          ["0", "1", "The height of the tree", "Undefined"], 0,
          "Depth counts the edges between the root and a node; the root is reached with none."),
        q("dsa-tr-3", 2, "traversal", A,
          "A tree has root 1; its left child 2 has children 4 and 5; its right child is 3. What is the "
          "preorder traversal?",
          ["4, 2, 5, 1, 3", "1, 2, 4, 5, 3", "4, 5, 2, 3, 1", "1, 2, 3, 4, 5"], 1,
          "Preorder visits a node, then its left subtree, then its right subtree: 1, then 2, 4, 5, then 3.",
          {0: "That is the inorder traversal.", 2: "That is the postorder traversal.",
           3: "That is the level-order traversal."}),
        q("dsa-tr-4", 2, "bst", A,
          "Insert 50, 30, 70, 20, 40 into an empty BST in that order. Which node is the parent of 40?",
          ["50", "30", "70", "20"], 1,
          "40 < 50 goes left to 30; 40 > 30 goes right, so 40 becomes 30's right child."),
        q("dsa-tr-5", 3, "bst", N,
          "Inserting the keys 1, 2, 3, …, n in increasing order into a plain, unbalanced BST gives what search "
          "cost?",
          ["O(1)", "O(log n)", "O(n)", "O(n log n)"], 2,
          "Each key becomes the right child of the previous one, so the tree is a chain of height n − 1 and a "
          "search may walk all of it. Self-balancing trees such as AVL or red-black trees prevent this.",
          {1: "O(log n) needs a balanced tree, which sorted insertions do not produce."}),
        q("dsa-tr-6", 3, "height", N, "What is the minimum height, in edges, of a binary tree with 15 nodes?",
          ["3", "4", "7", "14"], 0,
          "A perfect binary tree of height h holds 2^(h + 1) − 1 nodes; with h = 3 that is exactly 15.",
          {1: "Height 4 is possible, but 15 nodes fit in height 3 when every level is full.",
           3: "14 is the maximum height, when the tree is a chain."}),
    ],
)

HEAPS = topic(
    "dsa-heaps",
    "Heaps and Priority Queues",
    "Min-heaps, max-heaps, their operations, and serving the most urgent item first.",
    lesson=lesson(
        "A heap keeps the smallest (or largest) item instantly available while letting you add items cheaply.",
        [
            "In a min-heap every parent is no larger than its children, so the minimum sits at the root; a "
            "max-heap is the mirror image. A heap is a complete binary tree stored in an array: with 0-based "
            "indexing, node i's children are at 2i + 1 and 2i + 2.",
            "Insert appends at the end and sifts the item up; extract-min moves the last item to the root and "
            "sifts it down. Both are O(log n); reading the root is O(1). A priority queue, which always serves "
            "the highest-priority item next, is usually implemented with a heap; Python's heapq module keeps a "
            "min-heap in a list.",
        ],
        [
            "Root = minimum (min-heap) or maximum (max-heap).",
            "Insert and extract are O(log n).",
            "Children of i: 2i + 1 and 2i + 2.",
        ],
    ),
    concepts={
        "heap-property": concept(
            "Heap property",
            "Min-heap: every parent ≤ its children, so the minimum is at the root. The heap is not fully sorted.",
        ),
        "operations": concept(
            "Heap operations",
            "Insert: append, then sift up while the parent is larger. Extract-min: move the last item to the "
            "root, then sift down. Each is O(log n).",
        ),
        "priority-queue": concept(
            "Priority queues",
            "Always serve the most urgent item next. A heap gives O(log n) insert and removal and O(1) peek.",
        ),
    },
    questions=[
        q("dsa-hp-1", 1, "heap-property", R, "Where is the smallest element of a min-heap?",
          ["At the root", "At the last leaf", "In the left-most leaf", "It could be anywhere"], 0,
          "Every parent is no larger than its children, so following parents upwards always reaches smaller or "
          "equal values, ending at the root."),
        q("dsa-hp-2", 1, "operations", R, "What is the time complexity of inserting into a binary heap of n elements?",
          ["O(1)", "O(log n)", "O(n)", "O(n log n)"], 1,
          "The new item sifts up at most the height of the tree, which is O(log n) because the heap is a "
          "complete binary tree."),
        q("dsa-hp-3", 2, "heap-property", A,
          "In a heap stored as an array with 0-based indexing, where are the children of index i?",
          ["i − 1 and i + 1", "2i and 2i + 1", "2i + 1 and 2i + 2", "i/2 and i/2 + 1"], 2,
          "The root's children are at 1 and 2, index 1's at 3 and 4, and so on: 2i + 1 and 2i + 2.",
          {1: "2i and 2i + 1 is the formula for 1-based indexing."}),
        q("dsa-hp-4", 2, "priority-queue", U, "Which task is best served by a priority queue?",
          ["Reversing a string",
           "Repeatedly processing whichever waiting job has the earliest deadline",
           "Checking that brackets are balanced", "Looking up a word's definition"], 1,
          "A priority queue always hands out the most urgent item next, here the earliest deadline, in "
          "O(log n) per operation."),
        q("dsa-hp-5", 3, "operations", A,
          "Insert 1 into the min-heap stored as [2, 5, 3, 9, 7]. What is the array after sift-up?",
          ["[1, 5, 2, 9, 7, 3]", "[1, 2, 3, 5, 7, 9]", "[2, 5, 1, 9, 7, 3]", "[1, 2, 5, 9, 7, 3]"], 0,
          "1 goes to index 5; its parent (index 2) holds 3, so they swap; the new parent (index 0) holds 2, so "
          "they swap again: [1, 5, 2, 9, 7, 3].",
          {1: "A heap is not fully sorted; sift-up only swaps along one path.",
           2: "Sift-up continues while the parent is larger, and 1 is smaller than the root 2."}),
        q("dsa-hp-6", 3, "priority-queue", N, "Which approach finds the k largest of n numbers in O(n log k)?",
          ["Sort everything and take the last k",
           "Keep a min-heap of size k, replacing its root whenever a larger number arrives",
           "Put all n numbers into a max-heap and never pop", "Scan k times for the maximum, removing it each time"], 1,
          "The heap never exceeds k items, so each of the n numbers costs at most O(log k). Its root is always "
          "the smallest of the current top k.",
          {0: "This is correct but costs O(n log n).", 3: "This costs O(nk)."}),
    ],
)

GRAPHS = topic(
    "dsa-graphs",
    "Graphs: Representation, BFS, DFS and Shortest-Path Fundamentals",
    "Storing graphs, exploring them breadth-first and depth-first, and when weights change the rules.",
    lesson=lesson(
        "A graph is a set of vertices joined by edges; most graph algorithms are a systematic way of visiting "
        "them.",
        [
            "An adjacency list stores each vertex's neighbours, using O(V + E) memory, which suits sparse "
            "graphs. An adjacency matrix stores a V × V grid: O(V²) memory but an O(1) test for any edge.",
            "Breadth-first search explores in layers with a queue, so in an unweighted graph it finds shortest "
            "paths measured in edges. Depth-first search follows one branch as deep as it can before "
            "backtracking, using recursion or a stack. Both take O(V + E) with adjacency lists. When edges have "
            "different positive weights, the fewest edges is no longer the cheapest path, and Dijkstra's "
            "algorithm with a priority queue is used instead.",
        ],
        [
            "Sparse graph → adjacency list.",
            "BFS = queue = shortest paths in unweighted graphs.",
            "Weighted edges need Dijkstra, not plain BFS.",
        ],
    ),
    concepts={
        "representation": concept(
            "Graph representation",
            "Adjacency list: O(V + E) memory, iterate neighbours quickly. Adjacency matrix: O(V²) memory, O(1) "
            "edge test.",
        ),
        "bfs": concept(
            "Breadth-first search",
            "Visit vertices in order of distance from the source using a queue: shortest paths by edge count, "
            "O(V + E).",
        ),
        "dfs": concept(
            "Depth-first search",
            "Go as deep as possible along each branch before backtracking, with recursion or a stack: O(V + E).",
        ),
    },
    questions=[
        q("dsa-gr-1", 1, "bfs", R, "Which data structure does breadth-first search use to decide what to visit next?",
          ["Stack", "Queue", "Heap", "Only a hash set"], 1,
          "A queue makes BFS finish every vertex at distance d before any vertex at distance d + 1.",
          {0: "A stack gives depth-first order."}),
        q("dsa-gr-2", 1, "representation", U,
          "For a sparse graph with many vertices and few edges, which representation uses less memory?",
          ["Adjacency matrix", "Adjacency list", "They always use the same memory", "An edge-weight table"], 1,
          "An adjacency list stores only the edges that exist, O(V + E); a matrix always stores V² entries."),
        q("dsa-gr-3", 2, "bfs", U, "Why does BFS find shortest paths in an unweighted graph?",
          ["It visits vertices in order of their distance (number of edges) from the source",
           "It always picks the smallest vertex label", "It uses a priority queue", "It visits every edge twice"], 0,
          "Because of the queue, the first time BFS reaches a vertex is along a path with the fewest possible "
          "edges."),
        q("dsa-gr-4", 2, "dfs", A,
          "Edges: A–B, A–C, B–D, C–D. Neighbours are visited in alphabetical order. What is the DFS order "
          "starting from A?",
          ["A, B, C, D", "A, B, D, C", "A, C, D, B", "A, D, B, C"], 1,
          "From A go to B, from B to its unvisited neighbour D, from D to C. Every vertex is then visited.",
          {0: "That is the BFS order: it visits both of A's neighbours before going deeper."}),
        q("dsa-gr-5", 3, "representation", N,
          "What is the time complexity of BFS on a graph with V vertices and E edges stored as an adjacency "
          "matrix?",
          ["O(V + E)", "O(V²)", "O(E log V)", "O(V)"], 1,
          "Finding a vertex's neighbours means scanning its whole row of V entries, so visiting V vertices costs "
          "O(V²) whatever E is.",
          {0: "O(V + E) holds for adjacency lists, where each vertex's neighbours are listed directly."}),
        q("dsa-gr-6", 3, "bfs", N,
          "When edges have different positive weights, why is plain BFS no longer enough for shortest paths?",
          ["BFS cannot handle more than a few hundred vertices",
           "BFS minimises the number of edges, not the total weight; Dijkstra's algorithm with a priority "
           "queue is needed",
           "Weighted graphs have no shortest paths", "BFS only works on trees"], 1,
          "A path with more edges can be cheaper than one with fewer. Dijkstra's algorithm always expands the "
          "vertex with the smallest known total distance."),
    ],
)

DP = topic(
    "dsa-dp",
    "Dynamic Programming: Memoization, Tabulation and Simple Patterns",
    "Solving each overlapping subproblem once, top-down or bottom-up.",
    lesson=lesson(
        "Dynamic programming applies when a problem breaks into overlapping subproblems whose optimal answers "
        "combine into the optimal whole.",
        [
            "Memoization is top-down: write the natural recursion and cache each subproblem's answer the first "
            "time it is computed. Tabulation is bottom-up: fill a table from the smallest subproblems upwards, "
            "in an order where every dependency is already available.",
            "Designing a DP means naming the state (what defines a subproblem), the transition (how it builds on "
            "smaller ones) and the base cases. Climbing stairs, coin change and longest common subsequence all "
            "follow this recipe.",
        ],
        [
            "Overlapping subproblems + optimal substructure.",
            "Memoization = top-down cache; tabulation = bottom-up table.",
            "State, transition, base case.",
        ],
    ),
    concepts={
        "memoization": concept(
            "Memoization",
            "Top-down: recurse naturally but cache every result, so each subproblem is solved once.",
        ),
        "tabulation": concept(
            "Tabulation",
            "Bottom-up: fill a table from the base cases upwards so every value a cell needs is already computed.",
        ),
        "patterns": concept(
            "DP patterns",
            "Define the state, the transition and the base cases. Coin change: dp[a] = min over coins c ≤ a of "
            "dp[a − c] + 1.",
        ),
    },
    questions=[
        q("dsa-dp-1", 1, "memoization", R, "Which two properties make a problem suitable for dynamic programming?",
          ["Sorted input and unique values", "Overlapping subproblems and optimal substructure",
           "A graph and a source vertex", "Recursion and a global variable"], 1,
          "Overlapping subproblems make caching worthwhile; optimal substructure lets optimal sub-answers "
          "combine into an optimal answer."),
        q("dsa-dp-2", 1, "tabulation", U, "What distinguishes tabulation from memoization?",
          ["Tabulation is top-down and memoization bottom-up",
           "Tabulation fills a table bottom-up iteratively; memoization caches the results of a top-down "
           "recursion",
           "Only memoization stores results", "Tabulation cannot compute Fibonacci numbers"], 1,
          "Both store each subproblem's answer once. They differ in direction: recursion with a cache versus an "
          "explicit loop over a table.",
          {0: "It is the other way round."}),
        q("dsa-dp-3", 2, "memoization", A, "What is the time complexity of computing fib(n) with memoization?",
          ["O(2ⁿ)", "O(n)", "O(n²)", "O(log n)"], 1,
          "Each of fib(0) … fib(n) is computed once and every other call is an O(1) cache hit, so the work is "
          "O(n).",
          {0: "O(2ⁿ) is the naive recursion without a cache."}),
        q("dsa-dp-4", 2, "patterns", A,
          "You climb a staircase taking 1 or 2 steps at a time. With ways(1) = 1 and ways(2) = 2, how many "
          "distinct ways are there to climb 5 steps?",
          ["5", "8", "10", "13"], 1,
          "ways(n) = ways(n − 1) + ways(n − 2): ways(3) = 3, ways(4) = 5, ways(5) = 8.",
          {3: "13 is ways(6)."}),
        q("dsa-dp-5", 3, "patterns", N,
          "For coin change (the fewest coins that make amount a from coins c₁ … cₖ), which transition is correct?",
          ["dp[a] = min over coins c ≤ a of dp[a − c] + 1", "dp[a] = dp[a − 1] + dp[a − 2]",
           "dp[a] = max over coins c of dp[a − c]", "dp[a] = a / (largest coin)"], 0,
          "The last coin used is some c; the best way to make the rest is dp[a − c]. Trying every c and adding "
          "one coin gives the optimum.",
          {3: "Greedy use of the largest coin fails for some coin systems: with coins {1, 3, 4} and a = 6 it "
              "gives 4 + 1 + 1 (three coins) instead of 3 + 3 (two)."}),
        q("dsa-dp-6", 3, "tabulation", A,
          "In the bottom-up table for the longest common subsequence of strings X and Y, if X[i] == Y[j], then "
          "L[i][j] equals:",
          ["L[i − 1][j − 1] + 1", "max(L[i − 1][j], L[i][j − 1])", "L[i − 1][j] + L[i][j − 1]", "0"], 0,
          "A matching character extends the best subsequence of the two shorter prefixes by one.",
          {1: "That is the case when the characters differ."}),
    ],
)

SUBJECT = subject(
    "dsa",
    "DSA",
    "Data Structures & Algorithms",
    "DSA",
    "foundation",
    "Core data structures and algorithms: complexity, arrays, linked lists, stacks and queues, hashing, "
    "searching and sorting, recursion, trees, heaps, graphs and dynamic programming.",
    [
        unit(1, "Complexity", [ASYMPTOTIC]),
        unit(2, "Arrays & Strings", [
            TWO_POINTERS,
            topic("dsa-strings", "String Manipulation",
                  "Building, slicing and comparing strings efficiently.", level="Beginner"),
        ]),
        unit(3, "Linked Lists", [LINKED_LISTS]),
        unit(4, "Stacks & Queues", [STACKS_QUEUES]),
        unit(5, "Hashing", [HASHING]),
        unit(6, "Searching & Sorting", [SEARCHING, SORTING]),
        unit(7, "Recursion", [RECURSION]),
        unit(8, "Trees", [
            TREES,
            topic("dsa-balanced-trees", "Balanced Search Trees",
                  "Keeping a BST's height logarithmic: rotations, AVL and red-black trees."),
        ]),
        unit(9, "Heaps", [HEAPS]),
        unit(10, "Graphs", [
            GRAPHS,
            topic("dsa-shortest-paths", "Shortest Paths: Dijkstra and Bellman–Ford",
                  "Weighted shortest paths with and without negative edges."),
        ]),
        unit(11, "Dynamic Programming", [DP]),
    ],
    unit_label="Unit",
    area="foundations",
)
