from __future__ import annotations

from .shared import *  # noqa: F401,F403

def chronos_patch_aligned_tail_length(sequence_length: int, patch_size: int) -> int:
    if patch_size <= 0:
        return 0
    aligned = (int(sequence_length) // int(patch_size)) * int(patch_size)
    if aligned <= 0 or aligned >= int(sequence_length):
        return 0
    return aligned
