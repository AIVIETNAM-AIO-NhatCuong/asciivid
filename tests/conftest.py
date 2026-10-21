"""Pytest fixtures: a tiny synthetic video generated with numpy + cv2."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from asciivid.video import get_video_info


def _make_video(path, fps=10.0, n_frames=10, w=64, h=48):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    if not writer.isOpened():
        # Fallback codec.
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        path = path.rsplit(".", 1)[0] + ".avi"
        writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    for i in range(n_frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:] = (i * 25 % 256, 128, 255 - (i * 25 % 256))
        cv2.rectangle(frame, (i * 2, i * 2), (i * 2 + 10, i * 2 + 10), (255, 255, 255), -1)
        writer.write(frame)
    writer.release()
    return path


@pytest.fixture
def synthetic_video(tmp_path):
    path = tmp_path / "synthetic.mp4"
    actual = _make_video(str(path))
    info = get_video_info(actual)
    return {"path": actual, "info": info}
