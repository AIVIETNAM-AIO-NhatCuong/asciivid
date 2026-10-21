"""Tests for the rendering pipeline: frame count, ramp mapping, truecolor."""

from __future__ import annotations

import re
import cv2
import numpy as np
import pytest

from asciivid.render import render_frame
from asciivid.settings import AppSettings

RAMP = " .:-=+*#%@"


def _uniform_frame(color, h=20, w=20):
    return np.full((h, w, 3), color, dtype=np.uint8)


def test_render_frame_count(synthetic_video):
    import asciivid.video as vmod

    frames = list(vmod.iter_frames(synthetic_video["path"]))
    assert len(frames) == synthetic_video["info"].frame_count


def test_ramp_darkest_to_brightest():
    settings = AppSettings(cols=20, ramp=RAMP, color_mode="none")
    dark = render_frame(_uniform_frame((0, 0, 0)), settings)
    bright = render_frame(_uniform_frame((255, 255, 255)), settings)
    # Uniform frame -> every cell same char.
    assert set(dark.replace("\n", "")) == {RAMP[0]}
    assert set(bright.replace("\n", "")) == {RAMP[-1]}


def test_ramp_mid_value():
    settings = AppSettings(cols=20, ramp=RAMP, color_mode="none")
    mid = render_frame(_uniform_frame((128, 128, 128)), settings)
    expected = RAMP[int(round((128 / 255) * (len(RAMP) - 1)))]
    assert set(mid.replace("\n", "")) == {expected}


def test_invert_ramp():
    normal = AppSettings(cols=20, ramp=RAMP, color_mode="none", invert=False)
    inverted = AppSettings(cols=20, ramp=RAMP, color_mode="none", invert=True)
    dark_normal = render_frame(_uniform_frame((0, 0, 0)), normal)
    dark_inverted = render_frame(_uniform_frame((0, 0, 0)), inverted)
    assert set(dark_normal.replace("\n", "")) == {RAMP[0]}
    assert set(dark_inverted.replace("\n", "")) == {RAMP[-1]}


def test_truecolor_contains_escapes():
    settings = AppSettings(cols=20, ramp=RAMP, color_mode="truecolor")
    # Two-tone frame so at least one colour run appears.
    frame = np.zeros((20, 40, 3), dtype=np.uint8)
    frame[:, 20:] = (255, 0, 0)
    out = render_frame(frame, settings)
    assert re.search(r"\x1b\[38;2;\d+;\d+;\d+m", out), "missing truecolor ESC sequence"
    assert "\x1b[0m" in out


def test_ansi256_contains_escapes():
    settings = AppSettings(cols=20, ramp=RAMP, color_mode="ansi256")
    out = render_frame(_uniform_frame((100, 150, 200)), settings)
    assert re.search(r"\x1b\[38;5;\d+m", out)


def test_none_has_no_escapes():
    settings = AppSettings(cols=20, ramp=RAMP, color_mode="none")
    out = render_frame(_uniform_frame((100, 150, 200)), settings)
    assert "\x1b" not in out


def test_rows_from_aspect():
    settings = AppSettings(cols=40, char_aspect=0.5, color_mode="none")
    frame = np.zeros((100, 200, 3), dtype=np.uint8)  # 2:1 wide
    out = render_frame(frame, settings)
    rows = out.count("\n") + 1
    expected_rows = max(1, int(round(40 * (100 / 200) * 0.5)))  # = 10
    assert rows == expected_rows
