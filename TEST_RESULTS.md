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

## Studio refinement verification

20 tests pass with the current studio code, including 4 new audience-scoring tests.
The real integration fixture was refreshed via a new public YouTube download of
Me at the zoo. yt-dlp returned an actual public replay heatmap; full CPU transcription
and ranked candidates completed. The integration test rendered and fully decoded
an upper-caption, blurred-background 1080x1920 H.264 clip, verified metadata edits,
ZIP download, transcript, thumbnail and restart recovery. Updated old assertions
for the studio's existing subtitle margin and optional SRT bundle behavior.

Content-specific ranking was also run read-only on the existing 14:59 gaming
transcript; no user clip edits or exports were replaced. This validates processing,
not real-world audience performance. No claim of improved view counts is made.

## Public database verification — 5 October 2026

- 25 tests passed; 3 prior render/retry fixture tests skipped because the earlier
  downloaded video fixture is no longer present. They were not counted as passes.
- Eight database tests cover format rejection, unknown counts, snapshots and
  elapsed growth, stale/category/unrelated match rejection, bounded bonuses,
  ranking opt-out, API validation/export, metadata-only partial success, title
  matching with long tag lists, and Shorts-filter discovery (some tests cover
  several behaviors).
- Real ordinary video search initially returned landscape clips. Corrected
  discovery to YouTube's actual Shorts filter using yt-dlp's search-URL support;
  two eligible vertical results were then collected successfully.
- Two additional public square Shorts collected from verified links; observed
  approximately 1.326 million and 225 thousand views with likes/comments. Four
  real records persisted locally; no source video downloads were used.
- Verified a real-library match returns source links and a bounded +4 bonus for
  a relevant sample passage. This is a functionality check, not a performance study.
- React production build passed. Database dialog and public counts were inspected
  in the browser; refresh was exercised through the UI.
- No private retention analytics, global coverage, or improved audience outcomes
  are claimed. No NVIDIA/CUDA or cloud-inference dependency was added.

## Monthly trends verification — 5 October 2026

- 30 tests passed, 3 prior missing-video fixture checks skipped. New tests cover
  upload-month boundaries, format/topic filtering, median ranking, unknown counts,
  validation, deduplication and actual-date postfiltering during collection.
- Production frontend build passed. Browser checked month/topic filters, empty
  states, scan progress/completion, low-reach labels and navigation to/from studio.
  No browser console errors were recorded.
- Real October discovery saved seven matching Shorts across two inferred topics,
  totaling 41 public views at collection. These are low-reach examples, not proof
  of winning topics. A September gaming scan through the UI completed with no
  results; the page correctly retained an empty month instead of mixing dates.
- Metadata only: no new downloads, dependencies, CUDA or paid services.
