"""(22PC1AM301) Artificial Intelligence — VNR VJIET B.Tech. AIML R22, V Semester."""

from __future__ import annotations

from skillforge.teacher.content._build import concept, lesson, question, subject, topic, unit

AGENTS = topic(
    "ai-intelligent-agents",
    "Intelligent Agents: Agents and Environments, Rationality, Nature of Environments",
    "What an agent is, what makes it rational, how environments differ, and how agent structure follows.",
    level="Beginner",
    lesson=lesson(
        "An agent is anything that perceives its environment through sensors and acts upon it through "
        "actuators. Artificial intelligence studies how to build agents that act well.",
        [
            "A rational agent selects, for every percept sequence, the action expected to maximize its "
            "performance measure given what it has perceived and what it knows. Rationality is judged "
            "against the performance measure; it is not omniscience.",
            "Environments differ: fully or partially observable, deterministic or stochastic, static or "
            "dynamic, discrete or continuous, single- or multi-agent. These properties drive the agent's "
            "structure, from simple reflex agents (condition–action rules) to model-based, goal-based and "
            "utility-based agents.",
        ],
        [
            "Agent = sensors + actuators + agent program.",
            "Rational = maximizes expected performance measure.",
            "Harder environments need richer agent structures.",
        ],
    ),
    concepts={
        "agent-environment": concept(
            "Agents and environments",
            "Percepts come in through sensors; actions go out through actuators. The agent program maps "
            "percept sequences to actions, and simple reflex agents do so from the current percept alone.",
        ),
        "rationality": concept(
            "The concept of rationality",
            "Rationality is defined by the performance measure. The same behaviour can be rational under "
            "one measure and irrational under another.",
        ),
        "environments": concept(
            "The nature of environments",
            "Classify the task environment by observability, determinism, dynamics, and discreteness. "
            "Partially observable, stochastic, dynamic environments need internal models and utilities.",
        ),
    },
    questions=[
        question(
            "ai-ag-1", 1, "agent-environment",
            "An agent perceives its environment through ___ and acts upon it through ___.",
            ["actuators; sensors", "sensors; actuators", "goals; percepts", "rules; states"], 1,
            "Sensors deliver percepts into the agent; actuators carry its actions out into the environment.",
        ),
        question(
            "ai-ag-2", 1, "rationality",
            "Which statement describes a rational agent?",
            ["It always knows the actual outcome of its actions",
             "It imitates how a human would act",
             "It selects the action expected to maximize its performance measure, given its percepts and "
             "knowledge",
             "It chooses actions at random to explore"], 2,
            "Rationality maximizes expected performance given the evidence available. Knowing actual "
            "outcomes would be omniscience, which no agent has.",
            {0: "That is omniscience. A rational agent acts on expected outcomes, not certain ones."},
        ),
        question(
            "ai-ag-3", 2, "environments",
            "How is the task environment of a crossword-puzzle solver best described?",
            ["Partially observable, stochastic, dynamic",
             "Fully observable, deterministic, static",
             "Fully observable, stochastic, dynamic",
             "Partially observable, deterministic, continuous"], 1,
            "The whole grid is visible, filling a cell has a certain result, and the puzzle does not change "
            "while the agent deliberates.",
        ),
        question(
            "ai-ag-4", 2, "agent-environment",
            "Which type of agent chooses actions using only the current percept, through condition–action "
            "rules?",
            ["Goal-based agent", "Utility-based agent", "Model-based reflex agent", "Simple reflex agent"], 3,
            "A simple reflex agent ignores percept history and fires the rule whose condition matches the "
            "current percept.",
            {2: "A model-based reflex agent keeps internal state about the parts of the world it cannot "
                "currently see."},
        ),
        question(
            "ai-ag-5", 3, "environments",
            "Automated taxi driving is partially observable, stochastic and dynamic. Which agent design fits "
            "best?",
            ["A utility-based agent that maintains an internal model of the world",
             "A simple reflex agent with a lookup table of rules",
             "A table-driven agent listing an action for every percept sequence",
             "A random agent"], 0,
            "Partial observability needs an internal model; uncertainty and competing goals (safety, speed, "
            "comfort) need a utility to trade them off.",
            {2: "A table for every percept sequence would be astronomically large for driving."},
        ),
        question(
            "ai-ag-6", 3, "rationality",
            "A vacuum agent cleans every square, then keeps moving back and forth forever, losing a point "
            "for every move. What does this show?",
            ["Its behaviour is rational because the floor is clean",
             "Its behaviour is irrational under a performance measure that penalizes movement",
             "Rational agents must be omniscient",
             "Any action is rational in a fully observable environment"], 1,
            "Rationality is judged against the performance measure. Once the floor is clean, moving only "
            "loses points, so a rational agent would stop.",
        ),
    ],
)

SEARCH = topic(
    "ai-search-strategies",
    "Searching: Uninformed Search, Heuristic Search and Local Search",
    "Breadth-first and depth-limited search, greedy best-first and A*, and local search such as hill "
    "climbing and simulated annealing.",
    lesson=lesson(
        "Problem-solving agents search: they explore sequences of actions from the initial state until they "
        "reach a goal state.",
        [
            "Uninformed strategies use only the problem definition. Breadth-first search expands the "
            "shallowest node first; depth-limited search is depth-first search that stops at a fixed depth. "
            "Heuristic (informed) strategies add an estimate h(n) of the cost to the goal: greedy best-first "
            "expands the node with the smallest h(n); A* expands the node with the smallest "
            "f(n) = g(n) + h(n).",
            "Local search keeps only the current state and moves to neighbours. Hill climbing can stall at "
            "local maxima, ridges and plateaux; simulated annealing sometimes accepts worse moves so it can "
            "escape, with that probability falling as the temperature cools.",
        ],
        [
            "BFS: FIFO frontier, shallowest first.",
            "A*: f(n) = g(n) + h(n); optimal with an admissible heuristic.",
            "Simulated annealing accepts bad moves early to escape local maxima.",
        ],
    ),
    concepts={
        "uninformed": concept(
            "Uninformed search",
            "Breadth-first search uses a FIFO queue and finds the shallowest goal. Depth-limited search "
            "explores depth-first but never past the limit ℓ, so goals deeper than ℓ are missed.",
        ),
        "heuristic": concept(
            "Heuristic search: Greedy best-first and A*",
            "Greedy uses h(n) only and can be misled. A* adds the path cost so far, f(n) = g(n) + h(n), and "
            "is optimal when h never overestimates the true cost (admissible).",
        ),
        "local": concept(
            "Local search algorithms",
            "Hill climbing always moves uphill and can get stuck. Simulated annealing occasionally accepts a "
            "worse neighbour, more often at high temperature, to escape local maxima.",
        ),
    },
    questions=[
        question(
            "ai-s-1", 1, "uninformed",
            "In what order does breadth-first search expand nodes?",
            ["Deepest unexpanded node first",
             "Shallowest unexpanded node first, using a FIFO queue",
             "Lowest heuristic value first",
             "In random order"], 1,
            "BFS keeps its frontier in a FIFO queue, so all nodes at depth d are expanded before any node at "
            "depth d + 1.",
            {0: "Deepest-first is depth-first search, which uses a LIFO stack."},
        ),
        question(
            "ai-s-2", 1, "heuristic",
            "A* search ranks frontier nodes by which evaluation function?",
            ["f(n) = h(n)", "f(n) = g(n)", "f(n) = g(n) + h(n)", "f(n) = g(n) × h(n)"], 2,
            "A* adds the cost so far, g(n), to the estimated cost to the goal, h(n).",
            {0: "Ranking by h(n) alone is greedy best-first search.",
             1: "Ranking by g(n) alone is uniform-cost search."},
        ),
        question(
            "ai-s-3", 2, "heuristic",
            "What is the main weakness of greedy best-first search?",
            ["It ignores the path cost so far, so it is not optimal and can be misled by the heuristic",
             "It always uses more memory than breadth-first search",
             "It cannot use a heuristic function",
             "It always expands every node in the state space"], 0,
            "Greedy search chases whatever looks closest to the goal by h(n). Because it ignores g(n), it can "
            "commit to an expensive path.",
        ),
        question(
            "ai-s-4", 2, "uninformed",
            "Depth-limited search with limit ℓ fails to find a goal at depth d when:",
            ["d < ℓ", "d = ℓ", "the branching factor is large", "d > ℓ"], 3,
            "Nodes deeper than the limit are never generated, so a goal deeper than ℓ is unreachable. "
            "Iterative deepening fixes this by raising ℓ step by step.",
        ),
        question(
            "ai-s-5", 3, "heuristic",
            "A* tree search is guaranteed to return an optimal solution when the heuristic is:",
            ["larger than the true cost to the goal",
             "admissible: it never overestimates the true cost to the goal",
             "computed by hill climbing",
             "zero only at the start state"], 1,
            "With an admissible heuristic, f(n) never overestimates the cost of a solution through n, so A* "
            "cannot return a suboptimal goal before the optimal one.",
            {0: "An overestimating heuristic can make A* skip the optimal path."},
        ),
        question(
            "ai-s-6", 3, "local",
            "Why does simulated annealing sometimes accept a move to a worse state?",
            ["Because it cannot evaluate neighbouring states",
             "To guarantee the global optimum within a fixed number of steps",
             "To escape local maxima; the probability of accepting bad moves falls as the temperature "
             "decreases",
             "Because it keeps a population of states, like a genetic algorithm"], 2,
            "Occasional downhill moves let the search leave a local maximum. Early on (high temperature) "
            "they are common; as it cools the search behaves more like hill climbing.",
            {3: "Keeping a population of states describes genetic algorithms and local beam search."},
        ),
    ],
)

SUBJECT = subject(
    "artificial-intelligence",
    "22PC1AM301",
    "Artificial Intelligence",
    "AI",
    "theory",
    "Agents, search, constraint satisfaction and game playing, knowledge representation, learning and "
    "expert systems.",
    [
        unit(1, "Introduction", [
            topic("ai-foundations", "AI Problems, Foundations and History of AI",
                  "What AI problems look like and where the field came from.", level="Beginner"),
            AGENTS,
            topic("ai-problem-solving", "Problem Solving Agents and Problem Formulation",
                  "States, actions, goal tests and path costs."),
        ]),
        unit(2, "Searching", [
            SEARCH,
            topic("ai-memory-bounded", "Memory-Bounded Heuristic Search",
                  "Heuristic search that works within limited memory."),
            topic("ai-genetic", "Local Beam Search and Genetic Algorithms",
                  "Population-based local search."),
        ]),
        unit(3, "Constraint Satisfaction Problems and Game Playing", [
            topic("ai-csp", "Backtracking Search and Local Search for CSPs",
                  "Solving constraint satisfaction problems."),
            topic("ai-games", "Adversarial Search: Minimax and Alpha-Beta Pruning",
                  "Optimal decisions in games, evaluation functions and cutting off search."),
        ]),
        unit(4, "Knowledge Representation", [
            topic("ai-knowledge", "Procedural Versus Declarative Knowledge",
                  "Two ways of representing what an agent knows."),
            topic("ai-predicate-logic", "Predicate Logic: Representing Facts, Functions and Predicates",
                  "Using predicate logic to represent facts."),
            topic("ai-resolution", "Clause Form, Resolution and Unification",
                  "Resolution in propositional and predicate logic."),
        ]),
        unit(5, "Learning and Expert Systems", [
            topic("ai-learning", "Learning: Taking Advice, Problem Solving, Induction, "
                  "Explanation-Based Learning", "Forms of learning in AI systems."),
            topic("ai-expert-systems", "Expert Systems: Domain Knowledge, Reasoning, Shells and "
                  "Knowledge Acquisition", "How expert systems represent and use knowledge."),
        ]),
    ],
)
