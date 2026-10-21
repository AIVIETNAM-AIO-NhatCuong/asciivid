"""Tests for terminal handling (mocked, so no real terminal needed)."""

from __future__ import annotations

from unittest import mock

import pytest

from asciivid.errors import TerminalTooSmallError
from asciivid.terminal import LivePlayer, _enable_windows_vt
from asciivid.settings import AppSettings


def test_enable_windows_vt_non_windows():
    with mock.patch("os.name", "posix"):
        assert _enable_windows_vt() is True


def test_terminal_too_small(synthetic_video):
    settings = AppSettings(cols=9999, color_mode="none")
    player = LivePlayer(synthetic_video["path"], settings, audio=False)
    with mock.patch("shutil.get_terminal_size", return_value=(80, 24)):
        with pytest.raises(TerminalTooSmallError):
            player.run()


def test_audio_player_stop_without_start():
    from asciivid.audio import AudioPlayer
    ap = AudioPlayer("whatever.mp4", enabled=True)
    ap.stop()  # should not raise
