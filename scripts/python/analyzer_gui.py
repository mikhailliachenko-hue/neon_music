#!/usr/bin/env python3
"""Desktop GUI for the Neon Footstep analyzer and wall tuning."""
from __future__ import annotations

import json
import queue
import subprocess
import sys
import time
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import audio_analyzer
from neon_track_io import build_neon_track, write_neon_track
from lane_assignment import (
    DEFAULT_DIFFICULTY,
    DEFAULT_MAX_SAME_LANE_RUN,
    DEFAULT_MAX_SAME_SIDE_RUN,
    DEFAULT_MAX_SIMULTANEOUS_FEET,
    DEFAULT_HOLD_ENABLED,
    DEFAULT_HOLD_MAX_DURATION,
    DEFAULT_HOLD_MIN_DURATION,
    DEFAULT_HOLD_MIN_GAP,
    DEFAULT_HOLD_RATE_BARS,
    DEFAULT_HIGH_WALL_ENABLED,
    DEFAULT_HIGH_WALL_MIN_GAP_BARS,
    DEFAULT_HIGH_WALL_TARGET_RATIO,
    DEFAULT_REFERENCE_HAND_HOLDS_ENABLED,
    DEFAULT_REFERENCE_HAND_HOLD_RATE_PHRASES,
    DEFAULT_SPECTACLE_COMBOS_ENABLED,
    DEFAULT_RAMP_DURATION,
    DEFAULT_RAMP_STRENGTH,
    DEFAULT_WALL_ANTICIPATION,
    DEFAULT_WALL_DENSITY_MULTIPLIER,
    DEFAULT_WALL_DURATION_BEATS,
    DEFAULT_WALL_ENABLED,
    DEFAULT_LANE_LAYOUT,
    LANE_LAYOUTS,
    DEFAULT_WALL_MIN_GAP_BARS,
    DEFAULT_WALL_PREPARATION_WINDOW,
    DEFAULT_WALL_RATE_BARS,
    DEFAULT_WALL_RECOVERY_WINDOW,
    DEFAULT_WALL_REST_WINDOW,
    DIFFICULTY_PROFILES,
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
WALL_VISUAL_CONFIG = PROJECT_DIR / "assets" / "models" / "wall_visual_config.json"
DEFAULT_GODOT = r"C:\Users\BAZA\Documents\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64_console.exe"

VISUAL_DEFAULTS = {
    "wall_height": 4.8,
    "wall_width_x": 3.9,
    "wall_length_z": 24.0,
    "wall_opacity": 0.18,
    "wall_emission_strength": 2.1,
    "wall_edge_glow": 6.4,
    "wall_segment_count": 18.0,
    "wall_segment_spacing": 1.25,
    "wall_strip_emission": 4.8,
    "wall_edge_emission": 12.0,
    "safe_lane_emission": 2.1,
    "safe_lane_opacity": 0.12,
    "safe_lane_pulse": 0.35,
    "next_cell_ring_lead_time": 1.25,
    "next_cell_ring_brightness": 0.9,
    "next_cell_ring_fade_duration": 0.32,
    "camera_dodge_distance": 1.05,
    "camera_dodge_in_duration": 0.55,
    "camera_dodge_hold": 0.08,
    "camera_dodge_return_duration": 0.52,
    "camera_dodge_easing": "sine",
    "global_audio_offset_ms": 28.0,
    "visual_hit_offset_ms": 0.0,
    "wall_left_color": [0.196, 1.0, 1.0],
    "wall_right_color": [0.49, 0.0, 0.90],
    "safe_lane_color": [0.36, 0.86, 1.0],
    "next_cell_ring_color": [0.72, 1.0, 1.0],
}

VISUAL_RANGES = {
    "wall_height": [2.4, 6.2],
    "wall_width_x": [3.2, 4.4],
    "wall_length_z": [8.0, 36.0],
    "wall_opacity": [0.06, 0.55],
    "wall_emission_strength": [0.8, 6.0],
    "wall_edge_glow": [1.5, 14.0],
    "wall_segment_count": [6.0, 36.0],
    "wall_segment_spacing": [0.45, 2.6],
    "wall_strip_emission": [0.8, 10.0],
    "wall_edge_emission": [2.0, 24.0],
    "safe_lane_emission": [0.8, 8.0],
    "safe_lane_opacity": [0.04, 0.42],
    "safe_lane_pulse": [0.0, 1.0],
    "next_cell_ring_lead_time": [0.2, 3.0],
    "next_cell_ring_brightness": [0.0, 1.8],
    "next_cell_ring_fade_duration": [0.03, 1.2],
    "camera_dodge_distance": [0.0, 1.8],
    "camera_dodge_in_duration": [0.05, 2.5],
    "camera_dodge_hold": [0.0, 2.0],
    "camera_dodge_return_duration": [0.05, 3.0],
    "global_audio_offset_ms": [-150.0, 150.0],
    "visual_hit_offset_ms": [-80.0, 80.0],
}


class AnalyzerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        try:
            self.tk.call("tk", "scaling", max(1.0, self.winfo_fpixels("1i") / 72.0))
        except tk.TclError:
            pass
        self.title("Neon Footstep - Audio Analyzer")
        screen_height = max(640, self.winfo_screenheight())
        window_height = max(640, min(720, screen_height - 90))
        self.geometry(f"1040x{window_height}")
        self.minsize(860, 620)
        self.configure(bg="#10131c")
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._visual_config = self._load_visual_config()
        self._gpu_info = audio_analyzer.demucs_gpu_status()
        self._build_vars()
        self._build_ui()
        self.bind("<F5>", lambda _event: self._start_analyze())
        self.bind("<Control-Return>", lambda _event: self._start_analyze())
        self.after(100, self._poll_queue)

    def _load_visual_config(self) -> dict[str, object]:
        config = dict(VISUAL_DEFAULTS)
        if WALL_VISUAL_CONFIG.is_file():
            try:
                payload = json.loads(WALL_VISUAL_CONFIG.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    config.update(payload)
            except Exception:
                pass
        return config

    def _build_vars(self) -> None:
        project = PROJECT_DIR
        self.audio_var = tk.StringVar(value=str(project / "assets" / "audio" / "audio.wav"))
        self.track_var = tk.StringVar(value=str(project / "output" / "neon_track.json"))
        self.lane_layout_var = tk.StringVar(value=DEFAULT_LANE_LAYOUT)
        self.difficulty_var = tk.StringVar(value=DEFAULT_DIFFICULTY)
        self.ramp_duration_var = tk.DoubleVar(value=DEFAULT_RAMP_DURATION)
        self.ramp_strength_var = tk.DoubleVar(value=DEFAULT_RAMP_STRENGTH)
        self.anti_burst_var = tk.BooleanVar(value=True)
        self.max_lane_run_var = tk.IntVar(value=DEFAULT_MAX_SAME_LANE_RUN)
        self.max_side_run_var = tk.IntVar(value=DEFAULT_MAX_SAME_SIDE_RUN)
        self.max_simultaneous_feet_var = tk.IntVar(value=DEFAULT_MAX_SIMULTANEOUS_FEET)
        self.walls_enabled_var = tk.BooleanVar(value=DEFAULT_WALL_ENABLED)
        self.wall_duration_beats_var = tk.IntVar(value=DEFAULT_WALL_DURATION_BEATS)
        self.wall_min_gap_bars_var = tk.IntVar(value=DEFAULT_WALL_MIN_GAP_BARS)
        self.wall_rate_bars_var = tk.IntVar(value=DEFAULT_WALL_RATE_BARS)
        self.wall_anticipation_var = tk.DoubleVar(value=DEFAULT_WALL_ANTICIPATION)
        self.wall_density_multiplier_var = tk.DoubleVar(value=DEFAULT_WALL_DENSITY_MULTIPLIER)
        self.wall_preparation_window_var = tk.DoubleVar(value=DEFAULT_WALL_PREPARATION_WINDOW)
        self.wall_recovery_window_var = tk.DoubleVar(value=DEFAULT_WALL_RECOVERY_WINDOW)
        self.wall_rest_window_var = tk.DoubleVar(value=DEFAULT_WALL_REST_WINDOW)
        self.high_wall_enabled_var = tk.BooleanVar(value=DEFAULT_HIGH_WALL_ENABLED)
        self.high_wall_target_ratio_var = tk.DoubleVar(value=DEFAULT_HIGH_WALL_TARGET_RATIO)
        self.high_wall_min_gap_bars_var = tk.IntVar(value=DEFAULT_HIGH_WALL_MIN_GAP_BARS)
        self.holds_enabled_var = tk.BooleanVar(value=DEFAULT_HOLD_ENABLED)
        self.hold_rate_bars_var = tk.IntVar(value=DEFAULT_HOLD_RATE_BARS)
        self.hold_min_duration_var = tk.DoubleVar(value=DEFAULT_HOLD_MIN_DURATION)
        self.hold_max_duration_var = tk.DoubleVar(value=DEFAULT_HOLD_MAX_DURATION)
        self.hold_min_gap_var = tk.DoubleVar(value=DEFAULT_HOLD_MIN_GAP)
        self.reference_hand_holds_enabled_var = tk.BooleanVar(value=DEFAULT_REFERENCE_HAND_HOLDS_ENABLED)
        self.reference_hand_hold_rate_phrases_var = tk.IntVar(value=DEFAULT_REFERENCE_HAND_HOLD_RATE_PHRASES)
        self.spectacle_combos_enabled_var = tk.BooleanVar(value=DEFAULT_SPECTACLE_COMBOS_ENABLED)
        self.phrase_length_beats_var = tk.IntVar(value=32)
        self.subphrase_length_beats_var = tk.IntVar(value=8)
        self.manual_downbeat_offset_seconds_var = tk.DoubleVar(value=0.0)
        self.allow_crooked_phrase_var = tk.BooleanVar(value=False)
        self.godot_var = tk.StringVar(value=DEFAULT_GODOT)
        self.gpu_status_var = tk.StringVar(value=self._gpu_status_text(self._gpu_info))
        self.visual_vars = {
            key: tk.DoubleVar(value=float(self._visual_config.get(key, VISUAL_DEFAULTS[key])))
            for key in VISUAL_RANGES
        }
        self.color_vars = {
            key: tk.StringVar(value=self._format_rgb(self._visual_config.get(key, VISUAL_DEFAULTS[key])))
            for key in ("wall_left_color", "wall_right_color", "safe_lane_color", "next_cell_ring_color")
        }

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#10131c")
        style.configure("SectionBody.TFrame", background="#131a27")
        style.configure("TLabel", background="#10131c", foreground="#e9f5ff", font=("Segoe UI", 10))
        style.configure("SectionBody.TLabel", background="#131a27", foreground="#e9f5ff")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground="#6ff7ff", background="#10131c")
        style.configure("Hint.TLabel", foreground="#aab8c8", background="#10131c")
        style.configure("GPUReady.TLabel", foreground="#71ffb0", background="#10131c", font=("Segoe UI", 9, "bold"))
        style.configure("CPUMode.TLabel", foreground="#ffd27a", background="#10131c", font=("Segoe UI", 9, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 6))
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=(18, 9), foreground="#071014", background="#6ff7ff")
        style.map("Primary.TButton", background=[("active", "#a4fbff"), ("disabled", "#3d5960")])
        style.configure("Card.TLabelframe", background="#131a27", padding=(14, 10))
        style.configure("Card.TLabelframe.Label", background="#10131c", foreground="#6ff7ff", font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", fieldbackground="#1b2231", foreground="#ffffff")
        style.configure("TCheckbutton", background="#131a27", foreground="#e9f5ff")
        style.configure("TRadiobutton", background="#131a27", foreground="#e9f5ff")

        shell = ttk.Frame(self, padding=(18, 16, 18, 14))
        shell.pack(fill="both", expand=True)
        header = ttk.Frame(shell)
        header.pack(fill="x", pady=(0, 12))
        header_left = ttk.Frame(header)
        header_left.pack(side="left", fill="x", expand=True)
        ttk.Label(header_left, text="NEON FOOTSTEP", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header_left, text="Music-aware choreography generator", style="Hint.TLabel").pack(anchor="w")
        self.gpu_label = ttk.Label(
            header,
            textvariable=self.gpu_status_var,
            style="GPUReady.TLabel" if self._gpu_info.get("available") else "CPUMode.TLabel",
        )
        self.gpu_label.pack(side="right", anchor="e", padx=(16, 0))

        # Reserve the action bar before the expanding notebook. This keeps the
        # start button visible on 768p screens and under Windows DPI scaling.
        self._build_action_bar(shell)

        self.notebook = ttk.Notebook(shell)
        self.notebook.pack(fill="both", expand=True)
        basic = ttk.Frame(self.notebook, padding=12)
        obstacles = ttk.Frame(self.notebook, padding=12)
        visuals = ttk.Frame(self.notebook, padding=12)
        log_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(basic, text="1  Track & Dance")
        self.notebook.add(obstacles, text="2  Obstacles")
        self.notebook.add(visuals, text="3  Visual tuning")
        self.notebook.add(log_tab, text="Log")

        self._card(basic, "Input and output", self._build_files, 0, 0, 2)
        self._card(basic, "Dance difficulty", self._build_difficulty, 1, 0)
        self._card(basic, "Play area", self._build_layout, 1, 1)
        self._card(basic, "Readability and safety", self._build_note_safety, 2, 0)
        self._card(basic, "Musical phrases", self._build_phrase_grid, 2, 1)
        basic.columnconfigure(0, weight=1); basic.columnconfigure(1, weight=1)

        self._card(obstacles, "Walls", self._build_wall_timing, 0, 0)
        self._card(obstacles, "Hand holds and legacy holds", self._build_hold_notes, 0, 1)
        obstacles.columnconfigure(0, weight=1); obstacles.columnconfigure(1, weight=1)

        self._card(visuals, "Wall appearance", self._build_wall_visuals, 0, 0)
        self._card(visuals, "Guidance, camera and timing", self._build_guidance_preview, 0, 1)
        ttk.Button(visuals, text="Save visual settings", command=self._save_visual_config_from_ui).grid(row=1, column=1, sticky="e", padx=6, pady=8)
        visuals.columnconfigure(0, weight=1); visuals.columnconfigure(1, weight=1)

        self.log = tk.Text(log_tab, bg="#0a0d14", fg="#c5f8ff", insertbackground="white", relief="flat", padx=10, pady=8, wrap="word")
        self.log.pack(fill="both", expand=True)
        self._write("Ready. Choose an audio file, tune the dance, then press START ANALYSIS.\n")

    def _card(self, parent, title: str, builder, row: int, column: int, columnspan: int = 1) -> None:
        card = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe")
        card.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=6, pady=6)
        builder(card)

    def _build_files(self, parent) -> None:
        self._path_row(parent, "Audio", self.audio_var, self._choose_audio, [("Audio", "*.wav *.mp3"), ("WAV", "*.wav"), ("MP3", "*.mp3")])
        self._path_row(parent, "Track JSON", self.track_var, self._choose_track, [("JSON", "*.json")])

    def _build_difficulty(self, parent) -> None:
        row = self._grid_row(parent, 0, "Difficulty")
        for name in DIFFICULTY_PROFILES:
            ttk.Radiobutton(row, text=name, value=name, variable=self.difficulty_var).pack(side="left", padx=(0, 14))
        self._spin(parent, 1, "Ramp duration", self.ramp_duration_var, 0, 90, 1, "sec")
        self._scale(parent, 2, "Ramp strength", self.ramp_strength_var, 0.0, 1.0, 0.05)


    def _build_layout(self, parent) -> None:
        row = self._grid_row(parent, 0, "Lane layout")
        for value, label in (("4_lanes", "4 lanes"), ("2_cells", "2 cells")):
            ttk.Radiobutton(row, text=label, value=value, variable=self.lane_layout_var).pack(side="left", padx=(0, 14))
        ttk.Label(parent, text="2 cells uses only the large left/right pads like the reference.", style="SectionBody.TLabel").grid(row=1, column=1, sticky="w", pady=(0, 4))
        parent.columnconfigure(1, weight=1)

    def _build_note_safety(self, parent) -> None:
        ttk.Checkbutton(parent, text="Anti-burst protection", variable=self.anti_burst_var).grid(row=0, column=1, sticky="w", pady=4)
        self._spin(parent, 1, "Max lane run", self.max_lane_run_var, 1, 8, 1)
        self._spin(parent, 2, "Max side run", self.max_side_run_var, 1, 12, 1)
        self._spin(parent, 3, "Simultaneous feet", self.max_simultaneous_feet_var, 1, 2, 1, "max")
        ttk.Label(parent, text="Hard safety cap: never three step targets at one hit.", style="SectionBody.TLabel").grid(row=4, column=1, sticky="w", pady=(0, 4))
        self._spin(parent, 5, "Wall density brake", self.wall_density_multiplier_var, 1.0, 5.0, 0.05, "x")
        ttk.Checkbutton(parent, text="Spectacle combo choreography", variable=self.spectacle_combos_enabled_var).grid(row=6, column=1, sticky="w", pady=4)
        parent.columnconfigure(1, weight=1)

    def _build_wall_timing(self, parent) -> None:
        ttk.Checkbutton(parent, text="Enable wall events", variable=self.walls_enabled_var).grid(row=0, column=1, sticky="w", pady=4)
        self._spin(parent, 1, "Rate", self.wall_rate_bars_var, 4, 32, 1, "bars")
        self._spin(parent, 2, "Duration", self.wall_duration_beats_var, 2, 16, 1, "beats")
        self._spin(parent, 3, "Minimum gap", self.wall_min_gap_bars_var, 4, 32, 1, "bars")
        self._spin(parent, 4, "Anticipation", self.wall_anticipation_var, 0.25, 2.5, 0.05, "sec")
        self._spin(parent, 5, "Preparation rest", self.wall_preparation_window_var, 0.0, 3.0, 0.05, "sec")
        self._spin(parent, 6, "Recovery rest", self.wall_recovery_window_var, 0.0, 3.0, 0.05, "sec")
        self._spin(parent, 7, "Selection rest", self.wall_rest_window_var, 0.0, 3.0, 0.05, "sec")
        ttk.Separator(parent, orient="horizontal").grid(row=8, column=0, columnspan=3, sticky="ew", pady=(8, 6))
        ttk.Checkbutton(parent, text="Bright high walls", variable=self.high_wall_enabled_var).grid(row=9, column=1, sticky="w", pady=4)
        self._spin(parent, 10, "High wall share", self.high_wall_target_ratio_var, 0.0, 0.5, 0.05)
        self._spin(parent, 11, "High wall gap", self.high_wall_min_gap_bars_var, 8, 32, 1, "bars")
        parent.columnconfigure(1, weight=1)

    def _build_hold_notes(self, parent) -> None:
        ttk.Checkbutton(parent, text="Reference double-hand holds", variable=self.reference_hand_holds_enabled_var).grid(row=0, column=1, sticky="w", pady=4)
        self._spin(parent, 1, "Hand-hold spacing", self.reference_hand_hold_rate_phrases_var, 2, 8, 1, "phrases")
        ttk.Separator(parent, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 6))
        ttk.Label(parent, text="Legacy floor holds (compatibility)", style="SectionBody.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 3))
        ttk.Checkbutton(parent, text="Enable legacy floor holds", variable=self.holds_enabled_var).grid(row=4, column=1, sticky="w", pady=4)
        self._spin(parent, 5, "Legacy rate", self.hold_rate_bars_var, 2, 32, 1, "bars")
        self._spin(parent, 6, "Min duration", self.hold_min_duration_var, 0.25, 4.0, 0.05, "sec")
        self._spin(parent, 7, "Max duration", self.hold_max_duration_var, 0.25, 6.0, 0.05, "sec")
        self._spin(parent, 8, "Minimum gap", self.hold_min_gap_var, 0.0, 6.0, 0.05, "sec")
        parent.columnconfigure(1, weight=1)

    def _build_phrase_grid(self, parent) -> None:
        self._spin(parent, 0, "Phrase length", self.phrase_length_beats_var, 8, 64, 8, "beats")
        self._spin(parent, 1, "8-count block", self.subphrase_length_beats_var, 4, 16, 4, "beats")
        self._spin(parent, 2, "Downbeat offset", self.manual_downbeat_offset_seconds_var, -4.0, 4.0, 0.01, "sec")
        ttk.Checkbutton(parent, text="Allow crooked phrase", variable=self.allow_crooked_phrase_var).grid(row=3, column=1, sticky="w", pady=4)
        ttk.Label(
            parent,
            text="Automatic Director: teach → repeat → mirror → payoff.",
            style="SectionBody.TLabel",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 2))
        parent.columnconfigure(1, weight=1)

    def _build_wall_visuals(self, parent) -> None:
        fields = [
            ("Wall height", "wall_height"),
            ("Wall length Z", "wall_length_z"),
            ("Wall width X", "wall_width_x"),
            ("Wall opacity", "wall_opacity"),
            ("Wall emission", "wall_emission_strength"),
            ("Wall edge glow", "wall_edge_glow"),
            ("Segment count", "wall_segment_count"),
            ("Segment spacing", "wall_segment_spacing"),
            ("Strip emission", "wall_strip_emission"),
            ("Edge emission", "wall_edge_emission"),
        ]
        for row, (label, key) in enumerate(fields):
            low, high = VISUAL_RANGES[key]
            step = 1.0 if key == "wall_segment_count" else 0.25 if key == "wall_length_z" else 0.05 if high <= 10 else 0.1
            self._spin(parent, row, label, self.visual_vars[key], low, high, step)
        start = len(fields)
        for offset, (label, key) in enumerate((("Left wall RGB", "wall_left_color"), ("Right wall RGB", "wall_right_color"))):
            self._entry(parent, start + offset, label, self.color_vars[key])
        parent.columnconfigure(1, weight=1)

    def _build_guidance_preview(self, parent) -> None:
        fields = [
            ("Safe lane glow", "safe_lane_emission"),
            ("Safe lane opacity", "safe_lane_opacity"),
            ("Safe lane flow", "safe_lane_pulse"),
            ("Ring lead", "next_cell_ring_lead_time"),
            ("Ring brightness", "next_cell_ring_brightness"),
            ("Ring fade", "next_cell_ring_fade_duration"),
            ("Camera dodge", "camera_dodge_distance"),
            ("Dodge in", "camera_dodge_in_duration"),
            ("Dodge hold", "camera_dodge_hold"),
            ("Dodge return", "camera_dodge_return_duration"),
            ("Global audio offset ms", "global_audio_offset_ms"),
            ("Visual hit offset ms", "visual_hit_offset_ms"),
        ]
        for row, (label, key) in enumerate(fields):
            low, high = VISUAL_RANGES[key]
            self._spin(parent, row, label, self.visual_vars[key], low, high, 0.05)
        start = len(fields)
        self._entry(parent, start, "Safe lane RGB", self.color_vars["safe_lane_color"])
        self._entry(parent, start + 1, "Ring RGB", self.color_vars["next_cell_ring_color"])
        self._path_row(parent, "Godot", self.godot_var, self._choose_godot, [("Godot", "*.exe"), ("All", "*.*")], row=start + 2)
        parent.columnconfigure(1, weight=1)

    def _build_action_bar(self, parent) -> None:
        bar = ttk.Frame(parent, padding=(0, 12, 0, 0))
        bar.pack(side="bottom", fill="x")
        self.run_button = ttk.Button(bar, text="▶  START ANALYSIS", command=self._start_analyze, style="Primary.TButton")
        self.run_button.pack(side="left")
        self.validate_button = ttk.Button(bar, text="Validate current track", command=self._start_validate)
        self.validate_button.pack(side="left", padx=(8, 0))
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=180)
        self.progress.pack(side="right")
        self.status = tk.StringVar(value="Ready")
        ttk.Label(bar, textvariable=self.status, style="Hint.TLabel").pack(side="right", padx=(8, 12))

    def _gpu_status_text(self, info: dict[str, object]) -> str:
        if info.get("available"):
            return "GPU READY  •  {name}  •  CUDA {cuda}".format(
                name=info.get("name", "CUDA GPU"),
                cuda=info.get("cuda_version", "?"),
            )
        return f"CPU MODE  •  {info.get('reason', 'CUDA unavailable')}"

    def _refresh_gpu_status(self) -> dict[str, object]:
        self._gpu_info = audio_analyzer.demucs_gpu_status()
        self.gpu_status_var.set(self._gpu_status_text(self._gpu_info))
        if hasattr(self, "gpu_label"):
            self.gpu_label.configure(style="GPUReady.TLabel" if self._gpu_info.get("available") else "CPUMode.TLabel")
        return self._gpu_info

    def _grid_row(self, parent, row: int, label: str):
        ttk.Label(parent, text=label, width=18, style="SectionBody.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        holder = ttk.Frame(parent, style="SectionBody.TFrame")
        holder.grid(row=row, column=1, sticky="ew", pady=4)
        parent.columnconfigure(1, weight=1)
        return holder

    def _spin(self, parent, row: int, label: str, variable, low, high, step, suffix: str = "") -> None:
        holder = self._grid_row(parent, row, label)
        ttk.Spinbox(holder, from_=low, to=high, increment=step, textvariable=variable, width=9).pack(side="left")
        if suffix:
            ttk.Label(holder, text=suffix, foreground="#aab8c8", style="SectionBody.TLabel").pack(side="left", padx=(8, 0))

    def _scale(self, parent, row: int, label: str, variable, low: float, high: float, step: float) -> None:
        holder = self._grid_row(parent, row, label)
        ttk.Scale(holder, from_=low, to=high, variable=variable, orient="horizontal", length=220).pack(side="left", fill="x", expand=True)
        ttk.Spinbox(holder, from_=low, to=high, increment=step, textvariable=variable, width=7).pack(side="left", padx=(8, 0))

    def _entry(self, parent, row: int, label: str, variable) -> None:
        holder = self._grid_row(parent, row, label)
        ttk.Entry(holder, textvariable=variable, width=20).pack(side="left", fill="x", expand=True)

    def _path_row(self, parent, label, variable, command, filetypes, row: int | None = None):
        if row is None:
            row = len(parent.grid_slaves())
        ttk.Label(parent, text=label, width=18, style="SectionBody.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=4)
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=2, sticky="e", pady=4)
        parent.columnconfigure(1, weight=1)

    def _choose_audio(self):
        self._choose_open(self.audio_var, Path.cwd() / "reference", [("Audio", "*.wav *.mp3"), ("WAV", "*.wav"), ("MP3", "*.mp3")])

    def _choose_track(self):
        self._choose_save(self.track_var, "neon_track.json", ".json", [("JSON", "*.json")])

    def _choose_godot(self):
        self._choose_open(self.godot_var, Path(self.godot_var.get()).parent, [("Godot", "*.exe"), ("All", "*.*")])

    def _choose_open(self, variable, initialdir, filetypes):
        path = filedialog.askopenfilename(initialdir=str(initialdir), filetypes=filetypes)
        if path:
            variable.set(path)

    def _choose_save(self, variable, initialfile, ext, filetypes):
        path = filedialog.asksaveasfilename(initialdir=str(Path.cwd()), defaultextension=ext, filetypes=filetypes, initialfile=initialfile)
        if path:
            variable.set(path)

    def _start_analyze(self):
        audio = Path(self.audio_var.get().strip())
        if not audio.is_file() or audio.suffix.lower() not in {".wav", ".mp3"}:
            messagebox.showerror("Audio file", "Choose an existing WAV or MP3 file.")
            return
        if float(self.hold_min_duration_var.get()) > float(self.hold_max_duration_var.get()):
            messagebox.showerror("Hold duration", "Minimum hold duration cannot exceed maximum duration.")
            return
        gpu_info = self._refresh_gpu_status()
        analysis_device = "cuda" if gpu_info.get("available") else "cpu"
        options = {
            "difficulty": self.difficulty_var.get(), "ramp_duration": float(self.ramp_duration_var.get()),
            "ramp_strength": float(self.ramp_strength_var.get()), "anti_burst": bool(self.anti_burst_var.get()),
            "max_same_lane_run": int(self.max_lane_run_var.get()), "max_same_side_run": int(self.max_side_run_var.get()),
            "max_simultaneous_feet": int(self.max_simultaneous_feet_var.get()),
            "walls_enabled": bool(self.walls_enabled_var.get()), "wall_duration_beats": int(self.wall_duration_beats_var.get()),
            "wall_min_gap_bars": int(self.wall_min_gap_bars_var.get()), "wall_rate_bars": int(self.wall_rate_bars_var.get()),
            "wall_anticipation": float(self.wall_anticipation_var.get()), "wall_density_multiplier": float(self.wall_density_multiplier_var.get()),
            "wall_preparation_window": float(self.wall_preparation_window_var.get()), "wall_recovery_window": float(self.wall_recovery_window_var.get()),
            "wall_rest_window": float(self.wall_rest_window_var.get()), "holds_enabled": bool(self.holds_enabled_var.get()),
            "high_wall_enabled": bool(self.high_wall_enabled_var.get()),
            "high_wall_target_ratio": float(self.high_wall_target_ratio_var.get()),
            "high_wall_min_gap_bars": int(self.high_wall_min_gap_bars_var.get()),
            "hold_rate_bars": int(self.hold_rate_bars_var.get()), "hold_min_duration": float(self.hold_min_duration_var.get()),
            "hold_max_duration": float(self.hold_max_duration_var.get()), "hold_min_gap": float(self.hold_min_gap_var.get()),
            "reference_hand_holds_enabled": bool(self.reference_hand_holds_enabled_var.get()),
            "reference_hand_hold_rate_phrases": int(self.reference_hand_hold_rate_phrases_var.get()),
            "spectacle_combos_enabled": bool(self.spectacle_combos_enabled_var.get()),
            "phrase_length_beats": int(self.phrase_length_beats_var.get()), "subphrase_length_beats": int(self.subphrase_length_beats_var.get()),
            "manual_downbeat_offset_seconds": float(self.manual_downbeat_offset_seconds_var.get()),
            "allow_crooked_phrase": bool(self.allow_crooked_phrase_var.get()), "lane_layout": self.lane_layout_var.get(),
            "track_path": self.track_var.get().strip(),
            "demucs_device": analysis_device,
        }
        if analysis_device == "cuda":
            analysis_status = f"GPU analysis on {gpu_info.get('name', 'CUDA')}..."
        else:
            analysis_status = "CPU analysis (GPU unavailable)..."
        self._set_busy(True, analysis_status)
        threading.Thread(target=self._analyze_worker, args=(audio, options), daemon=True).start()

    def _analyze_worker(self, audio: Path, options: dict[str, object]):
        try:
            with audio_analyzer.isolated_rhythm_stems(audio, demucs_device=str(options["demucs_device"])) as stems:
                beatmap, timing = audio_analyzer.analyze_with_metadata(
                    stems["mix"],
                    difficulty=options["difficulty"], ramp_duration=options["ramp_duration"], ramp_strength=options["ramp_strength"],
                    anti_burst=options["anti_burst"], max_same_lane_run=options["max_same_lane_run"], max_same_side_run=options["max_same_side_run"],
                    max_simultaneous_feet=options["max_simultaneous_feet"],
                    walls_enabled=options["walls_enabled"], wall_duration_beats=options["wall_duration_beats"],
                    wall_min_gap_bars=options["wall_min_gap_bars"], wall_rate_bars=options["wall_rate_bars"],
                    wall_anticipation=options["wall_anticipation"], wall_density_multiplier=options["wall_density_multiplier"],
                    wall_preparation_window=options["wall_preparation_window"], wall_recovery_window=options["wall_recovery_window"],
                    wall_rest_window=options["wall_rest_window"], holds_enabled=options["holds_enabled"],
                    high_wall_enabled=options["high_wall_enabled"],
                    high_wall_target_ratio=options["high_wall_target_ratio"],
                    high_wall_min_gap_bars=options["high_wall_min_gap_bars"],
                    hold_rate_bars=options["hold_rate_bars"], hold_min_duration=options["hold_min_duration"],
                    hold_max_duration=options["hold_max_duration"], hold_min_gap=options["hold_min_gap"],
                    reference_hand_holds_enabled=options["reference_hand_holds_enabled"],
                    reference_hand_hold_rate_phrases=options["reference_hand_hold_rate_phrases"],
                    spectacle_combos_enabled=options["spectacle_combos_enabled"],
                    phrase_length_beats=options["phrase_length_beats"], subphrase_length_beats=options["subphrase_length_beats"],
                    manual_downbeat_offset_seconds=options["manual_downbeat_offset_seconds"], allow_crooked_phrase=options["allow_crooked_phrase"],
                    bass_audio_path=stems["bass"],
                    drums_audio_path=stems["drums"],
                    music_audio_path=audio,
                    lane_layout=options["lane_layout"],
                )
                track_path = Path(str(options["track_path"]))
                srt_path = track_path.parent / "combo.srt"
                feedback_srt_path = track_path.parent / "feedback.srt"
                track_path.parent.mkdir(parents=True, exist_ok=True)
                timing["audio"] = str(audio.resolve())
                beatmap["audio"] = timing["audio"]
                if isinstance(timing.get("analysis"), dict):
                    timing["analysis"]["source_separation"] = "demucs"
                    timing["analysis"]["separation_model"] = audio_analyzer.DEMUCS_MODEL
                    timing["analysis"]["separation_device"] = str(stems.get("device", "auto"))
                    timing["analysis"]["analyzed_stems"] = ["bass.wav", "drums.wav"]
                    timing["analysis"]["analyzed_mix"] = audio_analyzer.RHYTHM_MIX_FILENAME
                write_neon_track(
                    track_path,
                    build_neon_track(
                        beatmap=beatmap,
                        beat_grid=timing,
                        combo_srt=audio_analyzer.write_srt(
                            beatmap,
                            srt_path,
                            track_end=float(timing.get("duration", 0.0)) or None,
                        ),
                        source="analyzer_gui",
                    ),
                )
                audio_analyzer.write_feedback_srt(
                    beatmap,
                    feedback_srt_path,
                    track_end=float(timing.get("duration", 0.0)) or None,
                )
            diagnostics = timing.get("lane_assignment", {}).get("diagnostics", {})
            wall_summary = timing.get("wall_generation", {})
            hold_summary = timing.get("hold_generation", {})
            hold_count = int(timing.get("hold_count", 0))
            hand_hold_count = sum(str(event.get("movement", "")) == "DOUBLE_HAND_HOLD" for event in beatmap.get("movement_events", []))
            variant_counts = wall_summary.get("variant_counts", {})
            choreography = beatmap.get("choreography_v4", {})
            director = choreography.get("director_plan", {}) if isinstance(choreography, dict) else {}
            director_phrases = len(director.get("directives", [])) if isinstance(director, dict) else 0
            self._queue.put(("ok", "Detected {notes} gameplay notes and {walls} analyzer wall windows ({high_walls} bright high / {low_walls} low corridor); {runtime_walls} remain after V4 movement safety. Double-hand holds: {hand_holds}; legacy floor holds: {holds}. Music-aware sections: {sections}; neural meter: {neural}; peak accents: {peaks}. 32-count Director phrases: {director_phrases}. Strict candidates {strict}/{candidates}. Wall-window accepted prep/active/recovery: {prep}/{active}/{recovery}.\nWrote:\n{track}\n{srt}\n{feedback_srt}\n".format(
                notes=len(audio_analyzer._beatmap_notes(beatmap)),
                walls=wall_summary.get("event_count", 0),
                runtime_walls=wall_summary.get("runtime_event_count", 0),
                high_walls=variant_counts.get("high_side_wall", 0),
                low_walls=variant_counts.get("low_corridor", 0),
                holds=hold_count,
                hand_holds=hand_hold_count,
                sections=len(timing.get("sections", [])),
                neural=bool(timing.get("neural_meter", {}).get("used", False)),
                peaks=timing.get("music_expression", {}).get("summary", {}).get("peak_accent_count", 0),
                director_phrases=director_phrases,
                strict=wall_summary.get("strict_candidate_count", 0),
                candidates=wall_summary.get("candidate_count", 0),
                prep=diagnostics.get("wall_preparation_accepted_notes", 0),
                active=diagnostics.get("wall_active_accepted_notes", 0),
                recovery=diagnostics.get("wall_recovery_accepted_notes", 0),
                track=track_path,
                srt=srt_path,
                feedback_srt=feedback_srt_path,
            )))
        except Exception as exc:
            self._queue.put(("error", f"{type(exc).__name__}: {exc}\n"))

    def _start_validate(self):
        track = Path(self.track_var.get().strip())
        if not track.is_file():
            messagebox.showerror("Track JSON", "Generate or choose an existing neon_track.json first.")
            return
        self._set_busy(True, "Running validation...")
        threading.Thread(target=self._validate_worker, args=(str(track), self.godot_var.get().strip()), daemon=True).start()

    def _validate_worker(self, track: str, godot: str):
        command = [sys.executable, str(PROJECT_DIR / "scripts" / "python" / "validate_lanes.py"), "--track", track, "--godot", godot]
        result = subprocess.run(command, cwd=str(PROJECT_DIR), text=True, encoding="utf-8", errors="replace", capture_output=True)
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        self._queue.put(("ok" if result.returncode == 0 else "error", output or f"Validation exit code {result.returncode}\n"))

    def _set_busy(self, busy: bool, status: str) -> None:
        state = "disabled" if busy else "normal"
        for button in (self.run_button, self.validate_button):
            button.configure(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
        self.status.set(status)

    def _poll_queue(self):
        try:
            kind, payload = self._queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_queue)
            return
        self._set_busy(False, "Complete." if kind == "ok" else "Failed.")
        self._write(str(payload))
        if kind == "error":
            messagebox.showerror("Operation failed", str(payload))
        self.after(100, self._poll_queue)

    def _save_visual_config(self) -> None:
        config = self._load_visual_config()
        config["schema"] = "neon_music.wall_visual.v1"
        for key, variable in self.visual_vars.items():
            low, high = VISUAL_RANGES[key]
            value = max(low, min(high, float(variable.get())))
            config[key] = round(value, 6)
        for key, variable in self.color_vars.items():
            config[key] = self._parse_rgb(variable.get())
        config["camera_dodge_easing"] = str(config.get("camera_dodge_easing", VISUAL_DEFAULTS["camera_dodge_easing"]))
        config["safe_ranges"] = VISUAL_RANGES
        config.setdefault("calibration_frames", [
            {"time": 25.0, "role": "right wall / cyan-magenta full-height reference"},
            {"time": 75.0, "role": "left wall / high cyan span reference"},
            {"time": 86.0, "role": "left wall / magenta-blue glow reference"},
            {"time": 96.0, "role": "right wall / blue-violet glow reference"},
        ])
        WALL_VISUAL_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def _save_visual_config_from_ui(self) -> None:
        try:
            self._save_visual_config()
            self.status.set("Visual settings saved")
        except Exception as exc:
            messagebox.showerror("Visual settings", f"{type(exc).__name__}: {exc}")

    def run_scroll_smoke(self, screenshot_path: Path) -> str:
        self.update_idletasks()
        if len(self.notebook.tabs()) != 4:
            raise RuntimeError("Expected four workflow tabs.")
        for tab in self.notebook.tabs():
            self.notebook.select(tab)
            self.update_idletasks()
        # Leave the smoke capture on the controls changed by this workflow.
        self.notebook.select(self.notebook.tabs()[1])
        self.update_idletasks()
        if not self.run_button.winfo_viewable() or not self.validate_button.winfo_viewable():
            raise RuntimeError("Sticky action bar is not visible.")
        window_bottom = self.winfo_rooty() + self.winfo_height()
        action_bottom = self.run_button.winfo_rooty() + self.run_button.winfo_height()
        if action_bottom > window_bottom:
            raise RuntimeError("Sticky action bar is outside the window bounds.")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import ImageGrab
            self.attributes("-topmost", True)
            self.lift()
            self.focus_force()
            for _ in range(3):
                self.update()
                time.sleep(0.12)
            x0, y0 = self.winfo_rootx(), self.winfo_rooty()
            x1, y1 = x0 + self.winfo_width(), y0 + self.winfo_height()
            ImageGrab.grab(bbox=(x0, y0, x1, y1)).save(screenshot_path)
            self.attributes("-topmost", False)
            shot = str(screenshot_path)
        except Exception as exc:
            try:
                self.attributes("-topmost", False)
            except tk.TclError:
                pass
            shot = f"screenshot skipped: {type(exc).__name__}: {exc}"
        return f"GUI smoke: OK (workflow tabs reachable, sticky actions visible; {shot})"

    def _format_rgb(self, value) -> str:
        if isinstance(value, list) and len(value) >= 3:
            return ", ".join(f"{max(0.0, min(1.0, float(channel))):.3f}" for channel in value[:3])
        return "0.720, 1.000, 1.000"

    def _parse_rgb(self, text: str) -> list[float]:
        parts = [part.strip() for part in text.replace(";", ",").split(",")]
        if len(parts) < 3:
            raise ValueError("RGB fields require three comma-separated 0..1 values.")
        return [round(max(0.0, min(1.0, float(part))), 6) for part in parts[:3]]

    def _write(self, text):
        self.log.insert("end", text)
        self.log.see("end")


def run_gui_smoke_cli(screenshot: Path) -> int:
    app = AnalyzerApp()
    app.update()
    time.sleep(0.2)
    app.update()
    print(app.run_scroll_smoke(screenshot))
    app.destroy()
    return 0


if __name__ == "__main__":
    if "--gui-smoke" in sys.argv:
        if "--screenshot" in sys.argv:
            index = sys.argv.index("--screenshot")
            screenshot_path = Path(sys.argv[index + 1]) if index + 1 < len(sys.argv) else PROJECT_DIR / "output" / "previews" / "analyzer_gui_scrollbar.png"
        else:
            screenshot_path = PROJECT_DIR / "output" / "previews" / "analyzer_gui_scrollbar.png"
        raise SystemExit(run_gui_smoke_cli(screenshot_path))
    AnalyzerApp().mainloop()
