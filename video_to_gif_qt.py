
import sys
import os
import subprocess
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QSlider, QLabel, QFileDialog, QListWidget, QComboBox,
    QMessageBox, QGroupBox, QLineEdit, QSplitter, QFrame, QSpinBox, 
    QProgressBar, QSizePolicy, QSpacerItem, QStyle, QStyleOptionSlider,
    QStackedLayout, QGridLayout, QPlainTextEdit, QTextEdit, QDoubleSpinBox
)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, QThread, pyqtSignal, QSize, QEvent, QRect, QSettings, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QIcon, QDesktopServices
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
    if resize_mode == "scale":
        ratio = scale_percent / 100.0
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)
        # Ensure even coordinates for ffmpeg
        if new_w % 2 != 0: new_w += 1
        if new_h % 2 != 0: new_h += 1
        return new_w, new_h
        
    # Scale Presets
    if resize_mode == "scale_75":
        return _scale_dim(orig_w, orig_h, 0.75)
    elif resize_mode == "scale_50":
        return _scale_dim(orig_w, orig_h, 0.50)
    elif resize_mode == "scale_33":
        return _scale_dim(orig_w, orig_h, 0.33)
    elif resize_mode == "scale_25":
        return _scale_dim(orig_w, orig_h, 0.25)
        
    elif resize_mode == "custom":
        # Ensure even
        w = custom_w if custom_w % 2 == 0 else custom_w + 1
        h = custom_h if custom_h % 2 == 0 else custom_h + 1
        return w, h
        
    elif resize_mode == "original":
        return orig_w, orig_h
        
    # Presets like "1920x1080"
    m = re.match(r"(\d+)x(\d+)", resize_mode)
    if m:
        return int(m.group(1)), int(m.group(2))
        
    # Fallback/Legacy string check (shouldn't happen with new keys logic, but safe to keep?)
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

def _scale_dim(w, h, ratio):
    nw = int(w * ratio)
    nh = int(h * ratio)
    if nw % 2 != 0: nw += 1
    if nh % 2 != 0: nh += 1
    return nw, nh

TEXTS = {
    "en": {
        "title": "GifClip Maker",
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
        "msg_removed": "Removed: {}",
        "crop": "Crop",
        "crop_free": "Free",
        "res_original": "Original",
        "res_scale": "Scale (%)",
        "res_custom": "Custom Dimensions",
        "res_scale_75": "Scale 75%",
        "res_scale_50": "Scale 50%",
        "res_scale_33": "Scale 33%",
        "res_scale_25": "Scale 25%",
        "menu_file": "File",
        "menu_lang": "Language",
        "menu_help": "Help",
        "action_open": "Open Video",
        "action_exit": "Exit",
        "menu_update": "Update",
        "action_check_update": "Check for Updates      ",
        "menu_support": "Support",
        "action_bmc": "☕ Buy Me a Coffee      ",
        "action_blog": "⭐ Blog",
        "action_youtube": "❤️ YouTube",
        "action_patreon": "🤍 Patreon",
        "action_afdian": "💜 Afdian",
        "lang_en": "English",
        "lang_kr": "Korean",
    },
    "kr": {
        "title": "움짤 메이커",
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
        "msg_removed": "삭제됨: {}",
        "crop": "자르기",
        "crop_free": "자유",
        "res_original": "원본",
        "res_scale": "비율 (%)",
        "res_custom": "사용자 지정 크기",
        "res_scale_75": "비율 75%",
        "res_scale_50": "비율 50%",
        "res_scale_33": "비율 33%",
        "res_scale_25": "비율 25%",
        "menu_file": "파일",
        "menu_lang": "언어",
        "menu_help": "도움말",
        "action_open": "비디오 열기",
        "action_exit": "종료",
        "menu_update": "업데이트",
        "action_check_update": "업데이트 확인      ",
        "menu_support": "후원",
        "action_bmc": "☕ Buy Me a Coffee      ",
        "action_blog": "⭐ 블로그",
        "action_youtube": "❤️ 유튜브",
        "action_patreon": "🤍 Patreon",
        "action_afdian": "💜 Afdian",
        "lang_en": "English",
        "lang_kr": "한국어",
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
    padding-bottom: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: #aaa;
    background-color: #2b2b2b;
}
QGroupBox::indicator {
    width: 12px;
    height: 12px;
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

class CropOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        # self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True) 
        # Transparent background but captures mouse
        
        self.selection_rect = QRect() # Relative to this widget
        self.active_handle = None
        self.handle_size = 10
        self.aspect_ratio = 0.0 # 0 = Free
        
        # Handles: 0=TL, 1=T, 2=TR, 3=R, 4=BR, 5=B, 6=BL, 7=L
        self.handles = [] 
        
        # Make top-level tool window (Owned by Main)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow) # Removed (Graphics Glitch)
        self.setVisible(False)
        self.force_reset_on_resize = False

    def resizeEvent(self, event):
        # ensure selection is valid when resized
        if self.selection_rect.isEmpty() and self.width() > 0:
             self.reset_selection()
        
        # If forced reset is requested (e.g. from toggle_crop), do it now that we have real size
        if getattr(self, 'force_reset_on_resize', False):
             self.reset_selection()
             self.force_reset_on_resize = False
             
        self.raise_() # Force top
        super().resizeEvent(event)

# ... (omitted lines) ...

    # --- Logic ---

    def toggle_crop(self, checked):
        self.log_debug(f"toggle_crop called. checked={checked}")
        
        if checked:
            # Lazy Initialization
            if self.crop_overlay is None:
                self.log_debug("Lazy Init: Creating CropOverlay now.")
                self.crop_overlay = CropOverlay(None)
                self.crop_overlay.on_selection_change_callback = self.save_crop_to_settings
                self.crop_overlay.setVisible(False)
        
            # Check if layout is ready (using container)
            if self.video_container.width() < 100 or not self.video_container.isVisible():
                self.log_debug("toggle_crop delayed: container not ready")
                from PyQt6.QtCore import QTimer
                self.grp_crop.blockSignals(True)
                self.grp_crop.setChecked(True)
                self.grp_crop.blockSignals(False)
                QTimer.singleShot(100, lambda: self.toggle_crop(True))
                return

            self.crop_overlay.show()
            self.crop_overlay.raise_()
            self.log_debug("CropOverlay SHOWN")
            
            # 1. Force geometry update to match container size
            self.update_overlay_geometry(immediate=True, force=True)
            
            # 2. Reset selection based on valid dimensions
            w = self.video_container.width()
            h = self.video_container.height()
            self.crop_overlay.reset_selection(current_w=w, current_h=h)
            
        else:
            if self.crop_overlay:
                self.crop_overlay.hide()
                self.log_debug("CropOverlay HIDDEN via toggle_crop")
            
    def update_overlay_geometry(self, immediate=False, force=False):
        # LAZY LOAD: If overlay doesn't exist, we do nothing.
        if self.crop_overlay is None:
            return
            
        # STRICT Safety Check
        if not self.grp_crop.isChecked() and not force:
            self.crop_overlay.hide()
            # self.log_debug("update_overlay_geometry ABORT: Unchecked") # Too spammy if called frequently
            return

        def _update():
            # Double check inside the timer
            if self.crop_overlay is None: return

            if not self.grp_crop.isChecked() and not force:
                self.crop_overlay.hide()
                return

            if self.crop_overlay.isVisible() or force:
                if not self.video_container.isVisible():
                    self.crop_overlay.hide()
                    return

                # ROBUST GLOBAL MAPPING (via Main Window Anchor)
                # 1. Get container position relative to Main Window
                pos_in_main = self.video_container.mapTo(self, QPoint(0,0))
                
                # 2. Map Main Window point to Global Screen
                tl = self.mapToGlobal(pos_in_main)
                
                # Debug output
                msg = f"Crop Debug: Main({pos_in_main.x()},{pos_in_main.y()}) -> Global({tl.x()},{tl.y()}) Size({self.video_container.width()}x{self.video_container.height()})"
                self.lbl_status.setText(msg)
                # self.log_debug(msg) # Too spammy for move events
                
                # Set geometry
                self.crop_overlay.setGeometry(tl.x(), tl.y(), self.video_container.width(), self.video_container.height())
                
                if force or self.crop_overlay.isVisible():
                     self.crop_overlay.raise_()
        
        if immediate:
            _update()
        else:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, _update)

    def eventFilter(self, source, event):
        # Watch VIDEO CONTAINER for geometry changes
        if source == self.video_container:
            if event.type() == QEvent.Type.Resize or event.type() == QEvent.Type.Move:
                self.update_overlay_geometry()
            elif event.type() == QEvent.Type.Show:
                if self.grp_crop.isChecked():
                     self.crop_overlay.show()
                     self.update_overlay_geometry()
            elif event.type() == QEvent.Type.Hide:
                self.crop_overlay.hide()
            return super().eventFilter(source, event)
            
        # Specific handling for Video Widget (Drag&Drop only now, geometry handled by container)
        if source == self.video_widget:
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasUrls():
                    event.accept()
                else:
                    event.ignore()
                return True
            elif event.type() == QEvent.Type.Drop:
                files = [u.toLocalFile() for u in event.mimeData().urls()]
                video_files = [f for f in files if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.gif', '.webp'))]
                if video_files:
                    self.load_video(video_files[0])
                event.accept()
                return True
            # Allow propagation
            return False

        # Generic handling ...       painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QColor(0, 0, 0))
        self._update_handles()
        for r in self.handles:
             painter.drawRect(r)

    def set_aspect_ratio(self, ratio):
        self.aspect_ratio = ratio
        # Safety check for None or Empty
        if self.selection_rect.isEmpty() or ratio <= 0: return

        # Current Size
        old_r = self.selection_rect
        w = old_r.width()
        h = int(w / ratio)
        
        # Fit to window bounds (Prioritize fitting within screen)
        max_w = self.width()
        max_h = self.height()
        
        # 1. Check Height Conflict
        if h > max_h:
            h = max_h
            w = int(h * ratio)
            
        # 2. Check Width Conflict (Double check after height adjustment)
        if w > max_w:
            w = max_w
            h = int(w / ratio)
            
        new_rect = QRect(0, 0, w, h)
        new_rect.moveCenter(old_r.center())
        
        # Constrain (Keep fully inside)
        if new_rect.left() < 0: new_rect.moveLeft(0)
        if new_rect.top() < 0: new_rect.moveTop(0)
        if new_rect.right() > max_w: new_rect.moveRight(max_w)
        if new_rect.bottom() > max_h: new_rect.moveBottom(max_h)
        
        self.selection_rect = new_rect
        self.update()
        
        # Z-Order Fix: Bring overlay to front because clicking Main Window might have obscured it
        self.raise_()
        self.activateWindow()

    def reset_selection(self, current_w=None, current_h=None):
        # Allow explicit size override for sync updates
        base_w = current_w if current_w is not None else self.width()
        base_h = current_h if current_h is not None else self.height()
        
        # Default to 80% center
        w = int(base_w * 0.8)
        h = int(base_h * 0.8)
        if w <= 0: w = 100
        if h <= 0: h = 100
        
        if self.aspect_ratio > 0:
            if w / h > self.aspect_ratio:
                w = int(h * self.aspect_ratio)
            else:
                h = int(w / self.aspect_ratio)
                
        x = (base_w - w) // 2
        y = (base_h - h) // 2
        self.selection_rect = QRect(x, y, w, h)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dim background
        full_r = self.rect()
        painter.setBrush(QColor(0, 0, 0, 100)) # Slightly lighter dim
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw 4 rects around selection (Dimming)
        # Top
        painter.drawRect(0, 0, full_r.width(), self.selection_rect.top())
        # Bottom
        painter.drawRect(0, self.selection_rect.bottom() + 1, full_r.width(), full_r.height() - self.selection_rect.bottom())
        # Left
        painter.drawRect(0, self.selection_rect.top(), self.selection_rect.left(), self.selection_rect.height())
        # Right
        painter.drawRect(self.selection_rect.right() + 1, self.selection_rect.top(), 
                         full_r.width() - self.selection_rect.right(), self.selection_rect.height())
                         
        # Selection Border - High Visibility Red with Internal Fill for Hit Testing
        # Use alpha=1 to make it "solid" for mouse events but invisible to eye
        painter.setBrush(QColor(255, 255, 255, 1)) 
        painter.setPen(QPen(QColor("#3b8edb"), 3, Qt.PenStyle.SolidLine)) # Match Convert Button Blue
        painter.drawRect(self.selection_rect)
        
        # Draw Handles
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QColor(0, 0, 0))
        self._update_handles()
        for r in self.handles:
             painter.drawRect(r)

    def _update_handles(self):
        r = self.selection_rect
        hs = self.handle_size
        hs2 = hs // 2
        
        self.handles = [
            QRect(r.left()-hs2, r.top()-hs2, hs, hs),    # TL
            QRect(r.center().x()-hs2, r.top()-hs2, hs, hs), # T
            QRect(r.right()-hs2, r.top()-hs2, hs, hs),   # TR
            QRect(r.right()-hs2, r.center().y()-hs2, hs, hs), # R
            QRect(r.right()-hs2, r.bottom()-hs2, hs, hs), # BR
            QRect(r.center().x()-hs2, r.bottom()-hs2, hs, hs), # B
            QRect(r.left()-hs2, r.bottom()-hs2, hs, hs),   # BL
            QRect(r.left()-hs2, r.center().y()-hs2, hs, hs)  # L
        ]

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.activateWindow() # Ensure overlay keeps focus
            self.raise_()
            
            pos = event.pos()
            self.active_handle = None
            
            # Check handles
            for i, r in enumerate(self.handles):
                if r.contains(pos):
                    self.active_handle = i
                    event.accept()
                    return
            
            # Check inside for move
            if self.selection_rect.contains(pos):
                self.active_handle = 8 # Move
                self.last_pos = pos
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                event.accept()
                return
                
        event.ignore()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        
        # Cursor Update
        hover = False
        for i, r in enumerate(self.handles):
            if r.contains(pos):
                hover = True
                if i in [0, 4]: self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif i in [1, 5]: self.setCursor(Qt.CursorShape.SizeVerCursor)
                elif i in [2, 6]: self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                elif i in [3, 7]: self.setCursor(Qt.CursorShape.SizeHorCursor)
                break
        
        if not hover:
            if self.selection_rect.contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

        # Drag Logic
        if self.active_handle is not None:
            r = QRect(self.selection_rect)
            
            if self.active_handle == 8: # Move
                delta = pos - self.last_pos
                r.translate(delta)
                self.last_pos = pos
            else:
                # Resize Logic
                # 0=TL, 1=T, 2=TR, 3=R, 4=BR, 5=B, 6=BL, 7=L
                
                # Simple implementation without aspect ratio lock during drag for now
                # (Enhancement: support shift key for ratio)
                
                mx, my = pos.x(), pos.y()
                
                if self.active_handle in [0, 6, 7]: # Left
                     r.setLeft(max(0, min(mx, r.right() - 10)))
                if self.active_handle in [2, 3, 4]: # Right
                     r.setRight(min(self.width(), max(mx, r.left() + 10)))
                if self.active_handle in [0, 1, 2]: # Top
                     r.setTop(max(0, min(my, r.bottom() - 10)))
                if self.active_handle in [4, 5, 6]: # Bottom
                     r.setBottom(min(self.height(), max(my, r.top() + 10)))
                     
                # If aspect ratio forced (not 0), we need to recalculate
                if self.aspect_ratio > 0 and self.active_handle != 8:
                     pass # Todo: complex constraint logic
                     
            self.selection_rect = r
            
            # Only constrain (move) if we are moving the whole rect.
            # If resizing, we already clamped coordinates above.
            if self.active_handle == 8:
                self._constrain_rect()
            
            self.update()

    def mouseReleaseEvent(self, event):
        self.active_handle = None
        if hasattr(self, 'on_selection_change_callback'):
            self.on_selection_change_callback()

    def _constrain_rect(self):
        # Keep inside widget
        r = self.selection_rect
        p = self.rect()
        
        if r.left() < 0: r.moveLeft(0)
        if r.top() < 0: r.moveTop(0)
        if r.right() > p.right(): r.moveRight(p.right())
        if r.bottom() > p.bottom(): r.moveBottom(p.bottom())
        
        self.selection_rect = r

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
        
        # Crop Logic
        crop_filter = None
        if settings.get('crop_enabled', False):
            # Coordinates are normalized 0.0-1.0
            cx = settings.get('crop_x', 0)
            cy = settings.get('crop_y', 0)
            cw = settings.get('crop_w', 1.0)
            ch = settings.get('crop_h', 1.0)
            
            orig_w = settings['orig_width']
            orig_h = settings['orig_height']
            
            # Helper to make even coords
            final_x = int(cx * orig_w)
            final_y = int(cy * orig_h)
            final_w = int(cw * orig_w)
            final_h = int(ch * orig_h)
            
            # FFmpeg crop filter syntax: crop=w:h:x:y
            crop_filter = f"crop={final_w}:{final_h}:{final_x}:{final_y}"
            
            # Update 'effective' original size for scaling logic
            eff_orig_w = final_w
            eff_orig_h = final_h
        else:
            eff_orig_w = settings['orig_width']
            eff_orig_h = settings['orig_height']
        
        # 2. Compute Resolution (Based on cropped size if active)
        w, h = compute_output_resolution(
            eff_orig_w, eff_orig_h,
            settings['resize_mode'], settings['width'], settings['height'],
            settings['scale']
        )
        print(f"Resolving '{settings['resize_mode']}': {eff_orig_w}x{eff_orig_h} -> {w}x{h}")
        
        # 3. Trim Filters
        ss = settings['start_time'] / 1000.0 if settings['start_time'] >= 0 else 0
        to = settings['end_time'] / 1000.0 if settings['end_time'] >= 0 else 0
        
        bn = os.path.basename(task['path'])
        self.progress_signal.emit(idx, total, f"Converting {bn} ({w}x{h})...")
        
        # 4. Execute
        if task['format'] == "GIF":
            self.convert_to_gif(src, out, w, h, ss, to, settings['fps'], settings['quality'], crop_filter)
        else:
            self.convert_to_webp(src, out, w, h, ss, to, settings['fps'], settings['quality'], crop_filter)

    def convert_to_gif(self, src, out, w, h, ss, to, fps, quality, crop_filter=None):
        # 1. Try Gifski if available (Legacy/High Quality)
        if self.gifski and os.path.exists(self.gifski):
            # FFmpeg: Trim -> Crop -> FPS -> Scale -> Pipe
            filters = []
            if crop_filter: filters.append(crop_filter)
            filters.append(f"fps={fps}")
            filters.append(f"scale={w}:{h}:flags=lanczos")
            vf = ",".join(filters)
            
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
        
        filters = []
        if crop_filter: filters.append(crop_filter)
        filters.append(f"fps={fps}")
        filters.append(f"scale={w}:{h}:flags=lanczos")
        vf = ",".join(filters)
        
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

    def convert_to_webp(self, src, out, w, h, ss, to, fps, quality, crop_filter=None):
        # Native WebP Strategy (Optimized for Small Size)
        # We bypassed GIF completely to avoid dithering noise bloat.
        # We use standard yuv420p (4:2:0) subsampling which is standard for video/web.
        
        # Quality Mapping:
        # User requested aggressive quality settings: "Quality 1 (1.0x)" and "YUV444P".
        # This disables the safety cap. Q100 input = WebP Q100 output.
        # This WILL produce larger files, but offers maximum fidelity.
        webp_q = int(quality * 1.0)
        if webp_q < 1: webp_q = 1
        
        filters = []
        if crop_filter: filters.append(crop_filter)
        filters.append(f"fps={fps}")
        filters.append(f"scale={w}:{h}:flags=lanczos")
        vf = ",".join(filters)

        time_args = []
        if ss > 0: time_args.extend(["-ss", str(ss)])
        if to > 0: time_args.extend(["-to", str(to)])
        
        cmd = [self.ffmpeg, "-y"] + time_args + ["-i", src]
        cmd.extend(["-vf", vf, "-c:v", "libwebp", "-lossless", "0", 
                    "-compression_level", "6", "-q:v", str(webp_q), 
                    "-preset", "default", "-loop", "0", "-an", "-vsync", "0", 
                    "-pix_fmt", "yuv420p", out])
                    
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
        
    def run(self):
        results = []
        
        for idx, task in enumerate(self.tasks):
            if self.isInterruptionRequested(): break
            
            try:
                path = task["path"]
                s = task["settings"]
                fmt = s["format"].lower() 
                filename = os.path.basename(path)
                
                # Duration needed (This is the trimmed duration in seconds)
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

                # --- Effective Duration (Trim Support) ---
                start_ms = s.get('start_time', -1)
                end_ms = s.get('end_time', -1)
                
                # Defaults
                start_sec = 0.0
                end_sec = total_duration
                
                if start_ms >= 0:
                    start_sec = start_ms / 1000.0
                
                if end_ms > 0:
                    # If end_time is valid and less than total, use it
                    # (Also guard against end < start)
                    e_sec = end_ms / 1000.0
                    if e_sec > start_sec:
                        end_sec = min(total_duration, e_sec)
                
                effective_duration = max(0, end_sec - start_sec)
                
                if effective_duration <= 0:
                    # Fallback just in case
                    effective_duration = total_duration
                    start_sec = 0
                
                # --- 3-Point Distributed Sampling Strategy (User Request) ---
                # Sample 11% from Start, Middle, and End (Total 33%)
                # This provides a statistically superior VBR estimate compared to a single chunk.
                
                seg_ratio = 0.11
                seg_dur = effective_duration * seg_ratio
                
                # Safety for very short clips
                if seg_dur < 0.5: seg_dur = 0.5 # Minimum 0.5s per chunk
                if seg_dur * 3 > effective_duration:
                    # If total samples exceed duration (very short video), fall back to Single Full Chunk
                    seg_dur = effective_duration
                    t1, t2, t3 = start_sec, -1, -1
                    actual_sample_total = effective_duration
                else:
                    t1 = start_sec
                    t2 = start_sec + (effective_duration * 0.445) # Center-ish
                    t3 = start_sec + (effective_duration - seg_dur) # End
                    # Clamp t3
                    if t3 < t1: t3 = t1
                    actual_sample_total = seg_dur * 3

                # Prepare Crop Logic ONCE
                crop_filter_str = ""
                eff_orig_w = s['orig_width']
                eff_orig_h = s['orig_height']
                
                if s.get('crop_enabled', False):
                    cx = s.get('crop_x', 0)
                    cy = s.get('crop_y', 0)
                    cw = s.get('crop_w', 1.0)
                    ch = s.get('crop_h', 1.0)
                    
                    final_x = int(cx * s['orig_width'])
                    final_y = int(cy * s['orig_height'])
                    final_w = int(cw * s['orig_width'])
                    final_h = int(ch * s['orig_height'])
                    
                    crop_filter_str = f"crop={final_w}:{final_h}:{final_x}:{final_y}"
                    eff_orig_w = final_w
                    eff_orig_h = final_h
                
                w, h = compute_output_resolution(eff_orig_w, eff_orig_h, s['resize_mode'], 
                                               s['width'], s['height'], s['scale'])
                
                ext = "gif" if "gif" in fmt else "webp"
                self.temp_file = f"temp_estimate_{idx}.{ext}"
                
                startup_info = None
                if os.name == 'nt':
                    startup_info = subprocess.STARTUPINFO()
                    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                # Cleanup previous if exists
                if os.path.exists(self.temp_file):
                    try: os.remove(self.temp_file)
                    except: pass
                    
                # Build Common Filters (Crop -> Scale -> FPS)
                filters = []
                if crop_filter_str: filters.append(crop_filter_str)
                if w > 0 and h > 0:
                    filters.append(f"scale={w}:{h}:flags=lanczos")
                # FPS is usually handled by -r or filter. Let's use filter for complex chain safety.
                filters.append(f"fps={s['fps']}")
                
                post_process_filter = ",".join(filters)

                if "gif" in fmt:
                     # GIFSKI Pipeline
                     cmd_gifski = [self.gifski, "-o", self.temp_file]
                     cmd_gifski.extend(["--fps", str(s['fps']), "--quality", str(s['quality'])])
                     if w > 0 and h > 0:
                         cmd_gifski.extend(["--width", str(w), "--height", str(h)])
                     cmd_gifski.append("-")
                     
                     gif_proc = subprocess.Popen(cmd_gifski, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startup_info)
                     self.processes.append(gif_proc)
                     
                     # FFmpeg Command
                     cmd_ffmpeg = [self.ffmpeg, "-y"]
                     
                     # Inputs
                     cmd_ffmpeg.extend(["-ss", str(t1), "-t", str(seg_dur), "-i", path])
                     if t2 != -1: # Multi-chunk
                         cmd_ffmpeg.extend(["-ss", str(t2), "-t", str(seg_dur), "-i", path])
                         cmd_ffmpeg.extend(["-ss", str(t3), "-t", str(seg_dur), "-i", path])
                         
                         # Complex Filter: Concat -> PostProcess
                         # [0:v][1:v][2:v]concat=n=3:v=1:a=0[vcat];[vcat]filters...[out]
                         fc = f"[0:v][1:v][2:v]concat=n=3:v=1:a=0[vcat];[vcat]{post_process_filter}[out]"
                         cmd_ffmpeg.extend(["-filter_complex", fc, "-map", "[out]"])
                     else:
                         # Single chunk fallback
                         if post_process_filter:
                            cmd_ffmpeg.extend(["-vf", post_process_filter])
                     
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
                    # WebP Pipeline
                    webp_q = int(s['quality'] * 1.0)
                    if webp_q < 1: webp_q = 1
                    
                    cmd = [self.ffmpeg, "-y"]
                    
                    # Inputs
                    cmd.extend(["-ss", str(t1), "-t", str(seg_dur), "-i", path])
                    if t2 != -1:
                        cmd.extend(["-ss", str(t2), "-t", str(seg_dur), "-i", path])
                        cmd.extend(["-ss", str(t3), "-t", str(seg_dur), "-i", path])
                        
                        fc = f"[0:v][1:v][2:v]concat=n=3:v=1:a=0[vcat];[vcat]{post_process_filter}[out]"
                        cmd.extend(["-filter_complex", fc, "-map", "[out]"])
                    else:
                        if post_process_filter:
                            cmd.extend(["-vf", post_process_filter])
                    
                    # MATCHED TO CONVERSION THREAD: yuv420p, level 6
                    cmd.extend(["-c:v", "libwebp", "-lossless", "0", 
                                "-compression_level", "6", "-q:v", str(webp_q), 
                                "-preset", "default", "-loop", "0", "-an", "-vsync", "0", 
                                "-pix_fmt", "yuv420p", self.temp_file])
                    
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
                        ratio = effective_duration / actual_sample_total
                        # Removed Safety Factor (1.0x) as 3-point sampling is statistically representative
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
        # Install event filter
        self.installEventFilter(self)
        
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

    def create_menu_bar(self):
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False) # Force Qt rendering to support Stylesheets
        
        # 1. File Menu
        self.menu_file = menubar.addMenu("File")
        
        self.act_open = self.menu_file.addAction("Open")
        self.act_open.triggered.connect(self.open_file_dialog)
        self.act_open.setShortcut("Ctrl+O")
        
        self.menu_file.addSeparator()
        
        self.act_exit = self.menu_file.addAction("Exit")
        self.act_exit.triggered.connect(self.close)
        
        # 2. Language Menu
        self.menu_lang = menubar.addMenu("Language")
        from PyQt6.QtGui import QActionGroup, QAction
        
        lang_group = QActionGroup(self)
        lang_group.setExclusive(True)
        
        self.act_lang_en = QAction("English", self)
        self.act_lang_en.setCheckable(True)
        self.act_lang_en.setData("en")
        self.act_lang_en.triggered.connect(lambda: self.set_language("en"))
        
        self.act_lang_kr = QAction("Korean", self)
        self.act_lang_kr.setCheckable(True)
        self.act_lang_kr.setData("kr")
        self.act_lang_kr.triggered.connect(lambda: self.set_language("kr"))
        
        lang_group.addAction(self.act_lang_en)
        lang_group.addAction(self.act_lang_kr)
        
        self.menu_lang.addAction(self.act_lang_en)
        self.menu_lang.addAction(self.act_lang_kr)
        
        # 3. Update Menu
        self.menu_update = menubar.addMenu("Update")
        self.act_check_update = self.menu_update.addAction("Check for Updates")
        self.act_check_update.triggered.connect(self.open_update_url)

        # 4. Support Menu
        self.menu_support = menubar.addMenu("Support")
        
        self.act_bmc = self.menu_support.addAction("Buy Me a Coffee")
        self.act_bmc.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://buymeacoffee.com/smooth7")))
        
        self.act_blog = self.menu_support.addAction("Blog")
        self.act_blog.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://smooth-7.tistory.com/")))
        
        self.act_youtube = self.menu_support.addAction("YouTube")
        self.act_youtube.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.youtube.com/@SmoothAnimation")))
        
        self.act_patreon = self.menu_support.addAction("Patreon")
        self.act_patreon.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.patreon.com/SmoothAanimation")))
        
        self.act_afdian = self.menu_support.addAction("Afdian")
        self.act_afdian.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://afdian.com/a/SmoothAnimation")))

        # Set Init State
        if self.lang == 'kr':
            self.act_lang_kr.setChecked(True)
        else:
            self.act_lang_en.setChecked(True)
            
    def open_update_url(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://smooth-7.tistory.com/7"))

    def set_language(self, lang_code):
        if self.lang == lang_code: return
        self.lang = lang_code
        self.settings.setValue("language", self.lang)
        self.update_texts()

    def _init_ui(self):
        self.create_menu_bar()

        # Custom Style for QMenu to balance margins
        self.setStyleSheet("""
            QMenu::item {
                padding: 6px 35px 6px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #3b8edb;
                color: white;
            }
        """)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus) # Allow MainWindow to take focus
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 0, 10, 10)
        
        # --- Left Area ---
        # --- Left Area ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Video Container (Wrapper for QVideoWidget to ensure stable coordinate mapping)
        # QVideoWidget is a native window which causes coordinate issues. 
        # Wrapping it in a standard QWidget provides a reliable anchor.
        self.video_container = QWidget()
        container_layout = QVBoxLayout(self.video_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container_layout.addWidget(self.video_widget)
        
        # Install event filters inside _init_ui where the objects exist
        self.video_container.installEventFilter(self)
        self.video_widget.installEventFilter(self)

        left_layout.addWidget(self.video_container)
        
        # Crop Overlay (Floating Strategy - Top Level)
        # Implement LAZY INITIALIZATION to prevent "Ghost Window" at startup.
        # The overlay will only be created when the user first enables cropping.
        self.crop_overlay = None 
        
        # DEBUG LOGGING
        self.log_debug("App Initialized. CropOverlay set to None (Lazy).")
        
        # Force sync not needed for lazy load, but harmless to keep empty hook
        # from PyQt6.QtCore import QTimer
        # QTimer.singleShot(500, self.force_sync_crop_state)

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
        range_panel = QWidget()
        range_layout = QHBoxLayout(range_panel)
        range_layout.setContentsMargins(0, 5, 0, 5)
        
        # Range Controls (Moved to direct add)
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
        range_layout.addStretch() # Push everything left

        left_layout.addWidget(range_panel)
        
        # --- Right Area: Sidebar ---
        sidebar = QWidget()
        sidebar.setFixedWidth(360) # Increased bandwidth (300 -> 360)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 0, 0, 0)
        
        # --- Settings Area (Right) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Output Format
        # 1. Output Format
        self.grp_format = QGroupBox(self.tr("format"))
        lay_format = QVBoxLayout(self.grp_format)
        
        self.combo_format = QComboBox()
        self.combo_format.addItems(["GIF", "WebP"])
        lay_format.addWidget(self.combo_format)
        
        right_layout.addWidget(self.grp_format)
        
        # 2. Crop
        self.grp_crop = QGroupBox("Crop")
        self.grp_crop.setCheckable(True)
        self.grp_crop.setChecked(False)
        self.grp_crop.toggled.connect(self.toggle_crop)
        lay_crop = QVBoxLayout(self.grp_crop)
        
        # Presets
        lay_presets = QHBoxLayout()
        self.btn_ratio_free = QPushButton("Free")
        self.btn_ratio_1_1 = QPushButton("1:1")
        self.btn_ratio_16_9 = QPushButton("16:9")
        self.btn_ratio_9_16 = QPushButton("9:16")
        self.btn_ratio_4_3 = QPushButton("4:3")
        
        for b in [self.btn_ratio_free, self.btn_ratio_1_1, self.btn_ratio_16_9, self.btn_ratio_9_16, self.btn_ratio_4_3]:
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.clicked.connect(self.apply_crop_preset)
            lay_presets.addWidget(b)
        
        self.btn_ratio_free.setChecked(True) # Default
        lay_crop.addLayout(lay_presets)
        right_layout.addWidget(self.grp_crop)

        # 3. Quality & FPS
        # 3. Quality & FPS
        # 3. Quality & FPS
        self.grp_quality = QGroupBox(self.tr("quality"))
        lay_quality = QGridLayout(self.grp_quality)
        # lay_quality.setContentsMargins(5, 5, 5, 5) # Removed to match Output Format defaults
        
        # Row 0: FPS
        self.lbl_fps = QLabel(self.tr("fps"))
        self.lbl_fps.setMinimumWidth(110) # Align with others
        self.lbl_fps.setIndent(5) # Indent to match combo text
        self.spin_fps = QSpinBox()
        self.spin_fps.setRange(1, 60)
        self.spin_fps.setValue(15)
        
        lay_quality.addWidget(self.lbl_fps, 0, 0)
        lay_quality.addWidget(self.spin_fps, 0, 1)
        
        # Row 1: Quality
        self.lbl_quality_title = QLabel(self.tr("quality"))
        self.lbl_quality_title.setMinimumWidth(110) # Align with others
        self.lbl_quality_title.setIndent(5)
        
        # Slider + Value in a sub-layout or just add to grid?
        # Grid supports column spanning, but we have 2 widgets for quality control (slider + val label)
        # Let's put them in a widget/hbox container for column 1
        
        container_q = QWidget()
        hbox_q_inner = QHBoxLayout(container_q)
        hbox_q_inner.setContentsMargins(0, 0, 0, 0)
        
        self.slider_quality = QSlider(Qt.Orientation.Horizontal)
        self.slider_quality.setRange(1, 100)
        self.slider_quality.setValue(80)
        self.lbl_quality_val = QLabel("80") 
        self.slider_quality.valueChanged.connect(lambda v: self.lbl_quality_val.setText(str(v)))
        
        hbox_q_inner.addWidget(self.slider_quality)
        hbox_q_inner.addWidget(self.lbl_quality_val)
        
        lay_quality.addWidget(self.lbl_quality_title, 1, 0)
        lay_quality.addWidget(container_q, 1, 1)
        
        right_layout.addWidget(self.grp_quality)
        
        # 4. Resize
        # 4. Resize
        self.grp_resize = QGroupBox(self.tr("resize"))
        lay_resize = QVBoxLayout(self.grp_resize)
        
        self.combo_resize_mode = QComboBox()
        self.populate_resize_modes()
        self.combo_resize_mode.currentIndexChanged.connect(self.update_resize_ui)
        lay_resize.addWidget(self.combo_resize_mode)
        
        # Custom Dimensions
        self.widget_custom_dim = QWidget()
        lay_custom = QHBoxLayout(self.widget_custom_dim)
        lay_custom.setContentsMargins(5, 0, 5, 5)
        
        self.lbl_width = QLabel(self.tr("width"))
        self.lbl_width.setMinimumWidth(110) # Align column
        self.lbl_width.setIndent(5)
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 4096)
        self.spin_width.setValue(640)
        
        self.lbl_height = QLabel(self.tr("height"))
        self.spin_height = QSpinBox()
        self.spin_height.setRange(1, 4096)
        self.spin_height.setValue(480)
        
        lay_custom.addWidget(self.lbl_width)
        lay_custom.addWidget(self.spin_width)
        lay_custom.addSpacing(10) # Spacer
        lay_custom.addWidget(self.lbl_height)
        lay_custom.addWidget(self.spin_height)
        lay_resize.addWidget(self.widget_custom_dim)
        
        # Scale %
        self.widget_scale = QWidget()
        lay_scale = QHBoxLayout(self.widget_scale)
        lay_scale.setContentsMargins(5, 0, 5, 5) # Top 0 to sit flush under combo
        
        self.lbl_scale = QLabel(self.tr("scale"))
        self.lbl_scale.setMinimumWidth(110) # Align column
        self.lbl_scale.setIndent(5)
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(1, 500)
        self.spin_scale.setValue(75)
        
        lay_scale.addWidget(self.lbl_scale)
        lay_scale.addWidget(self.spin_scale)
        # Add spacer to keep spinbox from expanding too much? 
        # Actually letting it fill the row is fine or cleaner.
        lay_resize.addWidget(self.widget_scale)
        
        right_layout.addWidget(self.grp_resize)
        side_layout.addWidget(right_widget)
        
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
        
        # Crop Overlay (moved into stack_layout)
        # self.crop_overlay = CropOverlay(self.video_widget)
        # self.crop_overlay.setVisible(False)
        # self.crop_overlay.on_selection_change_callback = self.save_crop_to_settings
        
        self.update_resize_ui()
        
        # Connect Settings Signals to Save Logic
        self.combo_format.currentIndexChanged.connect(self.save_settings_from_ui)
        self.spin_fps.valueChanged.connect(self.save_settings_from_ui)
        self.slider_quality.valueChanged.connect(self.save_settings_from_ui)
        self.combo_resize_mode.currentIndexChanged.connect(self.save_settings_from_ui)
        self.spin_width.valueChanged.connect(self.save_settings_from_ui)
        self.spin_height.valueChanged.connect(self.save_settings_from_ui)
        self.spin_scale.valueChanged.connect(self.save_settings_from_ui)
        
        # Globally install event filter for Drag & Drop support on all widgets
        self._install_event_filter_recursive(central_widget)

    # --- Logic ---

    def toggle_crop(self, checked):
        self.log_debug(f"toggle_crop called. checked={checked}")
        
        if checked:
            # Lazy Initialization
            if self.crop_overlay is None:
                self.log_debug("Lazy Init: Creating CropOverlay now.")
                # Z-Order Fix: Parent to self so it stays on top of MainWindow
                self.crop_overlay = CropOverlay(self) 
                self.crop_overlay.on_selection_change_callback = self.save_crop_to_settings
                self.crop_overlay.setVisible(False)
        
            # Check if layout is ready (using container)
            if self.video_container.width() < 100 or not self.video_container.isVisible():
                self.log_debug("toggle_crop delayed: container not ready")
                from PyQt6.QtCore import QTimer
                self.grp_crop.blockSignals(True)
                self.grp_crop.setChecked(True)
                self.grp_crop.blockSignals(False)
                QTimer.singleShot(100, lambda: self.toggle_crop(True))
                return

            self.crop_overlay.show()
            self.crop_overlay.raise_()
            self.log_debug("CropOverlay SHOWN")
            
            # 1. Force geometry update to match container size
            self.update_overlay_geometry(immediate=True, force=True)
            
            # 2. Reset selection based on VIDEO CONTENT rect (not container)
            # Find current video path
            current_path = None
            items = self.list_batch.selectedItems()
            if items:
                 row = self.list_batch.row(items[0])
                 if 0 <= row < len(self.video_files):
                     current_path = self.video_files[row]
            
            if current_path:
                vx, vy, vw, vh = self.calculate_video_rect(current_path)
                # Default to safe video rect area
                self.crop_overlay.selection_rect = QRect(vx, vy, vw, vh)
                self.crop_overlay.update()
            else:
                # Fallback
                w = self.video_container.width()
                h = self.video_container.height()
                self.crop_overlay.reset_selection(current_w=w, current_h=h)
            
        else:
            if self.crop_overlay:
                self.crop_overlay.hide()
                self.log_debug("CropOverlay HIDDEN via toggle_crop")
            
    def update_overlay_geometry(self, immediate=False, force=False):
        # LAZY LOAD: If overlay doesn't exist, we do nothing.
        if self.crop_overlay is None:
            return
            
        # STRICT Safety Check
        if not self.grp_crop.isChecked() and not force:
            self.crop_overlay.hide()
            return

        def _update():
            # Double check inside the timer
            if self.crop_overlay is None: return

            if not self.grp_crop.isChecked() and not force:
                self.crop_overlay.hide()
                return

            if self.crop_overlay.isVisible() or force:
                if not self.video_container.isVisible():
                    self.crop_overlay.hide()
                    return

                # ROBUST GLOBAL MAPPING (via Main Window Anchor)
                # 1. Get container position relative to Main Window
                pos_in_main = self.video_container.mapTo(self, QPoint(0,0))
                
                # 2. Map Main Window point to Global Screen
                tl = self.mapToGlobal(pos_in_main)
                
                # Debug output
                msg = f"Crop Debug: Main({pos_in_main.x()},{pos_in_main.y()}) -> Global({tl.x()},{tl.y()}) Size({self.video_container.width()}x{self.video_container.height()})"
                self.lbl_status.setText(msg)
                # self.log_debug(msg) # Too spammy for move events
                
                # Set geometry
                self.crop_overlay.setGeometry(tl.x(), tl.y(), self.video_container.width(), self.video_container.height())
                
                if force or self.crop_overlay.isVisible():
                     self.crop_overlay.raise_()
        
        if immediate:
            _update()
        else:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, _update)
            
    def resizeEvent(self, event):
        self.update_overlay_geometry()
        super().resizeEvent(event)
        
    def moveEvent(self, event):
        self.update_overlay_geometry()
        super().moveEvent(event)
        
    def closeEvent(self, event):
        # Ensure overlay closes with main window
        self.crop_overlay.close()
        super().closeEvent(event)

    def apply_crop_preset(self):
        # Lazy Load Safety
        if self.crop_overlay is None:
            return

        btn = self.sender()
        ratio = 0.0
        if btn == self.btn_ratio_1_1: ratio = 1.0
        elif btn == self.btn_ratio_16_9: ratio = 16/9
        elif btn == self.btn_ratio_9_16: ratio = 9/16
        elif btn == self.btn_ratio_4_3: ratio = 4/3
        
        self.crop_overlay.set_aspect_ratio(ratio)
        
        # Z-Order Fix: Ensure overlay stays on top
        self.crop_overlay.raise_()
        self.crop_overlay.activateWindow()

    def _install_event_filter_recursive(self, widget):
        widget.installEventFilter(self)
        for child in widget.children():
            if isinstance(child, QWidget):
                self._install_event_filter_recursive(child)

    # --- Logic ---
    
    def update_texts(self):
        self.setWindowTitle(self.tr("title"))
        
        # Menu
        self.menu_file.setTitle(self.tr("menu_file"))
        self.act_open.setText(self.tr("action_open"))
        self.act_exit.setText(self.tr("action_exit"))
        
        self.menu_lang.setTitle(self.tr("menu_lang"))
        self.act_lang_en.setText(self.tr("lang_en"))
        self.act_lang_kr.setText(self.tr("lang_kr"))
        
        # Update Menu
        self.menu_update.setTitle(self.tr("menu_update"))
        self.act_check_update.setText(self.tr("action_check_update"))
        
        # Support Menu
        self.menu_support.setTitle(self.tr("menu_support"))
        self.act_bmc.setText(self.tr("action_bmc"))
        self.act_blog.setText(self.tr("action_blog"))
        self.act_youtube.setText(self.tr("action_youtube"))
        self.act_patreon.setText(self.tr("action_patreon"))
        self.act_afdian.setText(self.tr("action_afdian"))
        
        self.update_play_button_text()
        
        self.grp_crop.setTitle(self.tr("crop")) 
        self.btn_ratio_free.setText(self.tr("crop_free"))
        
        self.grp_format.setTitle(self.tr("format"))
        self.grp_quality.setTitle(self.tr("quality"))
        self.grp_resize.setTitle(self.tr("resize"))
        self.populate_resize_modes()
        
        self.lbl_fps.setText(self.tr("fps"))
        self.lbl_quality_title.setText(self.tr("quality"))
        
        self.lbl_width.setText(self.tr("width"))
        self.lbl_height.setText(self.tr("height"))
        self.lbl_scale.setText(self.tr("scale"))
        
        self.lbl_status.setText(self.tr("ready"))
        
        self.on_selection_changed() 
        self.grp_batch.setTitle(self.tr("batch_list"))
        self.btn_clear_batch.setText(self.tr("clear_batch"))
        self.btn_convert.setText(self.tr("convert"))
        self.btn_set_start.setText(self.tr("set_start"))
        self.btn_set_end.setText(self.tr("set_end"))
        self.btn_remove_sel.setText(self.tr("remove_selected"))
        self.btn_estimate.setText(self.tr("estimate_size"))

    def update_resolution_combo(self, w, h):
        self.combo_resize_mode.blockSignals(True)
        # Keep current key
        current_key = self.combo_resize_mode.currentData()
        
        self.combo_resize_mode.clear()
        
        # Add basic options with keys
        self.combo_resize_mode.addItem(self.tr("res_original"), "original")
        
        if w > 0 and h > 0:
            aspect = w / h
            targets = [1080, 720, 480, 360]
            for t_h in targets:
                t_w = int(t_h * aspect)
                if t_w % 2 != 0: t_w += 1
                label = f"{t_w}x{t_h} ({t_h}p)"
                key = f"{t_w}x{t_h}" # Key for presets
                self.combo_resize_mode.addItem(label, key)
            
        # Scale Presets
        self.combo_resize_mode.addItem(self.tr("res_scale_75"), "scale_75")
        self.combo_resize_mode.addItem(self.tr("res_scale_50"), "scale_50")
        self.combo_resize_mode.addItem(self.tr("res_scale_33"), "scale_33")
        self.combo_resize_mode.addItem(self.tr("res_scale_25"), "scale_25")
    
        # Add Custom & Scale Generic
        self.combo_resize_mode.addItem(self.tr("res_scale"), "scale")
        self.combo_resize_mode.addItem(self.tr("res_custom"), "custom")
        
        # Restore selection
        if current_key:
            idx = self.combo_resize_mode.findData(current_key)
            if idx >= 0:
                self.combo_resize_mode.setCurrentIndex(idx)
            else:
                self.combo_resize_mode.setCurrentIndex(0) # Default Original
        else:
             self.combo_resize_mode.setCurrentIndex(0)

        self.combo_resize_mode.blockSignals(False)

    def populate_resize_modes(self):
        current_data = self.combo_resize_mode.currentData()
        self.combo_resize_mode.blockSignals(True)
        self.combo_resize_mode.clear()
        
        # Add items with UserData
        self.combo_resize_mode.addItem(self.tr("res_original"), "original")
        self.combo_resize_mode.addItem(self.tr("res_scale"), "scale")
        self.combo_resize_mode.addItem(self.tr("res_custom"), "custom")
        
        self.combo_resize_mode.insertSeparator(3)
        
        # Presets (75, 50, 33, 25)
        self.combo_resize_mode.addItem(self.tr("res_scale_75"), "scale_75")
        self.combo_resize_mode.addItem(self.tr("res_scale_50"), "scale_50")
        self.combo_resize_mode.addItem(self.tr("res_scale_33"), "scale_33")
        self.combo_resize_mode.addItem(self.tr("res_scale_25"), "scale_25")
        
        self.combo_resize_mode.insertSeparator(8)
        
        # Resolutions
        self.combo_resize_mode.addItem("1920x1080 (1080p)", "1920x1080")
        self.combo_resize_mode.addItem("1280x720 (720p)", "1280x720")
        self.combo_resize_mode.addItem("640x480", "640x480")
        
        # Restore selection
        idx = self.combo_resize_mode.findData(current_data)
        if idx >= 0:
            self.combo_resize_mode.setCurrentIndex(idx)
        else:
            self.combo_resize_mode.setCurrentIndex(0) # Default to Original
            
        self.combo_resize_mode.blockSignals(False)

    def update_resize_ui(self):
        key = self.combo_resize_mode.currentData()
        
        is_custom_dim = (key == "custom")
        is_custom_scale = (key == "scale")
        
        self.widget_custom_dim.setVisible(is_custom_dim)
        self.widget_scale.setVisible(is_custom_scale)

    def eventFilter(self, source, event):
        # Watch video widget for geometry changes and drag/drop
        if source == self.video_widget:
            if event.type() == QEvent.Type.Resize or event.type() == QEvent.Type.Move:
                self.update_overlay_geometry()
                # Do not return True here, allow the event to propagate for layout/widget to handle
            elif event.type() == QEvent.Type.Show:
                if self.crop_overlay is not None:
                    self.crop_overlay.show()
                    self.update_overlay_geometry()
            elif event.type() == QEvent.Type.Hide:
                if self.crop_overlay is not None:
                    self.crop_overlay.hide()
            
            # Drag & Drop Support for video_widget
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasUrls():
                    event.accept()
                else:
                    event.ignore()
                return True
            elif event.type() == QEvent.Type.Drop:
                files = [u.toLocalFile() for u in event.mimeData().urls()]
                video_files = [f for f in files if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.gif', '.webp'))]
                if video_files:
                    self.load_video(video_files[0])
                event.accept()
                return True
            # For other events on video_widget, let them propagate
            return False

        # Spacebar in File List -> Play/Pause
        if hasattr(self, 'list_batch') and source == self.list_batch and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Space:
                self.toggle_play()
                return True # Consume event

        # Generic handling for other widgets (delegated via _install_event_filter_recursive)
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
                "resize_mode": "original", # Default key
                "width": orig_w, # Default to original width
                "height": orig_h, # Default to original height
                "scale": 100, # Default to 100% scale
                "start_time": -1,
                "end_time": -1,
                "orig_width": orig_w,
                "orig_height": orig_h,
                "duration": duration if 'duration' in locals() else 0,
                # Crop Settings
                "crop_enabled": False,
                "crop_x": 0.0,
                "crop_y": 0.0,
                "crop_w": 1.0,
                "crop_h": 1.0
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
        
        # Force first frame to show (Black screen fix)
        # We need to play briefly then pause.
        self.media_player.play()
        self.media_player.pause()
        self.media_player.setPosition(0)
        
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
        self.slider_quality.setValue(s["quality"])
        
        # Resolution
        # Update combo options based on effective size (Cropped if enabled)
        c_enabled = s.get("crop_enabled", False)
        orig_w = s["orig_width"]
        orig_h = s["orig_height"]
        
        cw = s.get("crop_w", 1.0)
        ch = s.get("crop_h", 1.0)
        
        cur_eff_w = int(orig_w * cw) if c_enabled else orig_w
        cur_eff_h = int(orig_h * ch) if c_enabled else orig_h
        
        self.update_resolution_combo(cur_eff_w, cur_eff_h)
        
        # Translate stored mode to current language - Disabled per user request (English Only)
        # Restore Mode via Key
        mode_key = s.get("resize_mode", "original")
        
        # LEGACY MIGRATION: Map old localized/text strings to new keys
        if mode_key in ["Original", "원본", "res_original"]: mode_key = "original"
        elif mode_key in ["Custom Dimensions", "사용자 지정 크기", "res_custom"]: mode_key = "custom"
        elif mode_key in ["Scale (%)", "비율 (%)", "res_scale", "res_scale_pct"]: mode_key = "scale"
        # Handle "1920x1080 (1080p)" style strings - extract key "1920x1080"
        elif isinstance(mode_key, str) and "x" in mode_key and "p)" in mode_key:
             import re
             m = re.match(r"(\d+)x(\d+)", mode_key)
             if m: mode_key = f"{m.group(1)}x{m.group(2)}"
        
        idx = self.combo_resize_mode.findData(mode_key)
        if idx >= 0:
            self.combo_resize_mode.setCurrentIndex(idx)
        else:
            # Fallback if specific resolution key not found (maybe video size changed?)
            # Default to original
             self.combo_resize_mode.setCurrentIndex(0)
        
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

        # Crop Settings
        c_enabled = s.get("crop_enabled", False)
        
        # Trigger toggle_crop via signal to handle Lazy Creation
        if self.grp_crop.isChecked() != c_enabled:
             self.grp_crop.setChecked(c_enabled)
        # If already matching, but enabled, make sure overlay exists? 
        # (Should be handled by toggle_crop state maintenance, but if loaded from file start...)
        
        if c_enabled:
            # Ensure overlay exists (just in case)
            if self.crop_overlay is None:
                self.toggle_crop(True)
                
            # Restore rect
            cx = s.get("crop_x", 0.0)
            cy = s.get("crop_y", 0.0)
            cw = s.get("crop_w", 1.0)
            ch = s.get("crop_h", 1.0)
            
            # Map normalized to widget coords
            # ww = self.video_widget.width()
            # wh = self.video_widget.height()
            
            # FIX: Use calculate_video_rect to map back to actual video area
            vx, vy, vw, vh = self.calculate_video_rect(path)
            
            if vw > 0 and vh > 0:
                rect = QRect(
                    int(vx + (cx * vw)), 
                    int(vy + (cy * vh)),
                    int(cw * vw), 
                    int(ch * vh)
                )
                self.crop_overlay.selection_rect = rect
                self.crop_overlay.update()
                # Z-Order Fix
                self.crop_overlay.raise_()
                self.crop_overlay.activateWindow()

        self._updating_ui = False
        
    def save_settings_from_ui(self):
        if self._updating_ui: return
        
        items = self.list_batch.selectedItems()
        for item in items:
            row = self.list_batch.row(item)
            if 0 <= row < len(self.video_files):
                path = self.video_files[row]
                s = self.video_settings[path]
                
                s["format"] = self.combo_format.currentText()
                s["fps"] = self.spin_fps.value()
                s["quality"] = self.slider_quality.value()
                
                # Check who sent signal
                sender = self.sender()
                if sender == self.slider_quality:
                    s["quality"] = self.slider_quality.value()
 
                s["quality"] = self.slider_quality.value()

                s["resize_mode"] = self.combo_resize_mode.currentData()
                s["width"] = self.spin_width.value()
                s["height"] = self.spin_height.value()
                s["scale"] = self.spin_scale.value()
                
    # Old duplicate method removed. Correct implementation is defined around line 1450.
        
    def save_crop_to_settings(self):
        # Called when overlay changes or toggle changes
        items = self.list_batch.selectedItems()
        if not items: return
        
        # Normalize
        r = self.crop_overlay.selection_rect
        ww = self.video_widget.width()
        wh = self.video_widget.height()
        
        if ww <= 0 or wh <= 0: return # Avoid div zero
        
        # FIX: Normalize against actual Video Rect, not Widget Rect
        # We need to know which file?
        items = self.list_batch.selectedItems()
        if not items: return
        # Use first selected for calculation context
        row = self.list_batch.row(items[0])
        if row < 0 or row >= len(self.video_files): return
        path = self.video_files[row]
        
        vx, vy, vw, vh = self.calculate_video_rect(path)
        
        if vw <= 0 or vh <= 0: return # Safety
        
        # Calculate relative to video rect
        # Clamp to 0-1
        nx = (r.left() - vx) / vw
        ny = (r.top() - vy) / vh
        nw = r.width() / vw
        nh = r.height() / vh
        
        # Clamp Logic (User might select black bars slightly? We should clamp to video content)
        # Actually if user selects black bars, we should probably clip it.
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))
        # Width/Height clamping is tricky if x/y moved.
        # Simple clamp:
        if nx + nw > 1.0: nw = 1.0 - nx
        if ny + nh > 1.0: nh = 1.0 - ny
        
        enabled = self.grp_crop.isChecked()
        
        # Determine effective dimensions for UI update
        eff_w = r.width() if enabled else self.video_widget.width() # Fallback, ideally from orig video metadata but widget size is proxy
        eff_h = r.height() if enabled else self.video_widget.height()
        
        # Better: use orig_width from settings if available
        # We prefer to update the combo NOW so user sees relevant resolutions
        # But we need to iterate all items? No, just save state.
        
        for item in items:
             row = self.list_batch.row(item)
             if 0 <= row < len(self.video_files):
                 path = self.video_files[row]
                 s = self.video_settings[path]
                 s["crop_enabled"] = enabled
                 s["crop_x"] = nx
                 s["crop_y"] = ny
                 s["crop_w"] = nw
                 s["crop_h"] = nh
                 
                 # If this is the currently loaded one (likely), update combo?
                 # Only if single selection or it's the anchor
                 if len(items) == 1:
                     # Calculate effective original size
                     orig_w = s["orig_width"]
                     orig_h = s["orig_height"]
                     
                     cur_eff_w = int(orig_w * nw) if enabled else orig_w
                     cur_eff_h = int(orig_h * nh) if enabled else orig_h
                     
                     self.update_resolution_combo(cur_eff_w, cur_eff_h)

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

    # --- Helper: Video Rect Calculation ---
    def calculate_video_rect(self, path):
        """
        Calculates the actual rectangle (x, y, w, h) where the video content is drawn
        within the self.video_widget, accounting for AspectRatioMode.KeepAspectRatio.
        """
        if not path or path not in self.video_settings:
            # Fallback to full widget
            return 0, 0, self.video_widget.width(), self.video_widget.height()
            
        s = self.video_settings[path]
        orig_w = s.get("orig_width", 0)
        orig_h = s.get("orig_height", 0)
        
        widget_w = self.video_widget.width()
        widget_h = self.video_widget.height()
        
        if orig_w <= 0 or orig_h <= 0 or widget_w <= 0 or widget_h <= 0:
            return 0, 0, widget_w, widget_h
            
        # Calculate ratios
        video_ratio = orig_w / orig_h
        widget_ratio = widget_w / widget_h
        
        # Fit logic (Keep Aspect Ratio)
        if video_ratio > widget_ratio:
            # Video is wider than widget (or widget is taller)
            # Fits width, letterbox top/bottom
            draw_w = widget_w
            draw_h = int(widget_w / video_ratio)
            x = 0
            y = (widget_h - draw_h) // 2
        else:
            # Video is taller than widget (or widget is wider)
            # Fits height, pillarbox left/right
            draw_h = widget_h
            draw_w = int(widget_h * video_ratio)
            y = 0
            x = (widget_w - draw_w) // 2
            
        return x, y, draw_w, draw_h

    # --- Input Handling ---
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            # Check if focus is on a text input to avoid conflict?
            focus_widget = QApplication.focusWidget()
            if isinstance(focus_widget, (QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox)):
                # Let the input handle the space
                super().keyPressEvent(event)
                return
                
            # Otherwise, toggle play
            if self.media_player.source().isValid():
                self.toggle_play()
                event.accept()
                return
                
        super().keyPressEvent(event)
        
    def mousePressEvent(self, event):
        # Taking focus on background click allows Spacebar play/pause to work immediately
        # without triggering previous buttons.
        target = self.childAt(event.pos())
        # If clicking empty space (target is None or just the window/container background)
        if target is None or target == self or target == self.video_container or target == self.centralWidget():
            self.setFocus()
            
        super().mousePressEvent(event)

    # --- Debugging & Sync Methods (Moved to end to preserve indentation structure) ---

    def log_debug(self, msg):
        try:
            log_path = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__), "debug.log")
            with open(log_path, "a", encoding="utf-8") as f:
                import datetime
                timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")
                f.write(f"[{timestamp}] {msg}\n")
        except:
            pass

    def force_sync_crop_state(self):
        checked = self.grp_crop.isChecked()
        self.log_debug(f"Force Sync. Checked={checked}")
        if not checked:
            if self.crop_overlay:
                self.crop_overlay.hide()
                self.log_debug("Force Sync: HIDDEN")
        else:
            if self.crop_overlay is None:
                self.toggle_crop(True) # Will creating it
            else:
                self.crop_overlay.show()
                self.update_overlay_geometry(force=True)
            
    def showEvent(self, event):
        super().showEvent(event)
        self.log_debug("MainWindow ShowEvent")
        self.force_sync_crop_state()

# ----------------------------
# Main Execution
# ----------------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
