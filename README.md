# asciivid

Convert video into coloured ASCII art, with live terminal playback and file
export. Each character's brightness matches local pixel luma (Rec.709) and its
colour matches the original video, with run-length merged ANSI colour escapes.

## Install

```bash
pip install -r requirements.txt
```

`opencv-python`, `numpy`, and `pillow` are pip-installed. **ffmpeg is an
external dependency** — install it separately from https://ffmpeg.org. On
Windows, asciivid auto-detects ffmpeg on `PATH` or at
`C:\ffmpeg\bin\ffmpeg.exe` / `C:\Program Files\ffmpeg\bin\ffmpeg.exe`.
`ffplay` (alongside ffmpeg) enables synced audio during live playback.

## CLI

```bash
# Live coloured playback in the terminal (Ctrl+C to stop)
python -m asciivid sample.mp4

# Export to MP4 with the original audio muxed back in
python -m asciivid sample.mp4 -o out.mp4 --cols 120 --color truecolor

# Export to text / HTML / PNG frames (format auto-detected from -o)
python -m asciivid sample.mp4 -o out.txt --color none
python -m asciivid sample.mp4 -o out.html
python -m asciivid sample.mp4 -o ./frames/        # directory -> PNG frames

# Options: --cols N --color {none,ansi16,ansi256,truecolor} --ramp STR
#          --no-audio --fps N --format {text,video,html,png}
```

## Library

```python
from asciivid import AsciiVideo, AppSettings, load_video, load_project

av = AsciiVideo("sample.mp4", AppSettings(cols=120, color_mode="truecolor"))
for i, frame in av.video_to_frames():      # streaming, one frame in RAM
    print(av.render_frame(frame))

av.to_video("out.mp4")                      # original audio muxed via ffmpeg
av.to_text("out.txt")
av.to_png_frames("frames/")
av.to_html("out.html")
av.save_project("proj.asciivideo")

source, settings, info = AsciiVideo.load_project("proj.asciivideo")
av2 = AsciiVideo.from_project("proj.asciivideo")
```

## GUI (optional Tkinter)

```bash
python -m asciivid.gui
```

## Tests

```bash
pip install pytest
python -m pytest
```

## Project format

`.asciivideo` is a JSON manifest storing the source path, `AppSettings`, and
video metadata so a conversion can be reopened, edited, and re-exported. This project is inspired by my GF Juliette Ngon Pham <3
