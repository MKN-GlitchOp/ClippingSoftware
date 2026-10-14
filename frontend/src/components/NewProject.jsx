import React, {useRef, useState} from 'react';
import AudienceProfile from './AudienceProfile';
import {
  YoutubeIcon, UploadIcon, PasteIcon, CloseIcon,
  CheckIcon, SlidersIcon, ChevronDownIcon
} from './Icons';

const defaults = {
  content_profile: 'auto',
  use_public_benchmarks: true,
  num_clips: 10,
  auto_pilot: true,
  caption_style: 'hormozi',
  caption_bounce: true,
  caption_chunk_size: 'phrase',
  min_length: 15,
  max_length: 60,
  ratio: '9:16',
  layout: 'crop',
  captions: true,
  model: 'base',
  ollama_model: '',
  summarize_mode: true
};

const PRESETS = [
  { id: 'shorts', label: 'Shorts / Reels', min: 15, max: 60 },
  { id: 'quick', label: 'Snappy', min: 12, max: 30 },
  { id: 'story', label: 'Extended', min: 35, max: 90 },
  { id: 'custom', label: 'Custom', min: null, max: null }
];

const CLIP_COUNT_PRESETS = [5, 10, 15, 25, 50];

const SUBTITLE_PRESETS = [
  { id: 'hormozi', name: 'Hormozi Pop', desc: 'Impact font, active word pop bounce, heavy outline', sample: 'VIRAL POP' },
  { id: 'beast', name: 'MrBeast Punch', desc: 'Arial Black, 1-2 words rapid punch, bold uppercase', sample: 'MR BEAST' },
  { id: 'neon', name: 'Cyber Neon', desc: 'Cyan glow, futuristic modern high-contrast aesthetic', sample: 'CYBER NEON' },
  { id: 'boxed', name: 'Boxed Karaoke', desc: 'Submagic translucent black rounded pill background', sample: 'BOXED PILL' },
  { id: 'minimal', name: 'Minimalist', desc: 'Clean mint dropped shadow, elegant and subtle', sample: 'MINIMAL' },
  { id: 'classic', name: 'Classic', desc: 'Clean Segoe UI with standard yellow highlight', sample: 'CLASSIC' }
];

export default function NewProject({health, busy, uploadProgress, onCreate}) {
  const [mode, setMode] = useState('url');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [settings, setSettings] = useState(defaults);
  const [activePreset, setActivePreset] = useState('shorts');
  const [error, setError] = useState('');
  const fileInput = useRef(null);

  const set = (key, value) => setSettings(prev => ({...prev, [key]: value}));

  const isYoutube = (str) => /(?:youtube\.com\/(?:watch\?|shorts\/|live\/)|youtu\.be\/)/i.test(str.trim());

  const handlePaste = async () => {
    try {
      if (navigator?.clipboard?.readText) {
        const text = await navigator.clipboard.readText();
        if (text) {
          setUrl(text.trim());
          setError('');
        }
      }
    } catch {}
  };

  const applyPreset = (preset) => {
    setActivePreset(preset.id);
    if (preset.min !== null) {
      setSettings(prev => ({...prev, min_length: preset.min, max_length: preset.max}));
    }
  };

  const submit = e => {
    e.preventDefault();
    const values = {
      ...settings,
      num_clips: Number(settings.num_clips),
      min_length: Number(settings.min_length),
      max_length: Number(settings.max_length)
    };
    if (values.min_length > values.max_length) {
      setError('Min length must be less than max length.');
      return;
    }
    if (mode === 'url' && !url.trim()) {
      setError('Enter a YouTube URL.');
      return;
    }
    if (mode === 'file' && !file) {
      setError('Select a video file.');
      return;
    }
    if (mode === 'file' && health && (file.size / 1024**3 + 0.5) > health.free_gb) {
      setError('Insufficient disk space.');
      return;
    }
    setError('');
    onCreate({
      url: mode === 'url' ? url.trim() : '',
      file: mode === 'file' ? file : null,
      settings: values
    });
  };

  return (
    <form onSubmit={submit} className="studio-deck">
      <fieldset disabled={busy} className="deck-fieldset">
        {/* Source Deck */}
        <section className="deck-card source-card">
          <div className="card-topline">
            <span className="section-index">01</span>
            <span className="section-title">VIDEO SOURCE</span>
          </div>

          <div className="segmented-switch">
            <button
              type="button"
              className={`segment-btn ${mode === 'url' ? 'selected' : ''}`}
              onClick={() => setMode('url')}
            >
              <YoutubeIcon size={16} />
              <span>YouTube URL</span>
            </button>
            <button
              type="button"
              className={`segment-btn ${mode === 'file' ? 'selected' : ''}`}
              onClick={() => setMode('file')}
            >
              <UploadIcon size={15} />
              <span>Local File</span>
            </button>
          </div>

          {mode === 'url' ? (
            <div className="source-input-group">
              <div className="url-bar">
                <input
                  type="url"
                  className="mono-input"
                  placeholder="Paste YouTube link (https://www.youtube.com/watch?v=...)"
                  required
                  value={url}
                  onChange={e => { setUrl(e.target.value); setError(''); }}
                  autoFocus
                />
                {url && (
                  <button
                    type="button"
                    className="clear-cross-btn"
                    onClick={() => setUrl('')}
                    title="Clear"
                  >
                    <CloseIcon size={14} />
                  </button>
                )}
                <button
                  type="button"
                  className="deck-action-btn"
                  onClick={handlePaste}
                  title="Paste from clipboard"
                >
                  <PasteIcon size={13} />
                  <span>Paste</span>
                </button>
              </div>

              {url && isYoutube(url) && (
                <div className="inline-confirmation">
                  <CheckIcon size={13} />
                  <span>YouTube URL recognized</span>
                </div>
              )}
            </div>
          ) : (
            <div
              className={`file-drop-strip ${dragging ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={e => {
                e.preventDefault();
                setDragging(false);
                if (!busy && e.dataTransfer.files[0]) {
                  setFile(e.dataTransfer.files[0]);
                  setError('');
                }
              }}
            >
              <input
                ref={fileInput}
                type="file"
                accept="video/*,.mkv,.avi,.mov,.webm,.mp4"
                hidden
                onChange={e => {
                  if (e.target.files[0]) {
                    setFile(e.target.files[0]);
                    setError('');
                  }
                }}
              />
              {file ? (
                <div className="file-selected-row">
                  <span className="mono-file-name">{file.name}</span>
                  <span className="mono-file-size">{(file.size / 1024**2).toFixed(1)} MB</span>
                  <button
                    type="button"
                    className="deck-action-btn small"
                    onClick={() => fileInput.current.click()}
                  >
                    Change
                  </button>
                </div>
              ) : (
                <div className="drop-prompt" onClick={() => fileInput.current.click()}>
                  <UploadIcon size={20} />
                  <span>Drop video file here or click to browse</span>
                </div>
              )}
            </div>
          )}
        </section>

        {/* 1-Click Auto-Pilot Banner */}
        <section className={`deck-card autopilot-card ${settings.auto_pilot ? 'active' : ''}`}>
          <div className="autopilot-toggle-row">
            <div className="autopilot-info">
              <div className="autopilot-title-row">
                <span className="autopilot-badge">⚡ 1-CLICK AUTO-PILOT</span>
                <span className="autopilot-tag">PASTE TO POST</span>
              </div>
              <p className="autopilot-sub">
                Automatically downloads, transcribes, picks top clips with AI face tracking, formats viral captions, and renders finished MP4s ready to post instantly.
              </p>
            </div>
            <button
              type="button"
              className={`autopilot-switch-btn ${settings.auto_pilot ? 'on' : 'off'}`}
              onClick={() => set('auto_pilot', !settings.auto_pilot)}
            >
              <span className="switch-status">{settings.auto_pilot ? 'AUTO-PILOT ON' : 'MANUAL REVIEW'}</span>
              <span className="switch-knob" />
            </button>
          </div>
        </section>

        {/* Summarize / Cold-Open Teaser Hook Mode */}
        <section className={`deck-card summarize-card ${settings.summarize_mode ? 'active' : ''}`}>
          <div className="autopilot-toggle-row">
            <div className="autopilot-info">
              <div className="autopilot-title-row">
                <span className="summarize-badge">🎬 SUMMARIZE & COLD-OPEN HOOK</span>
                <span className="summarize-tag">DROPOUTS & 20v1 VIRAL FORMAT</span>
              </div>
              <p className="autopilot-sub">
                Hooks viewers in the first 3 seconds with a teaser punchline reaction from the climax, displaying a "WAIT FOR IT..." badge, then seamlessly cuts back to the buildup without spoiling the full scene.
              </p>
            </div>
            <button
              type="button"
              className={`autopilot-switch-btn ${settings.summarize_mode ? 'on' : 'off'}`}
              onClick={() => set('summarize_mode', !settings.summarize_mode)}
            >
              <span className="switch-status">{settings.summarize_mode ? 'TEASER HOOK ON' : 'STANDARD CUT'}</span>
              <span className="switch-knob" />
            </button>
          </div>
        </section>

        {/* Clip Configuration Deck */}
        <section className="deck-card config-card">
          <div className="card-topline">
            <span className="section-index">02</span>
            <span className="section-title">CLIP PARAMETERS</span>
          </div>

          {/* Aspect Ratio */}
          <div className="param-block">
            <span className="param-label">ASPECT RATIO</span>
            <div className="ratio-grid">
              {[
                { id: '9:16', name: '9:16', sub: 'Vertical (Shorts / TikTok)' },
                { id: '1:1', name: '1:1', sub: 'Square (Feed)' },
                { id: '16:9', name: '16:9', sub: 'Landscape (YouTube)' }
              ].map(r => (
                <button
                  key={r.id}
                  type="button"
                  className={`ratio-btn ${settings.ratio === r.id ? 'active' : ''}`}
                  onClick={() => set('ratio', r.id)}
                >
                  <span className="ratio-name">{r.name}</span>
                  <span className="ratio-sub">{r.sub}</span>
                </button>
              ))}
            </div>
          </div>

          <AudienceProfile
            value={settings.content_profile}
            onChange={value => set('content_profile', value)}
            disabled={busy}
            useBenchmarks={settings.use_public_benchmarks}
            onBenchmarksChange={value => set('use_public_benchmarks', value)}
          />

          {/* Clip Volume & Duration Target */}
          <div className="param-block">
            <div className="param-header-with-pills">
              <span className="param-label">CLIP VOLUME (EXPANDED UP TO 50 CLIPS)</span>
              <div className="quick-volume-pills">
                {CLIP_COUNT_PRESETS.map(cnt => (
                  <button
                    key={cnt}
                    type="button"
                    className={`volume-pill ${Number(settings.num_clips) === cnt ? 'active' : ''}`}
                    onClick={() => set('num_clips', cnt)}
                  >
                    Top {cnt}
                  </button>
                ))}
              </div>
            </div>

            <div className="trio-inputs">
              <label className="param-input-col">
                <span>Target Clips (1–50)</span>
                <input
                  type="number"
                  min="1"
                  max="50"
                  className="mono-input"
                  value={settings.num_clips}
                  onChange={e => set('num_clips', Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
                />
              </label>
              <label className="param-input-col">
                <span>Min Length (sec)</span>
                <input
                  type="number"
                  min="3"
                  max="180"
                  className="mono-input"
                  value={settings.min_length}
                  onChange={e => {
                    set('min_length', e.target.value);
                    setActivePreset('custom');
                  }}
                />
              </label>
              <label className="param-input-col">
                <span>Max Length (sec)</span>
                <input
                  type="number"
                  min="3"
                  max="180"
                  className="mono-input"
                  value={settings.max_length}
                  onChange={e => {
                    set('max_length', e.target.value);
                    setActivePreset('custom');
                  }}
                />
              </label>
            </div>

            <div className="preset-row" style={{ marginTop: '0.6rem' }}>
              {PRESETS.map(p => (
                <button
                  key={p.id}
                  type="button"
                  className={`preset-btn ${activePreset === p.id ? 'active' : ''}`}
                  onClick={() => applyPreset(p)}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Framing and Subtitles */}
          <div className="param-block">
            <span className="param-label">FRAMING & SUBTITLES</span>
            <div className="framing-toggle-row">
              <button
                type="button"
                className={`toggle-option ${settings.layout === 'crop' ? 'active' : ''}`}
                onClick={() => set('layout', 'crop')}
              >
                <span>Center Crop (Fill Frame)</span>
              </button>
              <button
                type="button"
                className={`toggle-option ${settings.layout === 'blur' ? 'active' : ''}`}
                onClick={() => set('layout', 'blur')}
              >
                <span>Full Frame + Blurred Background</span>
              </button>
            </div>

            <label className="checkbox-toggle-row">
              <input
                type="checkbox"
                className="deck-checkbox"
                checked={settings.captions}
                onChange={e => set('captions', e.target.checked)}
              />
              <span className="checkbox-text">
                <strong>Burn-in Viral Captions</strong>
                <small>High-converting word-by-word synchronized subtitles</small>
              </span>
            </label>

            {settings.captions && (
              <div className="subtitles-preset-box">
                <span className="sub-box-title">VIRAL SUBTITLE PRESETS</span>
                <div className="presets-cards-grid">
                  {SUBTITLE_PRESETS.map(sp => (
                    <button
                      key={sp.id}
                      type="button"
                      className={`sub-preset-card ${settings.caption_style === sp.id ? 'active' : ''}`}
                      onClick={() => set('caption_style', sp.id)}
                    >
                      <div className="sp-top">
                        <span className="sp-name">{sp.name}</span>
                        <span className="sp-sample">{sp.sample}</span>
                      </div>
                      <span className="sp-desc">{sp.desc}</span>
                    </button>
                  ))}
                </div>

                <div className="sub-fine-tuning-row">
                  <label className="sub-fine-toggle">
                    <input
                      type="checkbox"
                      checked={settings.caption_bounce}
                      onChange={e => set('caption_bounce', e.target.checked)}
                    />
                    <span>Word Bounce / Scale Pop Animation (118% pop)</span>
                  </label>

                  <div className="sub-chunk-toggle">
                    <button
                      type="button"
                      className={`chunk-pill ${settings.caption_chunk_size === 'phrase' ? 'active' : ''}`}
                      onClick={() => set('caption_chunk_size', 'phrase')}
                    >
                      Phrase (3–4 Words)
                    </button>
                    <button
                      type="button"
                      className={`chunk-pill ${settings.caption_chunk_size === 'single' ? 'active' : ''}`}
                      onClick={() => set('caption_chunk_size', 'single')}
                    >
                      Punchy (1–2 Words)
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Engine Settings */}
          <details className="engine-details">
            <summary className="engine-summary">
              <div className="engine-summary-label">
                <SlidersIcon size={14} />
                <span>Whisper & LLM Settings</span>
              </div>
              <ChevronDownIcon size={13} />
            </summary>
            <div className="engine-content">
              <label className="param-input-col">
                <span>Whisper Model</span>
                <select
                  value={settings.model}
                  onChange={e => set('model', e.target.value)}
                  className="mono-select"
                >
                  <option value="tiny">tiny (fastest, lightweight)</option>
                  <option value="base">base (recommended balance)</option>
                  <option value="small">small (higher precision)</option>
                </select>
              </label>

              <label className="param-input-col">
                <span>Optional Ollama Model</span>
                <input
                  type="text"
                  placeholder="e.g. llama3.2 (leave empty for local heuristics)"
                  value={settings.ollama_model}
                  onChange={e => set('ollama_model', e.target.value)}
                  className="mono-input"
                />
              </label>
            </div>
          </details>
        </section>
      </fieldset>

      {error && (
        <div className="deck-error-banner">
          <span>{error}</span>
          <button type="button" onClick={() => setError('')} title="Dismiss">
            <CloseIcon size={13} />
          </button>
        </div>
      )}

      {uploadProgress !== null && (
        <div className="upload-indicator">
          <span>Uploading local video: {uploadProgress}%</span>
          <div className="indicator-track">
            <div className="indicator-bar" style={{width: `${uploadProgress}%`}} />
          </div>
        </div>
      )}

      {/* Main Execution Bar */}
      <div className="execute-bar">
        <div className="execute-status">
          <span className="status-dot-neutral" />
          <span>
            {settings.auto_pilot ? '⚡ Auto-Pilot Ready' : 'Manual Ready'} • Top {settings.num_clips} clips ({settings.min_length}s–{settings.max_length}s) • {settings.ratio}{settings.summarize_mode ? ' • 🎬 Summarize Teasers' : ''}
          </span>
        </div>
        <button
          type="submit"
          className="btn-execute"
          disabled={busy || !health?.ffmpeg || !health?.ffprobe}
        >
          {busy
            ? (settings.auto_pilot ? 'Auto-Pilot Running...' : 'Starting...')
            : (settings.auto_pilot ? '🚀 Auto-Pilot: Extract & Render →' : 'Extract Moments →')}
        </button>
      </div>
    </form>
  );
}
