================================================================================
LOCALCUT - CLIPPING SOFTWARE STUDIO
Autonomous Viral Moment Extraction, AI Face Tracking & Multi-Format Video Master
================================================================================

Repository: https://github.com/MKN-GlitchOp/ClippingSoftware
Author: Michael Pierce (MKN-GlitchOp)
Version: 2.0.0 Studio Edition


--------------------------------------------------------------------------------
1. OVERVIEW
--------------------------------------------------------------------------------
LocalCut (ClippingSoftware) is a high-performance, local-first AI video clipping
workstation engineered for creators, streamers, and video editors. It transforms
long-form YouTube videos, Twitch streams, and podcast recordings into viral,
broadcast-ready vertical (9:16) shorts, reels, TikToks, and widescreen (16:9) clips.

Everything runs 100% locally on your machine with zero external cloud API
dependencies. All transcripts, audio analysis, face detection, ASS styling, and
video rendering occur on your CPU/GPU using modern open-source foundations.


--------------------------------------------------------------------------------
2. COMPREHENSIVE LIST OF OVERHAULS & FEATURES IMPLEMENTED
--------------------------------------------------------------------------------

[+] MULTI-DIMENSION EXPORT SELECTION (1080x1920 vs 1920x1080 vs 1:1)
    - Full control over orientation and resolution per-clip and in batch:
      * 1080 x 1920 (Vertical 9:16): Optimized for TikTok, YouTube Shorts, Reels.
      * 1920 x 1080 (Landscape 16:9): Standard widescreen for YouTube & desktop.
      * 1080 x 1080 (Square 1:1): Social feeds & Instagram.
    - Quality scaling options: 1080p Full HD (default), 720p HD, and 4K Ultra HD.
    - Real-time video player monitor screen that dynamically reshapes its aspect
      ratio between vertical phone format and widescreen monitor preview.

[+] SUBTITLE CONTROLS: BURN-IN VS CLEAN VIDEO + SYNCHRONIZED SRT EXPORT
    - Choose whether to export with animated subtitles or clean video:
      * "WITH SUBTITLES (Burn-in)": Styled karaoke word-by-word highlight animation
        permanently rendered onto the MP4.
      * "WITHOUT SUBTITLES (Clean)": Pristine, clean video without text overlays.
    - Synchronized .SRT Subtitle Generation:
      * Generates a matching .srt subtitle file aligned to second 00:00:00,000 of
        the clip, ready for drag-and-drop into Adobe Premiere Pro, DaVinci Resolve,
        or CapCut.
      * One-click direct SRT download buttons on each candidate card and editor bar.
    - Intelligent ASS Typography Scaling:
      * Automatically scales font sizes, outlines, and margins based on aspect ratio
        and resolution (prevents oversized captions in 16:9 widescreen).

[+] DEEP-LEARNING AI ACTIVE SPEAKER FACE TRACKING
    - Integrated OpenCV YuNet ONNX face detection (backend/services/face_tracker.py).
    - Runs at ~7ms/frame on standard CPU with high accuracy on tilted/side profiles.
    - Generates smooth camera pan trajectories using deadband dampening (ignoring
      micro-fidgets < 2.5%) and builds time-based piecewise linear interpolation
      expressions directly into FFmpeg filtergraphs.
    - Instant toggle: "⚡ AI Face Tracking (ON)" vs "Fixed Crop (OFF)" with fallback
      anchor controls.

[+] TACTILE IN / OUT TRIMMING & TRANSPORT CONTROLS
    - Tactile transport bar with "[ Mark IN (I) ]", "[ Mark OUT (O) ]", and "⇤ Jump"
      buttons for instant playhead boundary tagging.
    - Keyboard hotkeys: Space (Play/Pause), I (Mark In), O (Mark Out), Home/End (Jump),
      Left/Right arrows for fine 1s / 0.1s frame stepping.
    - Draggable timeline scrubber handles: [IN] and [OUT] handles directly on the
      scrubber bar for drag-and-drop boundary adjustment.
    - Word-level transcript clicking: Clicking any word in the transcript seeks
      the video player instantly to that exact moment.

[+] EMBEDDED RMS AUDIO WAVEFORM VISUALIZATION
    - Direct visual audio energy waveform layer rendered across the timeline scrubber.
    - Powered by GET /api/projects/{pid}/waveform, extracting 0.5s RMS vocal energy
      data so creators can visually pinpoint screams, laughs, and punchlines.

[+] VIRAL CLIP EXTRACTION & EDITORIAL RANKING HEURISTICS
    - Upgraded lexical model trained on modern creator and streamer reaction hooks
      ("bro", "chat", "clip that", "ain't no way", "cooked", "trolling", "no cap",
       "locked in", "crazy", "insane", "gg", etc.).
    - Multi-signal acoustic scoring bonus:
      * +12 for high vocal intensity and emotional peaks.
      * +10 for climactic audio energy crescendos.
      * +6 for energetic opening bursts.
    - Sentence-boundary pause snapping: Clips snap to natural speech breaks,
      preventing mid-syllable cutoffs.

[+] BROADCAST AUDIO MASTERING (EBU R128 LOUDNORM)
    - Integrated broadcast loudness normalization (-af loudnorm=I=-14:TP=-1.5:LRA=11)
      into FFmpeg rendering for punchy, balanced audio optimized for mobile speakers.

[+] CUSTOM DESTINATION FOLDER & WINDOWS EXPLORER INTEGRATION
    - Allows custom folder destination paths for all rendered exports.
    - Quick-select presets: Videos\Shorts, Desktop, Downloads, and Default.
    - One-click "Show in Folder" button that launches Windows Explorer (explorer.exe)
      directly highlighting the exported files.

[+] BATCH RENDER QUEUE MODAL
    - Select multiple candidate clips and render them in batch.
    - Modal provides global dimension selection (1080x1920 vs 1920x1080), subtitle
      burn-in toggles, SRT export options, face tracking, and folder targets.

[+] OBSIDIAN / CARBON STUDIO WORKSTATION AESTHETIC
    - Clean monospaced interface styled with Google's Source Code Pro font.
    - Dark graphite/carbon palette with responsive layouts, accessible contrast,
      and safety-confirmed deletions for projects and clips.


--------------------------------------------------------------------------------
3. PROJECT ARCHITECTURE & FILE STRUCTURE
--------------------------------------------------------------------------------

ClippingSoftware/
├── backend/
│   ├── main.py                  FastAPI application routes and job dispatcher
│   ├── storage.py               Thread-safe file persistence & project state
│   └── services/
│       ├── clip_analysis.py     Multi-signal lexical, acoustic & heuristic ranking
│       ├── face_tracker.py      YuNet ONNX deep learning face tracking & FFmpeg lerp
│       ├── media.py             FFmpeg/FFprobe wrappers, audio extraction & RMS waveform
│       ├── reframing.py         Filtergraph generation for 9:16, 16:9, 1:1, blur & crop
│       ├── renderer.py          Export engine with loudnorm, ASS burn-in, SRT & copying
│       ├── subtitles.py         ASS karaoke animation & synchronized SRT generator
│       └── transcription.py     Faster-Whisper local speech transcription
├── frontend/
│   ├── index.html               Vite HTML entry with Source Code Pro font
│   ├── package.json             Node dependencies & build scripts
│   ├── vite.config.js           Vite bundler configuration
│   └── src/
│       ├── App.jsx              Main application shell, header, pipeline & tabs
│       ├── style.css            Obsidian workstation styling & responsive layout
│       ├── components/
│       │   ├── BatchRenderModal.jsx  Batch render queue & configuration modal
│       │   ├── Candidates.jsx        Shortlist clips table with instant filtering
│       │   ├── ClipEditor.jsx        Monitor, timeline scrubber, transport & controls
│       │   ├── Icons.jsx             Crisp SVG studio icons
│       │   └── Progress.jsx          Live pipeline execution and step progress
│       └── lib/
│           ├── api.js           REST API client, waveform, system dirs & folder reveal
│           └── useWorkspace.js  React custom hook for project polling & mutation
├── tests/
│   ├── test_analysis.py         Heuristics, ranking & keyword extraction tests
│   ├── test_face_tracker.py     YuNet tracking, smoothing & filtergraph tests
│   ├── test_refinements.py      API endpoint, batch render & bundle tests
│   └── test_subtitles.py        ASS timing, resolution scaling & SRT generation tests
├── models/
│   └── face_detection/          YuNet ONNX model cache
├── requirements.txt             Python package requirements
├── .gitignore                   Git exclusions for temp, venv, and large files
└── read me.txt                  Comprehensive documentation and release notes


--------------------------------------------------------------------------------
4. API SPECIFICATION
--------------------------------------------------------------------------------

GET    /api/health                       System health, ffmpeg, models, disk space
GET    /api/projects                     List all projects
POST   /api/projects                     Create new project from YouTube URL or upload
GET    /api/projects/{pid}               Get project state, settings, candidates
DELETE /api/projects/{pid}               Delete project and remove project folder
POST   /api/projects/{pid}/rename        Rename project title
POST   /api/projects/{pid}/retry         Retry a failed processing job
POST   /api/projects/{pid}/analyze       Re-analyze with customized clip lengths
GET    /api/projects/{pid}/source        Stream original source video
POST   /api/projects/{pid}/clips         Add custom clip with manual In/Out timestamps
DELETE /api/projects/{pid}/clips/{cid}   Delete candidate clip
POST   /api/projects/{pid}/clips/{cid}   Edit clip title, In/Out, ratio, layout, crop
POST   /api/projects/{pid}/render        Render single or batch clips with options
GET    /api/projects/{pid}/clips/{cid}/srt  Download synchronized .srt subtitle file
GET    /api/projects/{pid}/files/{name}  Stream or download exported MP4 file
GET    /api/projects/{pid}/bundle        Download ZIP bundle of all rendered clips
GET    /api/projects/{pid}/waveform      Get 0.5s RMS vocal energy series
GET    /api/system-directories           Get user Home, Videos, Desktop, Downloads paths
POST   /api/projects/{pid}/open-folder   Reveal exports folder in Windows File Explorer


--------------------------------------------------------------------------------
5. QUICK START & INSTALLATION
--------------------------------------------------------------------------------

PREREQUISITES:
- Windows 10/11, macOS, or Linux
- Python 3.10+
- Node.js 18+ and npm
- FFmpeg and FFprobe installed and available on system PATH

SETUP INSTRUCTIONS:

1. Clone Repository:
   git clone https://github.com/MKN-GlitchOp/ClippingSoftware.git
   cd ClippingSoftware

2. Setup Python Virtual Environment:
   python -m venv .venv
   .\.venv\Scripts\activate          # Windows PowerShell / CMD
   # source .venv/bin/activate        # Linux / macOS
   pip install -r requirements.txt

3. Build Frontend:
   cd frontend
   npm install
   npm run build
   cd ..

4. Launch Server:
   .\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

5. Open Browser:
   Navigate to http://localhost:8000


--------------------------------------------------------------------------------
6. RUNNING TESTS
--------------------------------------------------------------------------------
To run the automated test suite verifying all 13 core subsystems:
   .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider


================================================================================
Licensed under MIT. Crafted for high-velocity video creators and editors.
================================================================================
