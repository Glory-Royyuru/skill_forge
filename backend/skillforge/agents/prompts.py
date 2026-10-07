"""System prompts for baselines A (no training) and B (static skill)."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_SKILL_PATH = REPO_ROOT / "data" / "skills" / "ecommerce_reference_skill.json"

BASE_PROMPT = (
    "You are a customer support agent for an online store, handling refund requests.\n"
    "Use the available tools to look up the order, the customer, and store policy as needed "
    "(view_policy is available for store policy). Then take exactly one final action: "
    "process_refund, reject_refund, or escalate, with the correct parameters. "
    "Always look up the order before deciding."
)


def load_reference_skill() -> dict:
    return json.loads(REFERENCE_SKILL_PATH.read_text(encoding="utf-8"))


def condition_a_prompt() -> str:
    """No training: base prompt only, policy reachable only via view_policy."""
    return BASE_PROMPT


def condition_b_prompt() -> str:
    """Static skill: base prompt plus a structured reference skill."""
    skill = load_reference_skill()
    return (
        BASE_PROMPT
        + "\n\nYou have also been given this structured reference skill for this task:\n"
        + json.dumps(skill, indent=2)
    )


def prompt_for_condition(condition: str) -> str:
    if condition == "A":
        return condition_a_prompt()
    if condition == "B":
        return condition_b_prompt()
    raise ValueError(f"unknown condition: {condition!r}")
