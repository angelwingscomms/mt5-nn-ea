from __future__ import annotations

from .shared import *  # noqa: F401,F403

def chronos_context_label(context_tail_lengths: Sequence[int]) -> str:
    return "+".join("full" if int(tail_length) <= 0 else str(int(tail_length)) for tail_length in context_tail_lengths)
