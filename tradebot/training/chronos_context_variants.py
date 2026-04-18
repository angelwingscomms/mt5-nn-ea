from __future__ import annotations

from .shared import *  # noqa: F401,F403

def chronos_context_variants(args: argparse.Namespace, sequence_length: int, patch_size: int) -> tuple[tuple[int, ...], ...]:
    patch_aligned_tail = chronos_patch_aligned_tail_length(sequence_length, patch_size)

    if args.chronos_auto_context:
        variants: list[tuple[int, ...]] = [(0,)]
        if patch_size > 0:
            tail = (sequence_length // patch_size) * patch_size
            while tail >= patch_size:
                variant = (0,) if tail >= sequence_length else (tail,)
                if variant not in variants:
                    variants.append(variant)
                tail -= patch_size
        return tuple(variants)

    if args.chronos_ensemble_contexts and patch_aligned_tail > 0:
        return ((0, patch_aligned_tail),)

    if args.chronos_patch_aligned_context and patch_aligned_tail > 0:
        return ((patch_aligned_tail,),)

    return ((0,),)
