import React, {useState} from 'react';
import {CloseIcon, ScissorsIcon} from './Icons';

const DIMENSION_OPTIONS = [
  { id: '9:16', label: '1080 × 1920', badge: '📱 VERTICAL (9:16)', desc: 'TikTok, Shorts, Reels' },
  { id: '16:9', label: '1920 × 1080', badge: '🖥️ LANDSCAPE (16:9)', desc: 'YouTube, Standard Widescreen' },
  { id: '1:1', label: '1080 × 1080', badge: '⏹️ SQUARE (1:1)', desc: 'Instagram Feed' }
];

const RESOLUTION_OPTIONS = [
  { id: '1080p', label: '1080p Full HD', desc: 'Optimal clarity & recommended balance' },
  { id: '720p', label: '720p HD', desc: 'Fast export, lightweight' },
  { id: '4k', label: '4K Ultra HD', desc: 'Crisp premium detail' }
];

export default function BatchRenderModal({
  selectedCount,
  defaultRatio = '9:16',
  defaultResolution = '1080p',
  defaultDir = '',
  systemDirs,
  disabled,
  onClose,
  onConfirm
}) {
  const [ratio, setRatio] = useState(defaultRatio);
  const [resolution, setResolution] = useState(defaultResolution);
  const [captions, setCaptions] = useState(true);
  const [exportSrt, setExportSrt] = useState(true);
  const [faceTracking, setFaceTracking] = useState(true);
  const [exportDir, setExportDir] = useState(defaultDir);

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm({
      ratio,
      resolution,
      captions,
      export_srt: exportSrt,
      face_tracking: faceTracking,
      export_dir: exportDir.trim() || null
    });
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="render-modal-card" onClick={e => e.stopPropagation()}>
        <div className="render-modal-header">
          <div className="modal-header-left">
            <ScissorsIcon size={16} />
            <h3>BATCH RENDER QUEUE ({selectedCount} CLIPS)</h3>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            <CloseIcon size={14} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="render-modal-body">
          {/* DIMENSIONS & ORIENTATION */}
          <div className="render-modal-section">
            <label className="section-label">EXPORT DIMENSIONS & ORIENTATION</label>
            <div className="dimension-selector-grid modal-dim-grid">
              {DIMENSION_OPTIONS.map(opt => (
                <button
                  key={opt.id}
                  type="button"
                  className={`dimension-btn ${ratio === opt.id ? 'active' : ''}`}
                  onClick={() => setRatio(opt.id)}
                >
                  <span className="dim-badge">{opt.badge}</span>
                  <span className="dim-res">{opt.label}</span>
                  <span className="dim-sub">{opt.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* SUBTITLES */}
          <div className="render-modal-section">
            <label className="section-label">SUBTITLES & CAPTIONS</label>
            <div className="duo-toggle modal-duo-toggle">
              <button
                type="button"
                className={`duo-btn ${captions ? 'active' : ''}`}
                onClick={() => setCaptions(true)}
              >
                <span>💬 WITH SUBTITLES (Burn-in)</span>
              </button>
              <button
                type="button"
                className={`duo-btn ${!captions ? 'active' : ''}`}
                onClick={() => {
                  setCaptions(false);
                  setExportSrt(true);
                }}
              >
                <span>🚫 WITHOUT SUBTITLES (Clean)</span>
              </button>
            </div>

            <div className="modal-subtitles-options">
              <label className="modal-checkbox-row">
                <input
                  type="checkbox"
                  checked={exportSrt}
                  onChange={e => setExportSrt(e.target.checked)}
                />
                <div className="checkbox-text">
                  <strong>Export Aligned .SRT Subtitle File</strong>
                  <span>Save a clean, synchronized .srt subtitle file alongside each clip</span>
                </div>
              </label>
            </div>
          </div>

          {/* RESOLUTION */}
          <div className="render-modal-section">
            <label className="section-label">QUALITY SCALE</label>
            <div className="resolution-grid modal-res-grid">
              {RESOLUTION_OPTIONS.map(opt => (
                <button
                  key={opt.id}
                  type="button"
                  className={`resolution-btn ${resolution === opt.id ? 'active' : ''}`}
                  onClick={() => setResolution(opt.id)}
                >
                  <span className="res-title">{opt.label}</span>
                  <span className="res-desc">{opt.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* FACE TRACKING */}
          <div className="render-modal-section">
            <label className="section-label">ACTIVE SPEAKER FRAMING</label>
            <div className="modal-subtitles-options">
              <label className="modal-checkbox-row">
                <input
                  type="checkbox"
                  checked={faceTracking}
                  onChange={e => setFaceTracking(e.target.checked)}
                />
                <div className="checkbox-text">
                  <strong>⚡ AI Face Tracking (Active Speaker Auto-Reframe)</strong>
                  <span>Automatically track faces and smoothly pan camera to follow speakers. (Uncheck to use static center/manual crop)</span>
                </div>
              </label>
            </div>
          </div>

          {/* DESTINATION FOLDER */}
          <div className="render-modal-section">
            <div className="section-header-row">
              <label className="section-label">EXPORT DESTINATION FOLDER</label>
              <span className="section-hint">Where output files should be written</span>
            </div>

            <input
              type="text"
              className="mono-input folder-path-input"
              placeholder="Default: ./projects/{project_id}/exports/"
              value={exportDir}
              onChange={e => setExportDir(e.target.value)}
            />

            {systemDirs && (
              <div className="path-presets-row">
                <span className="preset-label">PRESETS:</span>
                <button
                  type="button"
                  className="path-preset-btn"
                  onClick={() => setExportDir(`${systemDirs.videos}\\Shorts`)}
                >
                  Videos\Shorts
                </button>
                <button
                  type="button"
                  className="path-preset-btn"
                  onClick={() => setExportDir(`${systemDirs.desktop}\\LocalCut_Exports`)}
                >
                  Desktop
                </button>
                <button
                  type="button"
                  className="path-preset-btn"
                  onClick={() => setExportDir('')}
                >
                  Default
                </button>
              </div>
            )}
          </div>

          <div className="render-modal-footer">
            <button
              type="button"
              className="btn-neutral"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-execute"
              disabled={disabled || !selectedCount}
            >
              <span>
                Render {selectedCount} Clips ({ratio === '16:9' ? '1920×1080 Landscape' : '1080×1920 Vertical'} • {captions ? 'With Subs' : 'No Subs'})
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
