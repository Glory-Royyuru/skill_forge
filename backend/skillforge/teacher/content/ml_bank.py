"""Machine Learning question banks carried over from the original SkillForge
curriculum, now placed in their VNR R22 syllabus units (see `ml.py`)."""

from __future__ import annotations

DECISION_TREES = {
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
}

BIAS_VARIANCE = {
    "id": "bias-variance",
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
}

LINEAR_REGRESSION = {
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
}
