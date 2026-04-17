from __future__ import annotations

from .shared import *  # noqa: F401,F403

def fixed_move_price_distance(fixed_move_points: float, point_size: float) -> float:
    return float(fixed_move_points) * float(point_size)
