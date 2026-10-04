# Verification — 4 October 2026

Completed on this Windows PC using the local Python 3.12 environment, Node 24 and FFmpeg 7.0 essentials. All transcription and video encoding used CPU, without CUDA.

| Check | Result |
|---|---|
| Five focused tests: lengths, bounds, overlap, sponsor penalty, caption escaping and relative timing, sentence splitting and edited transcript | Passed |
| Public YouTube `Me at the zoo`: actual yt-dlp download, merge, audio extraction, full tiny-model transcription | Passed |
| Public YouTube `Why do we dream? - Amy Adkins`: full 337.481-second source at 1920×1080, full transcription, scene and silence analysis, three ranked candidates | Passed |
| Export all three long-source candidates | Passed: 44.294, 41.625 and 41.959 seconds; 1080×1920 H.264/AAC |
| Full FFmpeg decode of all three exports | Passed |
| Browser local file chooser → upload → analysis → candidate → manual timing save → captioned render | Passed |
| Browser playback of long-source captioned export | Passed: readyState 4, playhead advancing, no media error |
| Browser console error check | No errors observed |
| Captions-off export and metadata download through API | Passed |
| Invalid URL, invalid lengths, out-of-bounds clip, unreadable local file | Handled errors verified |
| Optional Ollama unavailable | Heuristic fallback exercised with a simulated connection failure |
| Regeneration writes a new version and retains prior export | Passed |
| Foreign-origin mutation rejection | Passed |
| React production build, Python compilation, installed dependency consistency | Passed |

Two failures found and fixed during development: PyAV 19 incompatibility with Faster-Whisper 1.2.1 (pinned PyAV 16.1.0), and Windows sharing violations during frequent project saves (throttled progress writes and retrying atomic replacements). Regeneration uses versioned filenames to avoid replacing an actively streamed MP4.

Live scripts are opt-in, rather than part of the routine unit-test suite. Sources are used only for local testing. The long-video test uses tiny to keep checks fast; base/small accuracy and performance have not been benchmarked here. Ollama's successful-model path and speaker/face tracking have not been tested; no Ollama installation was found and face tracking is deferred. CPU throughput on hour-long recordings has not been benchmarked.

The delivered MVP covers phases 1–5. Phase 6 can add optional speaker tracking; phase 7 can add editing presets and effects after quality review of real user footage.
