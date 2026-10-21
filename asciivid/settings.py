"""AppSettings dataclass and colour-mode constants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

DEFAULT_RAMP = " .:-=+*#%@"
DEFAULT_COLOR_MODE = "truecolor"
DEFAULT_COLS = 120
DEFAULT_CHAR_ASPECT = 0.5

COLOR_MODES = ("none", "ansi16", "ansi256", "truecolor")


@dataclass
class AppSettings:
    """User-facing settings for ASCII video conversion.

    Attributes:
        cols: Target number of character columns.
        ramp: Character ramp, darkest to brightest.
        color_mode: one of "none", "ansi16", "ansi256", "truecolor".
        char_aspect: char_width / char_height ratio (default 0.5).
        invert: invert the ramp for light backgrounds.
        fps: override playback/export FPS (None = use source FPS).
    """

    cols: int = DEFAULT_COLS
    ramp: str = DEFAULT_RAMP
    color_mode: str = DEFAULT_COLOR_MODE
    char_aspect: float = DEFAULT_CHAR_ASPECT
    invert: bool = False
    fps: Optional[float] = None

    def __post_init__(self) -> None:
        if self.cols < 1:
            raise ValueError("cols must be >= 1")
        if self.char_aspect <= 0:
            raise ValueError("char_aspect must be > 0")
        if self.color_mode not in COLOR_MODES:
            raise ValueError(f"color_mode must be one of {COLOR_MODES}")
        if len(self.ramp) < 2:
            raise ValueError("ramp must contain at least 2 characters")
