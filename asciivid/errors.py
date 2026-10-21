"""Custom exceptions for asciivid."""

from __future__ import annotations


class AsciiVideoError(Exception):
    """Base exception for all asciivid errors."""


class UnreadableFileError(AsciiVideoError):
    """Raised when a video file cannot be opened or read."""


class MissingCodecError(AsciiVideoError):
    """Raised when the video codec cannot be handled by OpenCV."""


class FfmpegNotFoundError(AsciiVideoError):
    """Raised when ffmpeg is required for an operation but is not installed."""


class TerminalTooSmallError(AsciiVideoError):
    """Raised when the terminal is too small for the requested ASCII grid."""


class OutputPathError(AsciiVideoError):
    """Raised when an output path cannot be written to."""


class ProjectError(AsciiVideoError):
    """Raised when a project file cannot be loaded or saved."""
