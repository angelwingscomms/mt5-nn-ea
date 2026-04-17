from __future__ import annotations

from .shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class BarMode:
    USE_FIXED_TIME_BARS: bool
    USE_FIXED_TICK_BARS: bool

    @property
    def is_time(self) -> bool:
        return self.USE_FIXED_TIME_BARS

    @property
    def is_tick(self) -> bool:
        return self.USE_FIXED_TICK_BARS

    @property
    def is_imbalance(self) -> bool:
        return not (self.USE_FIXED_TIME_BARS or self.USE_FIXED_TICK_BARS)
