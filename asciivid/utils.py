"""Shared utilities: logging, ffmpeg/ffprobe detection, font discovery."""

from __future__ import annotations

import glob
import logging
import os
import platform
import shutil
from typing import Optional

logger = logging.getLogger("asciivid")


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the package logger."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _windows_candidates(*names: str) -> list[str]:
    """Common Windows install locations for a ffmpeg-family executable."""
    prefix = "C:\\ffmpeg\\bin\\"
    return [
        prefix + names[0],
        "C:\\Program Files\\ffmpeg\\bin\\" + names[0],
        "C:\\Program Files (x86)\\ffmpeg\\bin\\" + names[0],
        os.path.expanduser("~\\ffmpeg\\bin\\") + names[0],
    ]


def _package_manager_candidates(name: str) -> list[str]:
    """Glob common package-manager install locations (WinGet, WindowsApps)."""
    candidates: list[str] = []
    local = os.environ.get("LOCALAPPDATA", "")
    # WinGet unpacked package locations, e.g.
    # %LOCALAPPDATA%\Microsoft\WinGet\Packages\*\*\bin\ffmpeg.exe
    if local:
        candidates.extend(
            glob.glob(os.path.join(local, r"Microsoft\WinGet\Packages\*\*\bin", name))
        )
        candidates.extend(
            glob.glob(os.path.join(local, r"Microsoft\WinGet\Packages\*", name))
        )
    # WindowsApps command-line aliases / stubs
    candidates.append(
        os.path.join(local, r"Microsoft\WindowsApps", name) if local else name
    )
    return [c for c in candidates if os.path.isfile(c)]


def find_ffmpeg() -> Optional[str]:
    """Locate the ffmpeg executable (PATH first, then Windows defaults)."""
    for name in ("ffmpeg", "ffmpeg.exe"):
        found = shutil.which(name)
        if found:
            logger.debug("Found ffmpeg on PATH: %s", found)
            return found
    if platform.system() == "Windows":
        for c in _windows_candidates("ffmpeg.exe"):
            if os.path.isfile(c):
                logger.debug("Found ffmpeg at default Windows path: %s", c)
                return c
        for c in _package_manager_candidates("ffmpeg.exe"):
            logger.debug("Found ffmpeg at package-manager path: %s", c)
            return c
    logger.warning("ffmpeg not found; video export will be unavailable")
    return None


def find_ffplay() -> Optional[str]:
    """Locate the ffplay executable (used for synced live audio)."""
    for name in ("ffplay", "ffplay.exe"):
        found = shutil.which(name)
        if found:
            logger.debug("Found ffplay on PATH: %s", found)
            return found
    if platform.system() == "Windows":
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path:
            sibling = os.path.join(os.path.dirname(ffmpeg_path), "ffplay.exe")
            if os.path.isfile(sibling):
                return sibling
        for c in _windows_candidates("ffplay.exe") + _package_manager_candidates("ffplay.exe"):
            if os.path.isfile(c):
                return c
    logger.debug("ffplay not found; live audio will be unavailable")
    return None


def find_ffprobe() -> Optional[str]:
    """Locate the ffprobe executable."""
    for name in ("ffprobe", "ffprobe.exe"):
        found = shutil.which(name)
        if found:
            return found
    if platform.system() == "Windows":
        ffmpeg_path = find_ffmpeg()
        if ffmpeg_path:
            sibling = os.path.join(os.path.dirname(ffmpeg_path), "ffprobe.exe")
            if os.path.isfile(sibling):
                return sibling
        for c in _windows_candidates("ffprobe.exe") + _package_manager_candidates("ffprobe.exe"):
            if os.path.isfile(c):
                return c
    return None


def find_monospace_font() -> Optional[str]:
    """Find a monospace TrueType font for Pillow frame rendering."""
    system = platform.system()
    if system == "Windows":
        candidates = [
            r"C:\Windows\Fonts\consola.ttf",
            r"C:\Windows\Fonts\consolab.ttf",
            r"C:\Windows\Fonts\cour.ttf",
            r"C:\Windows\Fonts\courbd.ttf",
            r"C:\Windows\Fonts\lucon.ttf",
        ]
    elif system == "Darwin":
        candidates = [
            "/Library/Fonts/Courier New.ttf",
            "/System/Library/Fonts/Courier.ttf",
            "/System/Library/Fonts/Monaco.ttf",
        ]
    else:  # Linux and others
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
        ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    logger.warning("No monospace font found; PNG export will use the default font")
    return None
