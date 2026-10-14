"""The two V Semester laboratories — VNR VJIET B.Tech. AIML R22.

(22PC2AM322) Computer Networks and Operating Systems Laboratory
(22PC2AM302) Machine Learning Laboratory

Units follow the syllabus's own headings; topics are the listed weekly
programs/experiments.
"""

from __future__ import annotations

from skillforge.teacher.content._build import concept, lesson, question, subject, topic, unit

PAGE_REPLACEMENT = topic(
    "lab-page-replacement",
    "Week 5: Page Replacement Algorithms – FIFO, Optimal, LRU",
    "Simulating page replacement and counting page faults for a reference string.",
    lesson=lesson(
        "When a page fault occurs and every frame is full, the operating system must choose a victim page. "
        "This experiment simulates three replacement policies on a reference string and compares their "
        "page-fault counts.",
        [
            "FIFO evicts the page that has been in memory the longest. It is simple but can suffer Belady's "
            "anomaly, where adding frames increases faults. Optimal (OPT) evicts the page that will not be "
            "used for the longest time in the future; it gives the fewest faults but needs future knowledge, "
            "so it serves as a benchmark.",
            "LRU evicts the page that has gone unused for the longest time, approximating OPT by looking at "
            "the past. To simulate any policy, step through the reference string, track the frames, and "
            "count a fault whenever the page is not already resident.",
        ],
        [
            "FIFO: oldest page out; can show Belady's anomaly.",
            "OPT: furthest future use out; the benchmark.",
            "LRU: least recently used out; practical approximation of OPT.",
        ],
    ),
    concepts={
        "fifo": concept(
            "FIFO replacement",
            "Keep the frames in a queue by load time; the page at the head (loaded earliest) is evicted, "
            "regardless of how recently it was used.",
        ),
        "optimal": concept(
            "Optimal replacement",
            "Look ahead in the reference string and evict the resident page whose next use is furthest "
            "away, or never comes.",
        ),
        "lru": concept(
            "LRU replacement",
            "Look back: evict the resident page whose last use is furthest in the past. Hits update the "
            "page's recency.",
        ),
    },
    questions=[
        question(
            "lab-pr-1", 1, "fifo",
            "Which page does FIFO page replacement evict?",
            ["The page that will not be used for the longest time",
             "The page that has been in memory the longest",
             "The page that was used least recently",
             "The page that has been used least often"], 1,
            "FIFO only tracks load order: the earliest-loaded page leaves first.",
            {2: "Evicting the least recently used page is LRU."},
        ),
        question(
            "lab-pr-2", 1, "optimal",
            "Which page does the Optimal (OPT) algorithm replace?",
            ["The page loaded first",
             "A randomly chosen page",
             "The page that will not be used for the longest time in the future",
             "The most recently used page"], 2,
            "OPT looks ahead in the reference string. It minimizes page faults but needs knowledge of future "
            "references.",
        ),
        question(
            "lab-pr-3", 2, "lru",
            "Why do real systems use LRU (or approximations of it) instead of OPT?",
            ["OPT needs future knowledge of the reference string, which is not available",
             "LRU always causes fewer page faults than OPT",
             "OPT suffers from Belady's anomaly",
             "LRU needs no bookkeeping at all"], 0,
            "OPT is a theoretical benchmark. LRU uses the recent past to predict the near future, which "
            "works well thanks to locality of reference.",
            {1: "No algorithm beats OPT; it is optimal by definition.",
             2: "OPT and LRU are stack algorithms and do not suffer Belady's anomaly."},
        ),
        question(
            "lab-pr-4", 2, "fifo",
            "Belady's anomaly, where giving a process more frames increases its page faults, can occur with:",
            ["LRU", "Optimal", "FIFO", "every replacement algorithm"], 2,
            "FIFO is not a stack algorithm, so the pages held with n frames are not always a subset of those "
            "held with n + 1 frames, and faults can go up.",
        ),
        question(
            "lab-pr-5", 3, "lru",
            "Reference string 7, 0, 1, 2, 0, 3, 0, 4 with 3 frames, all initially empty, under LRU. How many "
            "page faults occur?",
            ["5", "6", "7", "8"], 1,
            "Faults on 7, 0, 1; 2 evicts 7; 0 hits; 3 evicts 1 (least recently used); 0 hits; 4 evicts 2. "
            "That is 6 faults.",
            {2: "7 is the FIFO count for this string; LRU keeps page 0 because it was just used."},
        ),
        question(
            "lab-pr-6", 3, "fifo",
            "The same reference string (7, 0, 1, 2, 0, 3, 0, 4) with 3 empty frames under FIFO. How many page "
            "faults occur?",
            ["6", "7", "5", "8"], 1,
            "Faults on 7, 0, 1; 2 evicts 7; 0 hits; 3 evicts 0 (the oldest); 0 faults again and evicts 1; 4 "
            "evicts 2. That is 7 faults, one more than LRU.",
        ),
    ],
)

MODEL_TRAINING = topic(
    "mllab-model-training",
    "Week 7: Model Training – Holdout, K-Fold Cross Validation and Bootstrap Sampling",
    "Ways to split and resample data so that a model's measured performance is trustworthy.",
    lesson=lesson(
        "A model must be judged on data it was not trained on. This experiment compares three ways of "
        "producing that data: holdout, k-fold cross-validation and bootstrap sampling.",
        [
            "The holdout method splits the data once into training and test sets. It is fast, but the estimate "
            "depends on one particular split, and the test set must never be used for tuning. K-fold "
            "cross-validation splits the data into k folds and trains k models, each validated on a different "
            "fold; stratified folds keep class proportions intact.",
            "Bootstrap sampling draws n rows with replacement from n rows. Some rows repeat and, for large n, "
            "about 36.8% never appear; these out-of-bag rows can serve as a validation set.",
        ],
        [
            "Holdout: one split; keep the test set untouched.",
            "K-fold: k models, every row validated exactly once.",
            "Bootstrap: sample with replacement; ~36.8% out-of-bag.",
        ],
    ),
    concepts={
        "holdout": concept(
            "Holdout method",
            "Split once: train on one part, test on the other. Any decision made by looking at test results "
            "leaks the test set into training.",
        ),
        "kfold": concept(
            "K-fold cross validation",
            "Partition into k folds; for each fold, train on the other k − 1 and validate on it; average the "
            "k scores. Stratify for imbalanced classes.",
        ),
        "bootstrap": concept(
            "Bootstrap sampling",
            "Draw n rows with replacement. The chance a given row is never drawn is (1 − 1/n)ⁿ ≈ e⁻¹ ≈ 0.368.",
        ),
    },
    questions=[
        question(
            "mllab-mt-1", 1, "holdout",
            "In the holdout method, the dataset is:",
            ["resampled with replacement many times",
             "split once into separate training and test sets",
             "split into k folds that take turns as the test set",
             "used entirely for training"], 1,
            "Holdout means a single split: one part trains the model and the held-out part tests it.",
            {2: "Rotating folds is k-fold cross-validation."},
        ),
        question(
            "mllab-mt-2", 1, "kfold",
            "How many models are trained in 5-fold cross-validation?",
            ["1", "4", "5", "10"], 2,
            "Each of the 5 folds serves once as the validation set, so 5 models are trained and their scores "
            "averaged.",
        ),
        question(
            "mllab-mt-3", 2, "kfold",
            "Why is stratified k-fold preferred for an imbalanced classification dataset?",
            ["It trains faster than ordinary k-fold",
             "It removes the minority class from the training folds",
             "It guarantees the model will not overfit",
             "Each fold keeps roughly the same class proportions as the full dataset"], 3,
            "Without stratification, some folds may contain few or no minority-class examples, making those "
            "fold scores unreliable.",
        ),
        question(
            "mllab-mt-4", 2, "bootstrap",
            "How is a bootstrap sample of a dataset with n rows formed?",
            ["By drawing n rows at random with replacement",
             "By drawing n / 2 rows without replacement",
             "By taking the first n rows in order",
             "By splitting the rows into k folds"], 0,
            "Sampling with replacement means some rows appear several times and others not at all.",
        ),
        question(
            "mllab-mt-5", 3, "bootstrap",
            "For a large dataset, roughly what fraction of the original rows never appear in a bootstrap "
            "sample (the out-of-bag rows)?",
            ["About 10%", "About 50%", "About 36.8%", "None; every row appears"], 2,
            "Each row is missed on every draw with probability (1 − 1/n)ⁿ, which tends to e⁻¹ ≈ 0.368. Random "
            "forests use these out-of-bag rows for validation.",
        ),
        question(
            "mllab-mt-6", 3, "holdout",
            "You tune hyperparameters by repeatedly checking accuracy on the test split, then report that test "
            "accuracy. What is wrong?",
            ["Nothing; the test split was never used for fitting weights",
             "The test set has leaked into model selection, so the reported accuracy is optimistically "
             "biased",
             "The training set becomes too small",
             "Accuracy cannot be computed on a holdout split"], 1,
            "Choosing settings by test performance tailors the model to that particular test set. Tune on a "
            "validation split (or with cross-validation) and touch the test set only once at the end.",
        ),
    ],
)

CNOS_LAB = subject(
    "cn-os-lab",
    "22PC2AM322",
    "Computer Networks and Operating Systems Laboratory",
    "CN & OS Lab",
    "laboratory",
    "Implementing data link layer mechanisms and networking tasks, and simulating CPU scheduling, memory, "
    "file, deadlock, page replacement and disk scheduling algorithms.",
    [
        unit(1, "Computer Networks Programs", [
            topic("lab-framing", "Week 1: Data Link Layer Framing – Character, Character Stuffing and "
                  "Bit Stuffing", "Implementing the data link layer framing methods."),
            topic("lab-crc", "Week 2: CRC Polynomials – CRC 12, CRC 16 and CRC CCIP",
                  "Computing CRCs on a data set of characters with three standard polynomials."),
            topic("lab-networking-commands", "Week 3: Basic Networking Commands",
                  "Everyday tools for inspecting and testing a network.", level="Beginner"),
            topic("lab-establish-network", "Week 4: Establishing a Network Between Computers",
                  "Connecting and configuring computers on a network."),
            topic("lab-ftp-server", "Week 5: Configuring an FTP Server for File Sharing",
                  "Setting up file sharing over FTP."),
            topic("lab-dijkstra", "Week 6: Dijkstra's Algorithm for the Shortest Path",
                  "Computing shortest paths through a graph."),
        ]),
        unit(2, "Operating Systems Programs", [
            topic("lab-cpu-scheduling", "Week 1: CPU Scheduling – Round Robin, SJF, FCFS, Priority",
                  "Simulating the four CPU scheduling algorithms."),
            topic("lab-memory-allocation", "Week 2: Memory Allocation – Best Fit, Worst Fit, First Fit",
                  "Simulating contiguous allocation strategies."),
            topic("lab-file-allocation", "Week 3: File Allocation – Sequential, Indexed, Linked",
                  "Simulating file allocation strategies."),
            topic("lab-deadlock", "Week 4: Deadlock Avoidance and Deadlock Detection",
                  "Simulating the Banker's algorithm and detection."),
            PAGE_REPLACEMENT,
            topic("lab-disk-scheduling", "Week 6: Disk Scheduling – SCAN, C-SCAN, LOOK",
                  "Simulating disk-arm scheduling."),
        ]),
    ],
    unit_label="Part",
)

ML_LAB = subject(
    "ml-lab",
    "22PC2AM302",
    "Machine Learning Laboratory",
    "ML Lab",
    "laboratory",
    "Implementing supervised and unsupervised algorithms, neural networks and ensembles, and training and "
    "evaluating models on real data.",
    [
        unit(1, "List of Programs / Experiments", [
            topic("mllab-nb-knn", "Week 1: Naïve Bayes Classifier and k-Nearest Neighbor (k-NN)",
                  "Implementing two baseline classifiers."),
            topic("mllab-decision-trees", "Week 2: Decision Trees – ID3 & CART",
                  "Implementing tree learners."),
            topic("mllab-regression", "Week 3: Linear Regression and Logistic Regression",
                  "Implementing the two regression learners."),
            topic("mllab-svm", "Week 4: Support Vector Machines – Linear and Non-Linear",
                  "Implementing SVMs with and without kernels."),
            topic("mllab-kmeans", "Week 5: Unsupervised k-Means Algorithm", "Implementing k-means."),
            topic("mllab-em-kmeans", "Week 6: EM Algorithm vs. k-Means on a CSV Dataset",
                  "Clustering the same data two ways and comparing quality."),
            MODEL_TRAINING,
            topic("mllab-evaluation", "Week 8: Evaluating Model Performance – Classification, Regression, "
                  "Clustering (Lower Back Pain Symptoms dataset)",
                  "Evaluation metrics, and cluster quality with purity and silhouette width."),
            topic("mllab-random-forest", "Week 9: Random Forest", "Implementing a random forest."),
            topic("mllab-boosting", "Week 10: AdaBoost and XGBoost", "Implementing boosting."),
            topic("mllab-perceptron", "Week 11: Single Layer and Multilayer Perceptron",
                  "Implementing perceptron learning."),
            topic("mllab-case-study", "Weeks 12–13: Real-World Case Study – Amazon Food Review or "
                  "Personalized Cancer Diagnosis", "An end-to-end machine learning project."),
        ]),
    ],
    unit_label="Section",
)
