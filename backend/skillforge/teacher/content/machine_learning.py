"""(22PC1AM302) Machine Learning — VNR VJIET B.Tech. AIML R22, V Semester."""

from __future__ import annotations

from skillforge.teacher.content._build import subject, topic, unit
from skillforge.teacher.content.ml_bank import BIAS_VARIANCE, DECISION_TREES, LINEAR_REGRESSION

# The inherited ML banks put the correct option in position B for 15 of 18
# questions. Move it for questions whose options have no natural order; the
# correct answer itself (and its explanation) is unchanged, only its letter.
ANSWER_POSITION = {
    "dt-2": 3, "dt-5": 0,
    "of-1": 3, "of-2": 0, "of-4": 3, "of-6": 3,
    "lr-3": 3, "lr-5": 3, "lr-1": 0,
}


def _move_answer(q: dict) -> dict:
    target = ANSWER_POSITION.get(q["id"])
    if target is None or target == q["answer"]:
        return q
    old = q["answer"]
    options = list(q["options"])
    options[old], options[target] = options[target], options[old]
    out = {**q, "options": options, "answer": target}
    if "why_wrong" in q:
        # The distractor that sat at `target` now sits at `old`.
        out["why_wrong"] = {(old if k == target else k): v for k, v in q["why_wrong"].items()}
    return out


def _rebalanced(topic: dict) -> dict:
    return {**topic, "questions": [_move_answer(q) for q in topic["questions"]]}


DECISION_TREES = _rebalanced(DECISION_TREES)
BIAS_VARIANCE = _rebalanced(BIAS_VARIANCE)
LINEAR_REGRESSION = _rebalanced(LINEAR_REGRESSION)

DECISION_TREES_TOPIC = {**DECISION_TREES, "title": "Decision Trees – ID3 and CART", "level": "Intermediate"}
LINEAR_REGRESSION_TOPIC = {**LINEAR_REGRESSION, "title": "Linear Regression and Multiple Linear Regression",
                           "level": "Beginner"}
BIAS_VARIANCE_TOPIC = {
    **BIAS_VARIANCE,
    "title": "Bias – Variance Trade-off",
    "level": "Intermediate",
    "summary": "Overfitting and underfitting, detecting them with validation, and balancing them with "
    "regularization.",
}

SUBJECT = subject(
    "machine-learning",
    "22PC1AM302",
    "Machine Learning",
    "ML",
    "theory",
    "Learning paradigms, supervised and unsupervised learning, and ensemble methods.",
    [
        unit(1, "Introduction to Machine Learning and Pre-requisites", [
            topic("ml-introduction", "Introduction to Machine Learning and Learning Paradigms",
                  "What machine learning is and the main learning paradigms.", level="Beginner"),
            topic("ml-pac-learning", "PAC Learning", "Probably Approximately Correct learning."),
            topic("ml-version-spaces", "Version Spaces", "The set of hypotheses consistent with the data."),
            topic("ml-role-in-ai", "Role of Machine Learning in Artificial Intelligence Applications",
                  "Where machine learning fits within AI systems.", level="Beginner"),
        ]),
        unit(2, "Supervised Learning – I", [
            topic("ml-linear-nonlinear", "Linear and Non-Linear Examples; Multi-Class & Multi-Label "
                  "Classification", "Separable and non-separable problems, and classification settings."),
            LINEAR_REGRESSION_TOPIC,
            topic("ml-naive-bayes", "Naïve Bayes Classifier", "Probabilistic classification with Bayes' rule."),
            DECISION_TREES_TOPIC,
            topic("ml-error-bounds", "Error Bounds", "Bounding the generalization error of a learner."),
        ]),
        unit(3, "Supervised Learning – II", [
            topic("ml-knn", "K-NN Classifier", "Classifying by the nearest training examples."),
            topic("ml-logistic-regression", "Logistic Regression", "Linear models for classification."),
            topic("ml-perceptron", "Perceptron – Single Layer & Multi-layer",
                  "From a single neuron to multilayer networks."),
            topic("ml-svm", "Support Vector Machines – Linear & Non-linear",
                  "Maximum-margin classifiers and kernels."),
            topic("ml-supervised-metrics", "Metrics & Error Correction (Supervised)",
                  "Evaluating and improving supervised models."),
        ]),
        unit(4, "Unsupervised Learning", [
            topic("ml-clustering-basics", "Clustering Basics: Partitioned, Hierarchical and Density Based",
                  "Families of clustering algorithms."),
            topic("ml-kmeans-kmode", "K-Means Clustering and K-Mode Clustering",
                  "Centroid-based clustering for numeric and categorical data."),
            topic("ml-som", "Self Organizing Maps", "Neural-network-based clustering and visualization."),
            topic("ml-em", "Expectation Maximization", "Fitting mixture models with hidden variables."),
            topic("ml-pca", "Principal Component Analysis and Kernel PCA", "Linear and non-linear "
                  "dimensionality reduction."),
            topic("ml-tsne", "t-SNE (t-distributed Stochastic Neighbour Embedding)",
                  "Visualizing high-dimensional data."),
        ]),
        unit(5, "Ensemble Learning", [
            BIAS_VARIANCE_TOPIC,
            topic("ml-bagging-boosting", "Bagging and Boosting: Random Forests, AdaBoost, XGBoost",
                  "Combining many models to reduce variance or bias."),
            topic("ml-ensemble-metrics", "Metrics & Error Correction (Ensembles)",
                  "Evaluating ensemble models."),
        ]),
    ],
)
