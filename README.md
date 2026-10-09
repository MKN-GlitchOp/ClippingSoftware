# LocalCut

A free local video-to-shorts workspace for Windows. React + FastAPI, FFmpeg, yt-dlp and Faster-Whisper. Speech inference is explicitly **CPU INT8**. No CUDA, paid APIs, accounts or cloud processing are used. Your RX 6600 XT does not need special drivers for this version.

## Install on Windows

1. Install **Python 3.12 (64-bit)** from [python.org](https://www.python.org/downloads/windows/). Select **Add python.exe to PATH** and the **Python launcher**. Alternatively, in PowerShell: `winget install -e --id Python.Python.3.12`.
2. Install **Node.js 24 LTS** from [nodejs.org](https://nodejs.org/en/download). Alternatively: `winget install -e --id OpenJS.NodeJS.LTS`.
3. Install FFmpeg: `winget install -e --id Gyan.FFmpeg`. Close and reopen PowerShell so PATH refreshes. Verify `ffmpeg -version` and `ffprobe -version`. The build must include `libx264` and `libass`; Gyan's essentials build does.
4. In this folder, double-click **setup.bat**. It creates `.venv`, installs Python dependencies (including yt-dlp), installs frontend dependencies from the lockfile and builds the interface. No global Python packages are modified.
5. Double-click **start.bat**. It opens [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser when the server is ready. Keep the launcher window open. Ctrl+C stops the server.

Equivalent manual setup from PowerShell in this directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

yt-dlp is installed through `yt-dlp[default]`, including the YouTube JavaScript challenge support package. Node is enabled as its JavaScript runtime. To update when YouTube changes:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade "yt-dlp[default]"
```

The first use of each speech model downloads free model weights from Hugging Face into `models/`. Internet is required for installation, this first download, and YouTube ingestion. After the model is cached, **local-file analysis and rendering run offline**. Tiny is fastest, base is balanced, small is more accurate. CPU speed varies with your processor and video duration.

### Optional Ollama

Install from [ollama.com](https://ollama.com/download/windows), or `winget install -e --id Ollama.Ollama`. Run `ollama pull qwen3:4b`. Ensure Ollama is running, then enter `qwen3:4b` under local analysis settings. Leave the field blank to skip it. The API is accessed only at `127.0.0.1:11434`. Failure falls back to heuristic results. Ollama currently reviews shortlisted passages; it does not find additional moments across the whole transcript. No particular GPU support is required by LocalCut.

## Workflow

Choose a public YouTube URL or upload a local video. Choose clip count, minimum/maximum duration, format and captions. Analyze, select ranked candidates, preview, edit start/end seconds, save and render. Export selected renders all checked candidates. Download each MP4 from its preview panel. Files are also directly available under `projects/<id>/exports/`.

The upload is streamed to disk, with one source copy in the project. Video is never loaded entirely into Python memory. YouTube streams are merged as necessary. Intermediate extracted audio is 16 kHz mono PCM. Full transcript JSON contains segment and word timestamps; an SRT is also saved. Analysis scans every segment, detects scene changes and pauses, and selects passages with limited overlap. Scene snapping moves outward by at most 0.35 seconds so spoken context is preserved.

Scores are transparent editorial heuristics (hooks, surprise, useful information, emotion, payoffs, complete endings, contextual dependence, sponsorship and silence), **not viral probability**. Strongest moments are subjective. Review clips before uploading. Long natural pauses are penalized but never automatically removed.

Regenerating writes a new version (for example `01_moment_v2.mp4`) so a playing preview never reads a file that is being overwritten. Earlier exports remain in the folder for comparison; the UI points to the newest version.

## Project layout

```text
backend/
  main.py                 Local API and background job queue
  services/
    downloader.py         YouTube validation and downloads
    media.py              FFmpeg probing, extraction, scenes and silence
    transcription.py      CPU Whisper, timestamped JSON and SRT
    clip_analysis.py      Scoring and optional Ollama review
    pipeline.py           Analysis orchestration
    storage.py            Atomic project JSON persistence
    renderer.py           H.264/AAC MP4 and metadata exports
    reframing.py          Modular center-crop strategy
    subtitles.py          ASS caption chunks and word highlighting
frontend/src/             React UI and styles
projects/<id>/
  source/ audio/ transcript/ analysis/ clips/ exports/
models/                   Shared local speech model cache
tests/                    Scoring and real pipeline checks
```

Jobs are serialized to avoid several CPU inference/rendering tasks competing. Projects survive restarts. Interrupted jobs can be retried; there is no automatic resume mid-transcription. Project JSON replaces SQLite for the MVP: it is easier to inspect and needs no database migration. Center crop is the reframing fallback; face tracking is an extension rather than a dependency.

## Development and verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m tests.phase1_live
.\.venv\Scripts\python.exe -m tests.phase1_live --url https://www.youtube.com/watch?v=2W85Dwxx218 --min 20 --max 45 --count 3
.\.venv\Scripts\python.exe -m tests.phase2_live
.\.venv\Scripts\python.exe -m tests.phase5_live
```

The live integration test downloads a public YouTube video and transcribes all its audio. It requires network access on the first run. Development frontend: `npm.cmd --prefix frontend run dev` with the backend running on port 8000. Vite proxies `/api` to the backend. For the single-server launcher, rebuild the frontend after editing it.

## Troubleshooting

- FFmpeg missing: install it, reopen the terminal, and verify both FFmpeg and ffprobe on PATH.
- YouTube unavailable/private or bot check: update yt-dlp, try a public video, or upload a file already on your disk. The app does not bypass sign-in restrictions.
- No candidates: lower the minimum length, or choose a video with clearer speech.
- Model download/transcription error: check internet for first model use and free RAM/disk space. Try tiny. Model files remain cached between runs.
- Not enough disk space: free space on the project's drive. Upload and analysis have safety checks; FFmpeg errors are caught, but the actual size of remote videos and exports varies.
- Slow renders: 1080×1920 H.264 is encoded on CPU using the veryfast preset, CRF 21 and AAC 160 kbps. No paid encoder or CUDA dependency.
- Keep the service bound to 127.0.0.1. This is a personal local app without authentication, intended for your own machine.

Verified API references: [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html), [Ollama generation API](https://docs.ollama.com/api/generate). PyAV is pinned to 16.1.0 because PyAV 19 removed an argument used by Faster-Whisper 1.2.1.

Future extensions: speaker/face tracking, punch-ins, jump cuts, caption templates, gameplay scoring, sound effects, split-screen, profiles, batch jobs and upload integrations. These are not part of the first MVP.

## MVP limitations

Heuristic scoring is tuned for English speech. Whisper can transcribe other languages, but the editorial score will be less informative. The center crop does not track speakers; captions use a lower safe-area position without face detection. Preview the output for each source. Timing edits update the exported transcript and invalidate old renders, but title/reason/score remain the original selection suggestions. Available clip count can be below your request when there are too few non-overlapping passages.

`requirements.lock.txt` and `frontend/package-lock.json` capture the dependency versions actually installed and tested. `requirements.txt` describes the main dependencies and compatible version ranges. The current virtual environment was created with Codex's bundled Python; fresh installations should use the standalone Python installation above for independence from the desktop app's runtime.

## Content-aware refinement (4 October 2026)

New projects and **Refine Content, Duration & Ranking** now offer Auto, Gaming,
Education, Podcast and Stories profiles. Clip cards show the chosen profile,
opening/payoff checks, evidence source, scoring breakdown and review cautions.

Fresh YouTube downloads retain public replay heatmaps when available. Above-average
replay interest contributes up to 8 points; missing heatmaps need no special setup.
Previously downloaded projects retain local-only analysis unless they already have
saved replay metadata. The app does not collect account analytics or live trends.

The weights are editorial heuristics informed by [YouTube's discovery guidance](https://support.google.com/youtube/answer/11914225)
and [TikTok's recommendation guidance](https://support.tiktok.com/en/using-tiktok/exploring-videos/how-tiktok-recommends-content).
They are not platform algorithms or predicted view counts. Public replay interest
reflects the original video's audience and does not prove that a short will perform.
Auto classification is keyword-based; choose a profile yourself when it guesses wrong.

The interface uses installed system fonts and makes no Google Fonts requests.
Existing face tracking, waveform, export resolutions and manual editing are retained.

## Public Shorts database (5 October 2026)

Open **Public Shorts database** in the sidebar. Search a topic or paste up to ten
public YouTube video links. Collection reads metadata only: title, tags, channel,
views, likes, comments, upload date, duration and dimensions. It downloads no videos
and requires no API key, paid service or account. Results persist in
`data/public_shorts.sqlite3` using Python's built-in SQLite; no dependency was added.

Discovery uses YouTube's Shorts search filter through yt-dlp's search-URL extractor,
checks up to 15 search results, and inspects up to 10 metadata records. Unknown,
landscape, live, and over-180-second videos are excluded. It is a growing sample of
public short-format videos, not a comprehensive/global list of the best Shorts.
Some public counts can be unavailable; the interface preserves them as unknown.

The library orders examples using log-scaled lifetime views per day plus capped
likes per view. These are design heuristics, not YouTube ranking weights. Refresh
oldest 20 records on demand. Daily snapshots permit observed view-growth estimates
once at least 24 hours separates samples. Same-day refreshes do not invent growth.
JSON export is available in the library; the SQLite file can also be backed up.

During analysis, a local inverted index compares candidate transcript topics with
public titles and tags. Matching requires at least two shared meaningful terms,
at least one title match, category compatibility, 1,000 public views, and data
collected within 30 days. Up to 6 points are added; multiple examples do not stack.
Clip cards display supporting links, matched terms, view counts and collection
dates. Disable **Use relevant examples from my public Shorts database** to ignore
this signal. New projects use it by default; re-analysis applies it to existing
projects only when requested, preserving already-exported files.

Your source transcript is never used as an online search query. Only the topic or
URLs you enter are sent to YouTube during collection. Cached ranking works offline.
The database contains no private retention, watch-time, swipe-away or revenue data.
Those require the channel owner's authorized analytics access: see
[YouTube Analytics](https://developers.google.com/youtube/analytics/channel_reports).
Public popularity and title similarity do not establish why a Short performed well.

Implementation: `backend/services/benchmarks.py`, `backend/api/benchmarks.py`, and
`frontend/src/components/BenchmarkLibrary.jsx`. Search/filter and format behavior
were checked against the installed yt-dlp extractor and real public metadata.


## Monthly trends page — 5 October 2026

Open **Monthly trends** in the sidebar (http://127.0.0.1:8000/#trends).
Choose an upload month, topic and format, then select **Scan this month**.
Top 5 & rankings is the default. Topic cards summarize the median performance,
number of examples and independent channels; the leaderboard can sort by public
views, likes or lifetime average views/day. Titles link to the original Shorts.

Discovery uses the existing yt-dlp installation and stores public metadata in
`data/public_shorts.sqlite3`. It checks at most six results per topic across seven
topics, validates real upload dates and vertical/square dimensions, and shares the
reference library used by clip scoring. No videos or private transcripts are uploaded.
Internet access is required for discovery; saved results remain local.

This is a collected sample, not a comprehensive global trend chart. Month refers
to upload date, not views earned in that month. Counts are cumulative at collection.
Topic/format labels come from titles. Topics without a 1,000-view example show
“Low reach so far”; this threshold is only a screening aid. The initial October
scan found seven matching records with low reach, so no strong trend is claimed.
Earlier months may have no matching results. Add known examples through the public
reference library to expand the sample. Scanning never re-renders existing projects.

Implementation: backend/services/trends.py, backend/api/trends.py,
frontend/src/components/TrendsPage.jsx, sidebar routing/style updates, and
hidden-editor keyboard/playback handling. No new dependencies.
