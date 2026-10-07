"""The Teacher Agent's curriculum: a small, hand-written question bank.

Three subjects x three topics. Each topic has a short lesson, a handful of
named concepts (with a one-paragraph "re-teach" note the Teacher uses when a
student keeps missing that concept), and six multiple-choice questions —
two per difficulty level (1 = Foundational, 2 = Intermediate,
3 = Advanced).

Answers and explanations live here alongside the questions, but they only
leave the backend through :func:`public_question` (which strips them) or
after the student has answered. The engine is the only consumer of the
answer key.
"""

from __future__ import annotations

from typing import Any

LEVEL_NAMES = {1: "Foundational", 2: "Intermediate", 3: "Advanced"}

SUBJECTS: list[dict[str, Any]] = [
    {
        "id": "ml",
        "name": "Machine Learning",
        "description": "Core ideas behind how models learn from data and how to tell when they generalize.",
        "topics": [
            {
                "id": "decision-trees",
                "title": "Decision Trees",
                "summary": "How trees split data, measure impurity, and why they need to be kept in check.",
                "lesson": {
                    "intro": (
                        "Before we begin, let's establish the core idea. A decision tree makes predictions "
                        "by repeatedly splitting data according to conditions. Each split attempts to "
                        "separate the data into increasingly useful groups."
                    ),
                    "body": [
                        "At every internal node the tree asks a yes/no question about one feature, such as "
                        "\"income > 50k?\". It picks the question that makes the resulting groups as pure "
                        "as possible, measured with entropy or Gini impurity. Information gain is simply "
                        "how much a split reduces that impurity.",
                        "Leaves hold the final prediction. Left unchecked, a tree will keep splitting until "
                        "every leaf is perfectly pure — memorizing the training data. Limiting depth or "
                        "requiring a minimum number of samples per leaf (pruning) keeps it general.",
                    ],
                    "key_points": [
                        "Internal nodes test a feature; leaves make predictions.",
                        "Entropy and Gini measure impurity; information gain measures improvement.",
                        "Depth limits and pruning prevent memorization.",
                    ],
                },
                "concepts": {
                    "tree-structure": {
                        "name": "Tree structure",
                        "reteach": "Think of the tree as a flowchart: each internal node is a question "
                        "about a feature, each branch is an answer, and each leaf is the final prediction.",
                    },
                    "splitting-criteria": {
                        "name": "Splitting criteria",
                        "reteach": "A split is good when the groups it creates are purer than before. "
                        "Entropy and Gini are the two standard ways to measure purity; information gain is "
                        "the drop in entropy a split achieves.",
                    },
                    "pruning": {
                        "name": "Controlling complexity",
                        "reteach": "A tree that grows until every leaf is pure memorizes noise. Capping "
                        "max_depth, raising min_samples_leaf, or pruning back weak branches trades a little "
                        "training accuracy for much better generalization.",
                    },
                },
                "questions": [
                    {
                        "id": "dt-1",
                        "why_wrong": {
                            0: (
                                "You're close, but you're mixing split criteria with optimization "
                                'parameters. Learning rate controls step size in gradient descent; '
                                'it plays no part in choosing a split.'
                            ),
                            2: (
                                "You're close, but you're mixing split criteria with optimization "
                                'parameters. Epochs count passes over the data in iterative '
                                "training; trees don't train in epochs."
                            ),
                            3: (
                                "You're close, but you're mixing split criteria with optimization "
                                'parameters. Batch size belongs to mini-batch gradient descent, not'
                                ' to tree construction.'
                            ),
                        },
                        "difficulty": 1,
                        "concept": "splitting-criteria",
                        "prompt": "Which of the following is commonly used to determine how a decision tree "
                        "should split data?",
                        "options": ["Learning rate", "Entropy", "Epoch count", "Batch size"],
                        "answer": 1,
                        "explanation": "Entropy measures how mixed the classes in a node are, so the tree "
                        "prefers splits that reduce it. Learning rate, epochs, and batch size belong to "
                        "iterative optimization methods such as gradient descent, not tree construction.",
                    },
                    {
                        "id": "dt-2",
                        "why_wrong": {
                            0: 'That describes an internal node, not a leaf: internal nodes test features.',
                            2: "Learning rate isn't part of a decision tree's structure at all.",
                            3: (
                                'A complete pass over the data is an epoch, a training concept '
                                'rather than a node.'
                            ),
                        },
                        "difficulty": 1,
                        "concept": "tree-structure",
                        "prompt": "In a decision tree, what does a leaf node represent?",
                        "options": [
                            "A feature the tree will split on next",
                            "A final prediction",
                            "The learning rate for that branch",
                            "A complete pass over the training data",
                        ],
                        "answer": 1,
                        "explanation": "Leaves are where the questions stop: each one holds a prediction "
                        "(a class or a value). Internal nodes are the ones that test features.",
                    },
                    {
                        "id": "dt-3",
                        "why_wrong": {
                            1: (
                                'Information gain is computed on the training data at the node, not'
                                ' from test-set accuracy.'
                            ),
                            2: 'The number of leaves describes tree size, not how good a split is.',
                            3: 'Depth is a consequence of splitting, not the measure used to choose a split.',
                        },
                        "difficulty": 2,
                        "concept": "splitting-criteria",
                        "prompt": "What does information gain measure for a candidate split?",
                        "options": [
                            "The reduction in entropy achieved by the split",
                            "The increase in test-set accuracy after the split",
                            "The number of leaves the split creates",
                            "How deep the tree becomes after the split",
                        ],
                        "answer": 0,
                        "explanation": "Information gain is the parent node's entropy minus the weighted "
                        "entropy of its children. The bigger the drop, the more useful the split.",
                    },
                    {
                        "id": "dt-4",
                        "why_wrong": {
                            0: "3 is the depth itself, not the number of leaves.",
                            1: "6 would mean adding two leaves per level; a binary split doubles them.",
                            3: "9 is 3 squared, but each level doubles the count: 2 cubed, not 3 squared.",
                        },
                        "difficulty": 2,
                        "concept": "tree-structure",
                        "prompt": "A binary decision tree has a maximum depth of 3. What is the largest "
                        "number of leaf nodes it can have?",
                        "options": ["3", "6", "8", "9"],
                        "answer": 2,
                        "explanation": "Each level of binary splits can at most double the number of nodes: "
                        "depth 1 gives 2 leaves, depth 2 gives 4, depth 3 gives 2³ = 8. Depth directly caps "
                        "how finely a tree can partition the data.",
                    },
                    {
                        "id": "dt-5",
                        "why_wrong": {
                            0: (
                                'A deeper tree would memorize even more, widening the gap between '
                                'training and validation.'
                            ),
                            2: 'More features give the tree more ways to memorize noise.',
                            3: 'Evaluating on training data would hide the problem rather than fix it.',
                        },
                        "difficulty": 3,
                        "concept": "pruning",
                        "prompt": "A fully grown tree reaches 100% training accuracy but only 68% "
                        "validation accuracy. Which change most directly addresses this?",
                        "options": [
                            "Increase max_depth so the tree can learn more patterns",
                            "Limit max_depth or raise min_samples_leaf",
                            "Add more features to every sample",
                            "Evaluate on the training set instead",
                        ],
                        "answer": 1,
                        "explanation": "The gap between training and validation accuracy is classic "
                        "overfitting. Constraining the tree's growth stops it from memorizing noise; "
                        "making it deeper would widen the gap.",
                    },
                    {
                        "id": "dt-6",
                        "why_wrong": {
                            0: 'Entropy is 0 only for a pure node; this one is evenly mixed.',
                            1: '0.5 is the class proportion, not the entropy.',
                            3: 'For two classes, base-2 entropy tops out at 1.',
                        },
                        "difficulty": 3,
                        "concept": "splitting-criteria",
                        "prompt": "A node holds 8 positive and 8 negative samples. What is its entropy "
                        "(base 2)?",
                        "options": ["0", "0.5", "1", "2"],
                        "answer": 2,
                        "explanation": "With a 50/50 split, entropy = -(0.5·log2 0.5 + 0.5·log2 0.5) = 1, "
                        "the maximum for two classes. It means the node is as mixed as it can be.",
                    },
                ],
            },
            {
                "id": "overfitting",
                "title": "Overfitting",
                "summary": "Recognizing when a model memorizes instead of learning, and the tools to fix it.",
                "lesson": {
                    "intro": (
                        "Let's start with the central tension in machine learning: we train on one set of "
                        "data, but we care about performance on data the model has never seen."
                    ),
                    "body": [
                        "A model overfits when it learns the noise in its training data along with the "
                        "signal. The tell-tale sign is a generalization gap: excellent training performance, "
                        "noticeably worse validation performance.",
                        "We detect overfitting by holding data out (a validation set or k-fold "
                        "cross-validation) and we reduce it with regularization, early stopping, simpler "
                        "models, or more data. Push too hard, though, and the model underfits.",
                    ],
                    "key_points": [
                        "Overfitting = low training error, high validation error.",
                        "Validation data estimates performance on unseen examples.",
                        "Regularization and early stopping trade variance for bias.",
                    ],
                },
                "concepts": {
                    "generalization-gap": {
                        "name": "Generalization gap",
                        "reteach": "Compare training and validation performance. If training keeps "
                        "improving while validation stalls or worsens, the model is memorizing rather than "
                        "learning patterns that transfer.",
                    },
                    "validation": {
                        "name": "Validation strategy",
                        "reteach": "Data the model trains on can't tell you how it will do on new data. "
                        "A held-out validation set — or k-fold cross-validation when data is scarce — gives "
                        "an honest estimate.",
                    },
                    "regularization": {
                        "name": "Regularization",
                        "reteach": "Regularization adds a penalty for complexity (for example, large "
                        "weights under L2). A moderate penalty curbs overfitting; an excessive one forces "
                        "the model to be too simple and it underfits.",
                    },
                },
                "questions": [
                    {
                        "id": "of-1",
                        "difficulty": 1,
                        "concept": "generalization-gap",
                        "prompt": "A model performs very well on its training data but poorly on new data. "
                        "What is this called?",
                        "options": ["Underfitting", "Overfitting", "Normalization", "Convergence"],
                        "answer": 1,
                        "explanation": "Strong training performance paired with weak performance on new "
                        "data is the definition of overfitting. Underfitting would show poor performance on "
                        "both.",
                    },
                    {
                        "id": "of-2",
                        "difficulty": 1,
                        "concept": "validation",
                        "prompt": "Why do we keep a separate validation set?",
                        "options": [
                            "To make training run faster",
                            "To estimate how the model performs on unseen data",
                            "To increase the size of the training set",
                            "To remove outliers automatically",
                        ],
                        "answer": 1,
                        "explanation": "The validation set is data the model never trains on, so its score "
                        "is an honest estimate of real-world performance and lets us spot overfitting.",
                    },
                    {
                        "id": "of-3",
                        "difficulty": 2,
                        "concept": "regularization",
                        "prompt": "How does L2 regularization reduce overfitting?",
                        "options": [
                            "By training for more epochs",
                            "By penalizing large weights in the loss",
                            "By removing the bias term",
                            "By increasing the learning rate",
                        ],
                        "answer": 1,
                        "explanation": "L2 adds λ·Σw² to the loss, so the optimizer prefers smaller "
                        "weights. Smaller weights mean a smoother function that is less able to chase noise.",
                    },
                    {
                        "id": "of-4",
                        "difficulty": 2,
                        "concept": "generalization-gap",
                        "prompt": "Training loss keeps falling while validation loss starts rising. What is "
                        "the most sensible action?",
                        "options": [
                            "Train for more epochs until validation loss recovers",
                            "Stop training near the point where validation loss was lowest",
                            "Increase the model's size",
                            "Shrink the validation set",
                        ],
                        "answer": 1,
                        "explanation": "Diverging curves mean the model has started memorizing. Early "
                        "stopping keeps the weights from the epoch with the best validation loss.",
                    },
                    {
                        "id": "of-5",
                        "difficulty": 3,
                        "concept": "validation",
                        "prompt": "Why is k-fold cross-validation often preferred over a single "
                        "train/validation split on a small dataset?",
                        "options": [
                            "Every example is used for both training and validation across folds, giving a "
                            "more reliable estimate",
                            "It trains one larger model, which generalizes better",
                            "It removes the need for a final test set",
                            "It guarantees the model cannot overfit",
                        ],
                        "answer": 0,
                        "explanation": "With little data, one split can be lucky or unlucky. Rotating the "
                        "validation fold and averaging the k scores reduces that variance. It does not "
                        "prevent overfitting by itself.",
                    },
                    {
                        "id": "of-6",
                        "difficulty": 3,
                        "concept": "regularization",
                        "prompt": "What typically happens if you increase the regularization strength λ far "
                        "too much?",
                        "options": [
                            "The model overfits more",
                            "The model underfits (high bias)",
                            "Training error drops to zero",
                            "Nothing changes",
                        ],
                        "answer": 1,
                        "explanation": "A huge penalty pushes weights toward zero, so the model becomes "
                        "too simple to capture the real pattern — both training and validation error rise.",
                    },
                ],
            },
            {
                "id": "linear-regression",
                "title": "Linear Regression",
                "summary": "Fitting a line, minimizing squared error, and interpreting coefficients.",
                "lesson": {
                    "intro": (
                        "Linear regression is the starting point for predicting a number. It assumes the "
                        "target changes in a straight-line way with each input feature."
                    ),
                    "body": [
                        "The model is y = w·x + b. Training finds the weights that minimize the mean "
                        "squared error between predictions and true values. Squaring keeps positive and "
                        "negative errors from cancelling and punishes large misses more.",
                        "Each coefficient has a direct reading: the change in the prediction for a one-unit "
                        "change in that feature. R² summarizes how much of the target's variance the model "
                        "explains. If the true relationship curves, a plain line will underfit.",
                    ],
                    "key_points": [
                        "Linear regression predicts continuous values.",
                        "Ordinary least squares minimizes mean squared error.",
                        "A coefficient is the slope for its feature.",
                    ],
                },
                "concepts": {
                    "model-form": {
                        "name": "Model form",
                        "reteach": "Linear regression outputs a continuous number from a weighted sum of "
                        "inputs plus an intercept. It can only draw straight lines (or flat planes) unless "
                        "you add transformed features such as x².",
                    },
                    "loss-function": {
                        "name": "Loss function",
                        "reteach": "Mean squared error averages the squared differences between predicted "
                        "and actual values. Squaring makes every error positive and weighs big errors more.",
                    },
                    "interpretation": {
                        "name": "Interpreting results",
                        "reteach": "A coefficient tells you how much the prediction moves per unit of its "
                        "feature. R² is the share of the target's variance the model accounts for — not the "
                        "share of predictions that are exactly right.",
                    },
                },
                "questions": [
                    {
                        "id": "lr-1",
                        "difficulty": 1,
                        "concept": "model-form",
                        "prompt": "What kind of output does linear regression predict?",
                        "options": [
                            "A category label",
                            "A continuous numeric value",
                            "A cluster assignment",
                            "A sequence of decisions",
                        ],
                        "answer": 1,
                        "explanation": "Linear regression produces a real number such as a price or a "
                        "temperature. Predicting categories is a classification task.",
                    },
                    {
                        "id": "lr-2",
                        "difficulty": 1,
                        "concept": "loss-function",
                        "prompt": "Which loss does ordinary least squares minimize?",
                        "options": ["Mean squared error", "Cross-entropy", "Hinge loss", "Accuracy"],
                        "answer": 0,
                        "explanation": "\"Least squares\" is in the name: it minimizes the (mean) squared "
                        "difference between predictions and targets. Cross-entropy and hinge loss are "
                        "classification losses.",
                    },
                    {
                        "id": "lr-3",
                        "difficulty": 2,
                        "concept": "interpretation",
                        "prompt": "In the fitted model y = 3x + 5, what does the coefficient 3 mean?",
                        "options": [
                            "y equals 3 when x is 0",
                            "Each 1-unit increase in x raises the predicted y by 3",
                            "x is always three times y",
                            "The model's error is 3%",
                        ],
                        "answer": 1,
                        "explanation": "The coefficient is the slope: the predicted change in y per unit "
                        "of x. The value of y at x = 0 is the intercept, 5.",
                    },
                    {
                        "id": "lr-4",
                        "difficulty": 2,
                        "concept": "loss-function",
                        "prompt": "Why are errors squared in MSE instead of simply added up?",
                        "options": [
                            "So positive and negative errors don't cancel, and large errors count more",
                            "Because squaring makes the computation faster",
                            "So that the loss can become negative",
                            "To normalize the input features",
                        ],
                        "answer": 0,
                        "explanation": "Raw errors of +5 and -5 would sum to zero even though both "
                        "predictions are wrong. Squaring removes the sign and penalizes big misses more.",
                    },
                    {
                        "id": "lr-5",
                        "difficulty": 3,
                        "concept": "interpretation",
                        "prompt": "A regression model reports R² = 0.85. What does that mean?",
                        "options": [
                            "85% of predictions are exactly correct",
                            "The model explains 85% of the variance in the target",
                            "The slope of the line is 0.85",
                            "15% of the data points are outliers",
                        ],
                        "answer": 1,
                        "explanation": "R² compares the model's squared error with that of always "
                        "predicting the mean. 0.85 means it accounts for 85% of the target's variability.",
                    },
                    {
                        "id": "lr-6",
                        "difficulty": 3,
                        "concept": "model-form",
                        "prompt": "A scatter plot shows a clear U-shaped relationship between x and y. What "
                        "will a plain linear regression on x most likely do?",
                        "options": [
                            "Fit the curve perfectly",
                            "Underfit — adding a feature such as x² would help",
                            "Overfit the training data",
                            "Turn into a classifier",
                        ],
                        "answer": 1,
                        "explanation": "A straight line can't bend to follow a U shape, so it underfits. "
                        "Adding x² keeps the model linear in its weights while letting it capture the curve.",
                    },
                ],
            },
        ],
    },
    {
        "id": "python",
        "name": "Python",
        "description": "The building blocks of writing clear, correct Python programs.",
        "topics": [
            {
                "id": "functions",
                "title": "Functions",
                "summary": "Defining functions, passing arguments, and understanding scope.",
                "lesson": {
                    "intro": (
                        "Functions let you name a piece of logic and reuse it. Almost every Python program "
                        "is organized around them, so it pays to know exactly how they behave."
                    ),
                    "body": [
                        "You define a function with def, list its parameters, and send a value back with "
                        "return. A function with no return statement gives back None. Parameters can have "
                        "default values, and *args / **kwargs collect any extra positional or keyword "
                        "arguments.",
                        "Variables assigned inside a function are local to it — they don't change a "
                        "variable with the same name outside. One classic trap: default values are "
                        "evaluated once, so a mutable default like [] is shared between calls.",
                    ],
                    "key_points": [
                        "No return statement means the function returns None.",
                        "Assignment inside a function creates a local variable.",
                        "Never use a mutable object as a default argument.",
                    ],
                },
                "concepts": {
                    "definition-return": {
                        "name": "Definition & return",
                        "reteach": "def name(params): starts a function; return sends a value back to the "
                        "caller. If execution reaches the end without a return, the caller receives None.",
                    },
                    "arguments": {
                        "name": "Arguments & defaults",
                        "reteach": "Positional arguments fill parameters in order, keyword arguments by "
                        "name. Defaults are evaluated once at definition time, *args gathers extra "
                        "positionals into a tuple, and **kwargs gathers extra keywords into a dict.",
                    },
                    "scope": {
                        "name": "Variable scope",
                        "reteach": "Assigning to a name inside a function creates a new local variable. "
                        "The outer variable is untouched unless you explicitly declare it global or "
                        "nonlocal.",
                    },
                },
                "questions": [
                    {
                        "id": "fn-1",
                        "difficulty": 1,
                        "concept": "definition-return",
                        "prompt": "Which keyword is used to define a function in Python?",
                        "options": ["function", "def", "fn", "define"],
                        "answer": 1,
                        "explanation": "Python functions start with def, as in def greet(name):. The other "
                        "keywords come from other languages or don't exist.",
                    },
                    {
                        "id": "fn-2",
                        "difficulty": 1,
                        "concept": "definition-return",
                        "prompt": "What does a function return if it has no return statement?",
                        "options": ["0", "None", "An empty string", "It raises an error"],
                        "answer": 1,
                        "explanation": "Python implicitly returns None when a function finishes without "
                        "hitting a return statement.",
                    },
                    {
                        "id": "fn-3",
                        "difficulty": 2,
                        "concept": "arguments",
                        "prompt": "Given def greet(name, greeting=\"Hello\"): return f\"{greeting}, "
                        "{name}\" — what does greet(\"Ada\") return?",
                        "options": ["\"Hello, Ada\"", "\"Ada, Hello\"", "A TypeError", "\"greeting, Ada\""],
                        "answer": 0,
                        "explanation": "\"Ada\" fills name and greeting falls back to its default \"Hello\", "
                        "so the f-string produces \"Hello, Ada\".",
                    },
                    {
                        "id": "fn-4",
                        "difficulty": 2,
                        "concept": "scope",
                        "prompt": "x = 10\ndef f():\n    x = 5\nf()\nprint(x)\n\nWhat is printed?",
                        "options": ["5", "10", "None", "An error"],
                        "answer": 1,
                        "explanation": "The x = 5 inside f creates a local variable that disappears when f "
                        "returns. The global x is still 10.",
                    },
                    {
                        "id": "fn-5",
                        "difficulty": 3,
                        "concept": "arguments",
                        "prompt": "def add(item, bucket=[]):\n    bucket.append(item)\n    return bucket\n\n"
                        "What does the second call return after add(1) then add(2)?",
                        "options": ["[2]", "[1, 2]", "An error", "[]"],
                        "answer": 1,
                        "explanation": "The default list is created once, when the function is defined, "
                        "and shared by every call. The fix is bucket=None and creating a new list inside.",
                    },
                    {
                        "id": "fn-6",
                        "difficulty": 3,
                        "concept": "arguments",
                        "prompt": "def f(a, b, *args, **kwargs): ...\nf(1, 2, 3, x=4)\n\nInside f, what is "
                        "kwargs?",
                        "options": ["{'x': 4}", "(3,)", "{}", "(3, 4)"],
                        "answer": 0,
                        "explanation": "1 and 2 fill a and b, the extra positional 3 goes into args as "
                        "(3,), and the keyword argument x=4 lands in kwargs as {'x': 4}.",
                    },
                ],
            },
            {
                "id": "lists",
                "title": "Lists",
                "summary": "Indexing, slicing, mutation, aliasing, and list comprehensions.",
                "lesson": {
                    "intro": (
                        "Lists are Python's go-to ordered collection. They are simple to use, but a few "
                        "behaviours — negative indices, slicing, and aliasing — catch people out."
                    ),
                    "body": [
                        "Indexing starts at 0, and negative indices count from the end, so items[-1] is "
                        "the last element. A slice items[a:b] includes index a but stops before b.",
                        "Lists are mutable: append, insert, and remove change them in place. Assigning a "
                        "list to another name does not copy it — both names point at the same list. "
                        "Comprehensions such as [x * 2 for x in items if x > 0] build new lists concisely.",
                    ],
                    "key_points": [
                        "Index 0 is first; index -1 is last.",
                        "Slices include the start and exclude the end.",
                        "b = a makes an alias, not a copy.",
                    ],
                },
                "concepts": {
                    "indexing-slicing": {
                        "name": "Indexing & slicing",
                        "reteach": "Positions start at 0. Negative positions count back from the end. "
                        "A slice [start:stop] takes items from start up to, but not including, stop.",
                    },
                    "mutation": {
                        "name": "Mutation & aliasing",
                        "reteach": "Methods like append change the list itself. If two names refer to the "
                        "same list, a change through one name is visible through the other. Use "
                        "list(a) or a.copy() for an independent copy.",
                    },
                    "comprehensions": {
                        "name": "Comprehensions",
                        "reteach": "Read [expr for x in items if cond] left to right: for each x in items, "
                        "keep it if cond is true, and collect expr. Nested for clauses run in the same "
                        "order as nested loops.",
                    },
                },
                "questions": [
                    {
                        "id": "ls-1",
                        "difficulty": 1,
                        "concept": "indexing-slicing",
                        "prompt": "nums = [10, 20, 30, 40]. What is nums[-1]?",
                        "options": ["10", "40", "30", "IndexError"],
                        "answer": 1,
                        "explanation": "Negative indices count from the end, so -1 is the last element, 40.",
                    },
                    {
                        "id": "ls-2",
                        "difficulty": 1,
                        "concept": "mutation",
                        "prompt": "Which method adds an element to the end of a list?",
                        "options": ["add()", "append()", "push()", "insert_end()"],
                        "answer": 1,
                        "explanation": "list.append(x) adds x to the end in place. push() is the name used "
                        "by stacks in other languages; Python lists don't have it.",
                    },
                    {
                        "id": "ls-3",
                        "difficulty": 2,
                        "concept": "indexing-slicing",
                        "prompt": "nums = [0, 1, 2, 3, 4, 5]. What is nums[1:4]?",
                        "options": ["[1, 2, 3]", "[1, 2, 3, 4]", "[0, 1, 2, 3]", "[2, 3, 4]"],
                        "answer": 0,
                        "explanation": "The slice starts at index 1 and stops before index 4, giving the "
                        "elements at positions 1, 2, and 3.",
                    },
                    {
                        "id": "ls-4",
                        "difficulty": 2,
                        "concept": "comprehensions",
                        "prompt": "What does [x * x for x in range(5) if x % 2 == 0] produce?",
                        "options": ["[0, 4, 16]", "[1, 9]", "[0, 1, 4, 9, 16]", "[4, 16]"],
                        "answer": 0,
                        "explanation": "range(5) is 0–4; the filter keeps the even numbers 0, 2, 4; "
                        "squaring them gives [0, 4, 16].",
                    },
                    {
                        "id": "ls-5",
                        "difficulty": 3,
                        "concept": "mutation",
                        "prompt": "a = [1, 2, 3]\nb = a\nb.append(4)\nprint(a)\n\nWhat is printed?",
                        "options": ["[1, 2, 3]", "[1, 2, 3, 4]", "An error", "[4]"],
                        "answer": 1,
                        "explanation": "b = a doesn't copy the list; both names refer to the same object. "
                        "Appending through b changes the list a also points to.",
                    },
                    {
                        "id": "ls-6",
                        "difficulty": 3,
                        "concept": "comprehensions",
                        "prompt": "matrix = [[1, 2], [3, 4]]. What is [n for row in matrix for n in row]?",
                        "options": ["[[1, 2], [3, 4]]", "[1, 2, 3, 4]", "[1, 3, 2, 4]", "An error"],
                        "answer": 1,
                        "explanation": "The for clauses run like nested loops: the outer loop takes each "
                        "row, the inner loop each number — flattening the matrix to [1, 2, 3, 4].",
                    },
                ],
            },
            {
                "id": "oop",
                "title": "Object-Oriented Programming",
                "summary": "Classes, instances, inheritance, and how attributes are looked up.",
                "lesson": {
                    "intro": (
                        "Object-oriented programming bundles data and the behaviour that operates on it. "
                        "In Python, a class is the blueprint and each object is an instance of it."
                    ),
                    "body": [
                        "__init__ runs when an instance is created and sets up its attributes. Inside "
                        "methods, self is the specific instance the method was called on.",
                        "A subclass inherits its parent's methods and can override them. Calling "
                        "super().__init__() from an overriding __init__ makes sure the parent's setup "
                        "still happens. Attributes defined on the class itself are shared by all instances "
                        "until an instance sets its own.",
                    ],
                    "key_points": [
                        "__init__ initializes a new instance; self is that instance.",
                        "Subclasses inherit and can override methods.",
                        "Class attributes are shared; instance attributes are per object.",
                    ],
                },
                "concepts": {
                    "classes-instances": {
                        "name": "Classes & instances",
                        "reteach": "A class defines structure and behaviour; an instance is one concrete "
                        "object built from it. __init__ fills in the new instance's attributes, and self "
                        "refers to that instance inside methods.",
                    },
                    "inheritance": {
                        "name": "Inheritance",
                        "reteach": "class Child(Parent) gives Child everything Parent has. If Child "
                        "defines a method with the same name, Child's version wins; super() lets it still "
                        "call the parent's version.",
                    },
                    "attributes": {
                        "name": "Attribute lookup",
                        "reteach": "Python looks for an attribute on the instance first, then on its "
                        "class, then on parent classes. A class attribute is shared by every instance that "
                        "hasn't set its own value.",
                    },
                },
                "questions": [
                    {
                        "id": "oop-1",
                        "difficulty": 1,
                        "concept": "classes-instances",
                        "prompt": "What is the role of the __init__ method?",
                        "options": [
                            "It deletes an object",
                            "It initializes a new instance's attributes",
                            "It imports the class's module",
                            "It sets the name of the class",
                        ],
                        "answer": 1,
                        "explanation": "__init__ runs automatically right after an instance is created and "
                        "is where you assign its starting attributes, like self.name = name.",
                    },
                    {
                        "id": "oop-2",
                        "difficulty": 1,
                        "concept": "classes-instances",
                        "prompt": "Inside an instance method, what does self refer to?",
                        "options": [
                            "The class itself",
                            "The instance the method was called on",
                            "The parent class",
                            "The current module",
                        ],
                        "answer": 1,
                        "explanation": "When you call dog.bark(), Python passes dog as the first argument, "
                        "which the method receives as self.",
                    },
                    {
                        "id": "oop-3",
                        "difficulty": 2,
                        "concept": "inheritance",
                        "prompt": "What does class Dog(Animal): declare?",
                        "options": [
                            "Dog inherits from Animal",
                            "Animal inherits from Dog",
                            "Dog holds an Animal instance as an attribute",
                            "Dog and Animal are unrelated",
                        ],
                        "answer": 0,
                        "explanation": "The class in parentheses is the parent. Dog gets all of Animal's "
                        "methods and attributes and can add or override its own.",
                    },
                    {
                        "id": "oop-4",
                        "difficulty": 2,
                        "concept": "inheritance",
                        "prompt": "A subclass defines a method with the same name as one in its parent. "
                        "Calling that method on a subclass instance runs:",
                        "options": [
                            "The parent's version",
                            "The subclass's version",
                            "Both versions, parent first",
                            "Neither — it raises an error",
                        ],
                        "answer": 1,
                        "explanation": "This is method overriding: lookup finds the subclass's method first. "
                        "The parent's version only runs if the subclass calls it via super().",
                    },
                    {
                        "id": "oop-5",
                        "difficulty": 3,
                        "concept": "inheritance",
                        "prompt": "Why call super().__init__(...) inside a subclass's own __init__?",
                        "options": [
                            "So the parent's initialization logic still runs",
                            "To make the class abstract",
                            "To remove the parent class",
                            "Python requires it in every class",
                        ],
                        "answer": 0,
                        "explanation": "Overriding __init__ replaces the parent's version entirely. Calling "
                        "super().__init__() runs the parent's setup too, so its attributes exist.",
                    },
                    {
                        "id": "oop-6",
                        "difficulty": 3,
                        "concept": "attributes",
                        "prompt": "class Counter:\n    count = 0\n\nc1 = Counter()\nc2 = Counter()\n"
                        "Counter.count = 5\nprint(c2.count)\n\nWhat is printed?",
                        "options": ["0", "5", "An AttributeError", "None"],
                        "answer": 1,
                        "explanation": "count is a class attribute. c2 has no instance attribute named "
                        "count, so lookup falls through to the class, which now holds 5.",
                    },
                ],
            },
        ],
    },
    {
        "id": "dsa",
        "name": "Data Structures & Algorithms",
        "description": "How data is organized and how to reason about the cost of operating on it.",
        "topics": [
            {
                "id": "arrays",
                "title": "Arrays",
                "summary": "Constant-time access, costly inserts, and single-pass techniques.",
                "lesson": {
                    "intro": (
                        "An array stores elements in one contiguous block of memory. That layout is what "
                        "makes some operations instant and others expensive."
                    ),
                    "body": [
                        "Because every element sits at a predictable offset, reading arr[i] is O(1). "
                        "Inserting or deleting near the front is O(n): every later element has to shift.",
                        "Many array problems are solved in a single pass, tracking a running value, or with "
                        "two pointers moving toward each other in a sorted array. Dynamic arrays (like "
                        "Python lists) grow by doubling, which makes append O(1) on average.",
                    ],
                    "key_points": [
                        "Access by index is O(1).",
                        "Insert or delete at the front is O(n).",
                        "Two pointers solve many sorted-array problems in O(n).",
                    ],
                },
                "concepts": {
                    "access": {
                        "name": "Indexed access",
                        "reteach": "An array's elements sit side by side in memory, so the address of "
                        "arr[i] is a simple calculation — constant time. Indices run from 0 to n - 1.",
                    },
                    "complexity": {
                        "name": "Operation costs",
                        "reteach": "Inserting at position 0 means shifting all n elements one step right: "
                        "O(n). Dynamic arrays occasionally copy everything when they grow, but doubling "
                        "capacity keeps the average append cost O(1).",
                    },
                    "traversal": {
                        "name": "Traversal techniques",
                        "reteach": "A single pass that tracks a running answer is O(n). In a sorted array, "
                        "two pointers starting at both ends can move inward based on a comparison, avoiding "
                        "nested loops.",
                    },
                },
                "questions": [
                    {
                        "id": "ar-1",
                        "difficulty": 1,
                        "concept": "access",
                        "prompt": "What is the time complexity of reading arr[i] from an array?",
                        "options": ["O(1)", "O(n)", "O(log n)", "O(n²)"],
                        "answer": 0,
                        "explanation": "The element's address is base + i × element size, a single "
                        "calculation regardless of the array's length.",
                    },
                    {
                        "id": "ar-2",
                        "difficulty": 1,
                        "concept": "access",
                        "prompt": "In a 0-indexed array of length n, what is the index of the last element?",
                        "options": ["n", "n - 1", "1", "0"],
                        "answer": 1,
                        "explanation": "Indices start at 0, so n elements occupy positions 0 through n - 1. "
                        "Index n is one past the end.",
                    },
                    {
                        "id": "ar-3",
                        "difficulty": 2,
                        "concept": "complexity",
                        "prompt": "What is the time complexity of inserting an element at the beginning of "
                        "an array of n elements?",
                        "options": ["O(1)", "O(n)", "O(log n)", "O(n log n)"],
                        "answer": 1,
                        "explanation": "Every existing element must shift one position to make room, so "
                        "the work grows linearly with n.",
                    },
                    {
                        "id": "ar-4",
                        "difficulty": 2,
                        "concept": "traversal",
                        "prompt": "What is the most efficient way to find the maximum value in an unsorted "
                        "array?",
                        "options": [
                            "Sort the array and take the last element",
                            "Scan once, keeping track of the largest value seen",
                            "Use binary search",
                            "Compare every pair of elements",
                        ],
                        "answer": 1,
                        "explanation": "A single pass is O(n), and you must look at every element at least "
                        "once anyway. Sorting costs O(n log n); binary search needs sorted data.",
                    },
                    {
                        "id": "ar-5",
                        "difficulty": 3,
                        "concept": "traversal",
                        "prompt": "Given a sorted array, you need to check whether any two numbers sum to a "
                        "target. Which approach runs in O(n) time with O(1) extra space?",
                        "options": [
                            "Nested loops over every pair",
                            "Two pointers starting at both ends, moving inward",
                            "Sorting the array again first",
                            "Recursing over every subset",
                        ],
                        "answer": 1,
                        "explanation": "If the pair sum is too small, move the left pointer right; if too "
                        "big, move the right pointer left. Each step discards one element, so it's O(n).",
                    },
                    {
                        "id": "ar-6",
                        "difficulty": 3,
                        "concept": "complexity",
                        "prompt": "Why is append on a dynamic array O(1) amortized?",
                        "options": [
                            "It never needs to resize",
                            "Capacity doubles when full, so rare O(n) copies are spread over many appends",
                            "It is secretly a linked list",
                            "The operating system resizes memory for free",
                        ],
                        "answer": 1,
                        "explanation": "A full array is copied into one twice the size. Copies get rarer as "
                        "the array grows, so the total copy work over n appends is O(n) — O(1) each.",
                    },
                ],
            },
            {
                "id": "binary-search",
                "title": "Binary Search",
                "summary": "Halving the search space: preconditions, mechanics, and edge cases.",
                "lesson": {
                    "intro": (
                        "Binary search finds a value in a sorted collection by repeatedly cutting the "
                        "search space in half. It's one of the most useful ideas in algorithms."
                    ),
                    "body": [
                        "Compare the target with the middle element. If it's smaller, discard the right "
                        "half; if larger, discard the left half. Repeat until you find it or the range is "
                        "empty. Halving each step gives O(log n) time.",
                        "It only works on sorted data. Details matter: compute the midpoint safely, update "
                        "the bounds correctly, and when duplicates exist, decide whether you want the first "
                        "or last occurrence.",
                    ],
                    "key_points": [
                        "The input must be sorted.",
                        "Each comparison halves the remaining range: O(log n).",
                        "Boundary updates decide which occurrence you find.",
                    ],
                },
                "concepts": {
                    "precondition": {
                        "name": "Sorted precondition",
                        "reteach": "Discarding half the range is only safe if order tells you which half "
                        "the target can't be in. Without sorted data, binary search can skip the answer.",
                    },
                    "mechanics": {
                        "name": "Search mechanics",
                        "reteach": "Keep low and high bounds, look at the middle, and move one bound past "
                        "the middle each step. For the first occurrence, keep searching left after a match.",
                    },
                    "bs-complexity": {
                        "name": "Logarithmic complexity",
                        "reteach": "Each step halves the range, so n elements need about log2(n) steps. "
                        "1,024 elements take about 10 comparisons; a million take about 20.",
                    },
                },
                "questions": [
                    {
                        "id": "bs-1",
                        "difficulty": 1,
                        "concept": "precondition",
                        "prompt": "What must be true of an array before you can binary search it?",
                        "options": [
                            "It must be sorted",
                            "It must contain no duplicates",
                            "Its length must be a power of two",
                            "It must contain only integers",
                        ],
                        "answer": 0,
                        "explanation": "Binary search relies on order to know which half to discard. "
                        "Duplicates, odd lengths, and non-integers are all fine as long as it's sorted.",
                    },
                    {
                        "id": "bs-2",
                        "difficulty": 1,
                        "concept": "mechanics",
                        "prompt": "At each step, binary search compares the target with which element?",
                        "options": ["The first element", "The middle element", "The last element",
                                    "A random element"],
                        "answer": 1,
                        "explanation": "Checking the middle splits the remaining range into two equal "
                        "halves, which is what guarantees the logarithmic running time.",
                    },
                    {
                        "id": "bs-3",
                        "difficulty": 2,
                        "concept": "bs-complexity",
                        "prompt": "What is the worst-case time complexity of binary search?",
                        "options": ["O(n)", "O(log n)", "O(1)", "O(n log n)"],
                        "answer": 1,
                        "explanation": "The range halves every step, so it takes about log2(n) steps to "
                        "shrink n elements to one.",
                    },
                    {
                        "id": "bs-4",
                        "difficulty": 2,
                        "concept": "bs-complexity",
                        "prompt": "Roughly how many comparisons does binary search need in the worst case "
                        "on 1,024 sorted elements?",
                        "options": ["About 10", "About 512", "About 1,024", "About 100"],
                        "answer": 0,
                        "explanation": "1,024 = 2¹⁰, so about 10 halvings shrink the range to a single "
                        "element (11 comparisons at most). Linear search could need 1,024.",
                    },
                    {
                        "id": "bs-5",
                        "difficulty": 3,
                        "concept": "mechanics",
                        "prompt": "Why do many implementations write mid = low + (high - low) // 2 instead "
                        "of (low + high) // 2?",
                        "options": [
                            "It avoids integer overflow when low + high exceeds the integer limit",
                            "It runs noticeably faster",
                            "It always rounds up instead of down",
                            "It lets binary search work on unsorted data",
                        ],
                        "answer": 0,
                        "explanation": "In languages with fixed-width integers, low + high can overflow on "
                        "huge arrays. The rewritten form computes the same midpoint without that risk.",
                    },
                    {
                        "id": "bs-6",
                        "difficulty": 3,
                        "concept": "mechanics",
                        "prompt": "To find the first occurrence of a target in a sorted array with "
                        "duplicates, what should you do when arr[mid] == target?",
                        "options": [
                            "Return mid immediately",
                            "Record mid, then keep searching the left half (high = mid - 1)",
                            "Keep searching the right half (low = mid + 1)",
                            "Restart the search from index 0",
                        ],
                        "answer": 1,
                        "explanation": "A match might not be the first one. Remember it as a candidate and "
                        "keep narrowing to the left until the range is empty.",
                    },
                ],
            },
            {
                "id": "stacks",
                "title": "Stacks",
                "summary": "Last-in, first-out: operations, costs, and where stacks show up.",
                "lesson": {
                    "intro": (
                        "A stack is a collection where the last item added is the first one removed — like "
                        "a stack of plates."
                    ),
                    "body": [
                        "Its two core operations are push (add to the top) and pop (remove from the top), "
                        "both O(1). Peek looks at the top without removing it.",
                        "Stacks appear wherever you need to undo or match things in reverse order: checking "
                        "balanced brackets, evaluating postfix expressions, undo history, and the call stack "
                        "that tracks function calls — which overflows under infinite recursion.",
                    ],
                    "key_points": [
                        "LIFO: last in, first out.",
                        "Push and pop are O(1).",
                        "Used for matching, parsing, undo, and function calls.",
                    ],
                },
                "concepts": {
                    "lifo": {
                        "name": "LIFO principle",
                        "reteach": "Only the top of a stack is accessible. Whatever was pushed most "
                        "recently is the next thing popped.",
                    },
                    "operations": {
                        "name": "Stack operations",
                        "reteach": "push adds to the top, pop removes from the top, peek reads the top. "
                        "Each touches a single end of the structure, so each is O(1).",
                    },
                    "applications": {
                        "name": "Applications",
                        "reteach": "Reach for a stack when the most recent unfinished item must be handled "
                        "first: an opening bracket waiting for its match, an operand waiting for its "
                        "operator, or a function waiting for the call it made to return.",
                    },
                },
                "questions": [
                    {
                        "id": "st-1",
                        "difficulty": 1,
                        "concept": "lifo",
                        "prompt": "Which ordering principle does a stack follow?",
                        "options": ["FIFO", "LIFO", "Random order", "Priority order"],
                        "answer": 1,
                        "explanation": "Last In, First Out: the most recently pushed item is the first "
                        "popped. FIFO describes a queue.",
                    },
                    {
                        "id": "st-2",
                        "difficulty": 1,
                        "concept": "operations",
                        "prompt": "You push 1, then 2, then 3 onto an empty stack, then pop once. Which "
                        "value is removed?",
                        "options": ["1", "2", "3", "None of them"],
                        "answer": 2,
                        "explanation": "3 was pushed last, so it sits on top and is the first to be popped.",
                    },
                    {
                        "id": "st-3",
                        "difficulty": 2,
                        "concept": "operations",
                        "prompt": "What is the time complexity of push and pop on a well-implemented stack?",
                        "options": ["O(1)", "O(n)", "O(log n)", "O(n²)"],
                        "answer": 0,
                        "explanation": "Both operations only touch the top element, so their cost doesn't "
                        "depend on how many items the stack holds.",
                    },
                    {
                        "id": "st-4",
                        "difficulty": 2,
                        "concept": "applications",
                        "prompt": "Which of these is a classic application of a stack?",
                        "options": [
                            "Breadth-first search of a graph",
                            "Checking whether brackets are balanced",
                            "Round-robin CPU scheduling",
                            "Looking up keys in a hash table",
                        ],
                        "answer": 1,
                        "explanation": "Push each opening bracket; on a closing bracket, pop and check it "
                        "matches. BFS and round-robin scheduling use queues instead.",
                    },
                    {
                        "id": "st-5",
                        "difficulty": 3,
                        "concept": "applications",
                        "prompt": "Function calls are tracked on a call stack. What does unbounded "
                        "recursion eventually cause?",
                        "options": ["A stack overflow", "Heap fragmentation", "A deadlock", "A cache miss"],
                        "answer": 0,
                        "explanation": "Every call pushes a frame that is only popped when the call "
                        "returns. Endless recursion keeps pushing until the stack runs out of space.",
                    },
                    {
                        "id": "st-6",
                        "difficulty": 3,
                        "concept": "applications",
                        "prompt": "Using a stack, what does the postfix expression 3 4 + 2 * evaluate to?",
                        "options": ["14", "11", "10", "24"],
                        "answer": 0,
                        "explanation": "Push 3 and 4; + pops both and pushes 7. Push 2; * pops 7 and 2 and "
                        "pushes 14 — the result.",
                    },
                ],
            },
        ],
    },
]


# How demanding each topic is overall (shown on the curriculum).
TOPIC_LEVELS = {
    "decision-trees": "Intermediate",
    "overfitting": "Intermediate",
    "linear-regression": "Beginner",
    "functions": "Beginner",
    "lists": "Beginner",
    "oop": "Intermediate",
    "arrays": "Beginner",
    "binary-search": "Intermediate",
    "stacks": "Beginner",
}


def _index() -> dict[str, tuple[dict, dict]]:
    return {t["id"]: (s, t) for s in SUBJECTS for t in s["topics"]}


_TOPICS = _index()


def topic_ids() -> list[str]:
    """Every topic id, in curriculum order."""
    return [t["id"] for s in SUBJECTS for t in s["topics"]]


def get_topic(topic_id: str) -> tuple[dict, dict] | None:
    """Return (subject, topic) for a topic id, or None."""
    return _TOPICS.get(topic_id)


def get_question(topic_id: str, question_id: str) -> dict | None:
    found = get_topic(topic_id)
    if found is None:
        return None
    return next((q for q in found[1]["questions"] if q["id"] == question_id), None)


def concept_name(topic_id: str, concept: str) -> str:
    found = get_topic(topic_id)
    if found is None:
        return concept
    return found[1]["concepts"].get(concept, {}).get("name", concept)


def public_question(topic: dict, question: dict) -> dict:
    """A question as the student sees it: no answer key, no explanation."""
    return {
        "id": question["id"],
        "prompt": question["prompt"],
        "options": list(question["options"]),
        "difficulty": question["difficulty"],
        "difficulty_label": LEVEL_NAMES[question["difficulty"]],
        "concept": question["concept"],
        "concept_name": topic["concepts"][question["concept"]]["name"],
    }


def public_curriculum() -> list[dict]:
    """The curriculum for browsing: lessons and concepts, no questions."""
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "topics": [
                {
                    "id": t["id"],
                    "title": t["title"],
                    "summary": t["summary"],
                    "subject_id": s["id"],
                    "subject_name": s["name"],
                    "question_count": len(t["questions"]),
                    "level": TOPIC_LEVELS.get(t["id"], "Intermediate"),
                    "concepts": [c["name"] for c in t["concepts"].values()],
                }
                for t in s["topics"]
            ],
        }
        for s in SUBJECTS
    ]
