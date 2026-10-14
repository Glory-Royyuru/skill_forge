"""(22PE1AM302) Explainable AI — VNR VJIET B.Tech. AIML R22, V Semester."""

from __future__ import annotations

from skillforge.teacher.content._build import concept, lesson, question, subject, topic, unit

POST_HOC = topic(
    "xai-post-hoc",
    "Post-Hoc Interpretability and Explanations: Visual Explanation, Feature Importance, Example-Based",
    "Explaining an already-trained model: local surrogates, feature importance, partial dependence and "
    "counterfactual examples.",
    lesson=lesson(
        "Post-hoc methods explain a model after it has been trained, without changing it. That lets us "
        "explain black-box models such as ensembles and deep networks.",
        [
            "Explanations can be global (how the model behaves overall) or local (why it made one "
            "prediction). Feature-importance methods score how much each input matters: permutation "
            "importance shuffles a feature and measures the drop in performance; SHAP assigns each feature a "
            "Shapley value whose sum equals the prediction minus the average prediction.",
            "Visual explanations such as partial dependence plots show how the average prediction changes as "
            "one feature varies. Example-based explanations use data points: counterfactuals state the "
            "smallest change that would flip the decision, and LIME fits a simple surrogate model around one "
            "instance.",
        ],
        [
            "Post-hoc = explain a trained model without modifying it.",
            "Permutation importance and SHAP quantify feature influence.",
            "Counterfactuals: the minimal change that flips the outcome.",
        ],
    ),
    concepts={
        "post-hoc": concept(
            "Post-hoc and local explanations",
            "A post-hoc method treats the model as given. Local methods such as LIME explain one prediction by "
            "approximating the model near that instance with something simple.",
        ),
        "feature-importance": concept(
            "Feature importance and visual explanation",
            "Permutation importance: shuffle one feature and see how much performance drops. SHAP: fair "
            "per-feature contributions that add up to the prediction minus the baseline. PDP: average "
            "prediction as one feature varies.",
        ),
        "example-based": concept(
            "Example-based explanations",
            "Explain with data points: a counterfactual is the closest input that would have received a "
            "different decision.",
        ),
    },
    questions=[
        question(
            "xai-ph-1", 1, "post-hoc",
            "What is a post-hoc explanation method?",
            ["A method that builds an interpretable model from scratch",
             "A method that explains a model after it has been trained, without changing the model",
             "A method that can only be applied before training",
             "A method that requires retraining the model with extra labels"], 1,
            "Post-hoc methods sit on top of an existing model and explain its behaviour, which is why they "
            "work for black boxes.",
            {0: "Building an interpretable model from the start is intrinsic interpretability, not post-hoc "
                "explanation."},
        ),
        question(
            "xai-ph-2", 1, "feature-importance",
            "How does permutation feature importance measure a feature's importance?",
            ["By reading the sign of the feature's coefficient",
             "By counting how often the feature appears in the training data",
             "By shuffling the feature's values and measuring how much model performance drops",
             "By computing the feature's correlation with every other feature"], 2,
            "If shuffling a feature breaks its relationship with the target and performance falls sharply, "
            "the model relied on that feature.",
        ),
        question(
            "xai-ph-3", 2, "example-based",
            "A loan application is rejected. Which of these is a counterfactual explanation?",
            ["The five features that matter most to the model overall",
             "If your annual income were ₹50,000 higher, the loan would have been approved",
             "The model's accuracy on the test set is 91%",
             "The most similar past applicant was also rejected"], 1,
            "A counterfactual describes the smallest change to the input that would change the decision, "
            "which also tells the applicant what they could do differently.",
            {0: "Ranking features globally is a feature-importance explanation, not a counterfactual.",
             3: "Pointing to a similar case is a prototype or nearest-neighbour explanation."},
        ),
        question(
            "xai-ph-4", 2, "feature-importance",
            "What does a partial dependence plot (PDP) show?",
            ["The average predicted outcome as one feature varies, averaging over the other features",
             "One curve per instance showing how its prediction changes",
             "The confusion matrix of the classifier",
             "Pairwise correlations between input features"], 0,
            "A PDP marginalizes over the other features, giving the average effect of one feature on the "
            "prediction.",
            {1: "One curve per instance is an Individual Conditional Expectation (ICE) plot."},
        ),
        question(
            "xai-ph-5", 3, "post-hoc",
            "How does LIME explain a single prediction?",
            ["By computing exact Shapley values over every coalition of features",
             "By inspecting the gradients of a neural network",
             "By training one global decision tree on the whole dataset",
             "By fitting a simple interpretable model to perturbed samples near the instance, weighted by "
             "their proximity"], 3,
            "LIME (Local Interpretable Model-agnostic Explanations) perturbs the instance, queries the black "
            "box, and fits a sparse linear surrogate that is faithful locally.",
            {1: "Gradient-based saliency is a different family, used for deep networks."},
        ),
        question(
            "xai-ph-6", 3, "feature-importance",
            "For one prediction, what do the SHAP values of all the features add up to?",
            ["The model's prediction for that instance minus the average (expected) prediction",
             "Exactly 1",
             "The number of features",
             "The model's accuracy"], 0,
            "SHAP's local-accuracy property: the baseline (expected prediction) plus the sum of the feature "
            "attributions equals the model's output for that instance.",
        ),
    ],
)

SUBJECT = subject(
    "explainable-ai",
    "22PE1AM302",
    "Explainable AI",
    "XAI",
    "theory",
    "Interpretable and explainable machine learning: pre-model, intrinsic and post-hoc methods, explainable "
    "deep learning, and the challenges and future of XAI.",
    [
        unit(1, "Introduction; Pre-model Interpretability and Explainability", [
            topic("xai-black-box", "Black-Box Problem, Goals, Brief History, Purpose and Societal Impact",
                  "Why explainability matters.", level="Beginner"),
            topic("xai-taxonomy", "Types of Explanations, Trade-offs, Taxonomy and Flowchart for "
                  "Interpretable and Explainable Techniques", "Organizing the space of XAI methods."),
            topic("xai-pre-model", "Data Science Process, Exploratory Data Analysis and Feature "
                  "Engineering", "Interpretability before a model is built."),
        ]),
        unit(2, "Model Visualization Techniques and Traditional Interpretable Algorithms", [
            topic("xai-model-validation", "Model Validation, Evaluation and Hyperparameters",
                  "Checking what a model has learned."),
            topic("xai-model-visualization", "Model Selection and Visualization: Classification, "
                  "Regression and Clustering", "Visual tools for understanding models."),
            topic("xai-traditional", "Interpretable Machine Learning Properties and Traditional "
                  "Interpretable Algorithms", "Models that are interpretable by design."),
        ]),
        unit(3, "Model Interpretability and Post-Hoc Explanations", [
            topic("xai-advances", "Interpretable vs. Explainable Algorithms: Ensemble-Based, Decision "
                  "Tree-Based, Rule-Based Techniques and Scoring Systems",
                  "Advances in interpretable machine learning."),
            POST_HOC,
        ]),
        unit(4, "Explainable Deep Learning", [
            topic("xai-deep-learning", "Intrinsic, Perturbation and Gradient / Backpropagation Methods",
                  "Explaining deep neural networks."),
        ]),
        unit(5, "Explainability in Time Series, NLP and Computer Vision; XAI Challenges and Future", [
            topic("xai-domains", "Explainability in Time Series Forecasting, NLP and Computer Vision",
                  "XAI for different data types."),
            topic("xai-challenges", "XAI Challenges: Properties, Categories and Evaluation of Explanations",
                  "How to judge an explanation."),
            topic("xai-future", "XAI Future: Responsible AI, Security, Causality and Human-Machine "
                  "Collaboration", "Where the field is heading."),
        ]),
    ],
)
