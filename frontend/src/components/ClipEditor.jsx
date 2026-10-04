import React, {useEffect, useRef, useState, useCallback} from 'react';
import {clipUrl, clipSrtUrl, time, openFolder, fetchSystemDirs, fetchWaveform} from '../lib/api';
import {
  PlayIcon, DownloadIcon, SlidersIcon,
  SubtitlesIcon, ClockIcon, CopyIcon, TrashIcon, FolderIcon
} from './Icons';

export function editorKey(clip) {
  return [
    clip.id, clip.start, clip.end, clip.title, clip.hook, clip.captions,
    clip.ratio || '9:16', clip.layout || 'crop', clip.crop_x ?? 50, clip.caption_position || 'lower',
    clip.caption_color || 'yellow', clip.caption_uppercase ?? false,
    clip.resolution || '1080p', clip.export_srt ?? true, clip.export_dir || '',
    clip.face_tracking ?? true
  ].join('|');
}

const SPEED_OPTIONS = [1, 1.25, 1.5, 2];
const DIMENSION_OPTIONS = [
  { id: '9:16', label: '1080 × 1920', badge: '📱 VERTICAL (9:16)', desc: 'TikTok, Shorts, Reels' },
  { id: '16:9', label: '1920 × 1080', badge: '🖥️ LANDSCAPE (16:9)', desc: 'YouTube, Standard Widescreen' },
  { id: '1:1', label: '1080 × 1080', badge: '⏹️ SQUARE (1:1)', desc: 'Instagram Feed' }
];

const RESOLUTION_OPTIONS = [
  { id: '1080p', label: '1080p Full HD', desc: 'Standard clarity & optimal balance' },
  { id: '720p', label: '720p HD', desc: 'Fast render & small file size' },
  { id: '4k', label: '4K Ultra HD', desc: 'Maximum crisp detail' }
];

const COLOR_PRESETS = [
  { id: 'yellow', label: 'Yellow', hex: '#ffe600' },
  { id: 'mint', label: 'Mint', hex: '#99ffbb' },
  { id: 'green', label: 'Green', hex: '#00ff66' },
  { id: 'cyan', label: 'Cyan', hex: '#00e5ff' },
  { id: 'gold', label: 'Gold', hex: '#ffd700' },
  { id: 'white', label: 'White', hex: '#ffffff' }
];

export default function ClipEditor({project, clip, busy, onSave, onRender, onDelete, onDirtyChange}) {
  const original = {
    start: clip.start,
    end: clip.end,
    title: clip.title,
    hook: clip.hook,
    ratio: clip.ratio || project.settings.ratio || '9:16',
    captions: clip.captions ?? true,
    export_srt: clip.export_srt ?? true,
    resolution: clip.resolution || project.settings.resolution || '1080p',
    export_dir: clip.export_dir || project.export_dir || '',
    layout: clip.layout || 'crop',
    crop_x: clip.crop_x ?? 50,
    face_tracking: clip.face_tracking ?? true,
    caption_position: clip.caption_position || 'lower',
    caption_color: clip.caption_color || 'yellow',
    caption_uppercase: Boolean(clip.caption_uppercase)
  };

  const [draft, setDraft] = useState(original);
  const [tab, setTab] = useState('timing');
  const [preview, setPreview] = useState(clip.file ? 'export' : 'source');
  const [mediaError, setMediaError] = useState('');
  const [ready, setReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playhead, setPlayhead] = useState(clip.start);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [showSafeZone, setShowSafeZone] = useState(false);
  const [copiedTranscript, setCopiedTranscript] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [draggingHandle, setDraggingHandle] = useState(null); // 'in' | 'out'
  const [systemDirs, setSystemDirs] = useState(null);
  const [folderNotice, setFolderNotice] = useState('');
  const [waveform, setWaveform] = useState([]);

  const video = useRef(null);
  const timelineRef = useRef(null);

  const set = (key, value) => setDraft(prev => ({...prev, [key]: value}));
  const length = Number(draft.end) - Number(draft.start);
  const totalDuration = project.media?.duration || 100;

  const valid = draft.start !== '' && draft.end !== '' &&
    Number(draft.start) >= 0 &&
    Number(draft.end) <= totalDuration &&
    length >= 3 && length <= 180 &&
    draft.title.trim().length > 0;

  const dirty = Object.keys(original).some(key =>
    ['start', 'end', 'crop_x'].includes(key)
      ? Number(draft[key]) !== Number(original[key])
      : draft[key] !== original[key]
  );

  const sourceMode = preview === 'source' || !clip.file;
  const ratio = draft.ratio || clip.ratio || project.settings.ratio || '9:16';

  useEffect(() => {
    fetchSystemDirs().then(dirs => setSystemDirs(dirs)).catch(() => {});
    fetchWaveform(project.id)
      .then(data => {
        if (data && Array.isArray(data.energies) && data.energies.length > 0) {
          setWaveform(data.energies);
        }
      })
      .catch(() => {});
  }, [project.id]);

  useEffect(() => {
    onDirtyChange(dirty);
    return () => onDirtyChange(false);
  }, [dirty, onDirtyChange]);

  useEffect(() => {
    setPreview(clip.file ? 'export' : 'source');
  }, [clip.file]);

  useEffect(() => {
    setReady(false);
    setMediaError('');
  }, [preview, clip.file, clip.id]);

  const seek = useCallback((val) => {
    if (!video.current || !ready) return;
    const clamped = Math.max(0, Math.min(totalDuration, val));
    video.current.currentTime = sourceMode ? clamped : Math.max(0, clamped - clip.start);
    setPlayhead(clamped);
  }, [ready, sourceMode, totalDuration, clip.start]);

  const togglePlay = useCallback(() => {
    if (!video.current || !valid) return;
    if (video.current.paused) {
      if (sourceMode && (video.current.currentTime < Number(draft.start) || video.current.currentTime >= Number(draft.end))) {
        video.current.currentTime = Number(draft.start);
      }
      video.current.play().catch(() => {
        setMediaError('Browser unable to decode source format directly. Render clip to generate an H.264 preview.');
      });
    } else {
      video.current.pause();
    }
  }, [valid, sourceMode, draft.start, draft.end]);

  const changeSpeed = (speed) => {
    setPlaybackSpeed(speed);
    if (video.current) {
      video.current.playbackRate = speed;
    }
  };

  const nudge = useCallback((field, delta) => {
    const current = Number(draft[field]);
    const newVal = Math.max(0, Math.min(totalDuration, +(current + delta).toFixed(2)));
    set(field, newVal);
  }, [draft, totalDuration]);

  // Handle timeline dragging for In and Out points
  useEffect(() => {
    if (!draggingHandle) return;

    const handlePointerMove = (e) => {
      if (!timelineRef.current) return;
      const rect = timelineRef.current.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      const targetTime = +(pct * totalDuration).toFixed(2);

      if (draggingHandle === 'in') {
        const newStart = Math.min(Number(draft.end) - 3, Math.max(0, targetTime));
        set('start', newStart);
        seek(newStart);
      } else if (draggingHandle === 'out') {
        const newEnd = Math.max(Number(draft.start) + 3, Math.min(totalDuration, targetTime));
        set('end', newEnd);
        seek(newEnd);
      }
    };

    const handlePointerUp = () => {
      setDraggingHandle(null);
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [draggingHandle, totalDuration, draft.start, draft.end, seek]);

  // Keyboard navigation for precision trimming
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

      if (e.code === 'Space') {
        e.preventDefault();
        togglePlay();
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        const step = e.shiftKey ? 0.1 : 1.0;
        seek(playhead - step);
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        const step = e.shiftKey ? 0.1 : 1.0;
        seek(playhead + step);
      } else if (e.code === 'KeyI') {
        e.preventDefault();
        set('start', +playhead.toFixed(2));
      } else if (e.code === 'KeyO') {
        e.preventDefault();
        set('end', +playhead.toFixed(2));
      } else if (e.code === 'Home') {
        e.preventDefault();
        seek(Number(draft.start));
      } else if (e.code === 'End') {
        e.preventDefault();
        seek(Number(draft.end));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [togglePlay, seek, playhead, draft.start, draft.end]);

  const copyTranscript = () => {
    if (clip.transcript) {
      navigator.clipboard?.writeText(clip.transcript);
      setCopiedTranscript(true);
      setTimeout(() => setCopiedTranscript(false), 2000);
    }
  };

  const handleOpenFolder = async () => {
    try {
      setFolderNotice('Opening Windows Explorer...');
      await openFolder(project.id, draft.export_dir);
      setTimeout(() => setFolderNotice(''), 3000);
    } catch (err) {
      setFolderNotice(err.message);
      setTimeout(() => setFolderNotice(''), 4000);
    }
  };

  const save = () => {
    onSave({
      ...draft,
      start: Number(draft.start),
      end: Number(draft.end),
      crop_x: Number(draft.crop_x)
    });
  };

  const handleRenderClick = () => {
    if (dirty && valid) {
      save();
    }
    onRender({
      ids: [clip.id],
      ratio: draft.ratio,
      resolution: draft.resolution,
      captions: draft.captions,
      export_srt: draft.export_srt,
      export_dir: draft.export_dir,
      face_tracking: draft.face_tracking
    });
  };

  const clipIndex = project.candidates.indexOf(clip) + 1;

  // Timeline proportions
  const startPercent = Math.max(0, Math.min(100, (Number(draft.start) / totalDuration) * 100));
  const endPercent = Math.max(0, Math.min(100, (Number(draft.end) / totalDuration) * 100));
  const playheadPercent = Math.max(0, Math.min(100, (playhead / totalDuration) * 100));

  return (
    <section className="editor-console" aria-label="Clip Console">
      {/* Console Top Header */}
      <div className="console-header">
        <div className="console-title-wrap">
          <span className="console-index">CLIP #{String(clipIndex).padStart(2, '0')}</span>
          <h3 className="console-title">{draft.title || 'Untitled'}</h3>
        </div>
        <div className="console-meta-pills">
          <span className="mono-pill">{draft.resolution}</span>
          <span className="mono-pill">{draft.face_tracking ? 'FACE TRACKING' : 'FIXED CROP'}</span>
          <span className="mono-pill">{ratio}</span>
          <span className="mono-pill">{draft.layout.toUpperCase()}</span>
          <span className="mono-pill score">SCORE: {clip.score}</span>
          {onDelete && (
            <button
              type="button"
              className={`btn-delete-clip ${confirmDelete ? 'confirming' : ''}`}
              onClick={() => {
                if (confirmDelete) {
                  onDelete(clip.id);
                } else {
                  setConfirmDelete(true);
                  setTimeout(() => setConfirmDelete(false), 3000);
                }
              }}
              title="Remove this clip from project"
            >
              <TrashIcon size={12} />
              <span>{confirmDelete ? 'CONFIRM' : ''}</span>
            </button>
          )}
        </div>
      </div>

      {/* Mode Toggle: Source Framing vs Exported MP4 */}
      <div className="monitor-switch">
        <button
          type="button"
          className={`monitor-btn ${sourceMode ? 'active' : ''}`}
          onClick={() => setPreview('source')}
        >
          <span>Source & Crop Framing</span>
        </button>
        <button
          type="button"
          className={`monitor-btn ${!sourceMode ? 'active' : ''}`}
          disabled={!clip.file}
          onClick={() => setPreview('export')}
        >
          <span>Rendered Video ({clip.file ? `${draft.resolution} Ready` : 'Not Rendered'})</span>
        </button>
      </div>

      {/* Video Monitor Box */}
      <div className="monitor-viewport">
        <div
          className={`monitor-screen ${sourceMode && draft.layout === 'blur' ? 'blur-active' : ''}`}
          style={{
            aspectRatio: ratio.replace(':', ' / '),
            width: ratio === '9:16' ? 'min(100%, 250px)' : ratio === '1:1' ? 'min(100%, 360px)' : '100%',
            '--frame-image': `url("/api/projects/${project.id}/thumbnail/${clip.id}?at=${clip.start}")`
          }}
        >
          {showSafeZone && ratio === '9:16' && (
            <div className="safe-zone-overlay">
              <div className="safe-zone-top">TOP HEADER (PROFILES / TABS)</div>
              <div className="safe-zone-right">
                <span>ACTIONS</span>
                <span>(LIKE, SHARE)</span>
              </div>
              <div className="safe-zone-bottom">CAPTION & AUDIO TITLE MARGIN</div>
            </div>
          )}

          <video
            key={`${project.id}:${clip.id}:${sourceMode}:${clip.file || ''}`}
            ref={video}
            controls
            playsInline
            preload="metadata"
            aria-label="Clip video"
            style={{
              objectFit: sourceMode && draft.layout === 'crop' ? 'cover' : 'contain',
              objectPosition: `${draft.crop_x}% 50%`
            }}
            src={sourceMode ? `/api/projects/${project.id}/source` : clipUrl(project.id, clip.file)}
            onLoadedMetadata={() => {
              setReady(true);
              setMediaError('');
              if (video.current) {
                video.current.currentTime = sourceMode ? Number(draft.start) : 0;
                video.current.playbackRate = playbackSpeed;
              }
            }}
            onError={() => {
              setMediaError(
                sourceMode
                  ? 'Source format not natively playable in browser. Render this clip to generate a browser-compatible preview.'
                  : 'Exported file could not load.'
              );
            }}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onTimeUpdate={() => {
              const player = video.current;
              if (!player) return;
              const current = sourceMode ? player.currentTime : clip.start + player.currentTime;
              setPlayhead(current);
              if (sourceMode && !player.paused && player.currentTime >= Number(draft.end)) {
                player.pause();
              }
            }}
          />
        </div>
      </div>

      {/* Monitor Timecodes Bar & Speed Controls */}
      <div className="timecode-bar">
        <div className="timecode-left">
          <button
            type="button"
            className="btn-play-cue"
            onClick={togglePlay}
            disabled={!ready || !valid}
          >
            <PlayIcon size={12} />
            <span>{isPlaying ? 'PAUSE' : 'PLAY RANGE'}</span>
          </button>

          {ratio === '9:16' && (
            <button
              type="button"
              className={`btn-safe-zone ${showSafeZone ? 'active' : ''}`}
              onClick={() => setShowSafeZone(!showSafeZone)}
              title="Toggle TikTok / Shorts mobile safe area overlay"
            >
              SAFE ZONE
            </button>
          )}
        </div>

        <div className="timecode-right">
          <div className="speed-pills">
            {SPEED_OPTIONS.map(spd => (
              <button
                key={spd}
                type="button"
                className={`speed-btn ${playbackSpeed === spd ? 'active' : ''}`}
                onClick={() => changeSpeed(spd)}
              >
                {spd}x
              </button>
            ))}
          </div>

          <div className="timecode-readout mono-number">
            <span>{time(playhead, true)}</span>
            <span className="dimmed">/ {time(totalDuration)}</span>
          </div>
        </div>
      </div>

      {/* TACTILE IN / OUT TRANSPORT STRIP */}
      <div className="in-out-quick-strip">
        <div className="io-button-group in-side">
          <button
            type="button"
            className="btn-mark-io in-btn"
            onClick={() => set('start', +playhead.toFixed(2))}
            title="Set In point to current playhead (Key: I)"
          >
            <span className="io-bracket">[</span>
            <span>Mark IN (I)</span>
          </button>
          <button
            type="button"
            className="btn-jump-cue"
            onClick={() => seek(Number(draft.start))}
            title="Jump playhead to IN point"
          >
            ⇤ Jump
          </button>
        </div>

        <div className="io-duration-badge">
          <span className="io-duration-value">{length.toFixed(2)}s</span>
          <span className="io-duration-label">DURATION</span>
        </div>

        <div className="io-button-group out-side">
          <button
            type="button"
            className="btn-jump-cue"
            onClick={() => seek(Number(draft.end))}
            title="Jump playhead to OUT point"
          >
            Jump ⇥
          </button>
          <button
            type="button"
            className="btn-mark-io out-btn"
            onClick={() => set('end', +playhead.toFixed(2))}
            title="Set Out point to current playhead (Key: O)"
          >
            <span>Mark OUT (O)</span>
            <span className="io-bracket">]</span>
          </button>
        </div>
      </div>

      {mediaError && <div className="monitor-error-note">{mediaError}</div>}

      {/* Interactive Visual Timeline Scrubber with Draggable In & Out Handles */}
      <div className="studio-timeline-deck">
        <div
          ref={timelineRef}
          className="timeline-track"
          onClick={(e) => {
            if (draggingHandle) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const pct = Math.max(0, Math.min(1, clickX / rect.width));
            seek(pct * totalDuration);
          }}
        >
          {/* Audio Waveform visualization layer */}
          {waveform.length > 0 && (
            <div className="timeline-waveform-layer" aria-hidden="true">
              {(() => {
                const count = 120;
                const step = waveform.length / count;
                const bars = [];
                for (let i = 0; i < count; i++) {
                  const idx = Math.floor(i * step);
                  const val = waveform[idx] || 0.05;
                  const h = Math.max(12, Math.min(100, Math.round(val * 100)));
                  bars.push(
                    <span
                      key={i}
                      className="waveform-bar"
                      style={{ height: `${h}%` }}
                    />
                  );
                }
                return bars;
              })()}
            </div>
          )}

          {/* Active clip range block */}
          <div
            className="timeline-range-block"
            style={{
              left: `${startPercent}%`,
              width: `${Math.max(1, endPercent - startPercent)}%`
            }}
          />

          {/* Draggable IN Handle */}
          <div
            className={`timeline-handle in ${draggingHandle === 'in' ? 'active' : ''}`}
            style={{ left: `${startPercent}%` }}
            title="Drag to adjust IN point (Start)"
            onPointerDown={(e) => { e.stopPropagation(); setDraggingHandle('in'); }}
          >
            <span className="timeline-handle-tooltip">IN: {time(draft.start, true)}</span>
          </div>

          {/* Draggable OUT Handle */}
          <div
            className={`timeline-handle out ${draggingHandle === 'out' ? 'active' : ''}`}
            style={{ left: `${endPercent}%` }}
            title="Drag to adjust OUT point (End)"
            onPointerDown={(e) => { e.stopPropagation(); setDraggingHandle('out'); }}
          >
            <span className="timeline-handle-tooltip">OUT: {time(draft.end, true)}</span>
          </div>

          {/* Current playhead marker */}
          <div className="timeline-playhead-needle" style={{ left: `${playheadPercent}%` }} />
        </div>

        <div className="timeline-stats-line">
          <span className="mono-stat in-label">● IN: {time(draft.start, true)}</span>
          <span className="mono-stat center">RANGE: {valid ? `${length.toFixed(2)}s` : 'INVALID'}</span>
          <span className="mono-stat out-label">OUT: {time(draft.end, true)} ●</span>
        </div>
      </div>

      {/* Sub-console Navigation */}
      <div className="sub-console-tabs" role="tablist">
        <button
          type="button"
          className={`sub-tab ${tab === 'timing' ? 'active' : ''}`}
          onClick={() => setTab('timing')}
        >
          <ClockIcon size={13} />
          <span>IN/OUT TIMING</span>
        </button>
        <button
          type="button"
          className={`sub-tab ${tab === 'style' ? 'active' : ''}`}
          onClick={() => setTab('style')}
        >
          <SlidersIcon size={13} />
          <span>FRAMING & STYLE</span>
        </button>
        <button
          type="button"
          className={`sub-tab ${tab === 'export' ? 'active' : ''}`}
          onClick={() => setTab('export')}
        >
          <DownloadIcon size={13} />
          <span>RENDER & OUTPUT</span>
        </button>
        <button
          type="button"
          className={`sub-tab ${tab === 'text' ? 'active' : ''}`}
          onClick={() => setTab('text')}
        >
          <SubtitlesIcon size={13} />
          <span>HOOK & TEXT</span>
        </button>
      </div>

      {/* Tab Panels */}
      <div className="sub-tab-panel">
        {/* 1. TIMING */}
        {tab === 'timing' && (
          <div className="panel-timing">
            <div className="in-out-grid">
              <div className="time-block">
                <div className="block-label-row">
                  <span className="time-block-tag in">● IN POINT (START)</span>
                  <button
                    type="button"
                    className="link-cue"
                    disabled={!ready || busy}
                    onClick={() => set('start', +playhead.toFixed(2))}
                  >
                    Set @ Playhead
                  </button>
                </div>
                <div className="stepper-row">
                  <button type="button" onClick={() => nudge('start', -1)}>-1s</button>
                  <button type="button" onClick={() => nudge('start', -0.1)}>-0.1s</button>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max={totalDuration}
                    disabled={busy}
                    className="mono-input centered"
                    value={draft.start}
                    onChange={e => set('start', e.target.value)}
                  />
                  <button type="button" onClick={() => nudge('start', 0.1)}>+0.1s</button>
                  <button type="button" onClick={() => nudge('start', 1)}>+1s</button>
                </div>
                <span className="mono-time-sub">{time(draft.start, true)}</span>
              </div>

              <div className="time-block">
                <div className="block-label-row">
                  <span className="time-block-tag out">● OUT POINT (END)</span>
                  <button
                    type="button"
                    className="link-cue"
                    disabled={!ready || busy}
                    onClick={() => set('end', +playhead.toFixed(2))}
                  >
                    Set @ Playhead
                  </button>
                </div>
                <div className="stepper-row">
                  <button type="button" onClick={() => nudge('end', -1)}>-1s</button>
                  <button type="button" onClick={() => nudge('end', -0.1)}>-0.1s</button>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max={totalDuration}
                    disabled={busy}
                    className="mono-input centered"
                    value={draft.end}
                    onChange={e => set('end', e.target.value)}
                  />
                  <button type="button" onClick={() => nudge('end', 0.1)}>+0.1s</button>
                  <button type="button" onClick={() => nudge('end', 1)}>+1s</button>
                </div>
                <span className="mono-time-sub">{time(draft.end, true)}</span>
              </div>
            </div>

            <div className="keyboard-shortcuts-strip">
              <span>SHORTCUTS:</span>
              <code>Space</code> Play/Pause •
              <code>I</code> Set In •
              <code>O</code> Set Out •
              <code>←/→</code> 1s •
              <code>Shift+←/→</code> 0.1s •
              <code>Home/End</code> In/Out
            </div>
          </div>
        )}

        {/* 2. STYLE & FRAMING */}
        {tab === 'style' && (
          <div className="panel-style">
            {/* Export Dimensions / Orientation */}
            <div className="control-group">
              <span className="control-label">EXPORT DIMENSIONS & ORIENTATION</span>
              <div className="dimension-selector-grid">
                {DIMENSION_OPTIONS.map(d => (
                  <button
                    key={d.id}
                    type="button"
                    className={`dimension-btn ${draft.ratio === d.id ? 'active' : ''}`}
                    onClick={() => { set('ratio', d.id); setPreview('source'); }}
                  >
                    <span className="dim-badge">{d.badge}</span>
                    <span className="dim-res">{d.label}</span>
                    <span className="dim-sub">{d.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Subtitles & Captions Choice */}
            <div className="control-group">
              <span className="control-label">SUBTITLES & CAPTIONS</span>
              <div className="duo-toggle">
                <button
                  type="button"
                  className={`duo-btn ${draft.captions ? 'active' : ''}`}
                  onClick={() => set('captions', true)}
                >
                  <span>💬 WITH SUBTITLES (Burn-in)</span>
                </button>
                <button
                  type="button"
                  className={`duo-btn ${!draft.captions ? 'active' : ''}`}
                  onClick={() => {
                    set('captions', false);
                    set('export_srt', true);
                  }}
                >
                  <span>🚫 WITHOUT SUBTITLES (Clean)</span>
                </button>
              </div>
              <div className="subtitle-mode-subtext">
                {draft.captions ? (
                  <span>Subtitles will be burned into MP4 with active word highlights.</span>
                ) : (
                  <span>Clean video will be rendered without text overlays.</span>
                )}
              </div>
              <label className="checkbox-sub-label">
                <input
                  type="checkbox"
                  checked={draft.export_srt}
                  onChange={e => set('export_srt', e.target.checked)}
                />
                <span>Also export aligned .SRT subtitle file alongside MP4</span>
              </label>
            </div>

            <div className="control-group">
              <span className="control-label">LAYOUT MODE</span>
              <div className="duo-toggle">
                <button
                  type="button"
                  className={`duo-btn ${draft.layout === 'crop' ? 'active' : ''}`}
                  onClick={() => { set('layout', 'crop'); setPreview('source'); }}
                >
                  Center Crop (Fill Frame)
                </button>
                <button
                  type="button"
                  className={`duo-btn ${draft.layout === 'blur' ? 'active' : ''}`}
                  onClick={() => { set('layout', 'blur'); setPreview('source'); }}
                >
                  Letterbox + Blurred Background
                </button>
              </div>
            </div>

            {draft.layout === 'crop' && (
              <div className="control-group">
                <span className="control-label">SPEAKER TRACKING</span>
                <div className="duo-toggle">
                  <button
                    type="button"
                    className={`duo-btn ${draft.face_tracking ? 'active' : ''}`}
                    onClick={() => set('face_tracking', true)}
                  >
                    <span>⚡ AI Face Tracking (ON)</span>
                  </button>
                  <button
                    type="button"
                    className={`duo-btn ${!draft.face_tracking ? 'active' : ''}`}
                    onClick={() => set('face_tracking', false)}
                  >
                    <span>Fixed Crop (OFF)</span>
                  </button>
                </div>
                <span className="control-subtext">
                  {draft.face_tracking
                    ? 'AI automatically tracks speaker faces and smoothly pans camera to keep them centered.'
                    : 'Fixed crop locked at your chosen manual pan position below.'}
                </span>
              </div>
            )}

            {draft.layout === 'crop' && (
              <div className="control-group">
                <div className="control-label-row">
                  <span className="control-label">
                    HORIZONTAL PAN OFFSET ({draft.crop_x}%)
                    {draft.face_tracking && <span className="mono-sub-badge"> (Fallback Anchor)</span>}
                  </span>
                  <button
                    type="button"
                    className="link-cue"
                    disabled={busy}
                    onClick={() => { set('crop_x', 50); setPreview('source'); }}
                  >
                    Reset Center (50%)
                  </button>
                </div>
                <input
                  type="range"
                  className="deck-range"
                  min="0"
                  max="100"
                  value={draft.crop_x}
                  disabled={busy}
                  onChange={e => { set('crop_x', +e.target.value); setPreview('source'); }}
                />
                <div className="slider-stats-row">
                  <span>LEFT</span>
                  <span>CENTER (50%)</span>
                  <span>RIGHT</span>
                </div>
              </div>
            )}

            {/* Subtitle Appearance Settings */}
            {draft.captions && (
              <>
                <div className="control-group">
                  <span className="control-label">SUBTITLE HIGHLIGHT COLOR</span>
                  <div className="color-presets-row">
                    {COLOR_PRESETS.map(c => (
                      <button
                        key={c.id}
                        type="button"
                        className={`color-chip-btn ${draft.caption_color === c.id ? 'active' : ''}`}
                        onClick={() => set('caption_color', c.id)}
                      >
                        <span className="color-swatch" style={{ background: c.hex }} />
                        <span>{c.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="control-group duo-grid">
                  <div>
                    <span className="control-label">SUBTITLE POSITION</span>
                    <div className="duo-toggle">
                      <button
                        type="button"
                        className={`duo-btn ${draft.caption_position === 'lower' ? 'active' : ''}`}
                        onClick={() => set('caption_position', 'lower')}
                      >
                        Lower Third
                      </button>
                      <button
                        type="button"
                        className={`duo-btn ${draft.caption_position === 'upper' ? 'active' : ''}`}
                        onClick={() => set('caption_position', 'upper')}
                      >
                        Upper Area
                      </button>
                    </div>
                  </div>

                  <div>
                    <span className="control-label">CAPITALIZATION</span>
                    <button
                      type="button"
                      className={`duo-btn ${draft.caption_uppercase ? 'active' : ''}`}
                      onClick={() => set('caption_uppercase', !draft.caption_uppercase)}
                    >
                      {draft.caption_uppercase ? 'ALL CAPS' : 'Normal Case'}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* 3. RENDER & OUTPUT CONFIGURATION */}
        {tab === 'export' && (
          <div className="panel-export-config">
            {/* Dimensions & Orientation Selector */}
            <div className="control-group">
              <span className="control-label">EXPORT DIMENSIONS & ORIENTATION</span>
              <div className="dimension-selector-grid">
                {DIMENSION_OPTIONS.map(d => (
                  <button
                    key={d.id}
                    type="button"
                    className={`dimension-btn ${draft.ratio === d.id ? 'active' : ''}`}
                    onClick={() => { set('ratio', d.id); setPreview('source'); }}
                  >
                    <span className="dim-badge">{d.badge}</span>
                    <span className="dim-res">{d.label}</span>
                    <span className="dim-sub">{d.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Subtitles & Captions Mode */}
            <div className="control-group">
              <span className="control-label">SUBTITLES & CAPTIONS MODE</span>
              <div className="duo-toggle">
                <button
                  type="button"
                  className={`duo-btn ${draft.captions ? 'active' : ''}`}
                  onClick={() => set('captions', true)}
                >
                  <span>💬 WITH SUBTITLES (Burn-in)</span>
                </button>
                <button
                  type="button"
                  className={`duo-btn ${!draft.captions ? 'active' : ''}`}
                  onClick={() => {
                    set('captions', false);
                    set('export_srt', true);
                  }}
                >
                  <span>🚫 WITHOUT SUBTITLES (Clean)</span>
                </button>
              </div>
              <small className="control-hint">
                {draft.captions
                  ? 'Subtitles are burned permanently onto the video with animated word highlighting.'
                  : 'Video renders clean without text; a matching .srt subtitle file is created for Premiere / CapCut / YouTube.'}
              </small>
              <div className="checkbox-sub-row">
                <label className="checkbox-sub-label">
                  <input
                    type="checkbox"
                    checked={draft.export_srt}
                    onChange={e => set('export_srt', e.target.checked)}
                  />
                  <span>Generate matching .SRT subtitle file alongside MP4</span>
                </label>
              </div>
            </div>

            {/* Resolution Selector */}
            <div className="control-group">
              <span className="control-label">QUALITY SCALE</span>
              <div className="resolution-grid">
                {RESOLUTION_OPTIONS.map(r => (
                  <button
                    key={r.id}
                    type="button"
                    className={`resolution-btn ${draft.resolution === r.id ? 'active' : ''}`}
                    onClick={() => set('resolution', r.id)}
                  >
                    <span className="res-title">{r.label}</span>
                    <span className="res-desc">{r.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Output Destination Folder */}
            <div className="control-group">
              <div className="control-label-row">
                <span className="control-label">DESTINATION FOLDER (WHERE TO SAVE)</span>
                {clip.file && (
                  <button
                    type="button"
                    className="link-cue"
                    onClick={handleOpenFolder}
                  >
                    <FolderIcon size={12} />
                    <span>Open in Explorer</span>
                  </button>
                )}
              </div>
              <input
                type="text"
                className="mono-input destination-input"
                placeholder="Leave blank for project folder (or paste custom path e.g. C:\Users\...\Videos)"
                value={draft.export_dir}
                onChange={e => set('export_dir', e.target.value)}
              />

              {/* Quick Directory Presets */}
              <div className="path-presets-row">
                <span className="presets-label">QUICK PATHS:</span>
                {systemDirs?.videos && (
                  <button
                    type="button"
                    className="preset-path-btn"
                    onClick={() => set('export_dir', `${systemDirs.videos}\\Shorts`)}
                  >
                    Videos\Shorts
                  </button>
                )}
                {systemDirs?.desktop && (
                  <button
                    type="button"
                    className="preset-path-btn"
                    onClick={() => set('export_dir', `${systemDirs.desktop}\\Clips`)}
                  >
                    Desktop\Clips
                  </button>
                )}
                <button
                  type="button"
                  className="preset-path-btn"
                  onClick={() => set('export_dir', '')}
                >
                  Default (Project Folder)
                </button>
              </div>
            </div>

            {folderNotice && (
              <div className="folder-status-note">
                <span>{folderNotice}</span>
              </div>
            )}
          </div>
        )}

        {/* 4. HOOK & TEXT */}
        {tab === 'text' && (
          <div className="panel-text">
            <div className="control-group">
              <label className="control-label">CLIP TITLE</label>
              <input
                type="text"
                maxLength={160}
                disabled={busy}
                className="mono-input"
                value={draft.title}
                onChange={e => set('title', e.target.value)}
              />
            </div>

            <div className="control-group">
              <label className="control-label">OPENING HOOK</label>
              <textarea
                maxLength={500}
                rows={2}
                disabled={busy}
                className="mono-textarea"
                value={draft.hook || ''}
                onChange={e => set('hook', e.target.value)}
              />
            </div>

            <div className="transcript-deck-box">
              <div className="box-topbar">
                <span>TRANSCRIPT IN SELECTED RANGE</span>
                <button
                  type="button"
                  className="copy-mono-btn"
                  onClick={copyTranscript}
                >
                  <CopyIcon size={12} />
                  <span>{copiedTranscript ? 'COPIED' : 'COPY'}</span>
                </button>
              </div>
              <p className="transcript-content">{clip.transcript || 'No transcript text in chosen range.'}</p>
            </div>
          </div>
        )}
      </div>

      {/* Save Bar */}
      <div className="console-save-bar">
        <div className="save-status-text">
          {dirty ? (
            <span className="dirty-flag">● UNSAVED CHANGES</span>
          ) : (
            <span className="clean-flag">CONFIG SAVED</span>
          )}
        </div>
        <div className="save-btn-group">
          {dirty && (
            <button
              type="button"
              className="btn-neutral"
              disabled={busy}
              onClick={() => setDraft(original)}
            >
              Discard
            </button>
          )}
          <button
            type="button"
            className="btn-save-changes"
            disabled={busy || !dirty || !valid}
            onClick={save}
          >
            Save Adjustments
          </button>
        </div>
      </div>

      {/* Render / Download Action Bar */}
      <div className="console-render-bar">
        <button
          type="button"
          className="btn-render-action"
          disabled={busy || dirty || !valid}
          onClick={handleRenderClick}
        >
          {clip.file
            ? `Regenerate (${draft.ratio === '16:9' ? '1920×1080 Landscape' : '1080×1920 Vertical'} • ${draft.captions ? 'With Subs' : 'No Subs'})`
            : `Render (${draft.ratio === '16:9' ? '1920×1080 Landscape' : '1080×1920 Vertical'} • ${draft.captions ? 'With Subs' : 'No Subs'})`}
        </button>

        {clip.file && (
          <div className="render-downloads-group">
            <a
              className="btn-download-action"
              href={`${clipUrl(project.id, clip.file)}?download=true`}
              download
              title="Download MP4 video"
            >
              <DownloadIcon size={14} />
              <span>Download MP4</span>
            </a>

            {/* Individual SRT Subtitle Download */}
            <a
              className="btn-download-action srt-btn"
              href={clipSrtUrl(project.id, clip.id)}
              download
              title="Download standalone SRT subtitles"
            >
              <SubtitlesIcon size={14} />
              <span>Export SRT</span>
            </a>

            {/* Open Folder in Windows Explorer */}
            <button
              type="button"
              className="btn-open-folder"
              onClick={handleOpenFolder}
              title="Open folder in Windows File Explorer"
            >
              <FolderIcon size={14} />
              <span>Show in Folder</span>
            </button>
          </div>
        )}
      </div>

      {clip.exported_path && (
        <div className="exported-path-deck">
          <FolderIcon size={12} />
          <span className="exported-path-text" title={clip.exported_path}>
            Saved: {clip.exported_path}
          </span>
        </div>
      )}

      {clip.render_error && (
        <div className="deck-error-banner" role="alert">
          {clip.render_error}
        </div>
      )}
    </section>
  );
}
