VtoG Tool
A simple GUI tool for converting video files into GIFs.
This application is built with Python (tkinter) and uses ffmpeg and gifski to generate high-quality GIF files.

Features

Convert videos to GIF format (supports mp4, mkv, avi, mov, webm, wmv)
Real-time video preview using a timeline slider
Play and pause video directly inside the application
Set start position based on the current frame
Set end position based on the current frame
Manually enter clip range using seconds or time format (mm:ss, hh:mm:ss)
Visual timeline bar showing the selected clip range
Adjust GIF quality from 1 to 100 (powered by gifski)
Set custom output FPS for the GIF
Keep original video resolution
Select from predefined resolution presets (1080p, 720p, etc.)
Set custom resolution using width and height values
Scale resolution by percentage based on the original size
Estimate final GIF file size before converting
Open video files using drag and drop (optional feature)
No command prompt windows shown during conversion
Conversion progress displayed via status messages
Output GIF is saved in the same folder as the source video

How To Use
Extract all files from the archive to the same folder
Launch the application executable
Click the Open Video button or drag and drop a video file into the window
Preview the video using the timeline slider
Set start and end positions if needed
Adjust quality, FPS, and resolution settings
Optionally click Estimate Size to preview output file size
Click Convert to GIF
The GIF file will be created next to the original video

Included Files
VtoG executable
ffmpeg.exe (official build)
gifski.exe (official build)

Requirements
Windows operating system
No additional installation required
ffmpeg and gifski are already included with the tool

Notes
ffmpeg.exe and gifski.exe must remain in the same folder as the program
Output resolution is automatically adjusted to even numbers for compatibility
Very short clips may produce less accurate size estimates
Conversion runs in the background to keep the UI responsive

License
This tool is provided free of charge
ffmpeg and gifski are included as unmodified official binaries
ffmpeg and gifski are distributed under their respective licenses