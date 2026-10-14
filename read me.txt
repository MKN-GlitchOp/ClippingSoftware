================================================================================
LOCALCUT - CLIPPING SOFTWARE PRO STUDIO
100% Free, Private, Local Alternative to EveryGen.ai & Opus Clip
Autonomous Viral Moment Extraction, AI Face Tracking, Viral Subtitles & MCP Server
================================================================================

Repository: https://github.com/MKN-GlitchOp/ClippingSoftware
Author: Michael Pierce (MKN-GlitchOp)
Version: 2.5.0 Pro Studio Edition


--------------------------------------------------------------------------------
1. OVERVIEW: WHY LOCALCUT SURPASSES CLOUD CLIPPERS (EVERYGEN / OPUS)
--------------------------------------------------------------------------------
LocalCut (ClippingSoftware) is a high-performance, local-first AI video clipping
workstation engineered for creators, streamers, and video editors who refuse to pay
monthly subscription fees or sacrifice video privacy.

Unlike cloud tools like EveryGen.ai or Opus Clip that charge $20-$100/month, cap
you at 5-10 clips, enforce server queues, throttle resolutions, and watermark exports:
- 100% Free & Unlimited: Process as many videos, hours, and clips as your drive holds.
- 100% Local & Private: Audio transcription, face detection, ASS subtitle rendering,
  and video encoding occur entirely on your own CPU/GPU using open-source models.
- Beyond Top 5: Extract 5, 10, 15, 25, or up to 50 viral candidate clips per video.
- 1-Click Auto-Pilot: Paste a link -> automatically analyze, detect faces, burn viral
  captions, and export finished vertical shorts without manual intervention.
- Ready to Post Hub: Instantly copy viral titles, hooks, descriptions, and trending
  hashtag stacks formatted specifically for TikTok, YouTube Shorts, and Instagram Reels.
- Native MCP Server: Connect ChatGPT (via Custom GPT / Actions / SSE) or Claude
  Desktop / Antigravity directly to your local clipping studio via Model Context Protocol.


--------------------------------------------------------------------------------
2. PRODUCT VISION: WHAT WE WANT TO GO FOR INSTEAD
--------------------------------------------------------------------------------
LocalCut Pro Studio is built from the ground up as a creator-first rebellion
against cloud clipping SaaS platforms (EveryGen.ai, Opus Clip, Submagic, Klap).
Instead of paying $20-$100/month for throttled queues, blurry 720p compression,
strict 5-clip caps, and generic linear snippet cutting, here is EXACTLY what we
go for instead:

[1] THE "SUMMARIZE & COLD-OPEN HOOK" VIRAL FORMAT (DROPOUTS & SIDEMEN 20V1 STYLE)
    * The Problem with Standard Clippers:
      EveryGen, Opus, and standard AI clippers blindly extract linear chronological
      chunks. They start at the natural beginning of a conversation, which is often
      slow, expository, and causes a 70%+ viewer swipe-away rate within the first 2
      seconds on TikTok, YouTube Shorts, and Instagram Reels.
    * What We Go For Instead:
      - Explosive Climax Cold-Open: LocalCut automatically extracts a 2.0s - 3.5s
        high-stakes punchline, dramatic reaction, or shocking climax cue from the
        end of the moment and prepends it to the very start (t = 0.0s) of the short.
      - "WAIT FOR IT..." Viral Teaser Badge: Overlays a high-retention pill badge
        (e.g., "⚡ WAIT FOR IT...", "😱 BEST PART...", "🔥 WATCH TILL END", "⚠️ NO WAY...")
        specifically during the cold-open hook so viewers immediately know an insane
        payoff is coming.
      - Seamless Context Retransmission: Cuts smoothly from the explosive teaser
        straight into the story setup / context buildup WITHOUT spoiling the full scene.
      - Strategic Cliffhanger Cut: Option to end the short right before the final
        punchline resolves, driving massive comment debate ("WHERE IS PART 2?!",
        "WHAT DID HE SAY?!"), skyrocketing algorithmic watch time, and driving
        traffic to the full-length video.
      - 1-Click Automation & Manual Precision: Enabled via `summarize_mode` in
        Auto-Pilot or New Project settings, with tactile visual controls in the
        Clip Editor to adjust hook start/end, preview the teaser, and customize badges.

[2] STUDIO-GRADE CRISP VISUALS & AUDIO (SOLVING "AWFUL RESOLUTION")
    * The Problem with Cloud Clippers:
      Cloud tools heavily compress exports to minimize their bandwidth and compute
      costs. Cropping 1920x1080 horizontal footage into vertical 1080x1920 9:16 results
      in pixelated, soft, and muddy video with washed-out dialogue.
    * What We Go For Instead:
      - Visually Lossless CRF 18 H.264 Encoding: High-profile encoding preserving
        crisp facial features, hair detail, and sharp text.
      - Lanczos High-Order Resampling: High-accuracy scaling filtergraph
        (`scale=1080:1920:flags=lanczos+accurate_rnd`) that avoids bilinear blurring
        when re-framing 16:9 widescreen into vertical 9:16.
      - Contrast Adaptive Sharpening (CAS / unsharp): Subtle sharpening filter pass
        to restore textures and edge acuity during crop and pan operations.
      - Multi-Aspect Ratio Freedom: Instant switching between 9:16 (Shorts/TikTok/Reels),
        16:9 (YouTube desktop), and 1:1 (Square social feeds) with smart blur padding.
      - EBU R128 Broadcast Loudness Mastering: Automatic `-14 LUFS` normalization
        with `-1.5 dBTP` true-peak limiting (`loudnorm`) baked directly into the
        FFmpeg filtergraph for punchy, distortion-free mobile speaker playback.

[3] "PASTE-TO-POST" INSTANT CREATOR VELOCITY
    * What We Go For Instead:
      Zero manual friction. A single automated pipeline:
      1. Paste YouTube URL or drop local video file.
      2. Automated high-speed stream download with YouTube challenge bypass.
      3. Faster-Whisper CPU INT8 speech-to-text with word-level timestamps.
      4. Multi-signal moment ranking (lexical hooks, acoustic energy peaks, speech velocity).
      5. YuNet ONNX deep-learning face tracking for smooth vertical panning.
      6. ASS dynamic karaoke subtitles with Alex Hormozi active-word bounce pop (\fscx118\fscy118).
      7. Ready-to-Post Social Hub: 1-click generation of platform-tailored titles,
         first-frame hooks, engaging descriptions, and trending hashtag stacks.

[4] ZERO PAYWALLS, EXPANDED DISCOVERY & COMPLETE PRIVACY
    * What We Go For Instead:
      - 100% Free & Open: No $20 - $100/mo subscription paywalls, no watermark extortion.
      - Up to 50 Clips: Discover 5, 10, 15, 25, or up to 50 viral candidate clips across
        a 2-3 hour podcast or stream (far exceeding the standard 5-clip cap).
      - Complete Privacy: Video files, audio tracks, and facial data never leave your PC.

[5] NATIVE MCP SERVER FOR CHATGPT & CLAUDE AGENTIC WORKFLOWS
    * What We Go For Instead:
      LocalCut runs a built-in Model Context Protocol server (stdio & SSE) enabling
      ChatGPT and Claude to act as your autonomous executive editor—triggering projects,
      refining clips, adjusting hooks, and queuing renders via natural language.

--------------------------------------------------------------------------------
3. COMPREHENSIVE LIST OF OVERHAULS & FEATURES IMPLEMENTED
--------------------------------------------------------------------------------

[+] VIRAL "SUMMARIZE & COLD-OPEN HOOK" FORMAT (DROPOUTS & SIDEMEN 20V1 STYLE)
    - Automatically locates and splices an explosive 2.0s - 3.5s climax punchline /
      reaction to the very beginning of the Short as a curiosity hook.
    - Features a customizable teaser pill badge:
      * "⚡ WAIT FOR IT..."
      * "😱 BEST PART..."
      * "🔥 WATCH TILL END"
      * "⚠️ NO WAY..."
    - Dual-input FFmpeg fast-seek concat (`concat=n=2:v=1:a=0`) with face-tracking
      keyframe alignment and unified broadcast loudnorm audio filtergraph.
    - Word-level ASS subtitles automatically synchronised: teaser words mapped from
      0.0s to T_dur, and main clip dialogue time-shifted by +T_dur.
    - Dedicated interactive "Teaser Hook" tab in the Clip Editor with 1-click
      playhead setting, auto-detect button, hook preview, and visual timeline scrubber highlight.
    - Optional cliffhanger trim to maximize viewer retention, comment debates, and click-throughs.



[+] 1-CLICK AUTO-PILOT PIPELINE (PASTE LINK TO FINISHED SHORTS)
    - Automatically executes the entire post-production pipeline in the background:
      1. Downloads / validates video stream (or imports local MP4/MKV).
      2. Faster-Whisper local speech transcription with word-level timestamps.
      3. Lexical and acoustic viral moment ranking.
      4. YuNet deep-learning face tracking for 9:16 vertical framing.
      5. Generates dynamic ASS karaoke word-bounce subtitles.
      6. Renders top clips into high-bitrate MP4s with EBU R128 loudness mastering.
    - Zero manual clicks needed: from URL input directly to finished shorts.

[+] EXPANDED CLIP VOLUME: BEYOND TOP 5 (UP TO 50 CLIPS)
    - No artificial 5-clip paywall cap.
    - User-selectable volume presets: Top 5, Top 10, Top 15, Top 25, or Max 50 clips.
    - Upgraded candidate search engine (`backend/services/clip_analysis.py`) scales
      moment discovery density proportionally with candidate count, ensuring diverse,
      non-overlapping moments across the entire video.

[+] VIRAL SUBTITLE STUDIO & ACTIVE WORD BOUNCE ANIMATION
    - Subtitle engine (`backend/services/subtitles.py`) with 6 viral presets:
      * Alex Hormozi Pop: Uppercase Impact font, custom highlight with active word
        scale bounce (\fscx118\fscy118), high-contrast outline.
      * MrBeast Punch: Punchy 1-2 word rapid pacing, bold warning yellow/red text,
        maximum energy and retention.
      * Cyber Neon: Modern electric cyan glow effect with Montserrat bold styling.
      * Boxed Karaoke: Rounded background pill styling (ASS BorderStyle=3) inspired
        by Submagic / CapCut popular templates.
      * Minimalist: Clean, elegant Segoe UI font for podcasts and documentaries.
      * Classic: Standard centered white text with subtle black drop shadow.
    - Granular Subtitle Customization:
      * Active Word Bounce Pop: Smooth ASS scale transformation toggle.
      * Highlight Colors: Yellow, Mint, Green, Cyan, Gold, Red, Magenta, Orange, White.
      * Custom Font Selection: Impact, Arial Black, Montserrat, Segoe UI, JetBrains Mono, Rubik.
      * Chunk Modes: Punchy (1-2 words for rapid retention) vs Phrase (3-4 words).
      * Vertical Offset Slider: Precise positioning control from 5% (top) to 92% (bottom).

[+] NATIVE MODEL CONTEXT PROTOCOL (MCP) SERVER FOR CHATGPT & CLAUDE
    - Built-in MCP server (`backend/mcp_server.py`) and configuration (`mcp_config.json`).
    - Exposes complete LocalCut API as standard AI tools:
      * `list_projects`: Inspect existing clipping jobs and statuses.
      * `get_project_details`: View candidate clips, scores, transcript summaries, and exports.
      * `create_clipping_project`: Trigger automated clipping from URL or file.
      * `edit_clip`: Modify timestamps, caption styles, aspect ratios, and layouts.
      * `render_clips`: Render selected or all candidate clips into MP4s.
      * `generate_social_post_metadata`: Get platform-optimized viral hooks, titles, and hashtags.
      * `open_export_folder`: Launch Windows File Explorer directly to rendered files.
    - Dual transport support:
      * Standard I/O (stdio) for Claude Desktop and Antigravity.
      * Server-Sent Events (SSE) via `--transport sse --port 8001` for ChatGPT Custom GPTs.

[+] "READY TO POST" SOCIAL STUDIO & 1-CLICK METADATA EXPORT
    - 5th dedicated tab in the Clip Editor (`frontend/src/components/ClipEditor.jsx`).
    - Platform-specific copy generators for TikTok, YouTube Shorts, and Instagram Reels.
    - Generates high-CTR video titles, scroll-stopping first-frame hooks, engaging
      descriptions with clear CTAs, and curated viral hashtag stacks (#shorts, #fyp, #viral).
    - 1-Click Copy All Package button to paste directly into your publishing scheduler.
    - Direct "Download MP4" and "Reveal in Windows Explorer" actions.

[+] MULTI-DIMENSION EXPORT SELECTION (1080x1920 vs 1920x1080 vs 1:1)
    - Full control over orientation and resolution per-clip and in batch:
      * 1080 x 1920 (Vertical 9:16): Optimized for TikTok, YouTube Shorts, Reels.
      * 1920 x 1080 (Landscape 16:9): Standard widescreen for YouTube & desktop.
      * 1080 x 1080 (Square 1:1): Social feeds & Instagram.
    - Quality scaling options: 1080p Full HD (default), 720p HD, and 4K Ultra HD.
    - Dynamic monitor preview that automatically conforms to selected aspect ratio.

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

[+] BROADCAST AUDIO MASTERING (EBU R128 LOUDNORM)
    - Integrated broadcast loudness normalization (-af loudnorm=I=-14:TP=-1.5:LRA=11)
      into FFmpeg rendering for punchy, balanced audio optimized for mobile speakers.


--------------------------------------------------------------------------------
4. PROJECT ARCHITECTURE & FILE STRUCTURE
--------------------------------------------------------------------------------

ClippingSoftware/
├── backend/
│   ├── main.py                  FastAPI application routes and job dispatcher
│   ├── mcp_server.py            Model Context Protocol (MCP) server for ChatGPT & Claude
│   ├── storage.py               Thread-safe file persistence & project state
│   └── services/
│       ├── clip_analysis.py     Multi-signal lexical, acoustic & heuristic ranking (up to 50 clips)
│       ├── face_tracker.py      YuNet ONNX deep learning face tracking & FFmpeg lerp
│       ├── media.py             FFmpeg/FFprobe wrappers, audio extraction & RMS waveform
│       ├── pipeline.py          Analysis & Auto-Pilot end-to-end rendering orchestration
│       ├── reframing.py         Filtergraph generation for 9:16, 16:9, 1:1, blur & crop
│       ├── renderer.py          Export engine with loudnorm, ASS burn-in, SRT & copying
│       ├── social_generator.py  Platform-tailored hooks, descriptions & hashtag generator
│       ├── subtitles.py         ASS karaoke engine with bounce scale & 6 viral presets
│       └── transcription.py     Faster-Whisper local speech transcription
├── frontend/
│   ├── index.html               Vite HTML entry with JetBrains Mono font
│   ├── package.json             Node dependencies & build scripts
│   ├── vite.config.js           Vite bundler configuration
│   └── src/
│       ├── App.jsx              Main application shell, header, pipeline & tabs
│       ├── style.css            High-contrast obsidian/carbon palette & animations
│       ├── components/
│       │   ├── BatchRenderModal.jsx  Batch render queue & configuration modal
│       │   ├── Candidates.jsx        Shortlist clips table with instant filtering
│       │   ├── ClipEditor.jsx        Monitor, timeline scrubber, transport & Ready to Post Hub
│       │   ├── Icons.jsx             Crisp SVG studio icons
│       │   ├── NewProject.jsx        Auto-Pilot toggle, volume pills & subtitle presets
│       │   └── Progress.jsx          Live pipeline execution and step progress
│       └── lib/
│           ├── api.js           REST API client, waveform, social posts & presets
│           └── useWorkspace.js  React custom hook for project polling & mutation
├── tests/
│   ├── test_analysis.py         Heuristics, ranking & keyword extraction tests
│   ├── test_audience.py         Audience retention & demographic scoring tests
│   ├── test_benchmarks.py       Performance & throughput benchmark tests
│   ├── test_face_tracker.py     YuNet tracking, smoothing & filtergraph tests
│   ├── test_refinements.py      API endpoint, batch render & bundle tests
│   ├── test_streamer.py         Streamer jargon & reaction keyword tests
│   ├── test_subtitles.py        ASS timing, resolution scaling & SRT generation tests
│   └── test_trends.py           Trend score & viral velocity tests
├── models/
│   └── face_detection/          YuNet ONNX model cache
├── mcp_config.json              MCP configuration for Claude Desktop and Antigravity
├── pytest.ini                   Pytest configuration with local cache Isolation
├── requirements.txt             Python package requirements
├── .gitignore                   Git exclusions for temp, venv, and large files
└── read me.txt                  Comprehensive documentation and release notes


--------------------------------------------------------------------------------
5. API SPECIFICATION
--------------------------------------------------------------------------------

GET    /api/health                         System health, ffmpeg, models, disk space
GET    /api/subtitle-presets               Available viral subtitle presets, fonts, colors
GET    /api/projects                       List all projects
POST   /api/projects                       Create new project (with Auto-Pilot option)
GET    /api/projects/{pid}                 Get project state, settings, candidates
DELETE /api/projects/{pid}                 Delete project and remove project folder
POST   /api/projects/{pid}/rename          Rename project title
POST   /api/projects/{pid}/retry           Retry a failed processing job
POST   /api/projects/{pid}/analyze         Re-analyze with customized clip count (up to 50)
GET    /api/projects/{pid}/source          Stream original source video
POST   /api/projects/{pid}/clips           Add custom clip with manual In/Out timestamps
DELETE /api/projects/{pid}/clips/{cid}     Delete candidate clip
POST   /api/projects/{pid}/clips/{cid}     Edit clip title, In/Out, captions, ratio, layout
GET    /api/projects/{pid}/clips/{cid}/social Get social post title, hook, desc, hashtags
POST   /api/projects/{pid}/render          Render single or batch clips with options
GET    /api/projects/{pid}/clips/{cid}/srt Download synchronized .srt subtitle file
GET    /api/projects/{pid}/files/{name}    Stream or download exported MP4 file
GET    /api/projects/{pid}/bundle          Download ZIP bundle of all rendered clips
GET    /api/projects/{pid}/waveform        Get 0.5s RMS vocal energy series
GET    /api/system-directories             Get user Home, Videos, Desktop, Downloads paths
POST   /api/projects/{pid}/open-folder     Reveal exports folder in Windows File Explorer


--------------------------------------------------------------------------------
6. CONNECTING CHATGPT & CLAUDE VIA MCP
--------------------------------------------------------------------------------

To connect ChatGPT or Claude Desktop directly to your local Clipping Studio:

1. Claude Desktop:
   Add the following snippet to your `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "localcut": {
         "command": "h:\\Clipping\\.venv\\Scripts\\python.exe",
         "args": ["-m", "backend.mcp_server", "--transport", "stdio"],
         "cwd": "h:\\Clipping"
       }
     }
   }
   ```

2. ChatGPT (via SSE Bridge / Custom GPT Action):
   Run the MCP server in SSE mode:
   ```powershell
   .\.venv\Scripts\python.exe -m backend.mcp_server --transport sse --port 8001
   ```
   Point ChatGPT Custom Actions / SSE connector to `http://127.0.0.1:8001/sse`.


--------------------------------------------------------------------------------
7. QUICK START & INSTALLATION
--------------------------------------------------------------------------------

PREREQUISITES:
- Windows 10/11, macOS, or Linux
- Python 3.10+ (Python 3.12 recommended)
- Node.js 18+ and npm
- FFmpeg and FFprobe installed and available on system PATH

SETUP INSTRUCTIONS:

1. Clone Repository:
   git clone https://github.com/MKN-GlitchOp/ClippingSoftware.git
   cd ClippingSoftware

2. Setup Python Virtual Environment:
   python -m venv .venv
   .\.venv\Scripts\activate          # Windows PowerShell / CMD
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
8. RUNNING TESTS
--------------------------------------------------------------------------------
To run the automated test suite verifying all 40 tests:
   .\.venv\Scripts\python.exe -m pytest --basetemp=h:\Clipping\.tmp_test


================================================================================
Licensed under MIT. Built for creators who want premium clipping without fees.
================================================================================
