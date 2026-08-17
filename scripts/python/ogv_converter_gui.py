from __future__ import annotations

import os
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import BooleanVar, IntVar, StringVar, Tk, filedialog, messagebox, ttk


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_FFMPEG = (
    PROJECT_ROOT
    / "third_party"
    / "ffmpeg"
    / "ffmpeg-master-latest-win64-lgpl"
    / "bin"
    / "ffmpeg.exe"
)


def find_ffmpeg() -> str:
    if LOCAL_FFMPEG.exists():
        return str(LOCAL_FFMPEG)
    return "ffmpeg"


def default_output_path(input_path: Path) -> Path:
    asset_background_dir = PROJECT_ROOT / "assets" / "images" / "background"
    if asset_background_dir.exists():
        return asset_background_dir / f"{input_path.stem}.ogv"
    backgrounds_dir = PROJECT_ROOT / "backgrounds"
    if backgrounds_dir.exists():
        return backgrounds_dir / f"{input_path.stem}.ogv"
    return input_path.with_suffix(".ogv")


class OgvConverterApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("MP4 -> OGV converter for Godot")
        self.root.minsize(680, 420)

        self.input_var = StringVar()
        self.output_var = StringVar()
        self.quality_var = IntVar(value=7)
        self.audio_var = BooleanVar(value=False)
        self.overwrite_var = BooleanVar(value=False)
        self.status_var = StringVar(value="Choose an MP4/MOV/WebM file and convert it to Godot-friendly .ogv.")

        self.messages: queue.Queue[tuple[str, str]] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.worker: threading.Thread | None = None

        self._build_ui()
        self.root.after(120, self._poll_messages)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(8, weight=1)

        ttk.Label(frame, text="Source video").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(frame, textvariable=self.input_var).grid(row=0, column=1, sticky="ew", padx=8, pady=(0, 6))
        ttk.Button(frame, text="Browse...", command=self.browse_input).grid(row=0, column=2, pady=(0, 6))

        ttk.Label(frame, text="Output .ogv").grid(row=1, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(frame, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 6))
        ttk.Button(frame, text="Save as...", command=self.browse_output).grid(row=1, column=2, pady=(0, 6))

        ttk.Label(frame, text="Video quality").grid(row=2, column=0, sticky="w", pady=(8, 4))
        quality_row = ttk.Frame(frame)
        quality_row.grid(row=2, column=1, sticky="ew", padx=8, pady=(8, 4))
        quality_row.columnconfigure(0, weight=1)
        ttk.Scale(
            quality_row,
            from_=1,
            to=10,
            orient="horizontal",
            variable=self.quality_var,
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(quality_row, textvariable=self.quality_var, width=3).grid(row=0, column=1, padx=(8, 0))

        options = ttk.Frame(frame)
        options.grid(row=3, column=1, sticky="w", padx=8, pady=(2, 10))
        ttk.Checkbutton(options, text="Include audio", variable=self.audio_var).pack(side="left")
        ttk.Checkbutton(options, text="Overwrite existing file", variable=self.overwrite_var).pack(side="left", padx=(20, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=1, sticky="w", padx=8, pady=(0, 10))
        self.convert_button = ttk.Button(buttons, text="Convert to OGV", command=self.start_conversion)
        self.convert_button.pack(side="left")
        self.cancel_button = ttk.Button(buttons, text="Cancel", command=self.cancel_conversion, state="disabled")
        self.cancel_button.pack(side="left", padx=(8, 0))

        ttk.Label(frame, textvariable=self.status_var).grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 4))

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(frame, text="FFmpeg output").grid(row=7, column=0, columnspan=3, sticky="w")
        log_frame = ttk.Frame(frame)
        log_frame.grid(row=8, column=0, columnspan=3, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log = tkinter_text_widget(log_frame)
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

    def browse_input(self) -> None:
        filename = filedialog.askopenfilename(
            title="Choose source video",
            initialdir=str(PROJECT_ROOT),
            filetypes=[
                ("Video files", "*.mp4 *.mov *.mkv *.webm *.avi *.m4v"),
                ("All files", "*.*"),
            ],
        )
        if not filename:
            return
        path = Path(filename)
        self.input_var.set(str(path))
        self.output_var.set(str(default_output_path(path)))

    def browse_output(self) -> None:
        initial = Path(self.output_var.get()) if self.output_var.get() else PROJECT_ROOT / "backgrounds" / "background.ogv"
        filename = filedialog.asksaveasfilename(
            title="Save OGV as",
            initialdir=str(initial.parent),
            initialfile=initial.name,
            defaultextension=".ogv",
            filetypes=[("Ogg Theora video", "*.ogv"), ("All files", "*.*")],
        )
        if filename:
            self.output_var.set(str(Path(filename)))

    def start_conversion(self) -> None:
        input_path = Path(self.input_var.get().strip('" '))
        output_path = Path(self.output_var.get().strip('" '))

        if not input_path.exists():
            messagebox.showerror("Input missing", "Choose an existing video file first.")
            return
        if output_path.suffix.lower() != ".ogv":
            output_path = output_path.with_suffix(".ogv")
            self.output_var.set(str(output_path))
        if output_path.exists() and not self.overwrite_var.get():
            messagebox.showerror("Output exists", "Enable overwrite or choose another output filename.")
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        args = [
            find_ffmpeg(),
            "-hide_banner",
            "-y" if self.overwrite_var.get() else "-n",
            "-i",
            str(input_path),
            "-c:v",
            "libtheora",
            "-q:v",
            str(max(1, min(10, self.quality_var.get()))),
        ]
        if self.audio_var.get():
            args.extend(["-c:a", "libvorbis", "-q:a", "4"])
        else:
            args.append("-an")
        args.append(str(output_path))

        self._set_running(True)
        self._clear_log()
        self._log_line("Running:\n" + subprocess.list2cmdline(args) + "\n")

        self.worker = threading.Thread(target=self._run_ffmpeg, args=(args, output_path), daemon=True)
        self.worker.start()

    def cancel_conversion(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status_var.set("Cancelling...")

    def _run_ffmpeg(self, args: list[str], output_path: Path) -> None:
        try:
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except FileNotFoundError:
            self.messages.put(("error", "ffmpeg.exe was not found. Put it in third_party/ffmpeg or install ffmpeg in PATH."))
            return
        except Exception as exc:
            self.messages.put(("error", f"Could not start ffmpeg: {exc}"))
            return

        assert self.process.stdout is not None
        for line in self.process.stdout:
            self.messages.put(("log", line))
            match = re.search(r"time=(\d+:\d+:\d+(?:\.\d+)?)", line)
            if match:
                self.messages.put(("status", f"Converting... {match.group(1)}"))

        code = self.process.wait()
        if code == 0:
            self.messages.put(("done", f"Done: {output_path}"))
        else:
            self.messages.put(("error", f"FFmpeg exited with code {code}. Check the log above."))

    def _poll_messages(self) -> None:
        while True:
            try:
                kind, payload = self.messages.get_nowait()
            except queue.Empty:
                break

            if kind == "log":
                self._log_line(payload)
            elif kind == "status":
                self.status_var.set(payload)
            elif kind == "done":
                self.status_var.set(payload)
                self._set_running(False)
                messagebox.showinfo("Conversion complete", payload)
            elif kind == "error":
                self.status_var.set(payload)
                self._set_running(False)
                messagebox.showerror("Conversion failed", payload)

        self.root.after(120, self._poll_messages)

    def _set_running(self, running: bool) -> None:
        if running:
            self.convert_button.configure(state="disabled")
            self.cancel_button.configure(state="normal")
            self.progress.start(12)
        else:
            self.process = None
            self.convert_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            self.progress.stop()

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _log_line(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")


def tkinter_text_widget(parent: ttk.Frame):
    import tkinter as tk

    widget = tk.Text(parent, height=12, wrap="word", state="disabled")
    return widget


def main() -> int:
    root = Tk()
    try:
        root.call("tk", "scaling", 1.25)
    except Exception:
        pass
    OgvConverterApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
