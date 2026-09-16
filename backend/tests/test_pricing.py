from __future__ import annotations

from skillforge.llm.pricing import estimate_cost


def test_mock_model_is_free():
    assert estimate_cost("mock-learner", input_tokens=10_000, output_tokens=10_000) == 0.0


def test_unknown_model_defaults_to_zero_cost():
    assert estimate_cost("some-unlisted-model", input_tokens=1000, output_tokens=1000) == 0.0


def test_known_model_cost_is_positive():
    cost = estimate_cost("gpt-4o", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost > 0
