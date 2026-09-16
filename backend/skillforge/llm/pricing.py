"""Price table for LLM cost estimation.

USD per 1M tokens. This is a static, hand-maintained table (no network
calls) so cost estimates stay deterministic and testable. Update it as
provider pricing changes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float


PRICE_TABLE: dict[str, ModelPrice] = {
    # OpenAI
    "gpt-4o": ModelPrice(input_per_million=2.50, output_per_million=10.00),
    "gpt-4o-mini": ModelPrice(input_per_million=0.15, output_per_million=0.60),
    # Anthropic
    "claude-opus-5": ModelPrice(input_per_million=15.00, output_per_million=75.00),
    "claude-sonnet-5": ModelPrice(input_per_million=3.00, output_per_million=15.00),
    "claude-haiku-4-5-20251001": ModelPrice(input_per_million=0.80, output_per_million=4.00),
    # Mock / offline — always free.
    "mock-model": ModelPrice(input_per_million=0.0, output_per_million=0.0),
    "mock-teacher": ModelPrice(input_per_million=0.0, output_per_million=0.0),
    "mock-learner": ModelPrice(input_per_million=0.0, output_per_million=0.0),
}

# Used for any model not found in PRICE_TABLE, so cost estimation never
# raises for an unrecognized/new model string.
DEFAULT_PRICE = ModelPrice(input_per_million=0.0, output_per_million=0.0)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICE_TABLE.get(model, DEFAULT_PRICE)
    return (
        input_tokens / 1_000_000 * price.input_per_million
        + output_tokens / 1_000_000 * price.output_per_million
    )
