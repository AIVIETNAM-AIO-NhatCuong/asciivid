"""asciivid: convert video into coloured ASCII art, live or exported."""

from __future__ import annotations

from .core import AsciiVideo
from .errors import (
    AsciiVideoError,
    FfmpegNotFoundError,
    MissingCodecError,
    OutputPathError,
    ProjectError,
    TerminalTooSmallError,
    UnreadableFileError,
)
from .render import render_frame
from .settings import AppSettings, COLOR_MODES, DEFAULT_RAMP
from .terminal import LivePlayer
from .utils import find_ffmpeg, find_ffplay, find_ffprobe, find_monospace_font, setup_logging
from .video import VideoInfo, get_video_info, iter_frames, load_video

__all__ = [
    "AsciiVideo",
    "AppSettings",
    "COLOR_MODES",
    "DEFAULT_RAMP",
    "FfmpegNotFoundError",
    "LivePlayer",
    "MissingCodecError",
    "OutputPathError",
    "ProjectError",
    "TerminalTooSmallError",
    "UnreadableFileError",
    "AsciiVideoError",
    "VideoInfo",
    "find_ffmpeg",
    "find_ffplay",
    "find_ffprobe",
    "find_monospace_font",
    "get_video_info",
    "iter_frames",
    "load_video",
    "render_frame",
    "setup_logging",
]

__version__ = "0.1.0"
