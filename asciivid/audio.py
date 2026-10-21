"""Audio playback helper for live terminal mode.

Launches ``ffplay`` in the background to play a video's audio track while the
terminal renders frames. Degrades silently when ffplay is unavailable.
"""

from __future__ import annotations

import subprocess
from typing import Optional

from .utils import find_ffplay, logger


class AudioPlayer:
    """Best-effort background audio player backed by ffplay."""

    def __init__(self, path: str, enabled: bool = True) -> None:
        self.path = path
        self.enabled = enabled
        self._proc: Optional[subprocess.Popen] = None

    def start(self) -> None:
        if not self.enabled:
            return
        ffplay = find_ffplay()
        if not ffplay:
            logger.warning("ffplay not found; live audio unavailable")
            return
        try:
            self._proc = subprocess.Popen(
                [ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet", self.path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.debug("Started ffplay audio: %s", self.path)
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("Could not start ffplay audio: %s", exc)

    def stop(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            self._proc.wait(timeout=2)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
        self._proc = None
