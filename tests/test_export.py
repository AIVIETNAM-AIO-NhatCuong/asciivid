"""Tests for all four export formats."""

from __future__ import annotations

import os
import re

import cv2
import numpy as np
import pytest

from asciivid.core import AsciiVideo
from asciivid.settings import AppSettings


def _make_frames(tmp_path, n=5, w=32, h=24):
    path = tmp_path / "src.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, 10.0, (w, h))
    for i in range(n):
        frame = np.full((h, w, 3), (i * 40 % 256, 100, 200), dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return str(path)


@pytest.mark.parametrize("fmt,ext", [("text", ".txt"), ("text", ".ans")])
def test_to_text(tmp_path, fmt, ext):
    src = _make_frames(tmp_path)
    av = AsciiVideo(src, AppSettings(cols=20, color_mode="none"))
    out = tmp_path / f"out{ext}"
    av.to_text(str(out))
    assert out.exists()
    content = out.read_text()
    assert "FRAME 0" in content
    assert "FRAME 4" in content
    assert "\f" in content or content.count("FRAME") == 5


def test_to_png_frames(tmp_path):
    src = _make_frames(tmp_path)
    av = AsciiVideo(src, AppSettings(cols=20, color_mode="truecolor"))
    out_dir = tmp_path / "pngs"
    written = av.to_png_frames(str(out_dir))
    assert len(written) == 5
    for p in written:
        assert os.path.isfile(p) and p.lower().endswith(".png")


def test_to_html(tmp_path):
    src = _make_frames(tmp_path)
    av = AsciiVideo(src, AppSettings(cols=20, color_mode="truecolor"))
    out = tmp_path / "out.html"
    av.to_html(str(out))
    assert out.exists()
    content = out.read_text()
    assert "data:image/png" in content
    assert "setInterval" in content


def test_save_load_project_round_trip(tmp_path):
    src = _make_frames(tmp_path)
    av = AsciiVideo(src, AppSettings(cols=90, ramp="#@", color_mode="ansi16", char_aspect=0.6, invert=True, fps=12.0))
    proj = tmp_path / "proj.asciivideo"
    av.save_project(str(proj))
    assert proj.exists()
    source, settings, info = AsciiVideo.load_project(str(proj))
    assert source == src
    assert settings.cols == 90
    assert settings.ramp == "#@"
    assert settings.color_mode == "ansi16"
    assert settings.char_aspect == 0.6
    assert settings.invert is True
    assert settings.fps == 12.0
    assert info["width"] > 0 and info["height"] > 0
