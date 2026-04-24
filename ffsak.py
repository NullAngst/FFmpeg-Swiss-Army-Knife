"""
FFmpeg Swiss Army Knife - Enhanced v3.0
Comprehensive GUI wrapper for FFmpeg with expanded codec support,
Media Info (ffprobe), live progress display, and numerous UX improvements.
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import shutil
import os
import sys
import json
import tempfile

# ── Constants ─────────────────────────────────────────────────────────────────

APP_VERSION = "3.0"

VIDEO_CODECS = [
    ("H.264  (libx264 - CPU)",    "libx264"),
    ("H.265  (libx265 - CPU)",    "libx265"),
    ("AV1    (libsvtav1 - CPU)",  "libsvtav1"),
    ("AV1    (libaom - CPU)",     "libaom-av1"),
    ("H.264  NVENC (Nvidia)",     "h264_nvenc"),
    ("H.265  NVENC (Nvidia)",     "hevc_nvenc"),
    ("AV1    NVENC (RTX 30+)",   "av1_nvenc"),
    ("H.264  AMF   (AMD)",        "h264_amf"),
    ("H.265  AMF   (AMD)",        "hevc_amf"),
    ("H.264  QSV   (Intel)",      "h264_qsv"),
    ("H.265  QSV   (Intel)",      "hevc_qsv"),
    ("ProRes (prores_ks)",        "prores_ks"),
    ("VP9    (libvpx-vp9)",      "libvpx-vp9"),
    ("VP8    (libvpx)",           "libvpx"),
    ("MPEG-4 (mpeg4)",            "mpeg4"),
    ("Copy   (No Re-encode)",     "copy"),
]

AUDIO_CODECS = [
    ("AAC  (Standard)",           "aac"),
    ("MP3  (libmp3lame)",         "libmp3lame"),
    ("AC3  (Dolby Digital)",      "ac3"),
    ("EAC3 (Dolby Digital+)",    "eac3"),
    ("PCM  16-bit WAV",           "pcm_s16le"),
    ("Opus (libopus)",            "libopus"),
    ("Vorbis (libvorbis)",        "libvorbis"),
    ("FLAC (Lossless)",           "flac"),
    ("Copy (No Re-encode)",       "copy"),
    ("No Audio",                  "none"),
]

CONTAINERS_VIDEO = [".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts", ".m2ts", ".mxf"]
CONTAINERS_AUDIO = [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".opus"]

PRESETS_STANDARD = [
    "ultrafast", "superfast", "veryfast", "faster",
    "fast", "medium", "slow", "slower", "veryslow",
]
PRESETS_NVENC = [
    "p1 (Fastest)", "p2", "p3", "p4 (Balanced)", "p5", "p6", "p7 (Best Quality)",
]

# Stored as (display name, filter string) tuples
DEINTERLACE_MODES = [
    ("Off",                      ""),
    ("YADIF",                    "yadif"),
    ("YADIF 2x (Double Rate)",   "yadif=mode=1"),
    ("BWDIF",                    "bwdif"),
    ("BWDIF 2x (Double Rate)",   "bwdif=mode=1"),
]

ROTATE_OPTIONS = [
    ("No Rotation",              ""),
    ("90 CW",                    "transpose=1"),
    ("180",                      "transpose=2,transpose=2"),
    ("90 CCW",                   "transpose=2"),
    ("Flip Horizontal",          "hflip"),
    ("Flip Vertical",            "vflip"),
]

# Speed display name -> multiplier
SPEED_MAP = {
    "0.25x (Quarter)": 0.25,
    "0.5x  (Half)":    0.5,
    "0.75x":           0.75,
    "1x    (Normal)":  1.0,
    "1.25x":           1.25,
    "1.5x":            1.5,
    "2x    (Double)":  2.0,
    "4x":              4.0,
}

# Channel display name -> ffmpeg -ac value
CHANNELS_MAP = {
    "Original":            None,
    "Mono   (1 ch)":       "1",
    "Stereo (2 ch)":       "2",
    "5.1 Surround (6 ch)": "6",
}

SAMPLE_RATES = ["Original", "8000", "22050", "44100", "48000", "96000"]

GIF_DITHER_MODES = [
    "sierra2_4a",
    "floyd_steinberg",
    "bayer:bayer_scale=2",
    "bayer:bayer_scale=3",
    "none",
]

BATCH_DEFAULTS = {
    ".mp4":  "-c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k",
    ".mkv":  "-c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k",
    ".mov":  "-c:v prores_ks -profile:v 3 -c:a pcm_s16le",
    ".avi":  "-c:v mpeg4 -q:v 5 -c:a libmp3lame -q:a 2",
    ".webm": "-c:v libvpx-vp9 -crf 30 -b:v 0 -c:a libopus",
    ".ts":   "-c:v libx264 -c:a aac",
    ".m2ts": "-c:v libx264 -c:a aac",
    ".mxf":  "-c:v libx264 -c:a pcm_s16le",
    ".mp3":  "-vn -c:a libmp3lame -q:a 2",
    ".wav":  "-vn -c:a pcm_s16le",
    ".flac": "-vn -c:a flac",
    ".m4a":  "-vn -c:a aac -b:a 192k",
    ".ogg":  "-vn -c:a libvorbis -q:a 4",
    ".aac":  "-vn -c:a aac -b:a 192k",
    ".opus": "-vn -c:a libopus -b:a 128k",
}

# ── Tooltip helper ────────────────────────────────────────────────────────────

class ToolTip:
    """Small hover tooltip attached to any widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _=None):
        if self.tip:
            return
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        except Exception:
            return
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#ffffe0", relief=tk.SOLID, borderwidth=1,
            font=("Segoe UI", 8), wraplength=320,
        ).pack()

    def _hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ── Main application ──────────────────────────────────────────────────────────

class FFmpegGUI:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"FFmpeg Swiss Army Knife  v{APP_VERSION}")
        self.root.geometry("1160x920")
        self.root.minsize(950, 720)

        if not shutil.which("ffmpeg"):
            messagebox.showerror(
                "FFmpeg Not Found",
                "FFmpeg was not found in your system PATH.\n\n"
                "Install FFmpeg and make sure it is accessible from your terminal, then restart.",
            )
            self.root.destroy()
            return

        self.ffprobe_ok = bool(shutil.which("ffprobe"))

        # Runtime state
        self.is_running      = False
        self.current_process = None
        self.stop_requested  = False

        # ── Global vars ──────────────────────────────────────────────────────
        self.output_dir   = tk.StringVar()
        self.open_on_done = tk.BooleanVar(value=False)

        # ── Video tab vars ───────────────────────────────────────────────────
        self.var_v_codec      = tk.StringVar(value="libx264")
        self.var_v_container  = tk.StringVar(value=".mp4")
        self.var_v_crf        = tk.StringVar(value="23")
        self.var_v_preset     = tk.StringVar(value="medium")
        self.var_v_bitrate    = tk.StringVar()
        self.var_v_twopass    = tk.BooleanVar(value=False)
        self.var_v_fps        = tk.StringVar()
        self.var_v_speed      = tk.StringVar(value="1x    (Normal)")

        self.var_v_acodec     = tk.StringVar(value="aac")
        self.var_v_abitrate   = tk.StringVar(value="128k")

        self.var_v_trim_start = tk.StringVar()
        self.var_v_trim_end   = tk.StringVar()
        self.var_v_scale_w    = tk.StringVar()
        self.var_v_scale_h    = tk.StringVar()
        self.var_v_crop       = tk.StringVar()
        self.var_v_rotate     = tk.StringVar(value="No Rotation")
        self.var_v_deinterlace= tk.StringVar(value="Off")
        self.var_v_hdr_sdr    = tk.BooleanVar(value=False)
        self.var_v_burn_sub   = tk.StringVar()
        self.var_v_copy_sub   = tk.BooleanVar(value=False)
        self.var_v_strip_meta = tk.BooleanVar(value=False)

        # ── Audio tab vars ───────────────────────────────────────────────────
        self.var_a_codec       = tk.StringVar(value="libmp3lame")
        self.var_a_container   = tk.StringVar(value=".mp3")
        self.var_a_bitrate     = tk.StringVar(value="192k")
        self.var_a_norm        = tk.BooleanVar(value=False)
        self.var_a_trim_start  = tk.StringVar()
        self.var_a_trim_end    = tk.StringVar()
        self.var_a_sample_rate = tk.StringVar(value="Original")
        self.var_a_channels    = tk.StringVar(value="Original")
        self.var_a_volume      = tk.StringVar()

        # ── GIF vars ─────────────────────────────────────────────────────────
        self.var_gif_fps   = tk.StringVar(value="15")
        self.var_gif_scale = tk.StringVar(value="480")
        self.var_gif_start = tk.StringVar()
        self.var_gif_end   = tk.StringVar()
        self.var_gif_dither= tk.StringVar(value="sierra2_4a")
        self.var_gif_loop  = tk.StringVar(value="0")

        # ── Batch vars ───────────────────────────────────────────────────────
        self.batch_v_in        = tk.StringVar()
        self.batch_v_out       = tk.StringVar()
        self.batch_v_args      = tk.StringVar(value=BATCH_DEFAULTS[".mp4"])
        self.batch_v_recursive = tk.BooleanVar(value=True)
        self.batch_v_ext_in    = tk.StringVar(value="*")

        self.batch_a_in        = tk.StringVar()
        self.batch_a_out       = tk.StringVar()
        self.batch_a_args      = tk.StringVar(value=BATCH_DEFAULTS[".mp3"])
        self.batch_a_recursive = tk.BooleanVar(value=True)
        self.batch_a_ext_in    = tk.StringVar(value="*")

        self._setup_styles()
        self._build_ui()

    # ── Styles ────────────────────────────────────────────────────────────────

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        BG = "#f0f2f5"
        s.configure("TFrame",          background=BG)
        s.configure("TLabel",          background=BG, font=("Segoe UI", 9))
        s.configure("TLabelframe",     background=BG)
        s.configure("TLabelframe.Label", background=BG, font=("Segoe UI", 9, "bold"))
        s.configure("TCheckbutton",    background=BG, font=("Segoe UI", 9))
        s.configure("TCombobox",       font=("Segoe UI", 9))
        s.configure("TButton",         padding=5, font=("Segoe UI", 9))
        s.configure("TNotebook",       background=BG)
        s.configure("TNotebook.Tab",   font=("Segoe UI", 9), padding=(10, 4))
        s.configure("Header.TLabel",   font=("Segoe UI", 11, "bold"), background=BG)
        s.configure("Sub.TLabel",      font=("Segoe UI", 8), background=BG, foreground="#555")
        s.configure("Run.TButton",     font=("Segoe UI", 10, "bold"), padding=8,
                    foreground="#1a4d1a", background="#b8e0b8")
        s.configure("Stop.TButton",    font=("Segoe UI", 9, "bold"),
                    foreground="#7a0000", background="#f5cccc")
        s.configure("Status.TLabel",   font=("Segoe UI", 8), background="#dce8f0")
        self.root.configure(bg=BG)

    # ── Top-level UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        # Toolbar
        tb = ttk.Frame(self.root, padding=(8, 5))
        tb.pack(fill=tk.X)
        ttk.Label(tb, text=f"FFmpeg Swiss Army Knife  v{APP_VERSION}",
                  font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Button(tb, text="Save Preset", command=self.save_preset).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Load Preset", command=self.load_preset).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="STOP ALL", style="Stop.TButton",
                   command=self.stop_all).pack(side=tk.RIGHT, padx=8)
        ttk.Checkbutton(tb, text="Open output folder when done",
                        variable=self.open_on_done).pack(side=tk.RIGHT, padx=8)

        # Global output folder
        gof = ttk.Frame(self.root, padding=(10, 3))
        gof.pack(fill=tk.X)
        ttk.Label(gof, text="Output Folder:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        out_entry = ttk.Entry(gof, textvariable=self.output_dir)
        out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ToolTip(out_entry, "Shared by all tabs. Leave blank to save each file next to its source.")
        ttk.Button(gof, text="Browse...", command=self._browse_output).pack(side=tk.LEFT)
        ttk.Button(gof, text="Open", command=self._open_output_folder).pack(side=tk.LEFT, padx=4)

        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        for attr, label, builder in [
            ("tab_video",  " Video Tools ",      self._build_video_tab),
            ("tab_audio",  " Audio Tools ",      self._build_audio_tab),
            ("tab_batch",  " Batch ",            self._build_batch_tab),
            ("tab_gif",    " GIF Creator ",      self._build_gif_tab),
            ("tab_stitch", " Stitch / Join ",    self._build_stitch_tab),
            ("tab_info",   " Media Info ",       self._build_info_tab),
            ("tab_custom", " Custom CLI ",       self._build_custom_tab),
        ]:
            f = ttk.Frame(self.notebook)
            setattr(self, attr, f)
            self.notebook.add(f, text=label)
            builder()

        # Log area
        log_wrap = ttk.Frame(self.root, padding=(10, 0, 10, 0))
        log_wrap.pack(fill=tk.BOTH)

        log_hdr = ttk.Frame(log_wrap)
        log_hdr.pack(fill=tk.X)
        ttk.Label(log_hdr, text="Process Log", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        ttk.Button(log_hdr, text="Copy", command=self._copy_log, padding=(4, 1)).pack(side=tk.RIGHT, padx=2)
        ttk.Button(log_hdr, text="Clear", command=self._clear_log, padding=(4, 1)).pack(side=tk.RIGHT, padx=2)

        self.log_text = scrolledtext.ScrolledText(
            log_wrap, height=7, state="disabled",
            font=("Consolas", 9), bg="#1e1e2e", fg="#cdd6f4",
            insertbackground="white",
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        self.log_text.tag_config("cmd",     foreground="#6c7086")
        self.log_text.tag_config("info",    foreground="#89dceb")
        self.log_text.tag_config("success", foreground="#a6e3a1")
        self.log_text.tag_config("error",   foreground="#f38ba8")
        self.log_text.tag_config("warn",    foreground="#fab387")

        # Bottom: live progress + status
        bot = ttk.Frame(self.root, padding=(10, 2, 10, 4))
        bot.pack(fill=tk.X)
        self.progress_label = ttk.Label(
            bot, text="", style="Status.TLabel",
            font=("Consolas", 8), anchor="w",
        )
        self.progress_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.status_label = ttk.Label(
            bot, text="Idle", style="Status.TLabel",
            font=("Segoe UI", 8, "bold"), foreground="#333",
            width=28, anchor="e",
        )
        self.status_label.pack(side=tk.RIGHT)

    # =========================================================================
    # TAB BUILDERS
    # =========================================================================

    # ── Video tab ─────────────────────────────────────────────────────────────

    def _build_video_tab(self):
        main = ttk.Frame(self.tab_video, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # File list
        inp = ttk.LabelFrame(main, text="Input Video Files", padding=5)
        inp.pack(fill=tk.X, pady=(0, 6))
        self.vid_list = tk.Listbox(inp, height=4, selectmode=tk.EXTENDED,
                                   font=("Segoe UI", 9), activestyle="none", bg="#fff")
        self.vid_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        _add_scrollbar(inp, self.vid_list)
        vbf = ttk.Frame(inp)
        vbf.pack(side=tk.RIGHT, fill=tk.Y, padx=4)
        ttk.Button(vbf, text="Add Files",    command=lambda: self._add_files(self.vid_list)).pack(fill=tk.X, pady=1)
        ttk.Button(vbf, text="Remove Sel.",  command=lambda: self._remove_selected(self.vid_list)).pack(fill=tk.X, pady=1)
        ttk.Button(vbf, text="Clear All",    command=lambda: self.vid_list.delete(0, tk.END)).pack(fill=tk.X, pady=1)

        # Three-column settings
        cols = ttk.Frame(main)
        cols.pack(fill=tk.BOTH, expand=True)
        col1 = ttk.LabelFrame(cols, text="Video Encoding", padding=8)
        col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        col2 = ttk.LabelFrame(cols, text="Filters & Transforms", padding=8)
        col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        col3 = ttk.LabelFrame(cols, text="Audio & Extras", padding=8)
        col3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

        g = dict(padx=4, pady=4, sticky="w")

        # Column 1 – encoding
        ttk.Label(col1, text="Video Codec:").grid(row=0, column=0, **g)
        self.v_codec_cb = ttk.Combobox(col1, values=[x[0] for x in VIDEO_CODECS],
                                        state="readonly", width=26)
        self.v_codec_cb.grid(row=0, column=1, **g)
        self.v_codec_cb.current(0)
        self.v_codec_cb.bind("<<ComboboxSelected>>", self._on_vcodec_change)

        ttk.Label(col1, text="Container:").grid(row=1, column=0, **g)
        ttk.Combobox(col1, values=CONTAINERS_VIDEO + CONTAINERS_AUDIO,
                     textvariable=self.var_v_container, width=8).grid(row=1, column=1, **g)

        ttk.Label(col1, text="CRF:").grid(row=2, column=0, **g)
        crf_e = ttk.Entry(col1, textvariable=self.var_v_crf, width=6)
        crf_e.grid(row=2, column=1, **g)
        ToolTip(crf_e,
                "Constant Rate Factor. Lower = better quality + larger file.\n"
                "H.264 typical: 18-28  |  H.265 typical: 24-32  |  0 = lossless.")

        ttk.Label(col1, text="Preset:").grid(row=3, column=0, **g)
        self.v_preset_cb = ttk.Combobox(col1, values=PRESETS_STANDARD,
                                         textvariable=self.var_v_preset, width=14)
        self.v_preset_cb.grid(row=3, column=1, **g)
        ToolTip(self.v_preset_cb,
                "Slower presets compress better but take longer.\n"
                "NVENC/AMF/QSV codecs use p1-p7 presets instead.")

        ttk.Label(col1, text="Bitrate:").grid(row=4, column=0, **g)
        br_e = ttk.Entry(col1, textvariable=self.var_v_bitrate, width=8)
        br_e.grid(row=4, column=1, **g)
        ToolTip(br_e, "e.g. 5M  (5 Mbit/s).  If set, overrides CRF.\nRequired for 2-pass encoding.")

        ttk.Checkbutton(col1, text="2-Pass Encoding", variable=self.var_v_twopass).grid(
            row=5, column=0, columnspan=2, **g)

        ttk.Label(col1, text="Output FPS:").grid(row=6, column=0, **g)
        fps_e = ttk.Entry(col1, textvariable=self.var_v_fps, width=8)
        fps_e.grid(row=6, column=1, **g)
        ToolTip(fps_e, "Force output frame rate. e.g. 24, 30, 60.\nLeave blank to keep original.")

        ttk.Label(col1, text="Speed:").grid(row=7, column=0, **g)
        ttk.Combobox(col1, values=list(SPEED_MAP.keys()), textvariable=self.var_v_speed,
                     state="readonly", width=14).grid(row=7, column=1, **g)

        # Column 2 – filters
        ttk.Label(col2, text="Trim Start:").grid(row=0, column=0, **g)
        ts = ttk.Entry(col2, textvariable=self.var_v_trim_start, width=10)
        ts.grid(row=0, column=1, **g)
        ToolTip(ts, "HH:MM:SS or seconds  (e.g. 00:01:30)")

        ttk.Label(col2, text="Trim End:").grid(row=1, column=0, **g)
        te = ttk.Entry(col2, textvariable=self.var_v_trim_end, width=10)
        te.grid(row=1, column=1, **g)
        ToolTip(te, "HH:MM:SS or seconds")

        ttk.Label(col2, text="Scale W x H:").grid(row=2, column=0, **g)
        sf = ttk.Frame(col2)
        sf.grid(row=2, column=1, **g)
        sw = ttk.Entry(sf, textvariable=self.var_v_scale_w, width=5)
        sw.pack(side=tk.LEFT)
        ToolTip(sw, "Use -1 to preserve aspect ratio.\ne.g. W=1280, H=-1 -> 1280px wide.")
        ttk.Label(sf, text="x").pack(side=tk.LEFT, padx=2)
        ttk.Entry(sf, textvariable=self.var_v_scale_h, width=5).pack(side=tk.LEFT)

        ttk.Label(col2, text="Crop (w:h:x:y):").grid(row=3, column=0, **g)
        crop_e = ttk.Entry(col2, textvariable=self.var_v_crop, width=14)
        crop_e.grid(row=3, column=1, **g)
        ToolTip(crop_e, "e.g. 1280:720:0:140  crops a 1280x720 area starting at x=0, y=140.")

        ttk.Label(col2, text="Deinterlace:").grid(row=4, column=0, **g)
        ttk.Combobox(col2, textvariable=self.var_v_deinterlace,
                     values=[x[0] for x in DEINTERLACE_MODES],
                     state="readonly", width=22).grid(row=4, column=1, **g)

        ttk.Label(col2, text="Rotate:").grid(row=5, column=0, **g)
        ttk.Combobox(col2, textvariable=self.var_v_rotate,
                     values=[x[0] for x in ROTATE_OPTIONS],
                     state="readonly", width=18).grid(row=5, column=1, **g)

        ttk.Checkbutton(col2, text="HDR -> SDR (Tone Map)",
                        variable=self.var_v_hdr_sdr).grid(row=6, column=0, columnspan=2, **g)
        ttk.Checkbutton(col2, text="Strip All Metadata",
                        variable=self.var_v_strip_meta).grid(row=7, column=0, columnspan=2, **g)

        # Column 3 – audio & extras
        ttk.Label(col3, text="Audio Codec:").grid(row=0, column=0, **g)
        self.v_acodec_cb = ttk.Combobox(col3, values=[x[0] for x in AUDIO_CODECS],
                                         state="readonly", width=22)
        self.v_acodec_cb.grid(row=0, column=1, **g)
        self.v_acodec_cb.current(0)
        self.v_acodec_cb.bind("<<ComboboxSelected>>", lambda _e: self.var_v_acodec.set(
            self._codec_code(self.v_acodec_cb.get(), AUDIO_CODECS)))

        ttk.Label(col3, text="Audio Bitrate:").grid(row=1, column=0, **g)
        ttk.Entry(col3, textvariable=self.var_v_abitrate, width=8).grid(row=1, column=1, **g)

        ttk.Label(col3, text="Burn-in Subs:").grid(row=2, column=0, **g)
        sub_row = ttk.Frame(col3)
        sub_row.grid(row=2, column=1, **g)
        ttk.Entry(sub_row, textvariable=self.var_v_burn_sub, width=12).pack(side=tk.LEFT)
        ttk.Button(sub_row, text="...", width=2, command=lambda: self.var_v_burn_sub.set(
            filedialog.askopenfilename(
                filetypes=[("Subtitle Files", "*.srt *.ass *.ssa *.vtt"), ("All", "*.*")]
            )
        )).pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(col3, text="Copy Soft Subtitles",
                        variable=self.var_v_copy_sub).grid(row=3, column=0, columnspan=2, **g)

        ttk.Button(col3, text="Preview Command",
                   command=self._preview_video_cmd).grid(row=8, column=0, columnspan=2, pady=(14, 0))

        ttk.Button(main, text="RUN VIDEO TASKS", style="Run.TButton",
                   command=self.run_video_tasks).pack(fill=tk.X, pady=(10, 0))

    def _on_vcodec_change(self, _=None):
        code = self._codec_code(self.v_codec_cb.get(), VIDEO_CODECS)
        self.var_v_codec.set(code)
        hw = any(x in code for x in ("nvenc", "amf", "qsv"))
        if hw:
            self.v_preset_cb.config(values=PRESETS_NVENC)
            self.var_v_preset.set("p4 (Balanced)")
        else:
            self.v_preset_cb.config(values=PRESETS_STANDARD)
            self.var_v_preset.set("medium")

    # ── Audio tab ─────────────────────────────────────────────────────────────

    def _build_audio_tab(self):
        main = ttk.Frame(self.tab_audio, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        inp = ttk.LabelFrame(main, text="Input Files (Video or Audio)", padding=5)
        inp.pack(fill=tk.X, pady=(0, 6))
        self.aud_list = tk.Listbox(inp, height=4, selectmode=tk.EXTENDED,
                                   font=("Segoe UI", 9), activestyle="none", bg="#fff")
        self.aud_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        _add_scrollbar(inp, self.aud_list)
        abf = ttk.Frame(inp)
        abf.pack(side=tk.RIGHT, fill=tk.Y, padx=4)
        ttk.Button(abf, text="Add Files",   command=lambda: self._add_files(self.aud_list)).pack(fill=tk.X, pady=1)
        ttk.Button(abf, text="Remove Sel.", command=lambda: self._remove_selected(self.aud_list)).pack(fill=tk.X, pady=1)
        ttk.Button(abf, text="Clear All",   command=lambda: self.aud_list.delete(0, tk.END)).pack(fill=tk.X, pady=1)

        sf = ttk.LabelFrame(main, text="Audio Conversion Settings", padding=12)
        sf.pack(fill=tk.X, pady=6)

        g = dict(padx=8, pady=6, sticky="w")

        ttk.Label(sf, text="Output Format:").grid(row=0, column=0, **g)
        ttk.Combobox(sf, values=CONTAINERS_AUDIO, textvariable=self.var_a_container,
                     width=8).grid(row=0, column=1, **g)

        ttk.Label(sf, text="Codec:").grid(row=0, column=2, **g)
        self.a_codec_cb = ttk.Combobox(
            sf, values=[x[0] for x in AUDIO_CODECS if x[1] != "none"],
            state="readonly", width=24)
        self.a_codec_cb.grid(row=0, column=3, **g)
        self.a_codec_cb.current(1)
        self.a_codec_cb.bind("<<ComboboxSelected>>", lambda _e: self.var_a_codec.set(
            self._codec_code(self.a_codec_cb.get(), AUDIO_CODECS)))

        ttk.Label(sf, text="Bitrate:").grid(row=1, column=0, **g)
        br_e = ttk.Entry(sf, textvariable=self.var_a_bitrate, width=10)
        br_e.grid(row=1, column=1, **g)
        ToolTip(br_e, "e.g. 320k, 192k, 128k")

        ttk.Label(sf, text="Sample Rate:").grid(row=1, column=2, **g)
        ttk.Combobox(sf, values=SAMPLE_RATES, textvariable=self.var_a_sample_rate,
                     width=12).grid(row=1, column=3, **g)

        ttk.Label(sf, text="Channels:").grid(row=2, column=0, **g)
        ttk.Combobox(sf, values=list(CHANNELS_MAP.keys()), textvariable=self.var_a_channels,
                     state="readonly", width=18).grid(row=2, column=1, **g)

        ttk.Label(sf, text="Volume Adjust:").grid(row=2, column=2, **g)
        vol_e = ttk.Entry(sf, textvariable=self.var_a_volume, width=10)
        vol_e.grid(row=2, column=3, **g)
        ToolTip(vol_e, "Multiplier: 1.0 = no change, 2.0 = double, 0.5 = half.\nOr use dB notation: 6dB, -3dB")

        ttk.Checkbutton(sf, text="Normalize (dynaudnorm)",
                        variable=self.var_a_norm).grid(row=3, column=0, columnspan=2, **g)

        trim_row = ttk.Frame(sf)
        trim_row.grid(row=4, column=0, columnspan=4, sticky="w", padx=8, pady=4)
        ttk.Label(trim_row, text="Trim Start:").pack(side=tk.LEFT)
        ttk.Entry(trim_row, textvariable=self.var_a_trim_start, width=10).pack(side=tk.LEFT, padx=4)
        ttk.Label(trim_row, text="Trim End:").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Entry(trim_row, textvariable=self.var_a_trim_end, width=10).pack(side=tk.LEFT, padx=4)

        ttk.Button(main, text="RUN AUDIO TASKS", style="Run.TButton",
                   command=self.run_audio_tasks).pack(fill=tk.X, pady=10)

    # ── Batch tab ─────────────────────────────────────────────────────────────

    def _build_batch_tab(self):
        nb = ttk.Notebook(self.tab_batch)
        nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for mode, label in [("video", " Video Batch "), ("audio", " Audio Batch ")]:
            f = ttk.Frame(nb)
            nb.add(f, text=label)
            self._build_batch_subtab(f, mode)

    def _build_batch_subtab(self, parent, mode):
        if mode == "video":
            in_var, out_var   = self.batch_v_in, self.batch_v_out
            args_var, rec_var = self.batch_v_args, self.batch_v_recursive
            ext_in_var        = self.batch_v_ext_in
            containers        = CONTAINERS_VIDEO
            default_ext       = ".mp4"
            run_fn            = self.run_batch_video
        else:
            in_var, out_var   = self.batch_a_in, self.batch_a_out
            args_var, rec_var = self.batch_a_args, self.batch_a_recursive
            ext_in_var        = self.batch_a_ext_in
            containers        = CONTAINERS_AUDIO
            default_ext       = ".mp3"
            run_fn            = self.run_batch_audio

        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        for lbl, var in [("Input Folder:", in_var), ("Output Folder:", out_var)]:
            ttk.Label(frame, text=lbl).pack(anchor="w")
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=(0, 6))
            ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(row, text="Browse...",
                       command=lambda v=var: v.set(filedialog.askdirectory())).pack(side=tk.RIGHT, padx=4)

        sf = ttk.LabelFrame(frame, text=f"{mode.title()} Settings", padding=10)
        sf.pack(fill=tk.X)

        r0 = ttk.Frame(sf)
        r0.pack(fill=tk.X, pady=4)
        ttk.Label(r0, text="Input ext filter:").pack(side=tk.LEFT, padx=4)
        fin_e = ttk.Entry(r0, textvariable=ext_in_var, width=8)
        fin_e.pack(side=tk.LEFT, padx=4)
        ToolTip(fin_e, "Only process files matching this extension.\ne.g. .mp4  or  *  for all files.")

        ttk.Label(r0, text="Output ext:").pack(side=tk.LEFT, padx=(10, 4))
        ext_cb = ttk.Combobox(r0, values=containers, width=8)
        ext_cb.set(default_ext)
        ext_cb.pack(side=tk.LEFT, padx=4)
        ext_cb.bind("<<ComboboxSelected>>", lambda _e: self._update_batch_defaults(ext_cb, args_var))
        ttk.Checkbutton(r0, text="Recurse subfolders", variable=rec_var).pack(side=tk.LEFT, padx=10)

        r1 = ttk.Frame(sf)
        r1.pack(fill=tk.X, pady=4)
        ttk.Label(r1, text="FFmpeg arguments:").pack(side=tk.LEFT, padx=4)
        ttk.Entry(r1, textvariable=args_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        if mode == "video":
            hlp = ttk.Frame(sf)
            hlp.pack(fill=tk.X, pady=2)
            ttk.Label(hlp, text="Quick add:").pack(side=tk.LEFT, padx=4)
            for label, arg in [
                ("Deinterlace",    "-vf yadif"),
                ("Scale 1080p",   "-vf scale=-1:1080"),
                ("Scale 720p",    "-vf scale=-1:720"),
                ("Normalize Audio","-af dynaudnorm"),
            ]:
                ttk.Button(hlp, text=f"+ {label}",
                           command=lambda a=arg: self._append_arg(args_var, a)).pack(side=tk.LEFT, padx=2)

        ttk.Button(frame, text=f"Run {mode.title()} Batch", style="Run.TButton",
                   command=lambda: run_fn(ext_cb.get())).pack(pady=16, fill=tk.X)

    # ── GIF tab ───────────────────────────────────────────────────────────────

    def _build_gif_tab(self):
        main = ttk.Frame(self.tab_gif, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="High-Quality GIF Creator", style="Header.TLabel").pack(anchor="w")
        ttk.Label(main,
                  text="Two-pass: generates a custom palette first for optimal color accuracy.",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        inp = ttk.Frame(main)
        inp.pack(fill=tk.X, pady=4)
        self.gif_list = tk.Listbox(inp, height=5, selectmode=tk.EXTENDED,
                                   font=("Segoe UI", 9), activestyle="none", bg="#fff")
        self.gif_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        _add_scrollbar(inp, self.gif_list)
        gbf = ttk.Frame(inp)
        gbf.pack(side=tk.RIGHT, fill=tk.Y, padx=4)
        ttk.Button(gbf, text="Add Files",   command=lambda: self._add_files(self.gif_list)).pack(fill=tk.X, pady=1)
        ttk.Button(gbf, text="Remove Sel.", command=lambda: self._remove_selected(self.gif_list)).pack(fill=tk.X, pady=1)
        ttk.Button(gbf, text="Clear All",   command=lambda: self.gif_list.delete(0, tk.END)).pack(fill=tk.X, pady=1)

        sf = ttk.LabelFrame(main, text="GIF Options", padding=10)
        sf.pack(fill=tk.X, pady=8)

        g = dict(padx=8, pady=6, sticky="w")
        ttk.Label(sf, text="Width (px):").grid(row=0, column=0, **g)
        ttk.Entry(sf, textvariable=self.var_gif_scale, width=8).grid(row=0, column=1, **g)

        ttk.Label(sf, text="FPS:").grid(row=0, column=2, **g)
        ttk.Entry(sf, textvariable=self.var_gif_fps, width=6).grid(row=0, column=3, **g)

        ttk.Label(sf, text="Loop:").grid(row=0, column=4, **g)
        lc = ttk.Entry(sf, textvariable=self.var_gif_loop, width=6)
        lc.grid(row=0, column=5, **g)
        ToolTip(lc, "0 = loop forever  |  1 = play once  |  2 = play twice, etc.")

        ttk.Label(sf, text="Trim Start:").grid(row=1, column=0, **g)
        ttk.Entry(sf, textvariable=self.var_gif_start, width=8).grid(row=1, column=1, **g)
        ttk.Label(sf, text="Trim End:").grid(row=1, column=2, **g)
        ttk.Entry(sf, textvariable=self.var_gif_end, width=8).grid(row=1, column=3, **g)

        ttk.Label(sf, text="Dither:").grid(row=1, column=4, **g)
        dm = ttk.Combobox(sf, textvariable=self.var_gif_dither, values=GIF_DITHER_MODES,
                          state="readonly", width=20)
        dm.grid(row=1, column=5, **g)
        ToolTip(dm,
                "sierra2_4a — best overall quality (default)\n"
                "floyd_steinberg — classic, good for photos\n"
                "bayer — retro pattern look\n"
                "none — fast, lower quality")

        ttk.Button(main, text="Generate GIFs", style="Run.TButton",
                   command=self.run_gif_tasks).pack(fill=tk.X, pady=8)

    # ── Stitch tab ────────────────────────────────────────────────────────────

    def _build_stitch_tab(self):
        frame = ttk.Frame(self.tab_stitch, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Join / Concatenate Video Files", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame,
                  text="Files are joined in the order listed. Without re-encode, all files must share "
                       "identical codec, resolution, and frame rate.",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        lf = ttk.Frame(frame)
        lf.pack(fill=tk.BOTH, expand=True)
        self.stitch_list = tk.Listbox(lf, height=10, font=("Segoe UI", 9),
                                      activestyle="none", bg="#fff")
        self.stitch_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        _add_scrollbar(lf, self.stitch_list)

        sbf = ttk.Frame(lf)
        sbf.pack(side=tk.RIGHT, fill=tk.Y, padx=4)
        ttk.Button(sbf, text="Add Files",   command=lambda: self._add_files(self.stitch_list)).pack(fill=tk.X, pady=1)
        ttk.Button(sbf, text="Remove Sel.", command=lambda: self._remove_selected(self.stitch_list)).pack(fill=tk.X, pady=1)
        ttk.Button(sbf, text="Move Up",     command=lambda: self._move_item(self.stitch_list, -1)).pack(fill=tk.X, pady=1)
        ttk.Button(sbf, text="Move Down",   command=lambda: self._move_item(self.stitch_list,  1)).pack(fill=tk.X, pady=1)
        ttk.Button(sbf, text="Clear All",   command=lambda: self.stitch_list.delete(0, tk.END)).pack(fill=tk.X, pady=1)

        opts = ttk.LabelFrame(frame, text="Options", padding=8)
        opts.pack(fill=tk.X, pady=8)
        self.stitch_reencode = tk.BooleanVar()
        ttk.Checkbutton(
            opts,
            text="Force Re-encode  (slower; required when files have different codecs or resolutions)",
            variable=self.stitch_reencode,
        ).pack(anchor="w")

        out_row = ttk.Frame(opts)
        out_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(out_row, text="Output File:").pack(side=tk.LEFT)
        self.stitch_out = ttk.Entry(out_row, font=("Segoe UI", 9))
        self.stitch_out.insert(0, "stitched.mp4")
        self.stitch_out.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(out_row, text="Save As...", command=self._stitch_browse_out).pack(side=tk.RIGHT)

        ttk.Button(frame, text="Stitch Files", style="Run.TButton",
                   command=self.run_stitch_tasks).pack(fill=tk.X, pady=8)

    def _stitch_browse_out(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("MKV", "*.mkv"), ("MOV", "*.mov"), ("All", "*.*")],
        )
        if f:
            self.stitch_out.delete(0, tk.END)
            self.stitch_out.insert(0, f)

    # ── Media Info tab ────────────────────────────────────────────────────────

    def _build_info_tab(self):
        frame = ttk.Frame(self.tab_info, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Media Info  (ffprobe)", style="Header.TLabel").pack(anchor="w", pady=(0, 8))

        sel = ttk.Frame(frame)
        sel.pack(fill=tk.X, pady=(0, 8))
        self.info_path = ttk.Entry(sel, font=("Segoe UI", 9))
        self.info_path.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(sel, text="Browse...", command=self._info_browse).pack(side=tk.LEFT, padx=4)
        ttk.Button(sel, text="Inspect", command=self.run_media_info).pack(side=tk.LEFT)

        self.info_text = scrolledtext.ScrolledText(
            frame, state="disabled", font=("Consolas", 9),
            bg="#1e1e2e", fg="#cdd6f4", wrap=tk.NONE,
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)
        self.info_text.tag_config("section", foreground="#a6e3a1", font=("Consolas", 9, "bold"))
        self.info_text.tag_config("key",     foreground="#89dceb")
        self.info_text.tag_config("val",     foreground="#fab387")
        self.info_text.tag_config("err",     foreground="#f38ba8")

        if not self.ffprobe_ok:
            self._info_write("ffprobe not found in PATH.\n"
                             "Install FFmpeg (which includes ffprobe) to use this tab.\n", "err")

    def _info_browse(self):
        f = filedialog.askopenfilename()
        if f:
            self.info_path.delete(0, tk.END)
            self.info_path.insert(0, f)

    def _info_write(self, text, tag=None):
        self.info_text.config(state="normal")
        self.info_text.insert(tk.END, text, tag or "")
        self.info_text.config(state="disabled")

    def run_media_info(self):
        if not self.ffprobe_ok:
            messagebox.showerror("Error", "ffprobe is not available.")
            return
        path = self.info_path.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showwarning("No File", "Select a valid file first.")
            return

        self.info_text.config(state="normal")
        self.info_text.delete("1.0", tk.END)
        self.info_text.config(state="disabled")

        def _thread():
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
                   "-show_format", "-show_streams", path]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True,
                                        encoding="utf-8", errors="replace")
                data = json.loads(result.stdout)
            except Exception as exc:
                self.root.after(0, lambda: self._info_write(f"Error: {exc}\n", "err"))
                return

            def _render():
                self.info_text.config(state="normal")
                self.info_text.delete("1.0", tk.END)

                fmt = data.get("format", {})
                self._info_write("=== FORMAT ===\n", "section")
                for k, v in fmt.items():
                    if k == "tags":
                        self._info_write("  TAGS:\n", "key")
                        for tk_, tv in v.items():
                            self._info_write(f"    {tk_}: ", "key")
                            self._info_write(f"{tv}\n", "val")
                    else:
                        self._info_write(f"  {k}: ", "key")
                        self._info_write(f"{v}\n", "val")

                for i, stream in enumerate(data.get("streams", [])):
                    ctype = stream.get("codec_type", "?").upper()
                    self._info_write(f"\n=== STREAM {i}  ({ctype}) ===\n", "section")
                    for k, v in stream.items():
                        if k == "tags":
                            self._info_write("  TAGS:\n", "key")
                            for tk_, tv in v.items():
                                self._info_write(f"    {tk_}: ", "key")
                                self._info_write(f"{tv}\n", "val")
                        elif k == "disposition":
                            continue   # noisy, skip
                        else:
                            self._info_write(f"  {k}: ", "key")
                            self._info_write(f"{v}\n", "val")

                self.info_text.config(state="disabled")

            self.root.after(0, _render)

        threading.Thread(target=_thread, daemon=True).start()

    # ── Custom CLI tab ────────────────────────────────────────────────────────

    def _build_custom_tab(self):
        frame = ttk.Frame(self.tab_custom, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Custom FFmpeg Command", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Builds:  ffmpeg -y -i <input> <arguments> <output>",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 12))

        for lbl, attr, is_output in [
            ("Input File:", "custom_in", False),
            ("Output File:", "custom_out", True),
        ]:
            ttk.Label(frame, text=lbl).pack(anchor="w")
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=(0, 6))
            entry = ttk.Entry(row, font=("Segoe UI", 9))
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            setattr(self, attr, entry)
            btn_text = "Save As..." if is_output else "Browse..."
            pick_fn  = filedialog.asksaveasfilename if is_output else filedialog.askopenfilename
            ttk.Button(row, text=btn_text,
                       command=lambda e=entry, fn=pick_fn: self._set_entry(e, fn())).pack(side=tk.RIGHT, padx=4)

        ttk.Label(frame, text="Arguments  (e.g.  -c:v copy -an):").pack(anchor="w", pady=(4, 0))
        self.custom_args = ttk.Entry(frame, font=("Segoe UI", 9))
        self.custom_args.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(frame, text="Live Preview:").pack(anchor="w", pady=(8, 0))
        self.custom_preview = scrolledtext.ScrolledText(
            frame, height=3, state="disabled",
            font=("Consolas", 9), bg="#1e1e2e", fg="#cdd6f4", wrap=tk.WORD,
        )
        self.custom_preview.pack(fill=tk.X, pady=(0, 10))

        for widget in (self.custom_in, self.custom_out, self.custom_args):
            widget.bind("<KeyRelease>", self._update_custom_preview)

        ttk.Button(frame, text="Run Command", style="Run.TButton",
                   command=self.run_custom_task).pack(fill=tk.X)

    def _update_custom_preview(self, _=None):
        i = self.custom_in.get()
        o = self.custom_out.get()
        a = self.custom_args.get()
        preview = f'ffmpeg -y -i "{i}" {a} "{o}"'
        self.custom_preview.config(state="normal")
        self.custom_preview.delete("1.0", tk.END)
        self.custom_preview.insert("1.0", preview)
        self.custom_preview.config(state="disabled")

    # =========================================================================
    # HELPERS
    # =========================================================================

    # ── Logging ───────────────────────────────────────────────────────────────

    def log(self, msg: str, tag: str = "info"):
        def _do():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, str(msg) + "\n", tag)
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.root.after(0, _do)

    def _set_status(self, msg: str, color: str = "#333333"):
        self.root.after(0, lambda: self.status_label.config(text=msg, foreground=color))

    def _set_progress(self, msg: str):
        self.root.after(0, lambda: self.progress_label.config(text=msg))

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")
        self.progress_label.config(text="")

    def _copy_log(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log_text.get("1.0", tk.END))

    # ── File / folder pickers ─────────────────────────────────────────────────

    def _add_files(self, listbox: tk.Listbox):
        for f in filedialog.askopenfilenames():
            listbox.insert(tk.END, f)

    def _remove_selected(self, listbox: tk.Listbox):
        for i in reversed(listbox.curselection()):
            listbox.delete(i)

    def _move_item(self, listbox: tk.Listbox, direction: int):
        sel = listbox.curselection()
        if not sel:
            return
        indices = sel if direction == 1 else reversed(sel)
        for idx in indices:
            new_idx = idx + direction
            if 0 <= new_idx < listbox.size():
                val = listbox.get(idx)
                listbox.delete(idx)
                listbox.insert(new_idx, val)
                listbox.selection_set(new_idx)

    def _browse_output(self):
        d = filedialog.askdirectory()
        if d:
            self.output_dir.set(d)

    def _open_output_folder(self):
        d = self.output_dir.get()
        if d and os.path.isdir(d):
            _open_folder(d)
        else:
            messagebox.showinfo("Info", "No valid output folder is set.")

    def _set_entry(self, entry: ttk.Entry, value: str):
        if value:
            entry.delete(0, tk.END)
            entry.insert(0, value)

    # ── Misc helpers ──────────────────────────────────────────────────────────

    def _codec_code(self, nice_name: str, codec_list: list) -> str:
        for name, code in codec_list:
            if name == nice_name:
                return code
        return "copy"

    def _append_arg(self, var: tk.StringVar, text: str):
        cur = var.get().rstrip()
        if text not in cur:
            var.set(cur + " " + text)

    def _update_batch_defaults(self, combo: ttk.Combobox, var: tk.StringVar):
        ext = combo.get()
        if ext in BATCH_DEFAULTS:
            var.set(BATCH_DEFAULTS[ext])

    def _guard_running(self) -> bool:
        if self.is_running:
            messagebox.showwarning(
                "Already Running",
                "A task is currently running.\nClick 'STOP ALL' to cancel it first.",
            )
            return True
        return False

    def _out_path(self, src_file: str, ext: str) -> str:
        """Resolve the output path for a given source file and extension."""
        out_dir = self.output_dir.get()
        base = os.path.splitext(os.path.basename(src_file))[0] + ext
        if out_dir:
            return os.path.join(out_dir, base)
        return os.path.join(os.path.dirname(src_file), base)

    @staticmethod
    def _build_atempo(factor: float) -> str:
        """Build an atempo filter chain that handles speeds outside the 0.5-2x limit."""
        parts = []
        while factor > 2.0:
            parts.append("atempo=2.0")
            factor /= 2.0
        while factor < 0.5:
            parts.append("atempo=0.5")
            factor *= 2.0
        parts.append(f"atempo={factor:.5f}")
        return ",".join(parts)

    # ── Process runner ────────────────────────────────────────────────────────

    def stop_all(self):
        self.stop_requested = True
        if self.current_process:
            self.log("!!! STOP REQUESTED !!!", "error")
            try:
                self.current_process.kill()
            except Exception:
                pass
        self._set_status("Stopped", "#cc0000")

    def run_process(self, cmd: list, desc: str, pass_label: str = "") -> int:
        if self.stop_requested:
            return 1

        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        label = f"{desc} {pass_label}".strip()
        # Pretty-print the command with quoting for readability
        printable = " ".join(f'"{c}"' if (" " in c or not c) else c for c in cmd)
        self.log(f">> {label}", "cmd")
        self.log(f"   {printable}", "cmd")
        self._set_status(f"Running: {desc[:32]}", "#1a4d1a")

        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, startupinfo=startupinfo,
                encoding="utf-8", errors="replace",
            )
        except FileNotFoundError:
            self.log("ERROR: ffmpeg executable not found.", "error")
            return 1

        self.current_process = process

        for line in process.stdout:
            if self.stop_requested:
                process.kill()
                break
            line = line.strip()
            if not line:
                continue
            # Progress lines: push to status bar, NOT the log (stops log spam)
            if any(x in line for x in ("frame=", "size=", "time=", "speed=")):
                self._set_progress(line)
            elif any(x in line.lower() for x in ("error", "invalid", "failed", "no such")):
                self.log(line, "error")
            elif "warning" in line.lower():
                self.log(line, "warn")

        process.wait()
        self.current_process = None
        rc = process.returncode

        if rc == 0 and not self.stop_requested:
            self.log(f"[OK] {label}", "success")
            self._set_progress("")
        elif not self.stop_requested:
            self.log(f"[FAILED] {label}  (exit {rc})", "error")

        return rc

    # =========================================================================
    # TASK RUNNERS
    # =========================================================================

    # ── Video ─────────────────────────────────────────────────────────────────

    def run_video_tasks(self):
        if self._guard_running():
            return
        files = self.vid_list.get(0, tk.END)
        if not files:
            messagebox.showwarning("No Input", "Add at least one video file.")
            return
        ext = self.var_v_container.get()
        self.stop_requested = False

        def _thread():
            self.is_running = True
            for f in files:
                if self.stop_requested:
                    break

                out = self._out_path(f, ext)
                vc  = self.var_v_codec.get()

                cmd = ["ffmpeg", "-y"]
                if self.var_v_trim_start.get():
                    cmd += ["-ss", self.var_v_trim_start.get()]
                if self.var_v_trim_end.get():
                    cmd += ["-to", self.var_v_trim_end.get()]
                cmd += ["-i", f]

                # ---- Video codec
                cmd += ["-c:v", vc]
                if vc != "copy":
                    preset = self.var_v_preset.get()
                    if preset:
                        # Strip friendly suffix from NVENC presets ("p4 (Balanced)" -> "p4")
                        clean_preset = preset.split(" ")[0]
                        cmd += ["-preset", clean_preset]

                    vb = self.var_v_bitrate.get().strip()
                    if vb and vb.replace(".", "", 1).isdigit():
                        vb += "M"

                    if not self.var_v_twopass.get():
                        if vb:
                            cmd += ["-b:v", vb]
                        else:
                            cmd += ["-crf", self.var_v_crf.get()]

                    fps = self.var_v_fps.get().strip()
                    if fps:
                        cmd += ["-r", fps]

                # ---- Video filters
                vf = []

                # Deinterlace
                di_name = self.var_v_deinterlace.get()
                for name, flt in DEINTERLACE_MODES:
                    if name == di_name and flt:
                        vf.append(flt)
                        break

                # Scale
                w = self.var_v_scale_w.get().strip()
                h = self.var_v_scale_h.get().strip()
                if w or h:
                    vf.append(f"scale={w or '-1'}:{h or '-1'}")

                # Crop
                crop = self.var_v_crop.get().strip()
                if crop:
                    vf.append(f"crop={crop}")

                # HDR -> SDR tone map
                if self.var_v_hdr_sdr.get():
                    vf.append(
                        "zscale=t=linear:npl=100,format=gbrpf32le,"
                        "zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
                        "zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
                    )

                # Rotate
                rot_name = self.var_v_rotate.get()
                for name, flt in ROTATE_OPTIONS:
                    if name == rot_name and flt:
                        vf.append(flt)
                        break

                # Speed (video portion via setpts)
                speed_factor = SPEED_MAP.get(self.var_v_speed.get(), 1.0)
                if speed_factor != 1.0:
                    vf.append(f"setpts={1.0 / speed_factor:.5f}*PTS")

                # Burn-in subtitles
                sub = self.var_v_burn_sub.get().strip()
                if sub:
                    safe_sub = sub.replace("\\", "/").replace(":", "\\:")
                    vf.append(f"subtitles='{safe_sub}'")

                if vf and vc != "copy":
                    cmd += ["-vf", ",".join(vf)]

                # ---- Audio
                ac = self.var_v_acodec.get()
                if ac == "none":
                    cmd.append("-an")
                else:
                    cmd += ["-c:a", ac]
                    if ac not in ("copy", "none") and self.var_v_abitrate.get():
                        cmd += ["-b:a", self.var_v_abitrate.get()]
                    # Speed-adjust audio in sync with video speed change
                    if speed_factor != 1.0 and ac not in ("copy", "none"):
                        atempo = self._build_atempo(speed_factor)
                        cmd += ["-af", atempo]

                # ---- Subtitles
                if self.var_v_copy_sub.get():
                    cmd += ["-c:s", "copy"]
                else:
                    cmd.append("-sn")

                # ---- Metadata
                if self.var_v_strip_meta.get():
                    cmd += ["-map_metadata", "-1"]

                # ---- Execute (1-pass or 2-pass)
                if self.var_v_twopass.get() and vc != "copy":
                    vb_final = vb if vb else "5M"   # safe fallback
                    logfile  = os.path.join(tempfile.gettempdir(),
                                            f"ffswak_{os.getpid()}")
                    c1 = list(cmd) + ["-b:v", vb_final, "-pass", "1",
                                      "-passlogfile", logfile, "-f", "null",
                                      os.devnull if os.name != "nt" else "NUL"]
                    if self.run_process(c1, os.path.basename(f), "(Pass 1)") == 0 \
                            and not self.stop_requested:
                        c2 = list(cmd) + ["-b:v", vb_final, "-pass", "2",
                                          "-passlogfile", logfile, out]
                        self.run_process(c2, os.path.basename(f), "(Pass 2)")
                    # Clean up pass log artefacts
                    for sfx in ("-0.log", "-0.log.mbtree"):
                        try:
                            os.remove(logfile + sfx)
                        except Exception:
                            pass
                else:
                    cmd.append(out)
                    self.run_process(cmd, os.path.basename(f))

            self.is_running = False
            self._set_status("Done", "#1a5e1a")
            if not self.stop_requested:
                out_dir = self.output_dir.get()
                self.root.after(0, lambda: messagebox.showinfo("Done", "Video queue finished."))
                if self.open_on_done.get() and out_dir:
                    _open_folder(out_dir)

        threading.Thread(target=_thread, daemon=True).start()

    # ── Audio ─────────────────────────────────────────────────────────────────

    def run_audio_tasks(self):
        if self._guard_running():
            return
        files = self.aud_list.get(0, tk.END)
        if not files:
            messagebox.showwarning("No Input", "Add at least one file.")
            return
        ext = self.var_a_container.get()
        self.stop_requested = False

        def _thread():
            self.is_running = True
            for f in files:
                if self.stop_requested:
                    break

                out = self._out_path(f, ext)
                cmd = ["ffmpeg", "-y"]

                if self.var_a_trim_start.get():
                    cmd += ["-ss", self.var_a_trim_start.get()]
                if self.var_a_trim_end.get():
                    cmd += ["-to", self.var_a_trim_end.get()]
                cmd += ["-i", f, "-vn"]

                ac = self.var_a_codec.get()
                cmd += ["-c:a", ac]

                if ac != "copy":
                    br = self.var_a_bitrate.get().strip()
                    if br:
                        cmd += ["-b:a", br]

                    sr = self.var_a_sample_rate.get()
                    if sr and sr != "Original":
                        cmd += ["-ar", sr]

                    ch_val = CHANNELS_MAP.get(self.var_a_channels.get())
                    if ch_val:
                        cmd += ["-ac", ch_val]

                    af = []
                    if self.var_a_norm.get():
                        af.append("dynaudnorm")
                    vol = self.var_a_volume.get().strip()
                    if vol:
                        af.append(f"volume={vol}")
                    if af:
                        cmd += ["-af", ",".join(af)]

                cmd.append(out)
                self.run_process(cmd, os.path.basename(f))

            self.is_running = False
            self._set_status("Done", "#1a5e1a")
            if not self.stop_requested:
                out_dir = self.output_dir.get()
                self.root.after(0, lambda: messagebox.showinfo("Done", "Audio queue finished."))
                if self.open_on_done.get() and out_dir:
                    _open_folder(out_dir)

        threading.Thread(target=_thread, daemon=True).start()

    # ── GIF ───────────────────────────────────────────────────────────────────

    def run_gif_tasks(self):
        if self._guard_running():
            return
        files = self.gif_list.get(0, tk.END)
        if not files:
            messagebox.showwarning("No Input", "Add at least one video file.")
            return
        fps    = self.var_gif_fps.get()
        width  = self.var_gif_scale.get()
        start  = self.var_gif_start.get()
        end    = self.var_gif_end.get()
        dither = self.var_gif_dither.get()
        loop   = self.var_gif_loop.get() if self.var_gif_loop.get().isdigit() else "0"
        self.stop_requested = False

        def _thread():
            self.is_running = True
            for f in files:
                if self.stop_requested:
                    break

                out = self._out_path(f, ".gif")
                time_args = []
                if start:
                    time_args += ["-ss", start]
                if end:
                    time_args += ["-to", end]

                scale_f = f"fps={fps},scale={width}:-1:flags=lanczos"

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    palette = tmp.name

                try:
                    # Pass 1: generate palette
                    cmd1 = (["ffmpeg", "-y"] + time_args +
                            ["-i", f, "-vf", f"{scale_f},palettegen=stats_mode=diff", palette])
                    if self.run_process(cmd1, os.path.basename(f), "(Palette)") == 0 \
                            and not self.stop_requested:
                        # Pass 2: use palette
                        cmd2 = (["ffmpeg", "-y"] + time_args + ["-i", f, "-i", palette,
                                 "-filter_complex",
                                 f"{scale_f}[x];[x][1:v]paletteuse=dither={dither}",
                                 "-loop", loop, out])
                        self.run_process(cmd2, os.path.basename(f), "(GIF)")
                finally:
                    try:
                        os.unlink(palette)
                    except Exception:
                        pass

            self.is_running = False
            self._set_status("Done", "#1a5e1a")
            if not self.stop_requested:
                self.root.after(0, lambda: messagebox.showinfo("Done", "GIFs created."))

        threading.Thread(target=_thread, daemon=True).start()

    # ── Batch ─────────────────────────────────────────────────────────────────

    def run_batch_video(self, out_ext: str):
        self._run_batch(self.batch_v_in.get(), self.batch_v_out.get(),
                        self.batch_v_args.get(), out_ext,
                        self.batch_v_recursive.get(), self.batch_v_ext_in.get())

    def run_batch_audio(self, out_ext: str):
        self._run_batch(self.batch_a_in.get(), self.batch_a_out.get(),
                        self.batch_a_args.get(), out_ext,
                        self.batch_a_recursive.get(), self.batch_a_ext_in.get())

    def _run_batch(self, in_d: str, out_d: str, args_str: str,
                   out_ext: str, recursive: bool, in_ext_filter: str):
        if not in_d or not out_d:
            messagebox.showwarning("Missing Paths", "Set both input and output folders.")
            return
        if self._guard_running():
            return
        self.stop_requested = False

        def _thread():
            self.is_running = True
            ext_f = in_ext_filter.strip().lower()
            files = []
            for root_dir, _, fnames in os.walk(in_d):
                if not recursive and root_dir != in_d:
                    continue
                for fname in fnames:
                    if ext_f in ("*", "", "all") or fname.lower().endswith(ext_f):
                        files.append(os.path.join(root_dir, fname))

            self.log(f"Batch: {len(files)} file(s) found.", "info")
            args = args_str.split()

            for f in files:
                if self.stop_requested:
                    break
                rel    = os.path.relpath(f, in_d)
                target = os.path.join(out_d, os.path.splitext(rel)[0] + out_ext)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                self.run_process(["ffmpeg", "-y", "-i", f] + args + [target], os.path.basename(f))

            self.is_running = False
            self._set_status("Done", "#1a5e1a")
            if not self.stop_requested:
                self.root.after(0, lambda: messagebox.showinfo("Done", "Batch complete."))
                if self.open_on_done.get() and out_d:
                    _open_folder(out_d)

        threading.Thread(target=_thread, daemon=True).start()

    # ── Stitch ────────────────────────────────────────────────────────────────

    def run_stitch_tasks(self):
        if self._guard_running():
            return
        files = self.stitch_list.get(0, tk.END)
        if len(files) < 2:
            messagebox.showwarning("Not Enough Files", "Add at least 2 files to stitch.")
            return
        out_file = self.stitch_out.get().strip()
        if not out_file:
            messagebox.showwarning("No Output", "Set an output file name.")
            return
        self.stop_requested = False

        def _thread():
            self.is_running = True

            if self.stitch_reencode.get():
                cmd = ["ffmpeg", "-y"]
                fstr = ""
                for i, f in enumerate(files):
                    cmd += ["-i", f]
                    fstr += f"[{i}:v][{i}:a]"
                fstr += f"concat=n={len(files)}:v=1:a=1[v][a]"
                cmd += ["-filter_complex", fstr, "-map", "[v]", "-map", "[a]", out_file]
                self.run_process(cmd, "Stitch (Re-encode)")
            else:
                # Use tempfile for the concat list so it's never in a random CWD
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False, encoding="utf-8"
                ) as tmp:
                    concat_path = tmp.name
                    for path in files:
                        safe = path.replace("\\", "/").replace("'", r"'\''")
                        tmp.write(f"file '{safe}'\n")
                try:
                    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                           "-i", concat_path, "-c", "copy", out_file]
                    self.run_process(cmd, "Stitch (Copy)")
                finally:
                    try:
                        os.unlink(concat_path)
                    except Exception:
                        pass

            self.is_running = False
            self._set_status("Done", "#1a5e1a")
            if not self.stop_requested:
                self.root.after(0, lambda: messagebox.showinfo("Done", f"Output: {out_file}"))
                if self.open_on_done.get():
                    _open_folder(os.path.dirname(os.path.abspath(out_file)))

        threading.Thread(target=_thread, daemon=True).start()

    # ── Custom CLI ────────────────────────────────────────────────────────────

    def run_custom_task(self):
        if self._guard_running():
            return
        i = self.custom_in.get().strip()
        o = self.custom_out.get().strip()
        a = self.custom_args.get().strip()
        if not i or not o:
            messagebox.showwarning("Missing Fields", "Set both an input and output file.")
            return
        self.stop_requested = False

        def _thread():
            self.run_process(["ffmpeg", "-y", "-i", i] + a.split() + [o], "Custom Task")
            self.is_running = False
            self._set_status("Done", "#1a5e1a")

        threading.Thread(target=_thread, daemon=True).start()

    # =========================================================================
    # PRESETS
    # =========================================================================

    def _collect_preset(self) -> dict:
        return {
            "vcodec":        self.var_v_codec.get(),
            "vcontainer":    self.var_v_container.get(),
            "vcrf":          self.var_v_crf.get(),
            "vpreset":       self.var_v_preset.get(),
            "vbitrate":      self.var_v_bitrate.get(),
            "vtwopass":      self.var_v_twopass.get(),
            "vfps":          self.var_v_fps.get(),
            "vspeed":        self.var_v_speed.get(),
            "vacodec":       self.var_v_acodec.get(),
            "vabitrate":     self.var_v_abitrate.get(),
            "vscale_w":      self.var_v_scale_w.get(),
            "vscale_h":      self.var_v_scale_h.get(),
            "vdeinterlace":  self.var_v_deinterlace.get(),
            "vrotate":       self.var_v_rotate.get(),
            "vhdr_sdr":      self.var_v_hdr_sdr.get(),
            "vstrip_meta":   self.var_v_strip_meta.get(),
            "vcopy_sub":     self.var_v_copy_sub.get(),
            "acodec":        self.var_a_codec.get(),
            "acontainer":    self.var_a_container.get(),
            "abitrate":      self.var_a_bitrate.get(),
            "asample_rate":  self.var_a_sample_rate.get(),
            "achannels":     self.var_a_channels.get(),
            "avolume":       self.var_a_volume.get(),
            "anorm":         self.var_a_norm.get(),
        }

    def _apply_preset(self, data: dict):
        mapping = {
            "vcodec":       self.var_v_codec,
            "vcontainer":   self.var_v_container,
            "vcrf":         self.var_v_crf,
            "vpreset":      self.var_v_preset,
            "vbitrate":     self.var_v_bitrate,
            "vtwopass":     self.var_v_twopass,
            "vfps":         self.var_v_fps,
            "vspeed":       self.var_v_speed,
            "vacodec":      self.var_v_acodec,
            "vabitrate":    self.var_v_abitrate,
            "vscale_w":     self.var_v_scale_w,
            "vscale_h":     self.var_v_scale_h,
            "vdeinterlace": self.var_v_deinterlace,
            "vrotate":      self.var_v_rotate,
            "vhdr_sdr":     self.var_v_hdr_sdr,
            "vstrip_meta":  self.var_v_strip_meta,
            "vcopy_sub":    self.var_v_copy_sub,
            "acodec":       self.var_a_codec,
            "acontainer":   self.var_a_container,
            "abitrate":     self.var_a_bitrate,
            "asample_rate": self.var_a_sample_rate,
            "achannels":    self.var_a_channels,
            "avolume":      self.var_a_volume,
            "anorm":        self.var_a_norm,
        }
        for key, var in mapping.items():
            if key in data:
                var.set(data[key])

    def save_preset(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON Preset", "*.json")]
        )
        if f:
            try:
                with open(f, "w", encoding="utf-8") as fp:
                    json.dump(self._collect_preset(), fp, indent=2)
                self.log(f"Preset saved: {f}", "success")
            except Exception as exc:
                messagebox.showerror("Error", f"Could not save preset:\n{exc}")

    def load_preset(self):
        f = filedialog.askopenfilename(filetypes=[("JSON Preset", "*.json")])
        if f:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    self._apply_preset(json.load(fp))
                self.log(f"Preset loaded: {f}", "success")
            except Exception as exc:
                messagebox.showerror("Error", f"Could not load preset:\n{exc}")

    # ── Command preview ───────────────────────────────────────────────────────

    def _preview_video_cmd(self):
        vc  = self.var_v_codec.get()
        ext = self.var_v_container.get()
        p   = ["ffmpeg", "-y"]
        if self.var_v_trim_start.get():
            p += ["-ss", self.var_v_trim_start.get()]
        if self.var_v_trim_end.get():
            p += ["-to", self.var_v_trim_end.get()]
        p += ["-i", "<input>"]
        p += ["-c:v", vc]
        if vc != "copy":
            preset = self.var_v_preset.get().split(" ")[0]
            p += ["-preset", preset]
            if self.var_v_bitrate.get():
                p += ["-b:v", self.var_v_bitrate.get()]
            else:
                p += ["-crf", self.var_v_crf.get()]
            if self.var_v_fps.get():
                p += ["-r", self.var_v_fps.get()]
        ac = self.var_v_acodec.get()
        if ac == "none":
            p.append("-an")
        else:
            p += ["-c:a", ac]
            if self.var_v_abitrate.get():
                p += ["-b:a", self.var_v_abitrate.get()]
        if self.var_v_strip_meta.get():
            p += ["-map_metadata", "-1"]
        p.append(f"<output>{ext}")
        messagebox.showinfo("Command Preview", " ".join(p))


# ── Module-level helpers ──────────────────────────────────────────────────────

def _add_scrollbar(parent: tk.Widget, listbox: tk.Listbox):
    sb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=listbox.yview)
    sb.pack(side=tk.LEFT, fill=tk.Y)
    listbox.config(yscrollcommand=sb.set)


def _open_folder(path: str):
    """Open a folder in the OS file manager."""
    try:
        if os.name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = FFmpegGUI(root)
    root.mainloop()
