"""Command-line interface for asciivid."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .core import AsciiVideo
from .errors import AsciiVideoError
from .export import load_project as _load_project
from .settings import AppSettings, COLOR_MODES
from .terminal import LivePlayer
from .utils import setup_logging, logger


def _detect_format(output: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit.lower()
    suffix = Path(output).suffix.lower()
    if suffix in {".mp4", ".mkv", ".avi", ".mov", ".webm"}:
        return "video"
    if suffix in {".txt", ".ans"}:
        return "text"
    if suffix == ".html":
        return "html"
    if Path(output).is_dir() or suffix == "":
        return "png"
    raise OutputPathError(
        f"Could not determine export format from {output!r}; use --format."
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="asciivid",
        description="Convert video to coloured ASCII art (live playback or export).",
    )
    p.add_argument("input", help="Input video file (.mp4/.mov/.avi/.mkv/.webm)")
    p.add_argument("-o", "--output", help="Output file/directory. Omits -> live terminal playback")
    p.add_argument("--cols", type=int, default=120, help="Character columns (default 120)")
    p.add_argument(
        "--color", default="truecolor", choices=COLOR_MODES,
        help="Color mode (default truecolor)",
    )
    p.add_argument("--ramp", default=" .:-=+*#%@", help="Character ramp darkest->brightest")
    p.add_argument("--no-audio", action="store_true", help="Disable audio (live & video export)")
    p.add_argument("--fps", type=float, default=None, help="Override FPS (default: source FPS)")
    p.add_argument(
        "--format", choices=["text", "video", "html", "png"], default=None,
        help="Force export format (default: auto-detect from -o extension)",
    )
    p.add_argument("--char-aspect", type=float, default=0.5, help="char_width/char_height (default 0.5)")
    p.add_argument("--invert", action="store_true", help="Invert ramp for light backgrounds")
    p.add_argument("--load-project", help="Load an .asciivideo project instead of a video")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.load_project:
            source, settings, _info = _load_project(args.load_project)
            # CLI overrides apply on top of project settings.
            settings.cols = args.cols
            settings.color_mode = args.color
            settings.ramp = args.ramp
            settings.char_aspect = args.char_aspect
            settings.invert = args.invert
            settings.fps = args.fps
            av = AsciiVideo(source, settings)
        else:
            av = AsciiVideo(
                args.input,
                AppSettings(
                    cols=args.cols,
                    ramp=args.ramp,
                    color_mode=args.color,
                    char_aspect=args.char_aspect,
                    invert=args.invert,
                    fps=args.fps,
                ),
            )

        if args.output is None:
            # Live terminal playback.
            player = LivePlayer(
                av.path,
                av.settings,
                audio=not args.no_audio,
                override_fps=args.fps,
            )
            try:
                player.run()
            except KeyboardInterrupt:
                pass
            return 0

        fmt = _detect_format(args.output, args.format)
        frames = av.video_to_frames()

        if fmt == "video":
            av.to_video(args.output, frames=frames, fps=args.fps, no_audio=args.no_audio)
        elif fmt == "text":
            av.to_text(args.output, frames=frames)
        elif fmt == "html":
            av.to_html(args.output, frames=frames)
        elif fmt == "png":
            av.to_png_frames(args.output, frames=frames)
        else:  # pragma: no cover
            raise OutputPathError(f"Unknown format {fmt}")
        return 0

    except AsciiVideoError as exc:
        logger.error(str(exc))
        return 1
    except Exception as exc:  # pragma: no cover - safety net
        logger.error("Unexpected error: %s", exc)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
