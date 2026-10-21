"""Export functions: text, PNG frames, video, HTML, project save/load."""

from __future__ import annotations

import html as html_mod
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Iterator, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .errors import FfmpegNotFoundError, OutputPathError, ProjectError
from .render import render_frame, render_frame_to_png
from .settings import AppSettings
from .utils import find_ffmpeg, find_ffprobe, find_monospace_font, logger
from .video import get_video_info, iter_frames

FrameSource = Iterable[Tuple[int, np.ndarray]]


def _ensure_writable(path: str) -> None:
    p = Path(path)
    if p.exists() and not p.is_file():
        raise OutputPathError(f"Output path is not a file: {path}")
    parent = p.parent if p.parent != Path("") else Path(".")
    if not parent.exists():
        raise OutputPathError(f"Output directory does not exist: {parent}")
    if not os.access(parent, os.W_OK):
        raise OutputPathError(f"Output directory not writable: {parent}")


def _font_and_metrics(settings: AppSettings):
    font_path = find_monospace_font()
    font_size = 14
    font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    bbox = font.getbbox("x")
    char_w = max(1, (bbox[2] - bbox[0]))
    char_h = max(1, (bbox[3] - bbox[1]) or font_size)
    return font, char_w, char_h


def to_text(
    path: str,
    settings: AppSettings,
    frames: FrameSource,
    *,
    separator: str = "\f",
) -> None:
    """Write all frames to a single .txt/.ans file separated by form feeds.

    Each frame is preceded by a header line ``--- FRAME N ---``.
    """
    _ensure_writable(path)
    with open(path, "w", encoding="utf-8") as fh:
        first = True
        for idx, frame in frames:
            if not first:
                fh.write(separator + "\n")
            fh.write(f"--- FRAME {idx} ---\n")
            fh.write(render_frame(frame, settings))
            fh.write("\n")
            first = False
    logger.info("Wrote text export to %s", path)


def to_png_frames(
    directory: str,
    settings: AppSettings,
    frames: FrameSource,
) -> list[str]:
    """Render every frame as a numbered PNG using Pillow + a monospace font.

    Returns the list of written file paths.
    """
    _ensure_writable(directory)
    out_dir = Path(directory)
    out_dir.mkdir(parents=True, exist_ok=True)

    font, char_w, char_h = _font_and_metrics(settings)
    written: list[str] = []
    for idx, frame in frames:
        img = render_frame_to_png(frame, settings, font, char_w, char_h)
        out_path = out_dir / f"frame_{idx:05d}.png"
        img.save(out_path)
        written.append(str(out_path))
    logger.info("Wrote %d PNG frames to %s", len(written), directory)
    return written


def _source_has_audio(source_path: str, ffprobe: str) -> bool:
    """Return True if the source video contains at least one audio stream."""
    try:
        out = subprocess.run(
            [
                ffprobe, "-v", "error", "-select_streams", "a",
                "-show_entries", "stream=codec_type", "-of",
                "csv=p=0", source_path,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return bool(out.stdout.strip())
    except Exception:
        return False


def to_video(
    path: str,
    source_path: str,
    settings: AppSettings,
    frames: FrameSource,
    *,
    fps: Optional[float] = None,
    no_audio: bool = False,
) -> None:
    """Render frames to an MP4 via Pillow + ffmpeg, muxing original audio.

    The source audio is muxed back in so duration stays within one frame of
    the input. The source is used as a second ffmpeg input so its audio is
    stream-copied without a fragile extract/re-encode step.

    Raises:
        FfmpegNotFoundError: if ffmpeg is not installed.
    """
    _ensure_writable(path)
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise FfmpegNotFoundError(
            "ffmpeg is required for video export but was not found. "
            "Install ffmpeg (https://ffmpeg.org) and ensure it is on PATH."
        )
    ffprobe = find_ffprobe()

    info = get_video_info(source_path)
    out_fps = fps or settings.fps or info.fps or 30.0

    with tempfile.TemporaryDirectory() as tmpdir:
        frames_dir = os.path.join(tmpdir, "frames")
        os.mkdir(frames_dir)

        font, char_w, char_h = _font_and_metrics(settings)
        count = 0
        for idx, frame in frames:
            img = render_frame_to_png(frame, settings, font, char_w, char_h)
            img.save(os.path.join(frames_dir, f"frame_{count:05d}.png"))
            count += 1
        if count == 0:
            raise OutputPathError(f"No frames to encode for {path}")

        # All inputs first, then all output options (ffmpeg option order matters).
        cmd = [
            ffmpeg, "-y",
            "-framerate", str(out_fps),
            "-i", os.path.join(frames_dir, "frame_%05d.png"),
        ]
        use_audio = (not no_audio) and ffprobe is not None and _source_has_audio(source_path, ffprobe)
        if use_audio:
            cmd.append("-i")
            cmd.append(source_path)

        cmd += [
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(out_fps),
            "-map", "0:v",
        ]
        if use_audio:
            cmd += ["-map", "1:a?", "-c:a", "copy", "-shortest"]
        else:
            cmd += ["-map", "0:v"]
        cmd.append(path)

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.decode("utf-8", "replace")[-500:] if exc.stderr else ""
            raise FfmpegNotFoundError(
                f"ffmpeg failed to encode {path}: {detail}"
            ) from exc

    logger.info("Wrote video export to %s (%d frames)", path, count)


def to_html(
    path: str,
    source_path: str,
    settings: AppSettings,
    frames: FrameSource,
) -> None:
    """Write a self-contained HTML file with JS playback of every frame.

    Each frame is embedded inline as coloured <span> runs.
    """
    _ensure_writable(path)
    info = get_video_info(source_path)
    fps = settings.fps or info.fps or 30.0
    interval_ms = max(1, int(1000.0 / fps))

    font, char_w, char_h = _font_and_metrics(settings)

    frames_html: list[str] = []
    for idx, frame in frames:
        img = render_frame_to_png(frame, settings, font, char_w, char_h)
        # Convert to a data URI so the HTML is fully self-contained.
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        import base64
        data = base64.b64encode(buf.getvalue()).decode("ascii")
        frames_html.append(
            f'<div class="frame" data-index="{idx}" style="display:none">'
            f'<img src="data:image/png;base64,{data}" style="image-rendering:pixelated">'
            f"</div>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ASCII Video</title>
<style>
  body {{ margin:0; background:#000; color:#0f0; font-family:monospace; display:flex; justify-content:center; align-items:center; height:100vh; }}
  #stage {{ max-width:100vw; max-height:100vh; overflow:auto; }}
  .frame {{ display:none; }}
  .frame.active {{ display:block; }}
  img {{ display:block; }}
  #controls {{ position:absolute; bottom:10px; left:10px; color:#aaa; font-size:12px; }}
</style>
</head>
<body>
<div id="stage">
{''.join(frames_html)}
</div>
<div id="controls">ASCII Video &bull; {info.width}x{info.height} &bull; {fps:.1f} FPS &bull; <span id="idx">0</span>/{len(frames_html)}</div>
<script>
  const frames = document.querySelectorAll('.frame');
  let i = 0;
  let playing = true;
  function show(n) {{
    frames.forEach((f, k) => f.classList.toggle('active', k === n));
    document.getElementById('idx').textContent = n;
  }}
  function next() {{ i = (i + 1) % frames.length; show(i); }}
  setInterval(next, {interval_ms});
  show(0);
</script>
</body>
</html>"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    logger.info("Wrote HTML export to %s (%d frames)", path, len(frames_html))


def save_project(
    path: str,
    source: str,
    settings: AppSettings,
    info,
) -> None:
    """Save a .asciivideo project manifest (JSON) with settings + source info."""
    _ensure_writable(path)
    manifest = {
        "source": source,
        "settings": {
            "cols": settings.cols,
            "ramp": settings.ramp,
            "color_mode": settings.color_mode,
            "char_aspect": settings.char_aspect,
            "invert": settings.invert,
            "fps": settings.fps,
        },
        "info": {
            "path": info.path,
            "fps": info.fps,
            "width": info.width,
            "height": info.height,
            "frame_count": info.frame_count,
            "duration": info.duration,
            "codec": info.codec,
        },
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    logger.info("Saved project to %s", path)


def load_project(path: str) -> Tuple[str, AppSettings, dict]:
    """Load a .asciivideo project manifest.

    Returns ``(source_path, AppSettings, info_dict)``.
    """
    p = Path(path)
    if not p.is_file():
        raise ProjectError(f"Project file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        raise ProjectError(f"Could not read project file {path}: {exc}") from exc

    try:
        source = manifest["source"]
        s = manifest["settings"]
        settings = AppSettings(
            cols=int(s["cols"]),
            ramp=str(s["ramp"]),
            color_mode=str(s["color_mode"]),
            char_aspect=float(s["char_aspect"]),
            invert=bool(s["invert"]),
            fps=s.get("fps"),
        )
        info = manifest.get("info", {})
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectError(f"Malformed project file {path}: {exc}") from exc

    logger.info("Loaded project %s -> %s", path, source)
    return source, settings, info
