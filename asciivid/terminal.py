"""Live terminal playback: cursor control, clear/redraw, FPS pacing."""

from __future__ import annotations

import os
import shutil
import sys
import time
from dataclasses import replace
from typing import Optional

import ctypes

from .audio import AudioPlayer
from .errors import TerminalTooSmallError
from .render import render_frame
from .settings import AppSettings
from .utils import logger
from .video import get_video_info, iter_frames

# ANSI control sequences.
_CURSOR_HIDE = "\x1b[?25l"
_CURSOR_SHOW = "\x1b[?25h"
_CLEAR = "\x1b[2J"
_HOME = "\x1b[H"
_RESET = "\x1b[0m"


def _enable_windows_vt() -> bool:
    """Enable VT/ANSI processing on the Windows console. No-op elsewhere."""
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        if kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING):
            return True
        logger.warning("Could not enable VT processing; falling back to plain text")
        return False
    except Exception as exc:  # pragma: no cover - platform specific
        logger.warning("VT enable failed: %s", exc)
        return False


class LivePlayer:
    """Plays a video as coloured ASCII in the terminal, synced to source FPS."""

    def __init__(
        self,
        path: str,
        settings: AppSettings,
        *,
        audio: bool = True,
        override_fps: Optional[float] = None,
    ) -> None:
        self.path = path
        self.settings = settings
        self.audio = audio
        self.override_fps = override_fps
        self._stop = False
        self._audio: Optional[AudioPlayer] = None

    def stop(self) -> None:
        """Request a clean stop (callable from a signal handler / another thread)."""
        self._stop = True

    def _restore(self) -> None:
        """Restore cursor and terminal state."""
        try:
            sys.stdout.write(_CURSOR_SHOW)
            sys.stdout.write(_CLEAR)
            sys.stdout.write(_RESET)
            sys.stdout.flush()
        except Exception:
            pass
        if self._audio is not None:
            self._audio.stop()

    def _required_rows(self, info) -> int:
        return max(
            1,
            int(round(self.settings.cols * (info.height / info.width) * self.settings.char_aspect)),
        )

    def run(self) -> None:
        info = get_video_info(self.path)
        fps = self.override_fps or self.settings.fps or info.fps or 30.0
        if fps <= 0:
            fps = 30.0
        frame_time = 1.0 / fps

        rows = self._required_rows(info)

        # Terminal size check.
        try:
            term_w, term_h = shutil.get_terminal_size((80, 24))
        except Exception:
            term_w, term_h = 80, 24
        if self.settings.cols > term_w or rows > term_h - 1:
            raise TerminalTooSmallError(
                f"Terminal {term_w}x{term_h} is too small for the "
                f"{self.settings.cols}x{rows} ASCII grid. "
                f"Resize the terminal or pass --cols {term_w} (or smaller)."
            )

        # Windows VT / ANSI support.
        vt_ok = _enable_windows_vt()
        if not vt_ok and self.settings.color_mode != "none":
            logger.warning(
                "Console lacks ANSI support; degrading to 'none' color mode"
            )
            self.settings = replace(self.settings, color_mode="none")

        # Start background audio (best effort).
        self._audio = AudioPlayer(self.path, enabled=self.audio)
        self._audio.start()

        sys.stdout.write(_CURSOR_HIDE + _CLEAR)
        sys.stdout.flush()

        next_frame_due = time.perf_counter()
        try:
            for _idx, frame in iter_frames(self.path):
                if self._stop:
                    break
                frame_str = render_frame(frame, self.settings)
                sys.stdout.write(_HOME + frame_str + "\n")
                sys.stdout.flush()

                # Pace to source FPS, compensating for render time.
                next_frame_due += frame_time
                sleep_for = next_frame_due - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    # Fell behind; reset the due time rather than spiralling.
                    next_frame_due = time.perf_counter()
        except KeyboardInterrupt:
            pass
        finally:
            self._restore()
