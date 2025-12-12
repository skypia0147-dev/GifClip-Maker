[ GifClip Maker - v3.0 ]

An all-in-one high-quality Video to GIF/WebP conversion tool powered by Python (PyQt6).
With a sleek dark theme UI and powerful editing features (Crop, Resize, Cut), anyone can easily create high-quality animated GIFs.

It combines the powerful encoding performance of FFmpeg with the high-quality GIF compression engine of Gifski to produce the best possible results.

--------------------------------------------------------------------------------
[ v3.0 Major Updates ]

1. Powerful Video Editing Tools
   - Crop: Provides an intuitive overlay UI to crop specific parts of the screen.
     * Presets supported: 1:1, 16:9, 9:16, 4:3, Free Ratio.
     * You can adjust the area directly by dragging with the mouse.
   - Precision Resize:
     * Offers various options including Keep Original, Scale Down (75%, 50%, 25%), and Custom Resolution.
   - Keyboard Control: You can Play/Pause the video using the Spacebar.

2. Significantly Improved User Experience
   - Menu Bar Introduced: Operations like Open Video and Language Settings are neatly organized in the top menu, expanding the workspace.
   - Improved UI Layout: Consistent margins and alignment provide a more professional and clean appearance.
   - Video Load Fix: Fixed an issue where a black screen appeared on load; now immediately shows the first frame.
   - Full Multilingual Support: Instantly switch between English and Korean from the menu, with the program title localized.
   - Drag & Drop: Simply drag and drop a video into the program window to load it immediately.

3. Bug Fixes
   - Fixed an issue where WebP file sizes were abnormally large during conversion.

4. Verified Performance
   - High-Quality Conversion: Uses the Gifski engine to create top-tier GIFs with minimal color loss.
   - Size Estimation: Pre-calculate the estimated file size before conversion (using 2-second sampling).
   - Multi-threading: The UI remains responsive during conversion, ensuring stable operation.

--------------------------------------------------------------------------------
[ Detailed Feature List ]

1. Format
   - GIF: Highly compatible animated image format.
   - WebP: Next-generation format offering higher compression and quality compared to GIF.

2. Video Control
   - Cut Segment: Extract desired segments by dragging the timeline slider or using the [Set Start/Set End] buttons.
   - Play/Pause: Use Spacebar or click the button.
   - Timeline Navigation: Instantly move to the desired frame using the slider.

3. Quality & Size Control
   - FPS (Frame Rate): Set frames per second for smoother animations.
   - Quality: Adjust the balance between file size and quality (1-100).
   - Resolution: Resize using presets (FHD, HD) or manual input.

4. Batch Processing
   - Register multiple video files at once for continuous management.
   - Save different settings for each file and convert them individually or in batch.

--------------------------------------------------------------------------------
[ How to Use ]

1. Select [File] Menu -> [Open Video], or drag a video into the program window.
2. Adjust the yellow timeline slider at the bottom or use [Set Start]/[Set End] buttons to select the segment to convert.
3. (Optional) Check the [Crop] box to crop a part of the screen.
4. Set Output Format, FPS, Quality, and Size in the right settings panel.
5. Select a file from the list and click [Estimate Size], or click [Convert] immediately.
6. Once conversion is complete, the result is saved in the same folder as the original file.

--------------------------------------------------------------------------------
[ System Requirements ]

- OS: Windows 10 / 11 (64-bit)
- Dependencies: No separate codec or program installation required. (ffmpeg.exe, gifski.exe included)

--------------------------------------------------------------------------------
[ License & Credits ]

- Developed by: Smooth + Antigravity (Powered by Google Deepmind)
- License: This program is Freeware.
- Open Source Notice:
  This program includes binaries from the FFmpeg and Gifski projects and compliance with their respective license regulations.