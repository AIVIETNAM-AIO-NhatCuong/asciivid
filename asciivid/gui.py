"""Optional Tkinter GUI for asciivid.

Provides "Open video", "Play"/"Stop", "Export as...", and sliders for
cols / color mode. Playback and export run in background threads so the
window stays responsive.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional

from .cli import build_parser  # noqa: F401  (kept for potential reuse)
from .core import AsciiVideo
from .errors import AsciiVideoError
from .settings import AppSettings, COLOR_MODES
from .terminal import LivePlayer
from .utils import setup_logging, logger


class AsciiVidGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("asciivid — ASCII Video Converter")
        root.geometry("640x420")

        self.av: Optional[AsciiVideo] = None
        self._player_thread: Optional[threading.Thread] = None
        self._player_stop = False

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 6}

        # File row.
        file_frame = tk.Frame(self.root)
        file_frame.pack(fill=tk.X, **pad)
        tk.Label(file_frame, text="Video:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value="(none)")
        tk.Label(file_frame, textvariable=self.path_var, anchor=tk.W, width=52).pack(side=tk.LEFT, padx=6)
        tk.Button(file_frame, text="Open video", command=self.open_video).pack(side=tk.LEFT)

        # Controls row.
        ctrl = tk.Frame(self.root)
        ctrl.pack(fill=tk.X, **pad)
        self.play_btn = tk.Button(ctrl, text="Play", command=self.toggle_play, width=10)
        self.play_btn.pack(side=tk.LEFT, padx=4)
        self.stop_btn = tk.Button(ctrl, text="Stop", command=self.stop_play, width=10, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="Export as...", command=self.export_as, width=14).pack(side=tk.LEFT, padx=4)

        # Sliders row.
        slider_frame = tk.Frame(self.root)
        slider_frame.pack(fill=tk.X, **pad)

        tk.Label(slider_frame, text="Cols:").pack(side=tk.LEFT)
        self.cols_var = tk.IntVar(value=120)
        cols_scale = tk.Scale(
            slider_frame, from_=20, to=240, orient=tk.HORIZONTAL,
            variable=self.cols_var, length=220,
        )
        cols_scale.pack(side=tk.LEFT, padx=6)

        tk.Label(slider_frame, text="Color mode:").pack(side=tk.LEFT, padx=(16, 0))
        self.color_var = tk.IntVar(value=3)  # index into COLOR_MODES
        color_scale = tk.Scale(
            slider_frame, from_=0, to=len(COLOR_MODES) - 1, orient=tk.HORIZONTAL,
            variable=self.color_var, length=180,
            command=self._on_color_change,
        )
        color_scale.pack(side=tk.LEFT, padx=6)
        self.color_label = tk.Label(slider_frame, text=COLOR_MODES[3])
        self.color_label.pack(side=tk.LEFT)

        # Author line in the blank middle area.
        self.author_var = tk.StringVar(value="ASCII video will run in terminal")
        author_frame = tk.Frame(self.root)
        author_frame.pack(fill=tk.X, padx=8, pady=(10, 2))
        tk.Label(author_frame, textvariable=self.author_var, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(author_frame, text="Nhat Cuong Luong", anchor=tk.E).pack(side=tk.RIGHT, fill=tk.X)

        # Status / log.
        self.status_var = tk.StringVar(value="Open a video to begin")
        tk.Label(self.root, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN).pack(
            fill=tk.X, padx=8, pady=(4, 8)
        )

    def _on_color_change(self, _value) -> None:
        self.color_label.config(text=COLOR_MODES[self.color_var.get()])

    def _status(self, text: str) -> None:
        self.status_var.set(text)
        self.root.update_idletasks()
        logger.info("GUI: %s", text)

    def open_video(self) -> None:
        path = filedialog.askopenfilename(
            title="Open video",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.webm"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        settings = AppSettings(
            cols=self.cols_var.get(),
            color_mode=COLOR_MODES[self.color_var.get()],
        )
        try:
            self.av = AsciiVideo(path, settings)
            self.path_var.set(path)
            self._status(f"Loaded: {self.av.info}")
        except AsciiVideoError as exc:
            messagebox.showerror("Cannot open video", str(exc))

    def toggle_play(self) -> None:
        if self.av is None:
            messagebox.showwarning("No video", "Open a video first.")
            return
        if self._player_thread is not None and self._player_thread.is_alive():
            return  # already playing
        self._player_stop = False
        self.author_var.set("ASCII video is running in terminal")
        self.play_btn.config(text="Pause", state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._player_thread = threading.Thread(target=self._run_play, daemon=True)
        self._player_thread.start()

    def _run_play(self) -> None:
        settings = AppSettings(
            cols=self.cols_var.get(),
            color_mode=COLOR_MODES[self.color_var.get()],
        )
        player = LivePlayer(self.av.path, settings, audio=False)
        try:
            player.run()
        except Exception as exc:  # noqa: BLE001 - surface to user
            err_msg = str(exc)
            self.root.after(0, lambda msg=err_msg: messagebox.showerror("Playback error", msg))
        finally:
            self._player_stop = True
            self.root.after(0, self._reset_play_buttons)

    def stop_play(self) -> None:
        self._player_stop = True

    def _reset_play_buttons(self) -> None:
        self.author_var.set("ASCII video will run in terminal")
        self.play_btn.config(text="Play", state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def export_as(self) -> None:
        if self.av is None:
            messagebox.showwarning("No video", "Open a video first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export as",
            defaultextension=".mp4",
            filetypes=[
                ("MP4 video", "*.mp4"),
                ("Text/ANSI", "*.txt *.ans"),
                ("HTML", "*.html"),
                ("PNG frames directory", "*.*"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        def work() -> None:
            try:
                settings = AppSettings(
                    cols=self.cols_var.get(),
                    color_mode=COLOR_MODES[self.color_var.get()],
                )
                av = AsciiVideo(self.av.path, settings)
                frames = av.video_to_frames()
                import os
                if os.path.isdir(path) or path == "":
                    av.to_png_frames(path or ".", frames=frames)
                    self.root.after(0, lambda: self._status(f"PNG frames exported to {path}"))
                elif path.lower().endswith((".mp4", ".mkv")):
                    av.to_video(path, frames=frames, no_audio=False)
                    self.root.after(0, lambda: self._status(f"Video exported to {path}"))
                elif path.lower().endswith((".txt", ".ans")):
                    av.to_text(path, frames=frames)
                    self.root.after(0, lambda: self._status(f"Text exported to {path}"))
                elif path.lower().endswith(".html"):
                    av.to_html(path, frames=frames)
                    self.root.after(0, lambda: self._status(f"HTML exported to {path}"))
                else:
                    av.to_video(path, frames=frames, no_audio=False)
                    self.root.after(0, lambda: self._status(f"Video exported to {path}"))
            except AsciiVideoError as exc:
                self.root.after(0, lambda: messagebox.showerror("Export error", str(exc)))

        threading.Thread(target=work, daemon=True).start()


def main() -> None:
    setup_logging()
    root = tk.Tk()
    AsciiVidGUI(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
