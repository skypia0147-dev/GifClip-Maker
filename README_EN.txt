[ Video To GIF Tool (v2.0 - PyQt6 Edition) ]

A powerful and modern GUI tool for converting video files into high-quality GIFs or WebP animations.  
This application has been completely rebuilt using PyQt6 for a modern dark-themed UI and utilizes FFmpeg and Gifski for superior conversion quality and performance.

--------------------------------------------------------------------------------
[ Features ]

1. Core Functionality
   - High-Quality Conversion: Uses gifski for optimal GIF quality (colors/dithering).
   - Format Support: Supports GIF and WebP output.
   - Batch Processing:
     * Add multiple videos to a list.
     * Apply individual settings (FPS, Resize, Quality) for each video.
     * Convert selected videos or the entire batch.
   - Accurate Size Estimation: Predicts the final file size using a 2.0s sample.
   - Persistent Settings: Language and other preferences are saved automatically.

2. Modern UI & Experience
   - Fluid Preview: Real-time video playback using GPU acceleration (QMediaPlayer).
   - Visual Timeline: Drag-and-drop slider to select Start/End points easily.
   - Drag & Drop: Drag video files directly into the window to load them.
   - Dark Theme: Sleek, professional dark interface.

3. Detailed Control
   - Range Selection: Set Start/End visually or manually (mm:ss).
   - Resolution Control: Presets (1080p, 720p), Custom Dimensions, or Scale by %.
   - Frame Rate (FPS): Auto-detected from source or custom value.
   - Quality: Adjustable quality slider (1-100).
   - Localization: Supports English and Korean.

--------------------------------------------------------------------------------
[ How To Use ]

1. Launch: Run VideoToGifTool.exe.
2. Add Videos: Drag & drop files or click "Open Video".
3. Select Range: Use the timeline slider or "Set Start/End" buttons to trim the video.
4. Configure: Adjust FPS, Resize, and Quality settings on the right panel.
5. Estimate (Optional): Select files in the list and click "Estimate Size" to check expected output size.
6. Convert: Click "Convert" to start processing.
   * The result is saved in the same folder as the source video.

--------------------------------------------------------------------------------
[ Requirements ]

- Windows 10 / 11 (64-bit recommended)
- No external installation required (Portable Build).
- ffmpeg.exe and gifski.exe are bundled internally.

--------------------------------------------------------------------------------
[ License ]

- This tool is provided free of charge.
- FFmpeg and Gifski are distributed under their respective licenses.