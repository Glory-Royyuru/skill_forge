"""SkillForge curriculum content, grouped into curriculum areas.

- VNR VJIET B.Tech. CSE (AI & ML), R22 (source: "10. AIML - R22 @
  19.07.2025.pdf"): the eight courses requested for SkillForge;
  professional/open-elective alternatives listed in the PDF are deliberately
  excluded. Order follows the course table.
- Foundations: Data Structures & Algorithms, a general area that belongs to
  no institution.

These modules are the seed source. At runtime the curriculum is read from
the database (see `skillforge.teacher.seed`).
"""

from __future__ import annotations

from skillforge.teacher.content import (
    artificial_intelligence,
    computer_networks,
    dsa,
    explainable_ai,
    gender_sensitization,
    labs,
    machine_learning,
    operating_systems,
    resources,
)
from skillforge.teacher.content.question_meta import annotate

SUBJECTS = [
    computer_networks.SUBJECT,
    artificial_intelligence.SUBJECT,
    operating_systems.SUBJECT,
    machine_learning.SUBJECT,
    explainable_ai.SUBJECT,
    labs.CNOS_LAB,
    labs.ML_LAB,
    gender_sensitization.SUBJECT,
    dsa.SUBJECT,
]

annotate(SUBJECTS)
resources.attach(SUBJECTS)
