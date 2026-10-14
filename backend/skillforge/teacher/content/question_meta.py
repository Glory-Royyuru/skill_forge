"""Question metadata kept beside the content: cognitive type and quality.

Cognitive types (a simplified Bloom's taxonomy):
- recall: retrieve a fact or definition
- understand: explain or interpret an idea
- apply: use a rule or procedure on a concrete case (often a calculation)
- analyze: reason about a scenario, compare options or diagnose a problem

Each type was assigned by reading what the question actually demands, not
from its difficulty level. All current questions were checked against their
explanations and why-wrong notes by the authoring pass, so they are marked
"reviewed"; future unreviewed additions should be added as "draft", which keeps
them out of analytics until reviewed.
"""

from __future__ import annotations

COGNITIVE_TYPES = ("recall", "understand", "apply", "analyze")
QUALITY_LEVELS = ("reviewed", "draft", "retired")
DEFAULT_SOURCE = "SkillForge question bank, written for the VNR R22 AIML syllabus"

R, U, A, N = "recall", "understand", "apply", "analyze"

COGNITIVE = {
    # Computer Networks
    "cn-osi-1": R, "cn-osi-2": R, "cn-osi-3": U, "cn-osi-4": U, "cn-osi-5": A, "cn-osi-6": N,
    "cn-ed-1": A, "cn-ed-2": R, "cn-ed-3": A, "cn-ed-4": U, "cn-ed-5": A, "cn-ed-6": A,
    "cn-tl-1": R, "cn-tl-2": R, "cn-tl-3": U, "cn-tl-4": U, "cn-tl-5": A, "cn-tl-6": N,
    # Artificial Intelligence
    "ai-ag-1": R, "ai-ag-2": U, "ai-ag-3": A, "ai-ag-4": R, "ai-ag-5": N, "ai-ag-6": N,
    "ai-s-1": R, "ai-s-2": R, "ai-s-3": U, "ai-s-4": U, "ai-s-5": U, "ai-s-6": U,
    # Operating Systems
    "os-cs-1": U, "os-cs-2": R, "os-cs-3": U, "os-cs-4": U, "os-cs-5": A, "os-cs-6": A,
    "os-dl-1": R, "os-dl-2": R, "os-dl-3": U, "os-dl-4": U, "os-dl-5": U, "os-dl-6": A,
    # Machine Learning
    "lr-1": R, "lr-2": R, "lr-3": U, "lr-4": U, "lr-5": U, "lr-6": N,
    "dt-1": R, "dt-2": R, "dt-3": U, "dt-4": A, "dt-5": N, "dt-6": A,
    "of-1": R, "of-2": U, "of-3": U, "of-4": A, "of-5": N, "of-6": U,
    # Explainable AI
    "xai-ph-1": R, "xai-ph-2": U, "xai-ph-3": A, "xai-ph-4": U, "xai-ph-5": U, "xai-ph-6": U,
    # Laboratories
    "lab-pr-1": R, "lab-pr-2": R, "lab-pr-3": U, "lab-pr-4": U, "lab-pr-5": A, "lab-pr-6": A,
    "mllab-mt-1": R, "mllab-mt-2": A, "mllab-mt-3": U, "mllab-mt-4": R, "mllab-mt-5": U, "mllab-mt-6": N,
    # Gender Sensitization
    "gs-1": U, "gs-2": R, "gs-3": U, "gs-4": U, "gs-5": N, "gs-6": A,
}


def annotate(subjects: list[dict]) -> None:
    """Attach metadata to every question in place (fails loudly on gaps)."""
    for s in subjects:
        for u in s["units"]:
            for t in u["topics"]:
                for q in t["questions"]:
                    # Content written with its metadata inline (e.g. DSA) keeps it.
                    if not q.get("cognitive_type"):
                        q["cognitive_type"] = COGNITIVE[q["id"]]
                    q.setdefault("quality", "reviewed")
                    q.setdefault("active", True)
                    q.setdefault("source", DEFAULT_SOURCE)
                    assert q["cognitive_type"] in COGNITIVE_TYPES, q["id"]
                    assert q["quality"] in QUALITY_LEVELS, q["id"]
