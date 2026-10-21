"""Vectorized ASCII rendering pipeline.

Converts BGR frames into coloured ANSI/ASCII strings using numpy for all
heavy lifting (downscaling, luma, colour quantisation). String assembly is
O(cells) per frame rather than O(pixels).
"""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from .settings import AppSettings

# Rec.709 luma coefficients (R, G, B).
LUMA_COEFFS = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

# ANSI 16 palette: normal (0-7) then bright (8-15).
ANSI16_RGB = np.array(
    [
        [0, 0, 0],
        [128, 0, 0],
        [0, 128, 0],
        [128, 128, 0],
        [0, 0, 128],
        [128, 0, 128],
        [0, 128, 128],
        [192, 192, 192],
        [128, 128, 128],
        [255, 0, 0],
        [0, 255, 0],
        [255, 255, 0],
        [0, 0, 255],
        [255, 0, 255],
        [0, 255, 255],
        [255, 255, 255],
    ],
    dtype=np.float32,
)


def _build_ansi256_palette() -> np.ndarray:
    colours: list[list[int]] = []
    colours.extend(ANSI16_RGB.tolist())  # 0-15
    levels = [0, 95, 135, 175, 215, 255]
    for r in levels:  # 16-231, 6x6x6 colour cube
        for g in levels:
            for b in levels:
                colours.append([r, g, b])
    for i in range(24):  # 232-255, grayscale ramp
        v = 8 + 10 * i
        colours.append([v, v, v])
    return np.array(colours, dtype=np.float32)


_ANSI256_PALETTE = _build_ansi256_palette()


def quantize_colors(rgb: np.ndarray, mode: str) -> np.ndarray:
    """Quantize an (H, W, 3) float RGB array to palette indices.

    Returns an (H, W) int32 array of palette indices for ``ansi16`` /
    ``ansi256``, or the RGB array itself for ``truecolor``.
    """
    if mode == "truecolor":
        return rgb
    palette = ANSI16_RGB if mode == "ansi16" else _ANSI256_PALETTE
    diff = rgb[:, :, None, :] - palette[None, None, :, :]
    dist = np.sum(diff * diff, axis=3)
    return np.argmin(dist, axis=2).astype(np.int32)


def _grid_dimensions(frame_h: int, frame_w: int, cols: int, char_aspect: float) -> tuple[int, int]:
    cols = max(1, cols)
    rows = max(1, int(round(cols * (frame_h / frame_w) * char_aspect)))
    return rows, cols


def render_frame(
    frame: np.ndarray,
    settings: AppSettings,
    *,
    cols: Optional[int] = None,
) -> str:
    """Render a single BGR frame to a coloured ANSI/ASCII string.

    The returned string contains ANSI escape sequences (unless color_mode is
    ``none``) and ends with a reset sequence. The caller is responsible for
    cursor positioning between frames. No per-pixel Python loops are used.
    """
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("frame must be HxWx3 BGR")

    h, w = frame.shape[:2]
    c = settings.cols if cols is None else cols
    c = max(1, c)
    rows, c = _grid_dimensions(h, w, c, settings.char_aspect)

    # Downscale to the cell grid. INTER_AREA averages each source cell block,
    # giving us per-cell mean RGB in one vectorized C call.
    small = cv2.resize(frame, (c, rows), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB).astype(np.float32)  # (rows, c, 3)

    # Per-cell Rec.709 luma.
    luma = rgb @ LUMA_COEFFS  # (rows, c)

    # Map luma -> ramp index (darkest -> brightest).
    ramp = settings.ramp[::-1] if settings.invert else settings.ramp
    n_chars = len(ramp)
    idx = np.round((luma / 255.0) * (n_chars - 1)).astype(np.int32)
    idx = np.clip(idx, 0, n_chars - 1)

    color_mode = settings.color_mode
    if color_mode == "none":
        lines = ["".join(ramp[idx[r, cc]] for cc in range(c)) for r in range(rows)]
        return "\n".join(lines)

    palette_indices = quantize_colors(rgb, color_mode)

    ESC = "\x1b"
    lines: list[str] = []
    if color_mode == "truecolor":
        for r in range(rows):
            parts: list[str] = []
            cc = 0
            while cc < c:
                base = rgb[r, cc]
                rr, gg, bb = (int(v) for v in base)
                end = cc
                while end + 1 < c and np.array_equal(base, rgb[r, end + 1]):
                    end += 1
                run_chars = "".join(ramp[idx[r, k]] for k in range(cc, end + 1))
                parts.append(f"{ESC}[38;2;{rr};{gg};{bb}m{run_chars}")
                cc = end + 1
            lines.append("".join(parts))
    else:  # ansi16 or ansi256 -> ESC[38;5;Nm
        for r in range(rows):
            parts: list[str] = []
            cc = 0
            while cc < c:
                color_idx = int(palette_indices[r, cc])
                end = cc
                while end + 1 < c and int(palette_indices[r, end + 1]) == color_idx:
                    end += 1
                run_chars = "".join(ramp[idx[r, k]] for k in range(cc, end + 1))
                parts.append(f"{ESC}[38;5;{color_idx}m{run_chars}")
                cc = end + 1
            lines.append("".join(parts))

    out = "\n".join(lines)
    out += f"{ESC}[0m"
    return out


def render_frame_to_png(
    frame: np.ndarray,
    settings: AppSettings,
    font,
    char_w: int,
    char_h: int,
) -> "Image.Image":
    """Render a single BGR frame to a Pillow RGB image with per-run colour.

    Heavy lifting is vectorized; only the final text drawing (O(cells)) uses
    Pillow.
    """
    from PIL import Image, ImageDraw

    h, w = frame.shape[:2]
    c = settings.cols
    rows, c = _grid_dimensions(h, w, c, settings.char_aspect)

    small = cv2.resize(frame, (c, rows), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB).astype(np.float32)
    luma = rgb @ LUMA_COEFFS
    ramp = settings.ramp[::-1] if settings.invert else settings.ramp
    n_chars = len(ramp)
    idx = np.round((luma / 255.0) * (n_chars - 1)).astype(np.int32)
    idx = np.clip(idx, 0, n_chars - 1)

    color_mode = settings.color_mode
    palette_indices = quantize_colors(rgb, color_mode)

    img_w = c * char_w
    img_h = rows * char_h
    img = Image.new("RGB", (img_w, img_h), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    for r in range(rows):
        y = r * char_h
        x = 0
        cc = 0
        while cc < c:
            base = rgb[r, cc]
            end = cc
            while end + 1 < c and np.array_equal(base, rgb[r, end + 1]):
                end += 1
            run_chars = "".join(ramp[idx[r, k]] for k in range(cc, end + 1))
            if color_mode == "truecolor":
                fill = (int(base[0]), int(base[1]), int(base[2]))
            elif color_mode == "ansi256":
                fill = tuple(int(v) for v in _ANSI256_PALETTE[int(palette_indices[r, cc])])
            else:  # ansi16
                fill = tuple(int(v) for v in ANSI16_RGB[int(palette_indices[r, cc])])
            draw.text((x, y), run_chars, font=font, fill=fill)
            x += len(run_chars) * char_w
            cc = end + 1

    return img
