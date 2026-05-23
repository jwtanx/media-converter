"""YouTube Downloader — tabbed GUI for video, audio download, and local conversion."""

from __future__ import annotations

from privacy import apply_privacy_environment

apply_privacy_environment()

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from converter import (
    AUDIO_FORMATS,
    AUDIO_QUALITY_MAP,
    VIDEO_EXTENSIONS,
    convert_video_to_audio,
    estimate_output_audio_size,
    ffmpeg_available,
)
from downloader import (
    FormatOption,
    download_audio,
    download_video,
    list_audio_formats,
    list_video_formats,
)
from utils import format_file_size

VIDEO_CONTAINERS = ("mp4", "mkv", "webm", "mov")
DEFAULT_VIDEO_CONTAINER = "mp4"
DEFAULT_AUDIO_FORMAT = "mp3"


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent: tk.Misc, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        self.inner.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas = canvas


class YouTubeDownloaderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("YouTube Downloader")
        self.minsize(640, 520)
        self.geometry("720x580")

        self._video_formats: list[FormatOption] = []
        self._audio_formats: list[FormatOption] = []
        self._busy = False

        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        notebook = ttk.Notebook(self, padding=8)
        notebook.pack(fill="both", expand=True)

        self._build_video_tab(notebook)
        self._build_audio_download_tab(notebook)
        self._build_convert_tab(notebook)

        if not ffmpeg_available():
            messagebox.showwarning(
                "ffmpeg not found",
                "ffmpeg is not on your PATH.\n\n"
                "• Video/audio YouTube downloads need ffmpeg for merging and audio extraction.\n"
                "• The Convert tab requires ffmpeg.\n\n"
                "Install ffmpeg: https://ffmpeg.org/download.html",
            )

    # ── Video download tab ──────────────────────────────────────────────

    def _build_video_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="Download Video")

        ttk.Label(frame, text="YouTube URL").grid(row=0, column=0, sticky="w")
        self.video_url = tk.StringVar()
        ttk.Entry(frame, textvariable=self.video_url, width=70).grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8)
        )

        ttk.Label(frame, text="Output folder").grid(row=2, column=0, sticky="w")
        self.video_output = tk.StringVar(value=str(Path.home() / "Downloads"))
        ttk.Entry(frame, textvariable=self.video_output, width=55).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )
        ttk.Button(frame, text="Browse…", command=self._browse_video_output).grid(
            row=3, column=2, sticky="e", padx=(8, 0)
        )

        row_fmt = ttk.Frame(frame)
        row_fmt.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        ttk.Label(row_fmt, text="Container").pack(side="left")
        self.video_container = tk.StringVar(value=DEFAULT_VIDEO_CONTAINER)
        ttk.Combobox(
            row_fmt,
            textvariable=self.video_container,
            values=VIDEO_CONTAINERS,
            state="readonly",
            width=8,
        ).pack(side="left", padx=(8, 16))

        ttk.Button(row_fmt, text="Load formats", command=self._load_video_formats).pack(
            side="left"
        )

        ttk.Label(frame, text="Resolution / format").grid(
            row=5, column=0, sticky="w", pady=(12, 0)
        )
        self.video_format_var = tk.StringVar()
        self.video_format_combo = ttk.Combobox(
            frame,
            textvariable=self.video_format_var,
            state="readonly",
            width=68,
        )
        self.video_format_combo.grid(row=6, column=0, columnspan=3, sticky="ew")

        self.video_size_label = ttk.Label(frame, text="Estimated size: —")
        self.video_size_label.grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.video_format_combo.bind("<<ComboboxSelected>>", self._on_video_format_selected)

        self.video_progress = ttk.Label(frame, text="")
        self.video_progress.grid(row=8, column=0, columnspan=3, sticky="w", pady=(8, 0))

        ttk.Button(frame, text="Download Video", command=self._start_video_download).grid(
            row=9, column=0, sticky="w", pady=(16, 0)
        )

        frame.columnconfigure(0, weight=1)

    # ── Audio download tab (YouTube → audio only) ───────────────────────

    def _build_audio_download_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="Download Audio")

        ttk.Label(
            frame,
            text="Downloads audio only from a YouTube link (no video file).",
            wraplength=640,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(frame, text="YouTube URL").grid(row=1, column=0, sticky="w")
        self.audio_url = tk.StringVar()
        ttk.Entry(frame, textvariable=self.audio_url, width=70).grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8)
        )

        ttk.Label(frame, text="Output folder").grid(row=3, column=0, sticky="w")
        self.audio_output = tk.StringVar(value=str(Path.home() / "Downloads"))
        ttk.Entry(frame, textvariable=self.audio_output, width=55).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )
        ttk.Button(frame, text="Browse…", command=self._browse_audio_output).grid(
            row=4, column=2, sticky="e", padx=(8, 0)
        )

        row_fmt = ttk.Frame(frame)
        row_fmt.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        ttk.Label(row_fmt, text="Output format").pack(side="left")
        self.audio_format = tk.StringVar(value=DEFAULT_AUDIO_FORMAT)
        ttk.Combobox(
            row_fmt,
            textvariable=self.audio_format,
            values=AUDIO_FORMATS,
            state="readonly",
            width=8,
        ).pack(side="left", padx=(8, 16))
        ttk.Button(row_fmt, text="Load qualities", command=self._load_audio_formats).pack(
            side="left"
        )

        ttk.Label(frame, text="Source quality").grid(row=6, column=0, sticky="w", pady=(12, 0))
        self.audio_format_var = tk.StringVar()
        self.audio_format_combo = ttk.Combobox(
            frame,
            textvariable=self.audio_format_var,
            state="readonly",
            width=68,
        )
        self.audio_format_combo.grid(row=7, column=0, columnspan=3, sticky="ew")
        self.audio_format_combo.bind("<<ComboboxSelected>>", self._on_audio_format_selected)

        self.audio_size_label = ttk.Label(frame, text="Estimated size: —")
        self.audio_size_label.grid(row=8, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.audio_progress = ttk.Label(frame, text="")
        self.audio_progress.grid(row=9, column=0, columnspan=3, sticky="w", pady=(8, 0))

        ttk.Button(frame, text="Download Audio", command=self._start_audio_download).grid(
            row=10, column=0, sticky="w", pady=(16, 0)
        )

        frame.columnconfigure(0, weight=1)

    # ── Convert local video → audio tab ─────────────────────────────────

    def _build_convert_tab(self, notebook: ttk.Notebook) -> None:
        outer = ttk.Frame(notebook, padding=12)
        notebook.add(outer, text="Convert to Audio")

        ttk.Label(
            outer,
            text="Convert video files already on your computer to audio.",
            wraplength=640,
        ).pack(anchor="w", pady=(0, 12))

        file_row = ttk.Frame(outer)
        file_row.pack(fill="x", pady=(0, 8))
        ttk.Label(file_row, text="Video file").pack(side="left")
        self.convert_input = tk.StringVar()
        ttk.Entry(file_row, textvariable=self.convert_input, width=50).pack(
            side="left", fill="x", expand=True, padx=(8, 8)
        )
        ttk.Button(file_row, text="Browse…", command=self._browse_convert_input).pack(side="left")

        out_row = ttk.Frame(outer)
        out_row.pack(fill="x", pady=(0, 8))
        ttk.Label(out_row, text="Output folder").pack(side="left")
        self.convert_output = tk.StringVar(value=str(Path.home() / "Downloads"))
        ttk.Entry(out_row, textvariable=self.convert_output, width=50).pack(
            side="left", fill="x", expand=True, padx=(8, 8)
        )
        ttk.Button(out_row, text="Browse…", command=self._browse_convert_output).pack(side="left")

        opts = ttk.Frame(outer)
        opts.pack(fill="x", pady=(8, 0))
        ttk.Label(opts, text="Output format").grid(row=0, column=0, sticky="w")
        self.convert_format = tk.StringVar(value=DEFAULT_AUDIO_FORMAT)
        ttk.Combobox(
            opts,
            textvariable=self.convert_format,
            values=AUDIO_FORMATS,
            state="readonly",
            width=10,
        ).grid(row=0, column=1, padx=(8, 24), sticky="w")

        ttk.Label(opts, text="Quality").grid(row=0, column=2, sticky="w")
        self.convert_quality = tk.StringVar(value="192 kbps (default)")
        quality_combo = ttk.Combobox(
            opts,
            textvariable=self.convert_quality,
            values=list(AUDIO_QUALITY_MAP.keys()),
            state="readonly",
            width=22,
        )
        quality_combo.grid(row=0, column=3, padx=(8, 0), sticky="w")
        quality_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_convert_estimate())
        self.convert_format.trace_add("write", lambda *_: self._update_convert_estimate())

        self.convert_size_label = ttk.Label(outer, text="Estimated output size: —")
        self.convert_size_label.pack(anchor="w", pady=(12, 0))

        self.convert_progress = ttk.Label(outer, text="")
        self.convert_progress.pack(anchor="w", pady=(8, 0))

        ttk.Button(outer, text="Convert to Audio", command=self._start_convert).pack(
            anchor="w", pady=(16, 0)
        )

        self.convert_input.trace_add("write", lambda *_: self._update_convert_estimate())

    # ── Browse helpers ──────────────────────────────────────────────────

    def _browse_video_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.video_output.set(path)

    def _browse_audio_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.audio_output.set(path)

    def _browse_convert_input(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("Video files", " ".join(f"*{e}" for e in sorted(VIDEO_EXTENSIONS))),
                ("All files", "*.*"),
            ]
        )
        if path:
            self.convert_input.set(path)
            self._update_convert_estimate()

    def _browse_convert_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.convert_output.set(path)

    # ── Format loading ──────────────────────────────────────────────────

    def _load_video_formats(self) -> None:
        url = self.video_url.get().strip()
        if not url:
            messagebox.showerror("Error", "Enter a YouTube URL.")
            return
        self._run_async(
            lambda: list_video_formats(url),
            self._apply_video_formats,
            "Loading video formats…",
            self.video_progress,
        )

    def _apply_video_formats(self, result: tuple[str, list[FormatOption]]) -> None:
        title, formats = result
        self._video_formats = formats
        labels = [f.label for f in formats]
        self.video_format_combo["values"] = labels
        if labels:
            self.video_format_var.set(labels[0])
            self._on_video_format_selected()
        self.video_progress.config(text=f"Loaded: {title}")

    def _load_audio_formats(self) -> None:
        url = self.audio_url.get().strip()
        if not url:
            messagebox.showerror("Error", "Enter a YouTube URL.")
            return
        self._run_async(
            lambda: list_audio_formats(url),
            self._apply_audio_formats,
            "Loading audio qualities…",
            self.audio_progress,
        )

    def _apply_audio_formats(self, result: tuple[str, list[FormatOption]]) -> None:
        title, formats = result
        self._audio_formats = formats
        labels = [f.label for f in formats]
        self.audio_format_combo["values"] = labels
        if labels:
            self.audio_format_var.set(labels[0])
            self._on_audio_format_selected()
        self.audio_progress.config(text=f"Loaded: {title}")

    def _on_video_format_selected(self, *_args) -> None:
        idx = self._selected_index(self.video_format_var.get(), self._video_formats)
        if idx is None:
            return
        fmt = self._video_formats[idx]
        self.video_size_label.config(text=f"Estimated size: {fmt.size_label}")

    def _on_audio_format_selected(self, *_args) -> None:
        idx = self._selected_index(self.audio_format_var.get(), self._audio_formats)
        if idx is None:
            return
        fmt = self._audio_formats[idx]
        self.audio_size_label.config(text=f"Estimated size: {fmt.size_label}")

    def _update_convert_estimate(self) -> None:
        path = self.convert_input.get().strip()
        if not path or not Path(path).exists():
            self.convert_size_label.config(text="Estimated output size: —")
            return
        est = estimate_output_audio_size(
            Path(path),
            self.convert_format.get(),
            self.convert_quality.get(),
        )
        video_size = format_file_size(Path(path).stat().st_size)
        self.convert_size_label.config(
            text=f"Source video: {video_size} · Estimated output: {est}"
        )

    @staticmethod
    def _selected_index(label: str, options: list[FormatOption]) -> int | None:
        for i, opt in enumerate(options):
            if opt.label == label:
                return i
        return None

    # ── Downloads & conversion ──────────────────────────────────────────

    def _start_video_download(self) -> None:
        url = self.video_url.get().strip()
        out = self.video_output.get().strip()
        if not url or not out:
            messagebox.showerror("Error", "URL and output folder are required.")
            return
        idx = self._selected_index(self.video_format_var.get(), self._video_formats)
        if idx is None:
            messagebox.showerror("Error", "Load formats and select a resolution.")
            return
        fmt = self._video_formats[idx]
        container = self.video_container.get() or DEFAULT_VIDEO_CONTAINER

        def task() -> Path:
            return download_video(
                url,
                Path(out),
                fmt.format_id,
                container,
                lambda msg: self.after(0, self.video_progress.config, {"text": msg}),
                lambda msg: self.after(0, self.video_progress.config, {"text": msg}),
            )

        self._run_async(
            task,
            lambda _p: messagebox.showinfo("Done", "Video downloaded successfully."),
            "Starting download…",
            self.video_progress,
        )

    def _start_audio_download(self) -> None:
        url = self.audio_url.get().strip()
        out = self.audio_output.get().strip()
        if not url or not out:
            messagebox.showerror("Error", "URL and output folder are required.")
            return
        idx = self._selected_index(self.audio_format_var.get(), self._audio_formats)
        if idx is None:
            messagebox.showerror("Error", "Load qualities and select one.")
            return
        fmt = self._audio_formats[idx]
        audio_fmt = self.audio_format.get() or DEFAULT_AUDIO_FORMAT

        def task() -> Path:
            return download_audio(
                url,
                Path(out),
                fmt.format_id,
                audio_fmt,
                lambda msg: self.after(0, self.audio_progress.config, {"text": msg}),
                lambda msg: self.after(0, self.audio_progress.config, {"text": msg}),
            )

        self._run_async(
            task,
            lambda _p: messagebox.showinfo("Done", "Audio downloaded successfully."),
            "Starting audio download…",
            self.audio_progress,
        )

    def _start_convert(self) -> None:
        video = self.convert_input.get().strip()
        out = self.convert_output.get().strip()
        if not video or not out:
            messagebox.showerror("Error", "Video file and output folder are required.")
            return
        if not Path(video).exists():
            messagebox.showerror("Error", "Video file does not exist.")
            return

        audio_fmt = self.convert_format.get() or DEFAULT_AUDIO_FORMAT
        quality = self.convert_quality.get()

        def task() -> Path:
            return convert_video_to_audio(
                Path(video),
                Path(out),
                audio_fmt,
                quality,
                lambda msg: self.after(0, self.convert_progress.config, {"text": msg}),
                lambda msg: self.after(0, self.convert_progress.config, {"text": msg}),
            )

        self._run_async(
            task,
            lambda _p: messagebox.showinfo("Done", "Conversion finished successfully."),
            "Converting…",
            self.convert_progress,
        )

    # ── Threading ───────────────────────────────────────────────────────

    def _run_async(self, work, on_success, busy_msg: str, label: ttk.Label) -> None:
        if self._busy:
            messagebox.showinfo("Busy", "Please wait for the current task to finish.")
            return
        self._busy = True
        label.config(text=busy_msg)

        def runner() -> None:
            try:
                result = work()
                self.after(0, lambda: on_success(result))
            except Exception as exc:  # noqa: BLE001 — show user-facing errors
                self.after(0, lambda: messagebox.showerror("Error", str(exc)))
            finally:
                self.after(0, self._clear_busy)

        threading.Thread(target=runner, daemon=True).start()

    def _clear_busy(self) -> None:
        self._busy = False


def main() -> None:
    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
