"""CLI smoke tests using the synthetic video fixture."""

from __future__ import annotations

import subprocess
import sys

import pytest


def run_cli(args):
    return subprocess.run(
        [sys.executable, "-m", "asciivid"] + args,
        capture_output=True,
        text=True,
    )


def test_cli_help():
    res = run_cli(["--help"])
    assert res.returncode == 0
    assert "Input video file" in res.stdout


def test_cli_text_export(tmp_path, synthetic_video):
    out = tmp_path / "out.txt"
    res = run_cli([synthetic_video["path"], "-o", str(out), "--color", "none", "--cols", "40"])
    assert res.returncode == 0, res.stderr
    assert out.exists()
    content = out.read_text()
    assert "FRAME 0" in content


def test_cli_html_export(tmp_path, synthetic_video):
    out = tmp_path / "out.html"
    res = run_cli([synthetic_video["path"], "-o", str(out), "--color", "truecolor", "--cols", "40"])
    assert res.returncode == 0, res.stderr
    assert out.exists()
    assert "data:image/png" in out.read_text()


def test_cli_nonexistent_input():
    res = run_cli(["/nonexistent/nope.mp4"])
    assert res.returncode != 0
