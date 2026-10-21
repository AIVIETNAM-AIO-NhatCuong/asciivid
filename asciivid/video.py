"""Video loading: OpenCV capture, metadata, streaming + RAM loaders."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, List, Tuple

import cv2
import numpy as np

from .errors import UnreadableFileError
from .utils import logger

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


class VideoInfo:
    """Metadata about a source video.

    Attributes:
        path: Source file path.
        fps: Frames per second.
        width: Frame width in pixels.
        height: Frame height in pixels.
        frame_count: Total number of frames.
        duration: Duration in seconds.
        codec: FourCC codec string.
    """

    def __init__(
        self,
        path: str,
        fps: float,
        width: int,
        height: int,
        frame_count: int,
        duration: float,
        codec: str,
    ) -> None:
        self.path = path
        self.fps = fps
        self.width = width
        self.height = height
        self.frame_count = frame_count
        self.duration = duration
        self.codec = codec

    def __repr__(self) -> str:
        return (
            f"VideoInfo(path={self.path!r}, fps={self.fps:.3f}, "
            f"{self.width}x{self.height}, frames={self.frame_count}, "
            f"duration={self.duration:.3f}s, codec={self.codec!r})"
        )


def _validate_path(path: str) -> None:
    p = Path(path)
    if not p.is_file():
        raise UnreadableFileError(f"Video file not found or not readable: {path}")
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise UnreadableFileError(
            f"Unsupported extension {p.suffix!r}; "
            f"supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )


def _fourcc_to_string(value: float) -> str:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return "unknown"
    return "".join(chr((v >> (8 * i)) & 0xFF) for i in range(4)) or "unknown"


def load_video(path: str) -> Tuple[List[np.ndarray], VideoInfo]:
    """Load all frames of a video into RAM.

    Returns ``(frames, info)``. This holds the whole video in memory; use
    :func:`iter_frames` for streaming when RAM is a concern.

    Raises:
        UnreadableFileError: if the file cannot be opened or contains no frames.
    """
    _validate_path(path)
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise UnreadableFileError(
            f"Could not open video (missing codec?): {path}"
        )

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        stored_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        codec = _fourcc_to_string(cap.get(cv2.CAP_PROP_FOURCC) or 0)

        frames: List[np.ndarray] = []
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            frames.append(frame)

        if not frames:
            raise UnreadableFileError(f"No frames could be read from {path}")

        if width == 0 or height == 0:
            height, width = frames[0].shape[:2]

        duration = (len(frames) / fps) if fps else 0.0
        info = VideoInfo(
            path=path,
            fps=fps,
            width=width,
            height=height,
            frame_count=len(frames),
            duration=duration,
            codec=codec,
        )
        # Trust stored count when available (some containers report it exactly).
        if stored_count and stored_count != len(frames):
            info.frame_count = stored_count
            info.duration = (stored_count / fps) if fps else 0.0

        logger.info("Loaded %s: %s", path, info)
        return frames, info
    finally:
        cap.release()


def iter_frames(path: str) -> Iterator[Tuple[int, np.ndarray]]:
    """Stream frames from a video, yielding ``(index, frame)`` tuples.

    Never holds more than one frame in RAM.

    Raises:
        UnreadableFileError: if the file cannot be opened.
    """
    _validate_path(path)
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise UnreadableFileError(f"Could not open video (missing codec?): {path}")
    try:
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            yield idx, frame
            idx += 1
    finally:
        cap.release()


def get_video_info(path: str) -> VideoInfo:
    """Return metadata without decoding frames.

    Raises:
        UnreadableFileError: if the file cannot be opened.
    """
    _validate_path(path)
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise UnreadableFileError(f"Could not open video: {path}")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = (frame_count / fps) if fps else 0.0
        codec = _fourcc_to_string(cap.get(cv2.CAP_PROP_FOURCC) or 0)
        return VideoInfo(
            path=path,
            fps=fps,
            width=width,
            height=height,
            frame_count=frame_count,
            duration=duration,
            codec=codec,
        )
    finally:
        cap.release()
