# FFmpeg Swiss Army Knife

A comprehensive desktop GUI for FFmpeg — built with Python and Tkinter. No command-line knowledge required. Covers video conversion, audio extraction, GIF creation, batch processing, file stitching, and more, all from a single window.

---

## Screenshots

> _Add screenshots here once the app is running._

---

## Features

### Video Tools
- Convert video files to any common format (MP4, MKV, MOV, AVI, WebM, TS, MXF, and more)
- Wide codec support: H.264, H.265, AV1 (SVT-AV1, libaom), VP9, VP8, ProRes, MPEG-4
- Hardware-accelerated encoding: NVENC (Nvidia), AMF (AMD), QSV (Intel) — including H.264, H.265, and AV1 variants
- CRF (constant quality), target bitrate, and 2-pass encoding modes
- Output FPS override
- Speed control (0.25x to 4x) with audio kept in sync automatically
- Trim by start/end timestamp
- Scale with aspect-ratio preservation (`-1` shorthand supported)
- Crop (`w:h:x:y` syntax)
- Deinterlace: YADIF, YADIF double-rate, BWDIF, BWDIF double-rate
- Rotate and flip: 90 CW, 90 CCW, 180, horizontal flip, vertical flip
- HDR to SDR tone mapping (Hable via zscale)
- Burn-in subtitle support (SRT, ASS, SSA, VTT)
- Soft subtitle copy pass-through
- Strip all metadata
- Audio codec selection per output (AAC, MP3, AC3, EAC3, Opus, Vorbis, FLAC, PCM, copy, or strip)
- Audio bitrate control

### Audio Tools
- Extract or convert audio from any video or audio file
- Output formats: MP3, WAV, FLAC, M4A, OGG, AAC, Opus
- Codec selection: libmp3lame, AAC, FLAC, Opus, Vorbis, PCM, copy
- Bitrate control
- Sample rate conversion (8 kHz to 96 kHz)
- Channel layout conversion (mono, stereo, 5.1)
- Volume adjustment (multiplier or dB)
- Loudness normalization via `dynaudnorm`
- Trim by start/end timestamp
- Process multiple files in a single queue

### GIF Creator
- Two-pass palette generation for maximum color accuracy
- Custom width (height scales automatically)
- FPS control
- Loop count (0 = infinite)
- Trim start/end
- Dither mode selection: `sierra2_4a`, `floyd_steinberg`, `bayer`, `none`
- Lanczos scaling for clean downsampling

### Batch Processing
- Separate video and audio batch modes
- Input folder with optional subfolder recursion
- Input extension filter (process only `.mp4`, only `.wav`, etc.)
- Output extension and folder independently configurable
- Fully custom FFmpeg argument string
- Quick-add buttons for common filters: deinterlace, scale to 1080p, scale to 720p, normalize audio
- Preserves relative subfolder structure in output

### Stitch / Join
- Concatenate any number of video files in a defined order
- Stream copy mode (lossless, instant — requires matching codec/resolution/fps)
- Re-encode mode for joining files with different codecs or resolutions
- Drag-order control with Move Up / Move Down buttons
- Browse for output file location

### Media Info
- Full `ffprobe` inspection of any media file
- Color-coded display: format block, per-stream details, embedded tags
- Shows codec, resolution, frame rate, bitrate, duration, sample rate, channel layout, and more

### Custom CLI
- Direct FFmpeg command builder for anything not covered by the other tabs
- Input file, output file, and argument field
- Live command preview updates as you type

---

## Requirements

| Requirement | Notes |
|---|---|
| Python 3.8+ | Tkinter is included in standard Python installs |
| FFmpeg | Must be available in your system `PATH` |
| ffprobe | Included with FFmpeg; required for the Media Info tab |

The app will display an error and exit on launch if FFmpeg is not found. The Media Info tab will be disabled independently if only `ffprobe` is missing.

---

## Installation

**1. Install FFmpeg**

- **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) or via [winget](https://winget.run/):
  ```
  winget install ffmpeg
  ```
- **macOS:**
  ```
  brew install ffmpeg
  ```
- **Linux (Debian/Ubuntu):**
  ```
  sudo apt install ffmpeg
  ```

**2. Clone this repository**

```bash
git clone https://github.com/NullAngst/FFmpeg-Swiss-Army-Knife.git
cd FFmpeg-Swiss-Army-Knife
```

**3. Run the app**

```bash
python ffmpeg_swiss_army_knife.py
```

No additional Python packages are required. Everything used (`tkinter`, `subprocess`, `threading`, `json`, `tempfile`, `shutil`) is part of the Python standard library.

---

## Usage Notes

### Output Folder
The global output folder at the top of the window is shared across all tabs. Leave it blank to save each output file next to its source. Set it once and every tab respects it.

### CRF vs Bitrate
- Leave **Bitrate** blank to use CRF (constant quality). This is the recommended mode for most use cases.
- Fill in **Bitrate** (e.g. `5M`) to target a specific file size. Required for 2-pass encoding.
- Typical CRF ranges: H.264 `18-28`, H.265 `24-32`, AV1 `28-45`. Lower = better quality, larger file.

### Hardware Encoding (NVENC / AMF / QSV)
Hardware codecs use `p1`-`p7` presets rather than the standard `ultrafast`/`slow` names. The preset dropdown swaps automatically when you select a hardware codec. `p4` is a balanced starting point. These are significantly faster than CPU encoding but may produce slightly larger files at equivalent visual quality.

### 2-Pass Encoding
Both passes must complete successfully to produce output. Pass log files are written to your system temp directory and cleaned up automatically. A bitrate value is required — if you leave it blank, the app defaults to `5M`.

### Speed Control
Speed adjustments affect both video and audio. Audio pitch is preserved using `atempo` filters. Speeds beyond the `0.5x`-`2x` range that a single `atempo` filter supports are handled automatically by chaining multiple filters.

### Stitch / Join — Stream Copy vs Re-encode
Stream copy is instant and lossless but requires every file to share the same codec, resolution, and frame rate. If your files differ in any of these, enable **Force Re-encode**.

### Presets
Save and load all current settings (video and audio tab) to a `.json` file via the toolbar buttons. Presets do not include file lists.

---

## Keyboard Shortcuts

| Action | Shortcut |
|---|---|
| Currently none defined | — |

> Keyboard shortcuts are planned for a future release.

---

## Roadmap

- [ ] Drag-and-drop file adding
- [ ] Progress bar with percentage and ETA (requires ffprobe duration pre-check)
- [ ] Per-file output naming templates (e.g. `{name}_converted{ext}`)
- [ ] Thumbnail extraction tab
- [ ] Stream selection UI (pick specific audio/subtitle tracks from multi-track files)
- [ ] Dark mode toggle
- [ ] Keyboard shortcuts

---

## Contributing

Pull requests are welcome. For significant changes, open an issue first to discuss what you want to change.

Please test against at least Windows and Linux before submitting.

---

## License

[MIT](LICENSE)

---

## Acknowledgments

Built on top of [FFmpeg](https://ffmpeg.org/) — the backbone of basically every video tool that exists.
