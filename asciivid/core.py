"""High-level AsciiVideo class tying loading, rendering, and export together."""

from __future__ import annotations

from typing import Iterable, Iterator, Optional, Tuple

import numpy as np

from .errors import OutputPathError
from .export import (
    FrameSource,
    load_project as _load_project,
    save_project as _save_project,
    to_html as _to_html,
    to_png_frames as _to_png_frames,
    to_text as _to_text,
    to_video as _to_video,
)
from .render import render_frame
from .settings import AppSettings
from .video import get_video_info, iter_frames, load_video


class AsciiVideo:
    """Library interface for converting a video to coloured ASCII.

    Parameters:
        path: Source video file.
        settings: Conversion settings (defaults if None).
    """

    def __init__(self, path: str, settings: Optional[AppSettings] = None) -> None:
        self.path = path
        self.settings = settings or AppSettings()
        self._info = None

    @property
    def info(self):
        if self._info is None:
            self._info = get_video_info(self.path)
        return self._info

    def video_to_frames(self) -> Iterator[Tuple[int, np.ndarray]]:
        """Stream frames from the source video (one frame in RAM at a time)."""
        return iter_frames(self.path)

    def render_frame(self, frame: np.ndarray, *, cols: Optional[int] = None) -> str:
        """Render a single BGR frame to a coloured ANSI/ASCII string."""
        return render_frame(frame, self.settings, cols=cols)

    def _frames(self, frames: Optional[FrameSource]) -> FrameSource:
        return frames if frames is not None else self.video_to_frames()

    def to_text(
        self, path: str, frames: Optional[FrameSource] = None
    ) -> None:
        _to_text(path, self.settings, self._frames(frames))

    def to_png_frames(
        self, directory: str, frames: Optional[FrameSource] = None
    ) -> list[str]:
        return _to_png_frames(directory, self.settings, self._frames(frames))

    def to_video(
        self,
        path: str,
        frames: Optional[FrameSource] = None,
        *,
        fps: Optional[float] = None,
        no_audio: bool = False,
    ) -> None:
        _to_video(path, self.path, self.settings, self._frames(frames), fps=fps, no_audio=no_audio)

    def to_html(
        self, path: str, frames: Optional[FrameSource] = None
    ) -> None:
        _to_html(path, self.path, self.settings, self._frames(frames))

    def save_project(self, path: str) -> None:
        _save_project(path, self.path, self.settings, self.info)

    @staticmethod
    def load_project(path: str) -> Tuple[str, AppSettings, dict]:
        """Load a .asciivideo project. Returns (source, settings, info)."""
        return _load_project(path)

    @classmethod
    def from_project(cls, path: str) -> "AsciiVideo":
        source, settings, _info = _load_project(path)
        return cls(source, settings)

    def load(self) -> Tuple[list[np.ndarray]]:
        """Load all frames into RAM (convenience wrapper around load_video)."""
        frames, _ = load_video(self.path)
        return frames
