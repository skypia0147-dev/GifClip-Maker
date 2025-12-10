import os
import sys
if os.name == "nt":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "VideoToGifTool"
    )
import threading
import subprocess
from pathlib import Path
import tempfile

import cv2
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    TKDND_AVAILABLE = True
except ImportError:
    TKDND_AVAILABLE = False

DARK_BG = "#1e1e1e"
PANEL_BG = DARK_BG
TEXT_FG = "#f0f0f0"
ENTRY_BG = "#333333"
ENTRY_FG = TEXT_FG
ACCENT = "#4ea1ff"
ACCENT_DARK = "#357acc"
BTN_BG = "#3b3b3b"
BTN_FG = TEXT_FG
SLIDER_TROUGH = "#3b3b3b"
RANGE_BG = "#303030"


def get_base_dir():
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()
DEFAULT_FFMPEG = str(BASE_DIR / "ffmpeg.exe")
DEFAULT_GIFSKI = str(BASE_DIR / "gifski.exe")


class VideoToGifApp:
    def __init__(self, root):
        self.root = root
        try:
            icon_path = os.path.join(get_base_dir(), "app_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass
        self.root.title("Video to GIF Tool (tkinter + ffmpeg + gifski)")
        self.root.configure(bg=DARK_BG)

        # Global style
        self.root.option_add("*Background", DARK_BG)
        self.root.option_add("*Foreground", TEXT_FG)
        self.root.option_add("*Entry.Background", ENTRY_BG)
        self.root.option_add("*Entry.Foreground", ENTRY_FG)
        self.root.option_add("*Entry.InsertBackground", ENTRY_FG)
        self.root.option_add("*Button.Background", BTN_BG)
        self.root.option_add("*Button.Foreground", BTN_FG)
        self.root.option_add("*Label.Background", DARK_BG)
        self.root.option_add("*Label.Foreground", TEXT_FG)
        self.root.option_add("*TCombobox*Listbox.Background", ENTRY_BG)
        self.root.option_add("*TCombobox*Listbox.Foreground", ENTRY_FG)

        self.root.minsize(600, 360)

        # Video state
        self.cap = None
        self.video_path = None
        self.frame_count = 0
        self.fps = 0.0
        self.duration = 0.0
        self.width = 0
        self.height = 0
        self.current_frame_index = 0
        self.playing = False

        # Range state
        self.start_time = None
        self.end_time = None

        # Async flags
        self.converting = False
        self.estimate_running = False

        # Conversion dialog / cancel state
        self.convert_dialog = None
        self.convert_progress = None
        self.convert_cancel_button = None
        self.cancel_requested = False
        self.current_ff_proc = None
        self.current_gif_proc = None

        self._init_styles()
        self._build_ui()
        self.update_loop()

        if TKDND_AVAILABLE:
            try:
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind("<<Drop>>", self.on_drop_files)
            except Exception:
                pass

    def _init_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("default")
        except tk.TclError:
            pass

        style.configure(
            "Dark.TCombobox",
            fieldbackground=ENTRY_BG,
            background=ENTRY_BG,
            foreground=ENTRY_FG,
            arrowcolor=ENTRY_FG,
            bordercolor=ENTRY_BG,
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", ENTRY_BG)],
            foreground=[("readonly", ENTRY_FG)],
        )

    def _build_ui(self):
        # Video display
        self.video_label = tk.Label(self.root, bg=DARK_BG)
        self.video_label.pack(padx=5, pady=5)

        # Info row
        info_frame = tk.Frame(self.root, bg=PANEL_BG)
        info_frame.pack(fill="x", padx=0, pady=(0, 2))

        self.info_label = tk.Label(
            info_frame,
            text="No video loaded",
            bg=PANEL_BG,
            fg=TEXT_FG,
        )
        self.info_label.pack(side="left", padx=(20, 5))

        self.time_label = tk.Label(
            info_frame,
            text="00:00.00 / 00:00.00",
            bg=PANEL_BG,
            fg=TEXT_FG,
        )
        self.time_label.pack(side="right", padx=(5, 20))

        # Timeline slider
        self.scale = tk.Scale(
            self.root,
            from_=0,
            to=100,
            orient="horizontal",
            length=500,
            command=self.on_scale,
            showvalue=False,
            bg=DARK_BG,
            fg=TEXT_FG,
            troughcolor=SLIDER_TROUGH,
            highlightthickness=0,
        )
        self.scale.pack(fill="x", padx=(20, 20), pady=(5, 2))

        # Range bar
        self.range_canvas = tk.Canvas(
            self.root,
            height=10,
            bg=DARK_BG,
            highlightthickness=0,
            bd=0,
        )
        self.range_canvas.pack(fill="x", padx=(20, 20), pady=(0, 6))
        self.range_canvas.bind("<Configure>", lambda e: self.draw_range_bar())

        # Open / Play buttons above range settings
        top_btn_frame = tk.Frame(self.root, bg=DARK_BG)
        top_btn_frame.pack(fill="x", padx=0, pady=(0, 12))

        self.open_button = tk.Button(
            top_btn_frame,
            text="Open Video",
            width=12,
            bg=BTN_BG,
            fg=BTN_FG,
            activebackground="#4a4a4a",
            activeforeground=BTN_FG,
            relief="flat",
            command=self.open_video,
        )
        self.open_button.pack(side="left", padx=(20, 3))

        self.play_button = tk.Button(
            top_btn_frame,
            text="Play",
            width=8,
            bg=BTN_BG,
            fg=BTN_FG,
            activebackground="#4a4a4a",
            activeforeground=BTN_FG,
            relief="flat",
            command=self.toggle_play,
        )
        self.play_button.pack(side="left", padx=3)

        # Range settings
        range_frame = tk.Frame(self.root, bg=PANEL_BG)
        range_frame.pack(fill="x", padx=5, pady=2)

        tk.Label(range_frame, text="Start", bg=PANEL_BG, fg=TEXT_FG).grid(
            row=0, column=0, sticky="w", padx=(20, 5)
        )
        self.start_entry = tk.Entry(
            range_frame,
            width=10,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=ENTRY_FG,
            relief="flat",
        )
        self.start_entry.grid(row=0, column=1, sticky="w", padx=(0, 6))
        self.start_entry.bind("<KeyRelease>", lambda e: self.draw_range_bar())

        self.start_button = tk.Button(
            range_frame,
            text="Set Start",
            width=14,
            bg=BTN_BG,
            fg=BTN_FG,
            activebackground="#4a4a4a",
            activeforeground=BTN_FG,
            relief="flat",
            command=self.set_start_from_current,
        )
        self.start_button.grid(row=0, column=2, sticky="w", padx=(0, 0))

        tk.Label(range_frame, text="End", bg=PANEL_BG, fg=TEXT_FG).grid(
            row=1, column=0, sticky="w", padx=(20, 5)
        )
        self.end_entry = tk.Entry(
            range_frame,
            width=10,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=ENTRY_FG,
            relief="flat",
        )
        self.end_entry.grid(row=1, column=1, sticky="w", padx=(0, 6))
        self.end_entry.bind("<KeyRelease>", lambda e: self.draw_range_bar())

        self.end_button = tk.Button(
            range_frame,
            text="Set End",
            width=14,
            bg=BTN_BG,
            fg=BTN_FG,
            activebackground="#4a4a4a",
            activeforeground=BTN_FG,
            relief="flat",
            command=self.set_end_from_current,
        )
        self.end_button.grid(row=1, column=2, sticky="w", padx=(0, 0))

        self.range_hint = tk.Label(
            range_frame,
            text="* Start/End can be entered as seconds or mm:ss (ex: 1.5 or 00:01.50)",
            bg=PANEL_BG,
            fg="#bbbbbb",
        )
        self.range_hint.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(3, 0),
            padx=(20, 0),
        )

        # Encode options
        opt_frame = tk.Frame(self.root, bg=PANEL_BG)
        opt_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(
            opt_frame,
            text="Quality (1-100):",
            bg=PANEL_BG,
            fg=TEXT_FG,
        ).grid(row=0, column=0, sticky="e", padx=(20, 5))
        self.quality_entry = tk.Entry(
            opt_frame,
            width=5,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=ENTRY_FG,
            relief="flat",
        )
        self.quality_entry.grid(row=0, column=1, padx=3)
        self.quality_entry.insert(0, "60")

        tk.Label(
            opt_frame,
            text="FPS:",
            bg=PANEL_BG,
            fg=TEXT_FG,
        ).grid(row=0, column=2, sticky="e", padx=(10, 3))
        self.fps_entry = tk.Entry(
            opt_frame,
            width=5,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=ENTRY_FG,
            relief="flat",
        )
        self.fps_entry.grid(row=0, column=3, padx=3)
        self.fps_entry.insert(0, "60")

        # Resolution options
        res_frame = tk.Frame(self.root, bg=PANEL_BG)
        res_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(
            res_frame,
            text="Resolution:",
            bg=PANEL_BG,
            fg=TEXT_FG,
        ).grid(row=0, column=0, sticky="e", padx=(20, 5))

        self.res_var = tk.StringVar()
        self.res_combo = ttk.Combobox(
            res_frame,
            textvariable=self.res_var,
            state="readonly",
            width=18,
            style="Dark.TCombobox",
        )
        self.resolutions = [
            "Original",
            "1920x1080",
            "1600x900",
            "1280x720",
            "1024x576",
            "854x480",
            "640x360",
            "480x270",
            "Custom pixels",
            "Custom percent",
        ]
        self.res_combo["values"] = self.resolutions
        self.res_combo.current(0)
        self.res_combo.grid(row=0, column=1, padx=3, sticky="w")
        self.res_combo.bind("<<ComboboxSelected>>", self.on_res_mode_change)

        tk.Label(res_frame, text="W:", bg=PANEL_BG, fg=TEXT_FG).grid(
            row=0, column=2, sticky="e"
        )
        self.custom_width_entry = tk.Entry(
            res_frame,
            width=6,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=ENTRY_FG,
            relief="flat",
        )
        self.custom_width_entry.grid(row=0, column=3, padx=2)

        tk.Label(res_frame, text="H:", bg=PANEL_BG, fg=TEXT_FG).grid(
            row=0, column=4, sticky="e"
        )
        self.custom_height_entry = tk.Entry(
            res_frame,
            width=6,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=ENTRY_FG,
            relief="flat",
        )
        self.custom_height_entry.grid(row=0, column=5, padx=2)

        tk.Label(res_frame, text="%:", bg=PANEL_BG, fg=TEXT_FG).grid(
            row=0, column=6, sticky="e"
        )
        self.custom_percent_entry = tk.Entry(
            res_frame,
            width=5,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=ENTRY_FG,
            relief="flat",
        )
        self.custom_percent_entry.grid(row=0, column=7, padx=2)

        self.custom_percent_entry.bind("<KeyRelease>", self.on_percent_typed)
        self.custom_width_entry.bind("<KeyRelease>", self.on_pixels_typed)
        self.custom_height_entry.bind("<KeyRelease>", self.on_pixels_typed)

        self.res_hint = tk.Label(
            res_frame,
            text="* Custom pixels: set W/H directly, Custom percent: scale vs original % (ex: 60)",
            bg=PANEL_BG,
            fg="#bbbbbb",
        )
        self.res_hint.grid(
            row=1,
            column=0,
            columnspan=8,
            sticky="w",
            pady=(3, 0),
            padx=(20, 0),
        )

        self._update_res_input_state()

        # Bottom buttons: Estimate + Convert
        bottom_btn_frame = tk.Frame(self.root, bg=DARK_BG)
        bottom_btn_frame.pack(fill="x", padx=0, pady=8)

        self.convert_button = tk.Button(
            bottom_btn_frame,
            text="Convert to GIF",
            width=14,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_DARK,
            activeforeground="white",
            relief="flat",
            command=self.on_convert_clicked,
        )
        self.convert_button.pack(side="right", padx=(5, 20))

        self.estimate_button = tk.Button(
            bottom_btn_frame,
            text="Estimate Size",
            width=14,
            bg=BTN_BG,
            fg=BTN_FG,
            activebackground="#4a4a4a",
            activeforeground=BTN_FG,
            relief="flat",
            command=self.on_estimate_clicked,
        )
        self.estimate_button.pack(side="right", padx=(5, 5))

        self.status_label = tk.Label(
            self.root,
            text="Ready",
            anchor="w",
            bg=DARK_BG,
            fg="#bbbbbb",
        )
        self.status_label.pack(fill="x", padx=(20, 5), pady=(0, 5))

    # -------- Video loading & playback --------

    def open_video(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Video files", "*.mp4;*.mkv;*.avi;*.mov;*.webm;*.wmv"),
                ("All files", "*.*"),
            ]
        )
        if not path:
            return
        self.load_video(path)

    def load_video(self, path: str):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            messagebox.showerror("Error", "Failed to open video.")
            return

        self.cap = cap
        self.video_path = path

        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 30.0)
        if self.fps <= 0:
            self.fps = 30.0
        self.duration = self.frame_count / self.fps if self.frame_count > 0 else 0.0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.current_frame_index = 0
        self.scale.config(from_=0, to=max(self.frame_count - 1, 0))
        self.playing = False
        self.play_button.config(text="Play")

        self.start_time = None
        self.end_time = None
        self.start_entry.delete(0, tk.END)
        self.end_entry.delete(0, tk.END)

        info_text = (
            f"Resolution: {self.width} x {self.height}   "
            f"Frames: {self.frame_count}   FPS: {self.fps:.2f}"
        )
        self.info_label.config(text=info_text)

        original_label = f"Original ({self.width}x{self.height})"
        values = [original_label] + self.resolutions[1:]
        self.res_combo["values"] = values
        self.res_combo.current(0)
        self._update_res_input_state()

        self.show_frame(self.current_frame_index)
        self.update_time_label()
        self.draw_range_bar()
        self.set_status("Video loaded.")

    def toggle_play(self):
        if self.cap is None:
            return
        self.playing = not self.playing
        self.play_button.config(text="Pause" if self.playing else "Play")

    def on_scale(self, value):
        if self.cap is None:
            return
        idx = int(float(value))
        self.current_frame_index = idx
        self.show_frame(self.current_frame_index)
        self.update_time_label()

    def show_frame(self, index):
        if self.cap is None:
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)

        max_display_width = 800
        if img.width > max_display_width:
            ratio = max_display_width / img.width
            img = img.resize(
                (int(img.width * ratio), int(img.height * ratio)),
                Image.LANCZOS,
            )

        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.config(image=imgtk, bg=DARK_BG)

    def update_time_label(self):
        cur = 0.0
        if self.fps > 0:
            cur = self.current_frame_index / self.fps
        total = self.duration
        self.time_label.config(
            text=f"{self.format_time(cur)} / {self.format_time(total)}"
        )

    @staticmethod
    def format_time(sec):
        sec = max(0.0, float(sec))
        m = int(sec // 60)
        s = sec - m * 60
        return f"{m:02d}:{s:05.2f}"

    def update_loop(self):
        if self.playing and self.cap is not None and self.fps > 0 and self.frame_count > 0:
            self.current_frame_index += 1
            if self.current_frame_index >= self.frame_count:
                self.current_frame_index = self.frame_count - 1
                self.playing = False
                self.play_button.config(text="Play")
            self.show_frame(self.current_frame_index)
            self.scale.set(self.current_frame_index)
            self.update_time_label()

        if self.playing and self.fps > 0:
            delay = int(1000 / self.fps)
            delay = max(10, delay)
        else:
            delay = 30

        self.root.after(delay, self.update_loop)

    # -------- Start / End handling --------

    def set_start_from_current(self):
        if self.cap is None or self.fps <= 0:
            return
        t = self.current_frame_index / self.fps
        self.start_time = t
        self.start_entry.delete(0, tk.END)
        self.start_entry.insert(0, f"{t:.2f}")
        self.draw_range_bar()
        self.set_status(f"Start set to {t:.2f} sec")

    def set_end_from_current(self):
        if self.cap is None or self.fps <= 0:
            return
        t = self.current_frame_index / self.fps
        self.end_time = t
        self.end_entry.delete(0, tk.END)
        self.end_entry.insert(0, f"{t:.2f}")
        self.draw_range_bar()
        self.set_status(f"End set to {t:.2f} sec")

    def parse_time_entry(self, text):
        text = text.strip()
        if not text:
            return None
        if ":" in text:
            parts = text.split(":")
            try:
                parts_f = [float(p) for p in parts]
            except ValueError:
                return None
            if len(parts_f) == 2:
                m, s = parts_f
                return max(0.0, m * 60 + s)
            if len(parts_f) == 3:
                h, m, s = parts_f
                return max(0.0, h * 3600 + m * 60 + s)
            return None
        try:
            v = float(text)
        except ValueError:
            return None
        return max(0.0, v)

    # -------- Range bar drawing --------

    def draw_range_bar(self):
        c = self.range_canvas
        c.delete("all")

        width = c.winfo_width()
        if width <= 0:
            return
        height = int(c["height"])
        margin = 2
        bar_y0 = margin
        bar_y1 = height - margin

        c.create_rectangle(0, bar_y0, width, bar_y1, fill=RANGE_BG, outline="")

        if self.duration <= 0:
            return

        s = self.parse_time_entry(self.start_entry.get()) or self.start_time or 0.0
        e = self.parse_time_entry(self.end_entry.get()) or self.end_time
        if e is None:
            e = self.duration

        s = max(0.0, min(self.duration, s))
        e = max(0.0, min(self.duration, e))
        if e <= s:
            return

        xs = int(width * (s / self.duration))
        xe = int(width * (e / self.duration))

        c.create_rectangle(xs, bar_y0, xe, bar_y1, fill=ACCENT, outline="")

    # -------- Resolution handling --------

    def on_res_mode_change(self, event=None):
        self._update_res_input_state()

    def on_percent_typed(self, event=None):
        txt = self.custom_percent_entry.get().strip()
        if txt:
            values = list(self.res_combo["values"])
            for i, v in enumerate(values):
                if v.startswith("Custom percent"):
                    self.res_combo.current(i)
                    self.res_var.set(v)
                    break
            self._update_res_input_state()

    def on_pixels_typed(self, event=None):
        txt_w = self.custom_width_entry.get().strip()
        txt_h = self.custom_height_entry.get().strip()
        if txt_w or txt_h:
            values = list(self.res_combo["values"])
            for i, v in enumerate(values):
                if v.startswith("Custom pixels"):
                    self.res_combo.current(i)
                    self.res_var.set(v)
                    break
            self._update_res_input_state()

    def _update_res_input_state(self):
        self.custom_width_entry.config(state="normal")
        self.custom_height_entry.config(state="normal")
        self.custom_percent_entry.config(state="normal")

    def compute_output_resolution(self):
        if self.width <= 0 or self.height <= 0:
            return (None, None)

        label = self.res_var.get()
        if label.startswith("Original"):
            w = (int(self.width) // 2) * 2
            h = (int(self.height) // 2) * 2
            return (w, h)

        if "Custom pixels" in label:
            w_text = self.custom_width_entry.get().strip()
            h_text = self.custom_height_entry.get().strip()
            if not w_text or not h_text:
                raise ValueError("Custom pixels mode selected, but width/height are empty.")
            try:
                w = int(w_text)
                h = int(h_text)
            except ValueError:
                raise ValueError("Custom width/height must be integers.")
            if w <= 0 or h <= 0:
                raise ValueError("Custom width/height must be positive.")
            w = (w // 2) * 2
            h = (h // 2) * 2
            return (w, h)

        if "Custom percent" in label:
            p_text = self.custom_percent_entry.get().strip()
            if not p_text:
                raise ValueError("Custom percent mode selected, but percent is empty.")
            try:
                p = float(p_text)
            except ValueError:
                raise ValueError("Percent must be a number.")
            if p <= 0:
                raise ValueError("Percent must be greater than 0.")
            scale = p / 100.0
            w = int(self.width * scale)
            h = int(self.height * scale)
            if w <= 0 or h <= 0:
                raise ValueError("Resulting resolution is too small.")
            w = (w // 2) * 2
            h = (h // 2) * 2
            return (w, h)

        if "x" in label:
            try:
                res_str = label.split(" ")[0]
                w_str, h_str = res_str.split("x")
                w = int(w_str)
                h = int(h_str)
            except Exception:
                raise ValueError("Invalid resolution preset format.")
            w = (w // 2) * 2
            h = (h // 2) * 2
            return (w, h)

        return (None, None)

    # -------- Convert to GIF --------

    def on_convert_clicked(self):
        if self.converting:
            return
        if self.cap is None or not self.video_path:
            messagebox.showwarning("Warning", "Please open a video first.")
            return

        try:
            quality = int(self.quality_entry.get().strip() or "60")
        except ValueError:
            messagebox.showerror("Error", "Quality must be an integer between 1 and 100.")
            return
        if not (1 <= quality <= 100):
            messagebox.showerror("Error", "Quality must be between 1 and 100.")
            return

        try:
            out_fps = float(self.fps_entry.get().strip() or "60")
        except ValueError:
            messagebox.showerror("Error", "FPS must be a number.")
            return
        if out_fps <= 0:
            messagebox.showerror("Error", "FPS must be greater than 0.")
            return

        start_text = self.start_entry.get().strip()
        end_text = self.end_entry.get().strip()

        start_time = self.parse_time_entry(start_text) if start_text else None
        end_time = self.parse_time_entry(end_text) if end_text else None

        if start_time is None and self.start_time is not None and start_text == "":
            start_time = self.start_time
        if end_time is None and self.end_time is not None and end_text == "":
            end_time = self.end_time

        if start_time is None:
            start_time = 0.0

        duration = None
        if end_time is not None:
            if end_time <= start_time:
                messagebox.showerror("Error", "End time must be greater than start time.")
                return
            duration = end_time - start_time

        try:
            out_w, out_h = self.compute_output_resolution()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        in_path = Path(self.video_path)
        out_name = f"{in_path.stem}_q{quality}_fps{int(out_fps)}.gif"
        out_path = str(in_path.with_name(out_name))

        ffmpeg_path = DEFAULT_FFMPEG if os.path.exists(DEFAULT_FFMPEG) else "ffmpeg"
        gifski_path = DEFAULT_GIFSKI if os.path.exists(DEFAULT_GIFSKI) else "gifski"

        self.set_status("Converting to GIF...")
        self.convert_button.config(state="disabled")
        self.converting = True
        self.cancel_requested = False

        thread = threading.Thread(
            target=self._run_conversion,
            args=(
                ffmpeg_path,
                gifski_path,
                str(in_path),
                out_path,
                quality,
                out_fps,
                start_time,
                duration,
                out_w,
                out_h,
            ),
            daemon=True,
        )
        thread.start()

        # Show conversion progress dialog
        self.show_convert_dialog()

    def _run_conversion(
        self,
        ffmpeg_path,
        gifski_path,
        input_path,
        output_path,
        quality,
        out_fps,
        start_time,
        duration,
        out_w,
        out_h,
    ):
        self.current_ff_proc = None
        self.current_gif_proc = None
        try:
            ff_args = [ffmpeg_path]
            if start_time is not None and start_time > 0:
                ff_args += ["-ss", f"{start_time:.3f}"]
            if duration is not None and duration > 0:
                ff_args += ["-t", f"{duration:.3f}"]
            ff_args += ["-i", input_path, "-pix_fmt", "yuv420p"]

            vf_filters = []
            if out_w is not None and out_h is not None:
                vf_filters.append(f"scale={out_w}:{out_h}")
            if vf_filters:
                ff_args += ["-vf", ",".join(vf_filters)]

            ff_args += ["-f", "yuv4mpegpipe", "-"]

            gif_args = [
                gifski_path,
                "--fps", str(out_fps),
                "--quality", str(quality),
            ]

            # Force output resolution so gifski does not downscale automatically
            if out_w is not None and out_h is not None:
                gif_args += [
                    "--width", str(out_w),
                    "--height", str(out_h),
                ]

            gif_args += [
                "-o", output_path,
                "-"
            ]

            popen_kwargs = {}
            if os.name == "nt":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            ff_proc = subprocess.Popen(
                ff_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **popen_kwargs,
            )
            self.current_ff_proc = ff_proc

            gif_proc = subprocess.Popen(
                gif_args,
                stdin=ff_proc.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                **popen_kwargs,
            )
            self.current_gif_proc = gif_proc

            ff_proc.stdout.close()

            _, ff_err = ff_proc.communicate()
            _, gif_err = gif_proc.communicate()

            ff_err_txt = ff_err.decode(errors="ignore")
            gif_err_txt = gif_err.decode(errors="ignore")

            if self.cancel_requested:
                self.root.after(0, self._on_convert_canceled)
                return

            if gif_proc.returncode != 0:
                raise RuntimeError(f"gifski failed:\n{gif_err_txt}")

            if ff_proc.returncode != 0:
                if ("Broken pipe" not in ff_err_txt
                        and "Error writing trailer of pipe" not in ff_err_txt):
                    raise RuntimeError(f"ffmpeg failed:\n{ff_err_txt}")

            self.root.after(0, lambda: self._on_convert_finished(output_path))

        except Exception as e:
            msg = str(e)
            if not self.cancel_requested:
                self.root.after(0, lambda: self._on_convert_error(msg))
        finally:
            self.current_ff_proc = None
            self.current_gif_proc = None
            self.cancel_requested = False

    def _on_convert_finished(self, output_path):
        self.converting = False
        self.convert_button.config(state="normal")
        self.hide_convert_dialog()
        self.set_status(f"GIF saved as: {output_path}")

    def _on_convert_error(self, msg):
        self.converting = False
        self.convert_button.config(state="normal")
        self.hide_convert_dialog()
        self.set_status("Conversion failed.")
        messagebox.showerror("Error", f"Conversion failed:\n{msg}")

    def _on_convert_canceled(self):
        self.converting = False
        self.convert_button.config(state="normal")
        self.hide_convert_dialog()
        self.set_status("Conversion canceled.")

    # -------- Estimate size --------

    def on_estimate_clicked(self):
        if self.estimate_running:
            return
        if self.cap is None or not self.video_path:
            messagebox.showwarning("Warning", "Please open a video first.")
            return

        try:
            quality = int(self.quality_entry.get().strip() or "60")
        except ValueError:
            messagebox.showerror("Error", "Quality must be an integer between 1 and 100.")
            return
        if not (1 <= quality <= 100):
            messagebox.showerror("Error", "Quality must be between 1 and 100.")
            return

        try:
            out_fps = float(self.fps_entry.get().strip() or "60")
        except ValueError:
            messagebox.showerror("Error", "FPS must be a number.")
            return
        if out_fps <= 0:
            messagebox.showerror("Error", "FPS must be greater than 0.")
            return

        start_text = self.start_entry.get().strip()
        end_text = self.end_entry.get().strip()

        start_time = self.parse_time_entry(start_text) if start_text else None
        end_time = self.parse_time_entry(end_text) if end_text else None

        if start_time is None and self.start_time is not None and start_text == "":
            start_time = self.start_time
        if end_time is None and self.end_time is not None and end_text == "":
            end_time = self.end_time

        if start_time is None:
            start_time = 0.0

        if end_time is not None:
            if end_time <= start_time:
                messagebox.showerror("Error", "End time must be greater than start time.")
                return
            clip_duration = end_time - start_time
        else:
            if self.duration <= 0:
                messagebox.showerror("Error", "Cannot estimate duration.")
                return
            clip_duration = self.duration - start_time

        if clip_duration <= 0:
            messagebox.showerror("Error", "Clip duration must be greater than 0.")
            return

        sample_duration = min(clip_duration, 3.0)
        if sample_duration < 0.5:
            sample_duration = clip_duration

        try:
            out_w, out_h = self.compute_output_resolution()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        in_path = Path(self.video_path)
        ffmpeg_path = DEFAULT_FFMPEG if os.path.exists(DEFAULT_FFMPEG) else "ffmpeg"
        gifski_path = DEFAULT_GIFSKI if os.path.exists(DEFAULT_GIFSKI) else "gifski"

        self.set_status("Estimating GIF size...")
        self.estimate_button.config(state="disabled")
        self.estimate_running = True

        thread = threading.Thread(
            target=self._run_estimate,
            args=(
                ffmpeg_path,
                gifski_path,
                str(in_path),
                quality,
                out_fps,
                start_time,
                sample_duration,
                clip_duration,
                out_w,
                out_h,
            ),
            daemon=True,
        )
        thread.start()

    def _run_estimate(
        self,
        ffmpeg_path,
        gifski_path,
        input_path,
        quality,
        out_fps,
        start_time,
        sample_duration,
        clip_duration,
        out_w,
        out_h,
    ):
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
                tmp_path = tmp.name

            ff_args = [ffmpeg_path]
            if start_time is not None and start_time > 0:
                ff_args += ["-ss", f"{start_time:.3f}"]
            if sample_duration is not None and sample_duration > 0:
                ff_args += ["-t", f"{sample_duration:.3f}"]
            ff_args += ["-i", input_path, "-pix_fmt", "yuv420p"]

            vf_filters = []
            if out_w is not None and out_h is not None:
                vf_filters.append(f"scale={out_w}:{out_h}")
            if vf_filters:
                ff_args += ["-vf", ",".join(vf_filters)]

            ff_args += ["-f", "yuv4mpegpipe", "-"]

            gif_args = [
                gifski_path,
                "--fps", str(out_fps),
                "--quality", str(quality),
            ]

            if out_w is not None and out_h is not None:
                gif_args += [
                    "--width", str(out_w),
                    "--height", str(out_h),
                ]

            gif_args += [
                "-o", tmp_path,
                "-"
            ]

            popen_kwargs = {}
            if os.name == "nt":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            ff_proc = subprocess.Popen(
                ff_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **popen_kwargs,
            )
            gif_proc = subprocess.Popen(
                gif_args,
                stdin=ff_proc.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                **popen_kwargs,
            )
            ff_proc.stdout.close()

            _, ff_err = ff_proc.communicate()
            _, gif_err = gif_proc.communicate()

            ff_err_txt = ff_err.decode(errors="ignore")
            gif_err_txt = gif_err.decode(errors="ignore")

            if gif_proc.returncode != 0:
                raise RuntimeError(f"gifski failed:\n{gif_err_txt}")

            if ff_proc.returncode != 0:
                if ("Broken pipe" not in ff_err_txt
                        and "Error writing trailer of pipe" not in ff_err_txt):
                    raise RuntimeError(f"ffmpeg failed:\n{ff_err_txt}")

            sample_size = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
            if sample_size <= 0:
                raise RuntimeError("Sample GIF size is zero or could not be read.")

            factor = clip_duration / sample_duration if sample_duration > 0 else 1.0
            estimated_size = sample_size * factor

            self.root.after(
                0, lambda: self._on_estimate_finished(estimated_size)
            )
        except Exception as e:
            msg = str(e)
            self.root.after(0, lambda: self._on_estimate_error(msg))
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _on_estimate_finished(self, bytes_size):
        self.estimate_running = False
        self.estimate_button.config(state="normal")

        mb = bytes_size / (1024 * 1024)
        kb = bytes_size / 1024

        if mb >= 1.0:
            txt = f"Estimated GIF size: ~{mb:.2f} MB"
        else:
            txt = f"Estimated GIF size: ~{kb:.0f} KB"

        self.set_status(txt)

    def _on_estimate_error(self, msg):
        self.estimate_running = False
        self.estimate_button.config(state="normal")
        self.set_status("Failed to estimate size.")
        messagebox.showerror("Error", f"Failed to estimate size:\n{msg}")

    # -------- Conversion dialog / cancel --------

    def show_convert_dialog(self):
        if self.convert_dialog is not None:
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Converting...")
        dlg.configure(bg=DARK_BG)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        label = tk.Label(dlg, text="Converting to GIF...", bg=DARK_BG, fg=TEXT_FG)
        label.pack(padx=15, pady=(12, 4))

        pb = ttk.Progressbar(dlg, mode="indeterminate", length=220)
        pb.pack(padx=15, pady=4)
        pb.start(10)

        btn = tk.Button(
            dlg,
            text="Cancel",
            width=10,
            bg=BTN_BG,
            fg=BTN_FG,
            activebackground="#4a4a4a",
            activeforeground=BTN_FG,
            relief="flat",
            command=self.on_cancel_convert,
        )
        btn.pack(padx=15, pady=(4, 12))

        dlg.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (dlg.winfo_width() // 2)
        y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (dlg.winfo_height() // 2)
        dlg.geometry(f"+{x}+{y}")

        dlg.protocol("WM_DELETE_WINDOW", self.on_cancel_convert)

        self.convert_dialog = dlg
        self.convert_progress = pb
        self.convert_cancel_button = btn

    def hide_convert_dialog(self):
        if self.convert_dialog is not None:
            try:
                if self.convert_progress is not None:
                    self.convert_progress.stop()
            except Exception:
                pass
            self.convert_dialog.destroy()
        self.convert_dialog = None
        self.convert_progress = None
        self.convert_cancel_button = None

    def on_cancel_convert(self):
        if self.cancel_requested:
            return
        self.cancel_requested = True
        self.set_status("Canceling conversion...")
        if self.convert_cancel_button is not None:
            self.convert_cancel_button.config(state="disabled")
        for proc in (self.current_ff_proc, self.current_gif_proc):
            if proc is not None:
                try:
                    proc.terminate()
                except Exception:
                    pass

    # -------- Drag & drop --------

    def on_drop_files(self, event):
        """Called when a video file is dropped onto the window from the file explorer."""
        data = event.data.strip()
        if not data:
            return

        path = None
        if "{" in data and "}" in data:
            import re
            matches = re.findall(r"\{([^}]*)\}", data)
            if matches:
                path = matches[0]
        else:
            path = data

        if not path:
            return

        if os.path.isfile(path):
            self.load_video(path)
            self.root.focus_force()

    # -------- Misc --------

    def set_status(self, text):
        self.status_label.config(text=text)


if __name__ == "__main__":
    if TKDND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = VideoToGifApp(root)
    root.mainloop()
