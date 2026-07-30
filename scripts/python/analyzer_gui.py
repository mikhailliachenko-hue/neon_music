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
from lane_assignment import (
    DEFAULT_DIFFICULTY,
    DEFAULT_MAX_SAME_LANE_RUN,
    DEFAULT_MAX_SAME_SIDE_RUN,
    DEFAULT_HOLD_ENABLED,
    DEFAULT_HOLD_MAX_DURATION,
    DEFAULT_HOLD_MIN_DURATION,
    DEFAULT_HOLD_MIN_GAP,
    DEFAULT_HOLD_RATE_BARS,
    DEFAULT_RAMP_DURATION,
    DEFAULT_RAMP_STRENGTH,
    DEFAULT_WALL_ANTICIPATION,
    DEFAULT_WALL_DENSITY_MULTIPLIER,
    DEFAULT_WALL_DURATION_BEATS,
    DEFAULT_WALL_ENABLED,
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
    "safe_lane_emission": 3.8,
    "safe_lane_opacity": 0.18,
    "safe_lane_pulse": 0.35,
    "next_cell_ring_lead_time": 1.25,
    "next_cell_ring_brightness": 0.9,
    "next_cell_ring_fade_duration": 0.32,
    "camera_dodge_distance": 1.05,
    "camera_dodge_in_duration": 0.55,
    "camera_dodge_hold": 0.25,
    "camera_dodge_return_duration": 0.7,
    "camera_dodge_easing": "sine",
    "global_audio_offset_ms": 28.0,
    "visual_hit_offset_ms": 0.0,
    "wall_left_color": [0.196, 1.0, 1.0],
    "wall_right_color": [0.49, 0.0, 0.90],
    "safe_lane_color": [1.0, 0.78, 0.12],
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


class AccordionSection(ttk.Frame):
    def __init__(self, parent, title: str, expanded: bool = True) -> None:
        super().__init__(parent)
        self._expanded = tk.BooleanVar(value=expanded)
        self._button = ttk.Button(self, text="", command=self.toggle, style="Section.TButton")
        self._button.pack(fill="x", pady=(8, 0))
        self.body = ttk.Frame(self, padding=(12, 10, 12, 8), style="SectionBody.TFrame")
        self._title = title
        self._sync()

    def toggle(self) -> None:
        self._expanded.set(not self._expanded.get())
        self._sync()

    def expand(self) -> None:
        self._expanded.set(True)
        self._sync()

    def collapse(self) -> None:
        self._expanded.set(False)
        self._sync()

    def _sync(self) -> None:
        self._button.configure(text=("[v] " if self._expanded.get() else "[>] ") + self._title)
        if self._expanded.get():
            self.body.pack(fill="x")
        else:
            self.body.pack_forget()


class AnalyzerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        try:
            self.tk.call("tk", "scaling", max(1.0, self.winfo_fpixels("1i") / 72.0))
        except tk.TclError:
            pass
        self.title("Neon Footstep - Audio Analyzer")
        self.geometry("860x680")
        self.minsize(700, 500)
        self.configure(bg="#10131c")
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.sections: dict[str, AccordionSection] = {}
        self._visual_config = self._load_visual_config()
        self._build_vars()
        self._build_ui()
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
        self.audio_var = tk.StringVar(value=str(project / "assets" / "audio" / "Iron & Ash.mp3"))
        self.beatmap_var = tk.StringVar(value=str(project / "output" / "beatmap.json"))
        self.metadata_var = tk.StringVar(value=str(project / "output" / "beat_grid.json"))
        self.srt_var = tk.StringVar(value=str(project / "output" / "combo.srt"))
        self.difficulty_var = tk.StringVar(value=DEFAULT_DIFFICULTY)
        self.ramp_duration_var = tk.DoubleVar(value=DEFAULT_RAMP_DURATION)
        self.ramp_strength_var = tk.DoubleVar(value=DEFAULT_RAMP_STRENGTH)
        self.anti_burst_var = tk.BooleanVar(value=True)
        self.max_lane_run_var = tk.IntVar(value=DEFAULT_MAX_SAME_LANE_RUN)
        self.max_side_run_var = tk.IntVar(value=DEFAULT_MAX_SAME_SIDE_RUN)
        self.walls_enabled_var = tk.BooleanVar(value=DEFAULT_WALL_ENABLED)
        self.wall_duration_beats_var = tk.IntVar(value=DEFAULT_WALL_DURATION_BEATS)
        self.wall_min_gap_bars_var = tk.IntVar(value=DEFAULT_WALL_MIN_GAP_BARS)
        self.wall_rate_bars_var = tk.IntVar(value=DEFAULT_WALL_RATE_BARS)
        self.wall_anticipation_var = tk.DoubleVar(value=DEFAULT_WALL_ANTICIPATION)
        self.wall_density_multiplier_var = tk.DoubleVar(value=DEFAULT_WALL_DENSITY_MULTIPLIER)
        self.wall_preparation_window_var = tk.DoubleVar(value=DEFAULT_WALL_PREPARATION_WINDOW)
        self.wall_recovery_window_var = tk.DoubleVar(value=DEFAULT_WALL_RECOVERY_WINDOW)
        self.wall_rest_window_var = tk.DoubleVar(value=DEFAULT_WALL_REST_WINDOW)
        self.holds_enabled_var = tk.BooleanVar(value=DEFAULT_HOLD_ENABLED)
        self.hold_rate_bars_var = tk.IntVar(value=DEFAULT_HOLD_RATE_BARS)
        self.hold_min_duration_var = tk.DoubleVar(value=DEFAULT_HOLD_MIN_DURATION)
        self.hold_max_duration_var = tk.DoubleVar(value=DEFAULT_HOLD_MAX_DURATION)
        self.hold_min_gap_var = tk.DoubleVar(value=DEFAULT_HOLD_MIN_GAP)
        self.phrase_length_beats_var = tk.IntVar(value=32)
        self.subphrase_length_beats_var = tk.IntVar(value=8)
        self.manual_downbeat_offset_seconds_var = tk.DoubleVar(value=0.0)
        self.allow_crooked_phrase_var = tk.BooleanVar(value=False)
        self.phrase_candidate_var = tk.StringVar(value="0")
        self.manual_movement_var = tk.StringVar(value="MARCH")
        self.manual_cue_var = tk.StringVar(value="ALTERNATING_FOOT_PULSES")
        self.godot_var = tk.StringVar(value=DEFAULT_GODOT)
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
        style.configure("Section.TButton", font=("Segoe UI", 10, "bold"), padding=(10, 7), anchor="w")
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 6))
        style.configure("TEntry", fieldbackground="#1b2231", foreground="#ffffff")
        style.configure("TCheckbutton", background="#131a27", foreground="#e9f5ff")
        style.configure("TRadiobutton", background="#131a27", foreground="#e9f5ff")

        shell = ttk.Frame(self, padding=(18, 16, 18, 14))
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="NEON FOOTSTEP", style="Title.TLabel").pack(anchor="w")
        ttk.Label(shell, text="Audio -> beatmap.json + beat_grid.json + combo.srt", style="Hint.TLabel").pack(anchor="w", pady=(0, 10))

        scroller = ttk.Frame(shell)
        scroller.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(scroller, bg="#10131c", highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(scroller, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.content = ttk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_mousewheel(self.canvas)

        self._section("Files", self._build_files, expanded=True)
        self._section("Difficulty & Ramp", self._build_difficulty, expanded=True)
        self._section("Note Patterns & Safety", self._build_note_safety, expanded=True)
        self._section("Wall Timing", self._build_wall_timing, expanded=True)
        self._section("Hold Notes", self._build_hold_notes, expanded=True)
        self._section("Phrase Grid V2", self._build_phrase_grid, expanded=True)
        self._section("Phrase Editor V3", self._build_phrase_editor, expanded=False)
        self._section("Wall Visuals", self._build_wall_visuals, expanded=False)
        self._section("Guidance & Preview", self._build_guidance_preview, expanded=False)
        self._section("Generate & Validation", self._build_generate_validate, expanded=True)

    def _section(self, title: str, builder, expanded: bool) -> None:
        section = AccordionSection(self.content, title, expanded=expanded)
        section.pack(fill="x", pady=(0, 2))
        self.sections[title] = section
        builder(section.body)

    def _on_content_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _bind_mousewheel(self, widget) -> None:
        widget.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind_all("<Button-4>", lambda _event: self.canvas.yview_scroll(-3, "units"), add="+")
        widget.bind_all("<Button-5>", lambda _event: self.canvas.yview_scroll(3, "units"), add="+")

    def _on_mousewheel(self, event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_files(self, parent) -> None:
        self._path_row(parent, "Audio", self.audio_var, self._choose_audio, [("Audio", "*.wav *.mp3"), ("WAV", "*.wav"), ("MP3", "*.mp3")])
        self._path_row(parent, "Beatmap", self.beatmap_var, self._choose_beatmap, [("JSON", "*.json")])
        self._path_row(parent, "Metadata", self.metadata_var, self._choose_metadata, [("JSON", "*.json")])
        self._path_row(parent, "Subtitles", self.srt_var, self._choose_srt, [("SubRip", "*.srt")])

    def _build_difficulty(self, parent) -> None:
        row = self._grid_row(parent, 0, "Difficulty")
        for name in DIFFICULTY_PROFILES:
            ttk.Radiobutton(row, text=name, value=name, variable=self.difficulty_var).pack(side="left", padx=(0, 14))
        self._spin(parent, 1, "Ramp duration", self.ramp_duration_var, 0, 90, 1, "sec")
        self._scale(parent, 2, "Ramp strength", self.ramp_strength_var, 0.0, 1.0, 0.05)

    def _build_note_safety(self, parent) -> None:
        ttk.Checkbutton(parent, text="Anti-burst protection", variable=self.anti_burst_var).grid(row=0, column=1, sticky="w", pady=4)
        self._spin(parent, 1, "Max lane run", self.max_lane_run_var, 1, 8, 1)
        self._spin(parent, 2, "Max side run", self.max_side_run_var, 1, 12, 1)
        self._spin(parent, 3, "Wall density brake", self.wall_density_multiplier_var, 1.0, 5.0, 0.05, "x")
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
        parent.columnconfigure(1, weight=1)

    def _build_hold_notes(self, parent) -> None:
        ttk.Checkbutton(parent, text="Enable hold notes", variable=self.holds_enabled_var).grid(row=0, column=1, sticky="w", pady=4)
        self._spin(parent, 1, "Rate", self.hold_rate_bars_var, 2, 32, 1, "bars")
        self._spin(parent, 2, "Min duration", self.hold_min_duration_var, 0.25, 4.0, 0.05, "sec")
        self._spin(parent, 3, "Max duration", self.hold_max_duration_var, 0.25, 6.0, 0.05, "sec")
        self._spin(parent, 4, "Minimum gap", self.hold_min_gap_var, 0.0, 6.0, 0.05, "sec")
        parent.columnconfigure(1, weight=1)

    def _build_phrase_grid(self, parent) -> None:
        self._spin(parent, 0, "Phrase length", self.phrase_length_beats_var, 8, 64, 8, "beats")
        self._spin(parent, 1, "8-count block", self.subphrase_length_beats_var, 4, 16, 4, "beats")
        self._spin(parent, 2, "Downbeat offset", self.manual_downbeat_offset_seconds_var, -4.0, 4.0, 0.01, "sec")
        ttk.Checkbutton(parent, text="Allow crooked phrase", variable=self.allow_crooked_phrase_var).grid(row=3, column=1, sticky="w", pady=4)
        parent.columnconfigure(1, weight=1)

    def _build_phrase_editor(self, parent) -> None:
        columns = ("template", "movement", "side", "beats", "cue", "lead")
        self.phrase_tree = ttk.Treeview(parent, columns=columns, show="tree headings", height=8)
        self.phrase_tree.heading("#0", text="8/32 boundary / phrase")
        for key, title, width in (("template", "Template", 150), ("movement", "Movement ID", 140), ("side", "Side", 60), ("beats", "Beats", 50), ("cue", "Cue archetype", 170), ("lead", "Lead", 45)):
            self.phrase_tree.heading(key, text=title); self.phrase_tree.column(key, width=width, stretch=True)
        self.phrase_tree.grid(row=0, column=0, columnspan=4, sticky="nsew", pady=(0, 6))
        bar = ttk.Frame(parent, style="SectionBody.TFrame"); bar.grid(row=1, column=0, columnspan=4, sticky="ew")
        for text, command in (("Refresh", self._refresh_phrase_editor), ("Mirror Phrase", self._mirror_phrase), ("Regenerate Phrase", self._regenerate_phrase), ("Lock Phrase", self._lock_phrase)):
            ttk.Button(bar, text=text, command=command).pack(side="left", padx=(0, 5))
        ttk.Label(parent, text="Candidate", style="SectionBody.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Combobox(parent, textvariable=self.phrase_candidate_var, values=[str(i) for i in range(8)], width=8).grid(row=2, column=1, sticky="w")
        ttk.Label(parent, text="Movement / cue", style="SectionBody.TLabel").grid(row=3, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.manual_movement_var, width=24).grid(row=3, column=1, sticky="ew")
        ttk.Entry(parent, textvariable=self.manual_cue_var, width=28).grid(row=3, column=2, sticky="ew")
        ttk.Button(parent, text="Apply", command=self._apply_manual_movement).grid(row=3, column=3, sticky="e")
        self.phrase_warnings = tk.Listbox(parent, height=4, bg="#0a0d14", fg="#ffd36f")
        self.phrase_warnings.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(6, 0)); parent.columnconfigure(2, weight=1)

    def _phrase_payloads(self):
        metadata = Path(self.metadata_var.get()); beatmap = Path(self.beatmap_var.get())
        if not metadata.is_file() or not beatmap.is_file(): return None, None
        return json.loads(metadata.read_text(encoding="utf-8-sig")), json.loads(beatmap.read_text(encoding="utf-8-sig"))

    def _selected_phrase_id(self):
        selection = self.phrase_tree.selection()
        if not selection: return ""
        item = selection[0]
        while self.phrase_tree.parent(item): item = self.phrase_tree.parent(item)
        return item

    def _refresh_phrase_editor(self):
        timing, _ = self._phrase_payloads()
        if timing is None: return
        self.phrase_tree.delete(*self.phrase_tree.get_children()); self.phrase_warnings.delete(0, "end")
        events = timing.get("movement_events", [])
        for phrase in timing.get("phrase_grid", {}).get("phrases", []):
            pid = phrase.get("id", ""); root = self.phrase_tree.insert("", "end", iid=pid, text=f"32 | {pid}", values=(phrase.get("template", ""), "", "", 32, "", ""))
            for event in [e for e in events if e.get("phrase_id") == pid]:
                self.phrase_tree.insert(root, "end", text=f"8:{event.get('count8_index', 0)+1}", values=(event.get("block_role", ""), event.get("movement", ""), event.get("side", ""), event.get("duration_beats", ""), event.get("cue_archetype", ""), event.get("lead_beats", "")))
            if phrase.get("left_right_balance", {}).get("difference_ratio", 0) > .20: self.phrase_warnings.insert("end", f"{pid}: left/right asymmetry")

    def _mutate_selected_phrase(self, mutator):
        timing, beatmap = self._phrase_payloads(); pid = self._selected_phrase_id()
        if timing is None or not pid: return
        mutator(timing, beatmap, pid)
        Path(self.metadata_var.get()).write_text(json.dumps(timing, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        Path(self.beatmap_var.get()).write_text(json.dumps(beatmap, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        self._refresh_phrase_editor()

    def _mirror_phrase(self):
        def apply(timing, beatmap, pid):
            library=timing.get("movement_library",{}).get("movements",{})
            for doc in (timing, beatmap):
                for event in doc.get("movement_events",[]):
                    if event.get("phrase_id")==pid:
                        movement=library.get(event.get("movement"),{}).get("mirror_id",event.get("movement")); event["movement"]=movement; event["side"]=library.get(movement,{}).get("side","center"); event["cue_archetype"]=library.get(movement,{}).get("cue_archetype",event.get("cue_archetype"))
        self._mutate_selected_phrase(apply)

    def _lock_phrase(self):
        def apply(timing, beatmap, pid):
            for doc in (timing, beatmap):
                for phrase in doc.get("phrase_grid",{}).get("phrases",[]):
                    if phrase.get("id")==pid: phrase["locked"]=not phrase.get("locked",False)
        self._mutate_selected_phrase(apply)

    def _regenerate_phrase(self):
        def apply(timing, beatmap, pid):
            for doc in (timing, beatmap):
                for phrase in doc.get("phrase_grid",{}).get("phrases",[]):
                    if phrase.get("id")==pid and not phrase.get("locked",False): phrase["selected_candidate"]=int(self.phrase_candidate_var.get())
        self._mutate_selected_phrase(apply)

    def _apply_manual_movement(self):
        def apply(timing, beatmap, pid):
            for doc in (timing, beatmap):
                target=next((e for e in doc.get("movement_events",[]) if e.get("phrase_id")==pid),None)
                if target: target["movement"]=self.manual_movement_var.get().strip(); target["cue_archetype"]=self.manual_cue_var.get().strip()
        self._mutate_selected_phrase(apply)

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
            ("Safe lane pulse", "safe_lane_pulse"),
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

    def _build_generate_validate(self, parent) -> None:
        buttons = ttk.Frame(parent, style="SectionBody.TFrame")
        buttons.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.run_button = ttk.Button(buttons, text="Analyze", command=self._start_analyze)
        self.run_button.pack(side="left", padx=(0, 8))
        self.validate_button = ttk.Button(buttons, text="Validate", command=self._start_validate)
        self.validate_button.pack(side="left", padx=(0, 8))
        self.gui_smoke_button = ttk.Button(buttons, text="GUI smoke", command=self._run_gui_smoke_button)
        self.gui_smoke_button.pack(side="left")
        self.progress = ttk.Progressbar(parent, mode="indeterminate", length=180)
        self.progress.grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(parent, textvariable=self.status, style="SectionBody.TLabel").grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(0, 8))
        self.log = tk.Text(parent, height=9, bg="#0a0d14", fg="#c5f8ff", insertbackground="white", relief="flat", padx=10, pady=8, wrap="word")
        self.log.grid(row=2, column=0, columnspan=3, sticky="nsew")
        parent.rowconfigure(2, weight=1)
        parent.columnconfigure(1, weight=1)
        self._write("Ready. Wall timing now uses strict low-onset/low-energy rest windows.\n")

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

    def _choose_beatmap(self):
        self._choose_save(self.beatmap_var, "beatmap.json", ".json", [("JSON", "*.json")])

    def _choose_metadata(self):
        self._choose_save(self.metadata_var, "beat_grid.json", ".json", [("JSON", "*.json")])

    def _choose_srt(self):
        self._choose_save(self.srt_var, "combo.srt", ".srt", [("SubRip subtitles", "*.srt")])

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
        self._set_busy(True, "Analyzing onsets...")
        threading.Thread(target=self._analyze_worker, args=(audio,), daemon=True).start()

    def _analyze_worker(self, audio: Path):
        try:
            self._save_visual_config()
            with audio_analyzer.isolated_rhythm_stems(audio) as stems:
                beatmap, timing = audio_analyzer.analyze_with_metadata(
                    stems["mix"],
                    difficulty=self.difficulty_var.get(),
                    ramp_duration=float(self.ramp_duration_var.get()),
                    ramp_strength=float(self.ramp_strength_var.get()),
                    anti_burst=bool(self.anti_burst_var.get()),
                    max_same_lane_run=int(self.max_lane_run_var.get()),
                    max_same_side_run=int(self.max_side_run_var.get()),
                    walls_enabled=bool(self.walls_enabled_var.get()),
                    wall_duration_beats=int(self.wall_duration_beats_var.get()),
                    wall_min_gap_bars=int(self.wall_min_gap_bars_var.get()),
                    wall_rate_bars=int(self.wall_rate_bars_var.get()),
                    wall_anticipation=float(self.wall_anticipation_var.get()),
                    wall_density_multiplier=float(self.wall_density_multiplier_var.get()),
                    wall_preparation_window=float(self.wall_preparation_window_var.get()),
                    wall_recovery_window=float(self.wall_recovery_window_var.get()),
                    wall_rest_window=float(self.wall_rest_window_var.get()),
                    holds_enabled=bool(self.holds_enabled_var.get()),
                    hold_rate_bars=int(self.hold_rate_bars_var.get()),
                    hold_min_duration=float(self.hold_min_duration_var.get()),
                    hold_max_duration=float(self.hold_max_duration_var.get()),
                    hold_min_gap=float(self.hold_min_gap_var.get()),
                    phrase_length_beats=int(self.phrase_length_beats_var.get()),
                    subphrase_length_beats=int(self.subphrase_length_beats_var.get()),
                    manual_downbeat_offset_seconds=float(self.manual_downbeat_offset_seconds_var.get()),
                    allow_crooked_phrase=bool(self.allow_crooked_phrase_var.get()),
                    bass_audio_path=stems["bass"],
                    drums_audio_path=stems["drums"],
                )
                beatmap_path = Path(self.beatmap_var.get())
                metadata_path = Path(self.metadata_var.get())
                subtitles_path = Path(self.srt_var.get())
                for out_path in (beatmap_path, metadata_path, subtitles_path):
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                timing["audio"] = str(audio.resolve())
                beatmap["audio"] = timing["audio"]
                if isinstance(timing.get("analysis"), dict):
                    timing["analysis"]["source_separation"] = "demucs"
                    timing["analysis"]["separation_model"] = audio_analyzer.DEMUCS_MODEL
                    timing["analysis"]["separation_device"] = str(stems.get("device", "auto"))
                    timing["analysis"]["analyzed_stems"] = ["bass.wav", "drums.wav"]
                    timing["analysis"]["analyzed_mix"] = audio_analyzer.RHYTHM_MIX_FILENAME
                beatmap_path.write_text(json.dumps(beatmap, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                metadata_path.write_text(json.dumps(timing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                audio_analyzer.write_srt(beatmap, subtitles_path)
            diagnostics = timing.get("lane_assignment", {}).get("diagnostics", {})
            wall_summary = timing.get("wall_generation", {})
            hold_summary = timing.get("hold_generation", {})
            hold_count = int(timing.get("hold_count", 0))
            self._queue.put(("ok", "Detected {notes} notes, {walls} wall events, and {holds} hold events. Strict candidates {strict}/{candidates}. Wall-window accepted prep/active/recovery: {prep}/{active}/{recovery}.\nWrote:\n{beatmap}\n{metadata}\n{subtitles}\n".format(
                notes=len(audio_analyzer._beatmap_notes(beatmap)),
                walls=len([event for event in audio_analyzer._beatmap_events(beatmap) if str(event.get("type", "")) in audio_analyzer.WALL_EVENT_TYPES]),
                holds=hold_count,
                strict=wall_summary.get("strict_candidate_count", 0),
                candidates=wall_summary.get("candidate_count", 0),
                prep=diagnostics.get("wall_preparation_accepted_notes", 0),
                active=diagnostics.get("wall_active_accepted_notes", 0),
                recovery=diagnostics.get("wall_recovery_accepted_notes", 0),
                beatmap=beatmap_path,
                metadata=metadata_path,
                subtitles=subtitles_path,
            )))
        except Exception as exc:
            self._queue.put(("error", f"{type(exc).__name__}: {exc}\n"))

    def _start_validate(self):
        self._set_busy(True, "Running validation...")
        threading.Thread(target=self._validate_worker, daemon=True).start()

    def _validate_worker(self):
        command = [sys.executable, str(PROJECT_DIR / "scripts" / "python" / "validate_lanes.py"), "--godot", self.godot_var.get().strip()]
        result = subprocess.run(command, cwd=str(PROJECT_DIR), text=True, encoding="utf-8", errors="replace", capture_output=True)
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        self._queue.put(("ok" if result.returncode == 0 else "error", output or f"Validation exit code {result.returncode}\n"))

    def _run_gui_smoke_button(self):
        try:
            path = PROJECT_DIR / "output" / "previews" / "analyzer_gui_scrollbar.png"
            result = self.run_scroll_smoke(path)
            self._write(result + "\n")
            self.status.set("GUI smoke complete.")
        except Exception as exc:
            messagebox.showerror("GUI smoke failed", f"{type(exc).__name__}: {exc}")

    def _set_busy(self, busy: bool, status: str) -> None:
        state = "disabled" if busy else "normal"
        for button in (self.run_button, self.validate_button, self.gui_smoke_button):
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

    def run_scroll_smoke(self, screenshot_path: Path) -> str:
        for title in ("Hold Notes", "Wall Visuals", "Guidance & Preview"):
            self.sections[title].expand()
        self.update_idletasks()
        scrollregion = self.canvas.bbox("all")
        if scrollregion is None or scrollregion[3] <= self.canvas.winfo_height():
            raise RuntimeError("Scroll region is not taller than the visible canvas.")
        self.canvas.yview_moveto(1.0)
        self.update_idletasks()
        if self.canvas.yview()[1] < 0.95:
            raise RuntimeError("Canvas did not scroll to the lower controls.")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import ImageGrab
            self.lift()
            self.focus_force()
            for _ in range(3):
                self.update()
                time.sleep(0.12)
            x0, y0 = self.winfo_rootx(), self.winfo_rooty()
            x1, y1 = x0 + self.winfo_width(), y0 + self.winfo_height()
            ImageGrab.grab(bbox=(x0, y0, x1, y1)).save(screenshot_path)
            shot = str(screenshot_path)
        except Exception as exc:
            shot = f"screenshot skipped: {type(exc).__name__}: {exc}"
        return f"GUI smoke: OK (scrollbar visible, sections opened, lower controls reached; {shot})"

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
