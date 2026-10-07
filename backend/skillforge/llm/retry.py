"""Exponential-backoff retry for transient/rate-limit provider errors.

Never logs the exception's string content (SDK error messages can embed
request details) — only the exception type and attempt count.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 0.5


def call_with_retry(
    fn: Callable[[], T],
    retryable_exceptions: tuple[type[BaseException], ...],
    max_retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY_SECONDS,
) -> T:
    attempt = 0
    while True:
        try:
            return fn()
        except retryable_exceptions as exc:
            attempt += 1
            if attempt > max_retries:
                raise
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.1)
            logger.warning(
                "retryable LLM error (%s), attempt %d/%d, retrying in %.2fs",
                type(exc).__name__,
                attempt,
                max_retries,
                delay,
            )
            time.sleep(delay)
