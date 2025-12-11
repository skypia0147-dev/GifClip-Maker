
import sys
import os
import subprocess
import glob
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QSlider, QLabel, QFileDialog, QListWidget, QComboBox,
    QMessageBox, QGroupBox, QLineEdit, QSplitter, QFrame, QSpinBox, 
    QProgressBar, QSizePolicy, QSpacerItem, QStyle, QStyleOptionSlider
)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, QThread, pyqtSignal, QSize, QEvent, QRect, QSettings
from PyQt6.QtGui import QPainter, QColor, QPen, QIcon
import cv2 # For metadata probing

# -------- Helpers --------

def get_base_dir():
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

BASE_DIR = get_base_dir()

# Dependency Paths
DEFAULT_FFMPEG = str(BASE_DIR / "ffmpeg.exe")
DEFAULT_GIFSKI = str(BASE_DIR / "gifski.exe")

def compute_output_resolution(orig_w, orig_h, resize_mode, custom_w, custom_h, scale_percent):
    if resize_mode == "Scale (%)":
        ratio = scale_percent / 100.0
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)
        # Ensure even coordinates for ffmpeg
        if new_w % 2 != 0: new_w += 1
        if new_h % 2 != 0: new_h += 1
        return new_w, new_h
        
    elif resize_mode == "Custom Dimensions":
        # Ensure even
        w = custom_w if custom_w % 2 == 0 else custom_w + 1
        h = custom_h if custom_h % 2 == 0 else custom_h + 1
        return w, h
        
    elif resize_mode == "Original":
        return orig_w, orig_h
        
    # Presets like "1920x1080 (1080p)"
    # We parse the width/height from string or just map targets?
    # Actually UI localized strings might make parsing hard.
    # Better to detecting numbers in string?
    # "1280x720 (720p)" -> extract 1280, 720
    import re
    m = re.match(r"(\d+)x(\d+)", resize_mode)
    if m:
        return int(m.group(1)), int(m.group(2))
        
    # Fallback "Scale 75%" etc
    if "Scale" in resize_mode and "%" in resize_mode:
        # Extract number
        m = re.search(r"(\d+)%", resize_mode)
        if m:
            ratio = int(m.group(1)) / 100.0
            new_w = int(orig_w * ratio)
            new_h = int(orig_h * ratio)
            if new_w % 2 != 0: new_w += 1
            if new_h % 2 != 0: new_h += 1
            return new_w, new_h
            
    return orig_w, orig_h

TEXTS = {
    "en": {
        "title": "Video to GIF Tool (PyQt6)",
        "open_video": "Open Video",
        "play": "Play",
        "pause": "Pause",
        "convert": "Convert",
        "settings": "Settings",
        "format": "Output Format:",
        "fps": "FPS:",
        "quality": "Quality (1-100):",
        "resize": "Resize:",
        "width": "Width:",
        "height": "Height:",
        "scale": "Scale (%):",
        "batch_list": "Batch List",
        "clear_batch": "Clear Batch",
        "converting": "Converting...",
        "ready": "Ready",
        "done": "Done",
        "error": "Error",
        "msg_select_video": "Please select at least one video to convert.",
        "msg_select_warning": "No Selection",
        "msg_start_set": "Start set to {:.2f}s",
        "msg_end_set": "End set to {:.2f}s",
        "msg_end_error": "End time cannot be before Start time",
        "set_start": "Set Start",
        "set_end": "Set End",
        "remove_selected": "Remove Selected",
        "estimate_size": "Estimate Size",
        "cancel": "Cancel",
        "msg_loaded": "Loaded: {}",
        "msg_removed": "Removed: {}"
    },
    "kr": {
        "title": "비디오 GIF 변환 툴",
        "open_video": "비디오 열기",
        "play": "재생",
        "pause": "일시정지",
        "convert": "변환하기",
        "settings": "설정",
        "format": "출력 포맷:",
        "fps": "FPS:",
        "quality": "품질 (1-100):",
        "resize": "크기 조절:",
        "width": "너비:",
        "height": "높이:",
        "scale": "비율 (%):",
        "batch_list": "일괄 목록",
        "clear_batch": "목록 비우기",
        "converting": "변환 중...",
        "ready": "준비됨",
        "done": "완료",
        "error": "오류",
        "msg_select_video": "변환할 비디오를 하나 이상 선택해주세요.",
        "msg_select_warning": "선택 없음",
        "msg_start_set": "시작 시간 설정: {:.2f}초",
        "msg_end_set": "종료 시간 설정: {:.2f}초",
        "msg_end_error": "종료 시간은 시작 시간보다 앞설 수 없습니다",
        "set_start": "시작 설정",
        "set_end": "종료 설정",
        "remove_selected": "선택 삭제",
        "estimate_size": "용량 예측",
        "cancel": "취소",
        "msg_loaded": "로드됨: {}",
        "msg_removed": "삭제됨: {}"
    }
}

# Styles
DARK_STYLESHEET = """
QMainWindow {
    background-color: #2b2b2b;
    color: #ffffff;
}
QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #555;
    margin-top: 10px;
    font-weight: bold;
    border-radius: 4px;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 3px;
    color: #aaa;
    background-color: #2b2b2b;
}
QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #505050;
    border-color: #666;
}
QPushButton:pressed {
    background-color: #2a2a2a;
}
QPushButton:disabled {
    background-color: #2b2b2b;
    color: #777;
    border-color: #444;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #1e1e1e;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 4px;
    color: #fff;
    selection-background-color: #3b8edb;
}
QListWidget {
    background-color: #1e1e1e;
    border: 1px solid #555;
    border-radius: 4px;
}
QSlider::groove:horizontal {
    border: 1px solid #3d3d3d;
    height: 6px;
    background: #1e1e1e;
    margin: 2px 0;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #3b8edb;
    border: 1px solid #3b8edb;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QProgressBar {
    border: 1px solid #555;
    border-radius: 4px;
    text-align: center;
    background-color: #1e1e1e;
}
QProgressBar::chunk {
    background-color: #3b8edb;
}
QLabel {
    background-color: transparent;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 24px;
    height: 16px;
}
QStatusBar {
    background-color: #2b2b2b;
    color: #ccc;
    min-height: 20px;
    padding-bottom: 15px;
}
QStatusBar::item {
    border: none;
}
#lbl_status {
    padding-left: 8px;
    color: #ccc;
}
"""

class RangeSlider(QSlider):
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.start_pos = -1
        self.end_pos = -1
        self.duration = 0

    def set_range_visual(self, start_ms, end_ms, duration):
        self.start_pos = start_ms
        self.end_pos = end_ms
        self.duration = duration
        self.update() # Force redraw

    def paintEvent(self, event):
        super().paintEvent(event)
        
        if self.duration <= 0 or self.start_pos < 0 or self.end_pos < 0 or self.start_pos >= self.end_pos:
            return
            
        painter = QPainter(self)
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        gr = self.style().subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self)
        
        range_len = self.maximum() - self.minimum()
        if range_len <= 0: return

        x_start = gr.left() + (self.start_pos - self.minimum()) / range_len * gr.width()
        x_end = gr.left() + (self.end_pos - self.minimum()) / range_len * gr.width()
        x_start = max(gr.left(), min(x_start, gr.right()))
        x_end = max(gr.left(), min(x_end, gr.right()))
        width = x_end - x_start
        if width <= 0: return
        
        c = QColor(59, 142, 219, 100) # Lighter blue to see handle
        painter.setBrush(c)
        painter.setPen(Qt.PenStyle.NoPen)
        h = gr.height()
        y = gr.top()
        painter.drawRect(int(x_start), int(y), int(width), int(h))

class ConversionThread(QThread):
    progress_signal = pyqtSignal(int, int, str) # current, total, status_message
    finished_signal = pyqtSignal(int, int) # success_count, fail_count
    error_signal = pyqtSignal(str)

    def __init__(self, tasks, ffmpeg_path, gifski_path):
        super().__init__()
        self.tasks = tasks
        self.ffmpeg = ffmpeg_path
        self.gifski = gifski_path
        self.is_running = True
        self.processes = []

    def run(self):
        success = 0
        fail = 0
        total = len(self.tasks)
        
        for idx, task in enumerate(self.tasks):
            if not self.is_running: break
            
            try:
                self.progress_signal.emit(idx, total, f"Converting {idx+1}/{total}: {os.path.basename(task['path'])}")
                self.process_video(task, idx, total)
                success += 1
            except Exception as e:
                print(f"Error converting {task['path']}: {e}")
                fail += 1
        
        self.finished_signal.emit(success, fail)

    def stop(self):
        self.is_running = False
        # Terminate any running subprocesses
        for p in self.processes:
            try:
                p.terminate()
                p.kill() # Ensure kill
            except Exception as e:
                print(f"Error killing process: {e}")
        self.processes.clear()

    def process_video(self, task, idx, total):
        # 1. Prepare Paths
        src = task['path']
        folder = os.path.dirname(src)
        name = os.path.splitext(os.path.basename(src))[0]
        ext = "gif" if task['format'] == "GIF" else "webp"
        
        # Ensure unique output name
        counter = 1
        out = os.path.join(folder, f"{name}.{ext}")
        while os.path.exists(out):
            out = os.path.join(folder, f"{name}_{counter}.{ext}")
            counter += 1
            
        settings = task['settings']
        
        # 2. Compute Resolution
        w, h = compute_output_resolution(
            settings['orig_width'], settings['orig_height'],
            settings['resize_mode'], settings['width'], settings['height'],
            settings['scale']
        )
        print(f"Resolving '{settings['resize_mode']}': {settings['orig_width']}x{settings['orig_height']} -> {w}x{h}")
        
        # 3. Trim Filters
        ss = settings['start_time'] / 1000.0 if settings['start_time'] >= 0 else 0
        to = settings['end_time'] / 1000.0 if settings['end_time'] >= 0 else 0
        
        bn = os.path.basename(task['path'])
        self.progress_signal.emit(idx, total, f"Converting {bn} ({w}x{h})...")
        
        # 4. Execute
        if task['format'] == "GIF":
            self.convert_to_gif(src, out, w, h, ss, to, settings['fps'], settings['quality'])
        else:
            self.convert_to_webp(src, out, w, h, ss, to, settings['fps'], settings['quality'])

    def convert_to_gif(self, src, out, w, h, ss, to, fps, quality):
        # 1. Try Gifski if available (Legacy/High Quality)
        if self.gifski and os.path.exists(self.gifski):
            # FFmpeg: Trim -> FPS -> Scale -> Pipe
            vf = f"fps={fps},scale={w}:{h}:flags=lanczos"
            time_args = []
            if ss > 0: time_args.extend(["-ss", str(ss)])
            if to > 0: time_args.extend(["-to", str(to)])
            
            # Ensure yuv420p for compatibility
            ff_cmd = [self.ffmpeg, "-y"] + time_args + ["-i", src, "-vf", vf, "-pix_fmt", "yuv420p", "-f", "yuv4mpegpipe", "-"]
            
            # Gifski: Read from - 
            gif_cmd = [
                self.gifski,
                "--fps", str(fps),
                "--quality", str(quality),
                "--width", str(w),
                "--height", str(h),
                "-o", out,
                "-"
            ]

            try:
                # Pipe
                # Deadlock Fix: Use DEVNULL for ffmpeg stderr to prevent buffer block if we don't read it immediately.
                ff_proc = subprocess.Popen(
                    ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, startupinfo=self.get_startup_info()
                )
                self.processes.append(ff_proc)
                
                gif_proc = subprocess.Popen(
                    gif_cmd, stdin=ff_proc.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, startupinfo=self.get_startup_info()
                )
                self.processes.append(gif_proc)
                
                try:
                    # Close ff_proc stdout in this process so pipe closes when ff finishes
                    ff_proc.stdout.close()
                    _, gif_err = gif_proc.communicate()
                    ff_proc.wait() # Wait for FFmpeg to exit
                    
                    if gif_proc.returncode != 0:
                        err_msg = gif_err.decode('utf-8', errors='ignore') or "Unknown Gifski error"
                        # If stopped, returncode might be != 0 but is_running false.
                        if self.is_running:
                             raise RuntimeError(f"Gifski failed: {err_msg}")
                        
                    if ff_proc.returncode != 0 and ff_proc.returncode != 255:
                         # Since we ignored stderr, we can't report exact ffmpeg error, but usually Gifski error covers it (broken pipe)
                         # or we just fail silently for ffmpeg part if gifski succeeded? 
                         # If gifski succeeded (code 0), then ffmpeg must have fed data.
                         pass
                finally:
                    if ff_proc in self.processes: self.processes.remove(ff_proc)
                    if gif_proc in self.processes: self.processes.remove(gif_proc)
                         
            except Exception as e:
                # If Gifski fails, we should probably output the error rather than silently fallback?
                # The user specifically complained about palette.png, so fallback is unwanted.
                print(f"Gifski execution failed: {e}")
                raise e # Propagate error
                
            return

        # 2. Fallback to FFmpeg palettegen/paletteuse ONLY if Gifski missing
        # ... logic ...
        # Palette Gen
        palette_path = os.path.join(os.path.dirname(out), "palette.png")
        
        vf = f"fps={fps},scale={w}:{h}:flags=lanczos"
        
        time_args = []
        if ss > 0: time_args.extend(["-ss", str(ss)])
        if to > 0: time_args.extend(["-to", str(to)])
        
        if to > 0: time_args.extend(["-to", str(to)])
        
        # 1. Generate Palette
        cmd_pal = [self.ffmpeg, "-y"] + time_args + ["-i", src, "-vf", f"{vf},palettegen", palette_path]
        try:
            self.run_command_simple(cmd_pal, "Palette Gen")
        except:
             # Cleanup if failed
             pass

        # 2. Convert
        cmd_gif = [self.ffmpeg, "-y"] + time_args + ["-i", src, "-i", palette_path, 
                   "-lavfi", f"{vf} [x]; [x][1:v] paletteuse", out]
        try:
            self.run_command_simple(cmd_gif, "GIF Convert")
        except Exception as e:
            raise e
        finally:
            if os.path.exists(palette_path):
                os.remove(palette_path)

    def convert_to_webp(self, src, out, w, h, ss, to, fps, quality):
        # Native WebP Strategy (Optimized for Small Size)
        # We bypassed GIF completely to avoid dithering noise bloat.
        # We use standard yuv420p (4:2:0) subsampling which is standard for video/web.
        
        # Quality Mapping:
        # User requested aggressive quality settings: "Quality 1 (1.0x)" and "YUV444P".
        # This disables the safety cap. Q100 input = WebP Q100 output.
        # This WILL produce larger files, but offers maximum fidelity.
        webp_q = int(quality * 1.0)
        if webp_q < 1: webp_q = 1
        
        vf = f"fps={fps},scale={w}:{h}:flags=lanczos"
        time_args = []
        if ss > 0: time_args.extend(["-ss", str(ss)])
        if to > 0: time_args.extend(["-to", str(to)])
        
        cmd = [self.ffmpeg, "-y"] + time_args + ["-i", src]
        cmd.extend(["-vf", vf, "-c:v", "libwebp", "-lossless", "0", 
                    "-compression_level", "6", "-q:v", str(webp_q), 
                    "-preset", "default", "-loop", "0", "-an", "-vsync", "0", 
                    "-pix_fmt", "yuv444p", out])
                    
        self.run_command_simple(cmd, "WebP Conversion")

    def run_command_simple(self, cmd, desc="Command"):
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=self.get_startup_info())
        self.processes.append(p)
        try:
            p.wait()
            if p.returncode != 0: raise RuntimeError(f"{desc} Failed")
        finally:
            if p in self.processes: self.processes.remove(p)

    def get_startup_info(self):
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            return si
        return None

class EstimateThread(QThread):
    finished_signal = pyqtSignal(str) # Result message
    
    # Updated to support Batch Estimation (List of tasks)
    def __init__(self, tasks, ffmpeg, gifski):
        super().__init__()
        self.tasks = tasks if isinstance(tasks, list) else [tasks]
        self.ffmpeg = ffmpeg
        self.gifski = gifski
        self.processes = []
        
    def stop(self):
        # Stop any running estimation
        for p in self.processes:
            try:
                if p.poll() is None:
                    p.terminate()
                    p.kill()
            except Exception as e:
                print(f"Error killing estimate process: {e}")
        self.processes.clear()
        
        # We don't have a loop like ConversionThread, but we can try to ensure
        # we don't emit signals if stopped? 
        # Actually checking self.isInterruptionRequested() might be good if we were in a loop.
        # But here we are linear. We just kill processes.

    def run(self):
        results = []
        
        for idx, task in enumerate(self.tasks):
            if self.isInterruptionRequested(): break
            
            try:
                path = task["path"]
                s = task["settings"]
                fmt = s["format"].lower() 
                filename = os.path.basename(path)
                
                # Duration needed
                total_duration = s.get("duration", 0)
                if total_duration <= 0:
                    try:
                        cap = cv2.VideoCapture(path)
                        if cap.isOpened():
                            fps = cap.get(cv2.CAP_PROP_FPS)
                            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                            if fps > 0: total_duration = frames / fps
                            cap.release()
                    except: pass
                
                if total_duration <= 0:
                    results.append(f"{filename}: Error (Unknown Duration)")
                    continue

                # Target 2.0 second sample (Middle) - Legacy Method
                sample_dur = 2.0
                if total_duration < sample_dur: sample_dur = total_duration
                
                ss = total_duration / 2.0
                if ss + sample_dur > total_duration: ss = 0
                
                w, h = compute_output_resolution(s['orig_width'], s['orig_height'], s['resize_mode'], 
                                               s['width'], s['height'], s['scale'])
                
                ext = "gif" if "gif" in fmt else "webp"
                self.temp_file = f"temp_estimate_{idx}.{ext}" # Unique file
                
                startup_info = None
                if os.name == 'nt':
                    startup_info = subprocess.STARTUPINFO()
                    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                # Cleanup previous if exists
                if os.path.exists(self.temp_file):
                    try: os.remove(self.temp_file)
                    except: pass

                if "gif" in fmt:
                     # GIFSKI Pipeline (yuv4mpegpipe)
                     cmd_gifski = [self.gifski, "-o", self.temp_file]
                     cmd_gifski.extend(["--fps", str(s['fps']), "--quality", str(s['quality'])])
                     if w > 0 and h > 0:
                         cmd_gifski.extend(["--width", str(w), "--height", str(h)])
                     cmd_gifski.append("-")
                     
                     gif_proc = subprocess.Popen(cmd_gifski, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startup_info)
                     self.processes.append(gif_proc)
                     
                     vf_filters = []
                     if w > 0 and h > 0:
                          vf_filters.append(f"scale={w}:{h}:flags=lanczos")
                     
                     cmd_ffmpeg = [self.ffmpeg, "-y", "-ss", str(ss), "-t", str(sample_dur), "-i", path]
                     if vf_filters:
                         cmd_ffmpeg.extend(["-vf", ",".join(vf_filters)])
                     
                     cmd_ffmpeg.extend(["-pix_fmt", "yuv420p", "-f", "yuv4mpegpipe", "-"])
                     
                     ff_proc = subprocess.Popen(cmd_ffmpeg, stdout=gif_proc.stdin, stderr=subprocess.DEVNULL, startupinfo=startup_info)
                     self.processes.append(ff_proc)
                     
                     try:
                        ff_proc.wait()
                        gif_proc.communicate()
                        
                        if ff_proc.returncode != 0 and ff_proc.returncode != 255:
                            raise RuntimeError(f"FFmpeg Error {ff_proc.returncode}")
                        if gif_proc.returncode != 0:
                            raise RuntimeError(f"Gifski Error {gif_proc.returncode}")
                     finally:
                        if ff_proc in self.processes: self.processes.remove(ff_proc)
                        if gif_proc in self.processes: self.processes.remove(gif_proc)
                     
                else:
                    # WebP (Native Optimized - High Quality)
                    webp_q = int(s['quality'] * 1.0)
                    if webp_q < 1: webp_q = 1
                    
                    vf_filters = []
                    if w > 0 and h > 0:
                        vf_filters.append(f"scale={w}:{h}:flags=lanczos")
                    vf_filters.append(f"fps={s['fps']}")
                    
                    cmd = [self.ffmpeg, "-y", "-ss", str(ss), "-t", str(sample_dur), "-i", path]
                    if vf_filters:
                         cmd.extend(["-vf", ",".join(vf_filters)])
                    
                    cmd.extend(["-c:v", "libwebp", "-lossless", "0", 
                                "-compression_level", "4", "-q:v", str(webp_q), 
                                "-preset", "default", "-loop", "0", "-an", "-vsync", "0", 
                                "-pix_fmt", "yuv444p", self.temp_file])
                    
                    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startup_info)
                    self.processes.append(p)
                    try:
                        p.wait()
                        if p.returncode != 0:
                            raise RuntimeError(f"WebP Error {p.returncode}")
                    finally:
                        if p in self.processes: self.processes.remove(p)

                # Check size
                if os.path.exists(self.temp_file):
                    size_bytes = os.path.getsize(self.temp_file)
                    if size_bytes > 0:
                        ratio = total_duration / sample_dur
                        est_total = size_bytes * ratio
                        mb = est_total / (1024 * 1024)
                        results.append(f"{filename}: ~{mb:.1f} MB (Expected)")
                    else:
                        results.append(f"{filename}: Error (0 bytes)")
                    
                    # Cleanup temp immediate
                    try: os.remove(self.temp_file)
                    except: pass
                else:
                    results.append(f"{filename}: Error (File not created)")
                    
            except Exception as e:
                results.append(f"{task.get('path','Unknown')}: Error ({str(e)})")
            finally:
                # Cleanup processes just in case
                for p in self.processes:
                    if p.poll() is None:
                        p.terminate()
                        p.wait(timeout=0.5)
                self.processes.clear()
        
        # Emit all results joined
        report = "\n".join(results)
        self.finished_signal.emit(report)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Persistence
        self.settings = QSettings("VideoToGifTool", "Settings")

        # Load Language (Default: English)
        self.lang = self.settings.value("language", "en") 
        
        self.setWindowTitle("VideoToGifTool")
        self.setWindowIcon(QIcon(str(BASE_DIR / "app_icon.ico")))
        self.resize(1160, 750) # Increase total width slightly
        self.setAcceptDrops(True)

        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        # Fix: QVideoWidget can block Drag&Drop. Enable drops and filter events.
        self.video_widget.setAcceptDrops(True)
        self.video_widget.installEventFilter(self)
        
        self.video_files = []
        self.video_settings = {} # Path -> Dict of settings
        self.duration = 0
        self.range_start = -1
        self.range_end = -1
        
        # Block signals flag
        self._updating_ui = False
        
        # State for Seek
        self.was_playing_before_drag = False
        
        self.converter_thread = None
        self.estimate_thread = None # Added for estimate feature

        self._init_ui()
        self.setStyleSheet(DARK_STYLESHEET)
        
        self.media_player.positionChanged.connect(self.on_position_changed)
        self.media_player.durationChanged.connect(self.on_duration_changed)
        self.media_player.errorOccurred.connect(self.handle_media_error)
        self.media_player.playbackStateChanged.connect(self.update_play_button_text)
        self.update_texts()

    def tr(self, key):
        return TEXTS.get(self.lang, TEXTS["en"]).get(key, key)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # --- Left Area ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self.video_widget)
        
        # Timeline Controls
        ctrl_panel = QFrame()
        ctrl_panel.setStyleSheet("background-color: #222; border-radius: 8px;")
        ctrl_layout = QHBoxLayout(ctrl_panel)
        
        self.btn_play = QPushButton("Play")
        self.btn_play.setFixedWidth(80)
        self.btn_play.clicked.connect(self.toggle_play)
        
        self.lbl_current = QLabel("00:00")
        self.lbl_current.setFixedWidth(50)
        self.lbl_current.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.slider = RangeSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.set_position)
        # Fix: Capture state on press, recover on release
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        
        self.lbl_total = QLabel("00:00")
        self.lbl_total.setFixedWidth(50)
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.lbl_current)
        ctrl_layout.addWidget(self.slider)
        ctrl_layout.addWidget(self.lbl_total)
        
        left_layout.addWidget(ctrl_panel)
        
        # --- Range Selection Area (Bottom Left) ---
        range_panel = QFrame()
        range_layout = QHBoxLayout(range_panel)
        range_layout.setContentsMargins(0, 5, 0, 5)
        
        # 1. Open/Language (Swapped to Left)
        self.btn_open = QPushButton("Open Video")
        self.btn_open.clicked.connect(self.open_file_dialog)
        
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["English", "한국어"])
        # Set initial selection based on self.lang (loaded in __init__)
        index = self.combo_lang.findText("한국어" if self.lang == "kr" else "English")
        if index >= 0:
            self.combo_lang.setCurrentIndex(index)
        else:
             self.combo_lang.setCurrentIndex(0) # Default English
             
        # Connect signal AFTER setting index to avoid triggering update_texts() 
        # before UI is fully built (AttributeError: grp_settings)
        self.combo_lang.currentIndexChanged.connect(self.on_language_change)
        
        self.combo_lang.setFixedWidth(80)
        
        range_layout.addWidget(self.btn_open)
        range_layout.addWidget(self.combo_lang)
        range_layout.addStretch() # Spacer middle
        
        # 2. Range Controls (Swapped to Right)
        self.btn_set_start = QPushButton("Set Start")
        self.btn_set_start.clicked.connect(self.set_start_from_current)
        self.entry_start = QLineEdit()
        self.entry_start.setPlaceholderText("0.0")
        self.entry_start.setFixedWidth(60)

        self.btn_set_end = QPushButton("Set End")
        self.btn_set_end.clicked.connect(self.set_end_from_current)
        self.entry_end = QLineEdit()
        self.entry_end.setPlaceholderText("End")
        self.entry_end.setFixedWidth(60)
        
        range_layout.addWidget(self.btn_set_start)
        range_layout.addWidget(self.entry_start)
        range_layout.addSpacing(10)
        range_layout.addWidget(self.btn_set_end)
        range_layout.addWidget(self.entry_end)

        left_layout.addWidget(range_panel)
        
        # --- Right Area: Sidebar ---
        sidebar = QWidget()
        sidebar.setFixedWidth(360) # Increased bandwidth (300 -> 360)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 0, 0, 0)
        
        # Settings Group
        self.grp_settings = QGroupBox("Settings")
        form_layout = QVBoxLayout(self.grp_settings)
        
        # Format
        fmt_layout = QHBoxLayout()
        self.lbl_format = QLabel("Format:")
        self.combo_format = QComboBox()
        self.combo_format.addItems(["GIF", "WebP"])
        fmt_layout.addWidget(self.lbl_format)
        fmt_layout.addWidget(self.combo_format)
        form_layout.addLayout(fmt_layout)
        
        # FPS & Quality
        fq_layout = QHBoxLayout()
        self.lbl_fps = QLabel("FPS:")
        self.lbl_fps.setFixedWidth(30) # Reduced gap
        self.spin_fps = QSpinBox()
        self.spin_fps.setRange(1, 60)
        self.spin_fps.setValue(20)
        
        self.lbl_quality = QLabel("Quality:")
        self.lbl_quality.setFixedWidth(100)
        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(1, 100)
        self.spin_quality.setValue(80)
        
        fq_layout.addWidget(self.lbl_fps)
        fq_layout.addWidget(self.spin_fps)
        fq_layout.addSpacing(20) # Increased gap
        fq_layout.addWidget(self.lbl_quality)
        fq_layout.addWidget(self.spin_quality)
        form_layout.addLayout(fq_layout)
        
        # Resize
        self.grp_resize = QGroupBox("Resize")
        res_layout = QVBoxLayout(self.grp_resize)
        
        self.combo_resize_mode = QComboBox()
        self.combo_resize_mode.addItems([
            "Original", 
            "1920x1080 (1080p)", "1280x720 (720p)", "640x480 (480p)", "480x360 (360p)",
            "Scale 75%", "Scale 50%", "Scale 33%", "Scale 25%",
            "Custom Dimensions", "Scale (%)"
        ])
        self.combo_resize_mode.currentIndexChanged.connect(self.update_resize_ui)
        
        self.req_width_layout = QHBoxLayout()
        self.lbl_width = QLabel("W:")
        self.spin_width = QSpinBox()
        self.spin_width.setRange(10, 7680)
        self.spin_width.setValue(800)
        
        self.lbl_height = QLabel("H:")
        self.spin_height = QSpinBox() # Logic will auto-calc usually, but UI present
        self.spin_height.setRange(10, 4320)
        self.spin_height.setValue(600)
        self.spin_height.setEnabled(False) # Default disabled unless custom full
        
        self.req_width_layout.addWidget(self.lbl_width)
        self.req_width_layout.addWidget(self.spin_width)
        self.req_width_layout.addWidget(self.lbl_height)
        self.req_width_layout.addWidget(self.spin_height)
        
        self.req_scale_layout = QHBoxLayout()
        self.lbl_scale = QLabel("Scale:")
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(1, 100)
        self.spin_scale.setValue(100)
        self.req_scale_layout.addWidget(self.lbl_scale)
        self.req_scale_layout.addWidget(self.spin_scale)
        
        res_layout.addWidget(self.combo_resize_mode)
        res_layout.addLayout(self.req_width_layout)
        res_layout.addLayout(self.req_scale_layout)
        
        form_layout.addWidget(self.grp_resize)
        side_layout.addWidget(self.grp_settings)
        
        # Batch List
        self.grp_batch = QGroupBox("Batch List")
        batch_layout = QVBoxLayout(self.grp_batch)
        self.list_batch = QListWidget()
        self.list_batch.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_batch.itemSelectionChanged.connect(self.on_selection_changed)
        
        batch_btn_layout = QHBoxLayout()
        self.btn_remove_sel = QPushButton("Remove Selected")
        self.btn_remove_sel.clicked.connect(self.remove_selected_file)
        self.btn_clear_batch = QPushButton("Clear")
        self.btn_clear_batch.clicked.connect(self.clear_batch)
        
        batch_layout.addWidget(self.list_batch)
        batch_btn_layout.addWidget(self.btn_remove_sel)
        batch_btn_layout.addWidget(self.btn_clear_batch)
        batch_layout.addLayout(batch_btn_layout)
        
        side_layout.addWidget(self.grp_batch)
        
        # Convert Action
        action_layout = QHBoxLayout()
        self.btn_estimate = QPushButton("Estimate Size")
        self.btn_estimate.setFixedWidth(100) # Increased width for longer text
        self.btn_estimate.clicked.connect(self.estimate_size)
        self.btn_convert = QPushButton("CONVERT")
        self.btn_convert.setFixedHeight(40)
        self.btn_convert.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_convert.setStyleSheet("""
            QPushButton {
                background-color: #3b8edb; 
                font-weight: bold; 
                font-size: 16px;
                font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
                padding-top: 0px;
                padding-bottom: 4px;
                border: 1px solid #3b8edb;
            }
            QPushButton:pressed { background-color: #2a7bbd; }
        """)
        self.btn_convert.clicked.connect(self.on_convert_click)
        
        action_layout.addWidget(self.btn_estimate)
        action_layout.addWidget(self.btn_convert)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        
        side_layout.addLayout(action_layout)
        side_layout.addWidget(self.progress_bar)
        
        # Status Bar
        self.status_bar = self.statusBar()
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("lbl_status")
        self.status_bar.addWidget(self.lbl_status, 1)
        # self.status_bar.showMessage("Ready")
        
        # Assemble
        main_layout.addWidget(left_widget, stretch=3)
        main_layout.addWidget(sidebar, stretch=1)
        
        self.update_resize_ui()
        
        # Connect Settings Signals to Save Logic
        self.combo_format.currentIndexChanged.connect(self.save_settings_from_ui)
        self.spin_fps.valueChanged.connect(self.save_settings_from_ui)
        self.spin_quality.valueChanged.connect(self.save_settings_from_ui)
        self.combo_resize_mode.currentIndexChanged.connect(self.save_settings_from_ui)
        self.spin_width.valueChanged.connect(self.save_settings_from_ui)
        self.spin_height.valueChanged.connect(self.save_settings_from_ui)
        self.spin_scale.valueChanged.connect(self.save_settings_from_ui)
        
        # Globally install event filter for Drag & Drop support on all widgets
        self._install_event_filter_recursive(central_widget)

    def _install_event_filter_recursive(self, widget):
        widget.installEventFilter(self)
        for child in widget.children():
            if isinstance(child, QWidget):
                self._install_event_filter_recursive(child)

    # --- Logic ---
    
    def change_language(self, index): # This method is now unused and can be removed if desired.
        self.lang = "en" if index == 0 else "kr"
        self.update_texts()
        
    def update_texts(self):
        self.setWindowTitle(self.tr("title"))
        self.btn_open.setText(self.tr("open_video"))
        self.update_play_button_text()
        self.grp_settings.setTitle(self.tr("settings"))
        self.lbl_format.setText(self.tr("format"))
        self.lbl_fps.setText(self.tr("fps"))
        self.lbl_quality.setText(self.tr("quality"))
        self.grp_resize.setTitle(self.tr("resize"))
        self.lbl_width.setText(self.tr("width"))
        self.lbl_height.setText(self.tr("height")) # Added missing translation for height
        self.lbl_scale.setText(self.tr("scale"))
        
        # Update status text if it was "Ready" or "Done" or localized variant?
        # Simpler: just set to Ready if idle? Or leave as is?
        # User might want localization of "Ready". 
        # self.status_bar.showMessage(self.tr("ready")) -> self.lbl_status.setText
        self.lbl_status.setText(self.tr("ready"))
        
        self.on_selection_changed() # Refresh UI elements (Dropdowns etc)
        self.grp_batch.setTitle(self.tr("batch_list"))
        self.btn_clear_batch.setText(self.tr("clear_batch"))
        self.btn_convert.setText(self.tr("convert"))
        self.btn_set_start.setText(self.tr("set_start"))
        self.btn_set_end.setText(self.tr("set_end"))
        self.btn_remove_sel.setText(self.tr("remove_selected"))
        self.btn_estimate.setText(self.tr("estimate_size"))

    def update_resolution_combo(self, w, h):
        # Generate dynamic resolution options based on aspect ratio
        if w <= 0 or h <= 0: # Safe against 0x0
            # If dimensions are invalid, provide a default set of options
            items = [
                "Original",
                "1920x1080 (1080p)", "1280x720 (720p)", "640x480 (480p)", "480x360 (360p)",
                "Scale 75%", "Scale 50%", "Scale 33%", "Scale 25%",
                "Custom Dimensions", "Scale (%)"
            ]
            self.combo_resize_mode.blockSignals(True)
            self.combo_resize_mode.clear()
            self.combo_resize_mode.addItems(items)
            self.combo_resize_mode.blockSignals(False)
            return
        
        # Keep current text to restore if possible
        current = self.combo_resize_mode.currentText()
        
        aspect = w / h
        
        # Targets: 1080p, 720p, 480p, 360p (based on Height)
        # Exception: if source is smaller? No, usually offer standard up/down scales.
        # But we must respect aspect ratio.
        targets = [1080, 720, 480, 360]
        
        items = ["Original"]
        for t_h in targets:
            t_w = int(t_h * aspect)
            # Even numbers preferred
            if t_w % 2 != 0: t_w += 1
            items.append(f"{t_w}x{t_h} ({t_h}p)")
            
        items.extend([
            "Scale 75%", "Scale 50%", "Scale 33%", "Scale 25%",
            "Custom Dimensions", "Scale (%)"
        ])
        
        self.combo_resize_mode.blockSignals(True)
        self.combo_resize_mode.clear()
        self.combo_resize_mode.addItems(items)
        self.combo_resize_mode.blockSignals(False)
        
        # Restore selection? 
        # Logic in load_settings_to_ui handles selection.

    def update_resize_ui(self):
        text = self.combo_resize_mode.currentText()
        
        is_custom_dim = (text == "Custom Dimensions")
        is_custom_scale = (text == "Scale (%)")
        
        self.lbl_width.setVisible(is_custom_dim)
        self.spin_width.setVisible(is_custom_dim)
        self.lbl_height.setVisible(is_custom_dim)
        self.spin_height.setVisible(is_custom_dim)
        
        self.lbl_scale.setVisible(is_custom_scale)
        self.spin_scale.setVisible(is_custom_scale)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.DragEnter:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True
        elif event.type() == QEvent.Type.Drop:
            if event.mimeData().hasUrls():
                self.dropEvent(event)
                return True
        return super().eventFilter(source, event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
            self.add_files(paths)
            event.acceptProposedAction()

    def open_file_dialog(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, self.tr("open_video"), "", "Video Files (*.mp4 *.avi *.mov *.mkv *.ts)")
        if fnames:
            self.add_files(fnames)

    def add_files(self, paths):
        # Filter existing
        new_files = [p for p in paths if p not in self.video_files]
        if not new_files:
            return
            
        self.video_files.extend(new_files)
        
            
        # Add to list widget & Init settings
        for p in new_files:
            self.list_batch.addItem(os.path.basename(p))
            
            # Probe FPS and Init Settings
            fps = 0 # Default to 0, will be handled by fallback
            w, h = 0, 0
            try:
                cap = cv2.VideoCapture(p)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    duration = frames / fps if fps > 0 else 0
                    cap.release()
            except Exception as e:
                print(f"Error probing video {p}: {e}")
                pass
            
            print(f"Loaded {p}: {w}x{h} ({fps} fps)")
            
            # Fallback if probe failed or values are invalid
            orig_w = w if w > 0 else 800
            orig_h = h if h > 0 else 600
            
            self.video_settings[p] = {
                "format": "GIF",
                "fps": int(fps) if fps > 0 else 20, # Default 20 per fix
                "quality": 80,
                "resize_mode": "Original", # Changed from self.tr("res_original")
                "width": orig_w, # Default to original width
                "height": orig_h, # Default to original height
                "scale": 100, # Default to 100% scale
                "start_time": -1,
                "end_time": -1,
                "orig_width": orig_w,
                "orig_height": orig_h,
                "duration": duration if 'duration' in locals() else 0
            }
            
        # If this was the first file, load it
        if len(self.video_files) == len(new_files): # Was empty
             self.load_video(self.video_files[0])
             self.list_batch.setCurrentRow(0) # Select first item

        elif len(self.video_files) > 1:
             pass

    def clear_batch(self):
        self.video_files.clear()
        self.list_batch.clear()
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self.slider.setRange(0, 0)
        self.lbl_current.setText("00:00")
        self.lbl_total.setText("00:00")
        self.range_start = -1
        self.range_end = -1
        self.slider.set_range_visual(-1, -1, 0)

    def load_video(self, path):
        self.media_player.setSource(QUrl.fromLocalFile(path))
        self.btn_play.setText(self.tr("play"))
        self.status_bar.showMessage(self.tr("msg_loaded").format(os.path.basename(path)))
        # Auto-play removed per user request
        
        # NOTE: logic to reset global range vars is moved to load_settings (state restore)
        # or clear_batch. load_video just handles the player.

    def toggle_play(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def update_play_button_text(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText(self.tr("pause"))
        else:
            self.btn_play.setText(self.tr("play"))

    def on_position_changed(self, position):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self.lbl_current.setText(self.format_time(position))
        
    def on_duration_changed(self, duration):
        self.slider.setRange(0, duration)
        self.duration = duration
        self.lbl_total.setText(self.format_time(duration))
        self.slider.set_range_visual(self.range_start, self.range_end, self.duration)

    def set_position(self, position):
        self.media_player.setPosition(position)
        
    def on_slider_pressed(self):
        # Determine if we should resume logic after drag
        self.was_playing_before_drag = (self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        self.media_player.pause()
        
    def on_slider_released(self):
        if self.was_playing_before_drag:
            self.media_player.play()

    def handle_media_error(self):
        self.btn_play.setEnabled(False)
        # self.lbl_current.setText("Error: " + self.media_player.errorString())

    # --- Features ---

    def set_start_from_current(self):
        # Current position in ms
        pos_ms = self.media_player.position()
        self.range_start = pos_ms
        sec = pos_ms / 1000.0
        self.entry_start.setText(f"{sec:.2f}")
        self.status_bar.showMessage(f"Start set to {sec:.2f}s")
        # Ensure correct order
        if self.range_end != -1 and self.range_start > self.range_end:
             self.range_end = -1
             self.entry_end.setText("")
             
        self.save_range_to_settings()
        self.slider.set_range_visual(self.range_start, self.range_end, self.duration)

    def set_end_from_current(self):
        pos_ms = self.media_player.position()
        if self.range_start != -1 and pos_ms < self.range_start:
             self.status_bar.showMessage(self.tr("msg_end_error"))
             return
             
        self.range_end = pos_ms
        sec = pos_ms / 1000.0
        self.entry_end.setText(f"{sec:.2f}")
        self.status_bar.showMessage(self.tr("msg_end_set").format(sec))
        self.slider.set_range_visual(self.range_start, self.range_end, self.duration)
        
        # Save to Current Setting
        self.save_range_to_settings()

    def save_range_to_settings(self):
        # Save current range_start/end to the currently selected item(s) video_settings
        items = self.list_batch.selectedItems()
        for item in items:
            row = self.list_batch.row(item)
            if 0 <= row < len(self.video_files):
                path = self.video_files[row]
                self.video_settings[path]["start_time"] = self.range_start
                self.video_settings[path]["end_time"] = self.range_end

    # --- Settings Management ---

    def on_selection_changed(self):
        # If multiple selected, we show settings of the *first* selected, 
        # but edits could apply to all? User said "Individual settings".
        # Let's simple model: Load settings of the current item (focus).
        # Editing settings updates specific item? Or all selected?
        # Standard: Editing updates ALL selected items.
        
        items = self.list_batch.selectedItems()
        if not items:
            return
            
        # Load settings from the first selected item
        # Find path
        # Assume unique basenames? No, full path is key.
        # We need to map item text to path. Index is safer.
        # Check indices.
        
        row = self.list_batch.row(items[0])
        if row < 0 or row >= len(self.video_files): return
        
        path = self.video_files[row]
        
        # Load video to player if single select?
        # User might want to preview while changing settings.
        if len(items) == 1:
            self.load_video(path)
            
        self.load_settings_to_ui(path)

    def load_settings_to_ui(self, path):
        s = self.video_settings.get(path)
        if not s: return
        
        self._updating_ui = True
        
        # Format
        idx = self.combo_format.findText(s["format"])
        if idx >= 0: self.combo_format.setCurrentIndex(idx)
        
        # FPS & Quality
        self.spin_fps.setValue(s["fps"])
        self.spin_quality.setValue(s["quality"])
        
        # Resolution
        # Update combo options first based on original size
        self.update_resolution_combo(s["orig_width"], s["orig_height"])
        
        # Translate stored mode to current language - Disabled per user request (English Only)
        # But we might need to map old Korean settings hardcodings or broken keys logic back to English
        mode = s["resize_mode"]
        if mode == "원본" or mode == "res_original": mode = "Original"
        if mode == "사용자 지정 크기" or mode == "res_custom": mode = "Custom Dimensions"
        if mode == "비율 (%)" or mode == "res_scale_pct": mode = "Scale (%)"
        
        self.combo_resize_mode.setCurrentText(mode)
        
        # Custom inputs
        self.spin_width.setValue(s["width"])
        self.spin_height.setValue(s["height"])
        self.spin_scale.setValue(s["scale"])
        self.update_resize_ui()
        
        # Restore Range
        # Default is -1 if not set
        r_start = s.get("start_time", -1)
        r_end = s.get("end_time", -1)
        
        self.range_start = r_start
        self.range_end = r_end
        
        # Update UI text
        if r_start >= 0:
            self.entry_start.setText(f"{r_start/1000.0:.2f}")
        else:
            self.entry_start.setText("")
            
        if r_end >= 0:
            self.entry_end.setText(f"{r_end/1000.0:.2f}")
        else:
            self.entry_end.setText("")
            
        # Update Slider Visual
        # Duration is available from media player if loaded?
        # But load_video happens separately. 
        # load_video calls load_settings_to_ui.
        # So duration might generate range visual correctly if media loaded.
        if self.duration > 0:
            self.slider.set_range_visual(self.range_start, self.range_end, self.duration)
        
        self._updating_ui = False
        
    def save_settings_from_ui(self):
        if self._updating_ui: return
        
        items = self.list_batch.selectedItems()
        if not items: return
        
        # Gather current UI values
        new_s = {
            "format": self.combo_format.currentText(),
            "fps": self.spin_fps.value(),
            "quality": self.spin_quality.value(),
            "resize_mode": self.combo_resize_mode.currentText(),
            "width": self.spin_width.value(),
            "height": self.spin_height.value(),
            "scale": self.spin_scale.value()
        }
        
        # Apply to ALL selected items
        for item in items:
            row = self.list_batch.row(item)
            if 0 <= row < len(self.video_files):
                path = self.video_files[row]
                # Update dict (merge)
                self.video_settings[path].update(new_s)

    def on_convert_click(self):
        if hasattr(self, 'converter_thread') and self.converter_thread and self.converter_thread.isRunning():
            self.cancel_conversion()
        else:
            self.start_conversion()

    def start_conversion(self):
        items = self.list_batch.selectedItems()
        if not items:
            QMessageBox.warning(self, self.tr("msg_select_warning"), self.tr("msg_select_video"))
            return

        # Prepare Tasks
        tasks = []
        for item in items:
            row = self.list_batch.row(item)
            path = self.video_files[row]
            s = self.video_settings.get(path)
            tasks.append({
                "path": path,
                "settings": s,
                "format": s['format']
            })
            
        # Start Thread
        self.btn_convert.setText(self.tr("cancel"))
        self.progress_bar.setVisible(True)
        
        # If single file, show indeterminate "Busy" progress because parsing FFmpeg progress is hard
        # If batch, show file count progress
        if len(tasks) == 1:
            self.progress_bar.setRange(0, 0) # Infinite spin
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            
        self.lbl_status.setText(self.tr("converting"))
        
        self.converter_thread = ConversionThread(tasks, DEFAULT_FFMPEG, DEFAULT_GIFSKI)
        self.converter_thread.progress_signal.connect(self.on_conversion_progress)
        self.converter_thread.finished_signal.connect(self.on_conversion_finished)
        self.converter_thread.start()
        
    def cancel_conversion(self):
        if self.converter_thread:
            self.lbl_status.setText("Cancelling...")
            self.btn_convert.setEnabled(False) 
            self.converter_thread.stop()
        
    def on_conversion_progress(self, current, total, status):
        self.lbl_status.setText(status)
        # Only update specific percentage if not infinite spin
        if self.progress_bar.maximum() > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
        
    def on_conversion_finished(self, success, fail):
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText(self.tr("convert"))
        self.progress_bar.setRange(0, 100) # Reset to normal
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(self.tr("done") + f" (Success: {success}, Failed: {fail})")

    def on_language_change(self):
        txt = self.combo_lang.currentText()
        if txt == "한국어":
            self.lang = "kr"
        else:
            self.lang = "en"
            
        # Save setting
        self.settings.setValue("language", self.lang)
            
        self.update_texts()

    def remove_selected_file(self):
        row = self.list_batch.currentRow()
        if row >= 0:
            removed_file = self.video_files.pop(row)
            self.list_batch.takeItem(row) # This removes from widget
            self.lbl_status.setText(self.tr("msg_removed").format(os.path.basename(removed_file)))
            
            # If empty
            if not self.video_files:
                self.clear_batch()

    def estimate_size(self):
        item = self.list_batch.currentItem()
        # Support batch selection
        items = self.list_batch.selectedItems()
        if not items:
            # If nothing selected, maybe use implicit all? 
            # Or if list has items but no selection, select all? 
            # Or just warn?
            # User said "Select multiple in list".
            if self.list_batch.count() > 0:
                 # If list exists but no selection, maybe just suggest selecting?
                 # Or just do the first one?
                 # Let's fallback to current item if no selection (behavior match)
                 # Actually single selection is safer default if user forgot.
                 current = self.list_batch.currentItem()
                 if current: items = [current]
                 else: 
                    QMessageBox.warning(self, "Estimate", self.tr("msg_select_video"))
                    return
            else:
                QMessageBox.warning(self, "Estimate", self.tr("msg_select_video"))
                return
        
        if not items: return

        tasks = []
        for item in items:
            row = self.list_batch.row(item)
            if 0 <= row < len(self.video_files):
                path = self.video_files[row]
                s = self.video_settings[path]
                tasks.append({"path": path, "settings": s})

        self.btn_estimate.setEnabled(False)
        self.lbl_status.setText(f"Estimating size for {len(tasks)} file(s)...")
        
        self.est_thread = EstimateThread(tasks, DEFAULT_FFMPEG, DEFAULT_GIFSKI)
        self.est_thread.finished_signal.connect(self.on_estimate_finished)
        self.est_thread.start()
        
    def on_estimate_finished(self, result):
        self.btn_estimate.setEnabled(True)
        self.btn_estimate.setText(self.tr("estimate_size"))
        self.lbl_status.setText(self.tr("ready")) # Also localize status? or just "Estimation Complete"? "done" is safer.
        QMessageBox.information(self, "Estimation Result", result)


    @staticmethod
    def format_time(ms):
        seconds = ms / 1000
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:05.2f}"

    def closeEvent(self, event):
        # Cleanup
        if self.converter_thread and self.converter_thread.isRunning():
            self.converter_thread.stop()
            self.converter_thread.wait(2000) # Wait up to 2s
            
        if hasattr(self, 'est_thread') and self.est_thread and self.est_thread.isRunning():
            self.est_thread.requestInterruption() # Flag for loop
            self.est_thread.stop() # Kill processes
            self.est_thread.wait(2000)
            
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
