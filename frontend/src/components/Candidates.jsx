import React, {useState} from 'react';
import {time, clipUrl, clipSrtUrl, openFolder} from '../lib/api';
import {PlayIcon, DownloadIcon, ChevronRightIcon, TrashIcon, CloseIcon, FolderIcon, SubtitlesIcon} from './Icons';

export default function Candidates({
  project,
  activeId,
  onChoose,
  onSelect,
  onAddClip,
  onDeleteClip,
  disabled
}) {
  const [sort, setSort] = useState('score');
  const [filterText, setFilterText] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newStart, setNewStart] = useState(0);
  const [newEnd, setNewEnd] = useState(30);
  const [newTitle, setNewTitle] = useState('');

  const totalDuration = project.media?.duration || 100;

  let clips = [...project.candidates];

  // Filter by text query
  if (filterText.trim()) {
    const q = filterText.toLowerCase();
    clips = clips.filter(c =>
      (c.title || '').toLowerCase().includes(q) ||
      (c.hook || '').toLowerCase().includes(q) ||
      (c.transcript || '').toLowerCase().includes(q)
    );
  }

  // Sort
  clips.sort((a, b) => {
    if (sort === 'time') return a.start - b.start;
    if (sort === 'duration') return b.duration - a.duration;
    return b.score - a.score;
  });

  const handleCreateClip = (e) => {
    e.preventDefault();
    const s = Number(newStart);
    const end = Number(newEnd);
    if (s >= end || end - s < 3 || end - s > 180) {
      alert('Range must be between 3 and 180 seconds.');
      return;
    }
    onAddClip(s, end, newTitle.trim() || `Clip at ${time(s)}`);
    setShowAddModal(false);
    setNewTitle('');
  };

  return (
    <section className="candidates-pane" aria-label="Candidate moments">
      {/* Shortlist Toolbar */}
      <div className="pane-header-strip">
        <div className="selection-count">
          <span>{project.candidates.filter(c => c.selected).length} OF {project.candidates.length} SELECTED</span>
        </div>
        <div className="pane-actions-row">
          <button
            type="button"
            className="btn-add-clip-manual"
            onClick={() => {
              setNewStart(0);
              setNewEnd(Math.min(30, Math.floor(totalDuration)));
              setShowAddModal(true);
            }}
            title="Create a custom clip range anywhere in the video"
          >
            + Add Range
          </button>
          <select
            value={sort}
            onChange={e => setSort(e.target.value)}
            className="mono-select-small"
          >
            <option value="score">Score</option>
            <option value="time">Timeline</option>
            <option value="duration">Length</option>
          </select>
        </div>
      </div>

      {/* Instant filter bar */}
      <div className="clip-filter-box">
        <input
          type="text"
          className="mono-input clip-filter-input"
          placeholder="Filter moments by keyword / transcript..."
          value={filterText}
          onChange={e => setFilterText(e.target.value)}
        />
        {filterText && (
          <button
            type="button"
            className="filter-clear-btn"
            onClick={() => setFilterText('')}
          >
            <CloseIcon size={12} />
          </button>
        )}
      </div>

      {/* Manual Clip Modal */}
      {showAddModal && (
        <form className="manual-add-card" onSubmit={handleCreateClip}>
          <div className="manual-add-header">
            <span>ADD CUSTOM CLIP RANGE</span>
            <button type="button" onClick={() => setShowAddModal(false)}>
              <CloseIcon size={13} />
            </button>
          </div>
          <div className="manual-add-inputs">
            <label className="param-input-col">
              <span>Title</span>
              <input
                type="text"
                placeholder="e.g. Best Joke or Intro"
                className="mono-input"
                value={newTitle}
                onChange={e => setNewTitle(e.target.value)}
              />
            </label>
            <div className="in-out-duo">
              <label className="param-input-col">
                <span>Start (s)</span>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max={totalDuration}
                  required
                  className="mono-input"
                  value={newStart}
                  onChange={e => setNewStart(e.target.value)}
                />
              </label>
              <label className="param-input-col">
                <span>End (s)</span>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max={totalDuration}
                  required
                  className="mono-input"
                  value={newEnd}
                  onChange={e => setNewEnd(e.target.value)}
                />
              </label>
            </div>
          </div>
          <div className="manual-add-actions">
            <span className="mono-stat">Length: {(Number(newEnd) - Number(newStart)).toFixed(1)}s</span>
            <div className="btn-duo">
              <button type="button" className="btn-neutral small" onClick={() => setShowAddModal(false)}>
                Cancel
              </button>
              <button type="submit" className="btn-execute small">
                Add to Shortlist
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Clips Stack */}
      <div className="clip-stack">
        {clips.map(clip => {
          const isActive = activeId === clip.id;
          const originalIndex = project.candidates.indexOf(clip) + 1;
          const isExportReady = clip.file && clip.render_status === 'ready';

          return (
            <article
              key={clip.id}
              className={`clip-row-card ${isActive ? 'is-active' : ''}`}
            >
              {/* Row Header */}
              <div className="clip-row-header">
                <label className="clip-check-label">
                  <input
                    type="checkbox"
                    className="deck-checkbox"
                    checked={!!clip.selected}
                    disabled={disabled}
                    onChange={e => onSelect(clip.id, e.target.checked)}
                  />
                  <span className="clip-index-mono">CLIP #{String(originalIndex).padStart(2, '0')}</span>
                </label>

                <div className="header-meta-group">
                  <div className="score-meter-tag">
                    <span className="score-val">{clip.score}</span>
                    <span className="score-max">/100</span>
                  </div>
                  {onDeleteClip && (
                    <button
                      type="button"
                      className="btn-trash-inline"
                      onClick={() => onDeleteClip(clip.id)}
                      title="Remove clip"
                    >
                      <TrashIcon size={12} />
                    </button>
                  )}
                </div>
              </div>

              {/* Clickable Card Body */}
              <button
                type="button"
                className="clip-interactive-body"
                onClick={() => onChoose(clip.id)}
              >
                <div className="clip-thumb-box">
                  <img
                    loading="lazy"
                    alt=""
                    src={`/api/projects/${project.id}/thumbnail/${clip.id}?at=${clip.start}`}
                    onError={e => { e.currentTarget.style.opacity = '0'; }}
                  />
                  <div className="thumb-hover-overlay">
                    <PlayIcon size={16} />
                  </div>
                  <span className="thumb-timecode">{time(clip.start)}</span>
                  <span className="thumb-dur">{clip.duration.toFixed(1)}s</span>
                </div>

                <div className="clip-info-col">
                  <h4 className="clip-title-line">{clip.title}</h4>
                  {clip.hook && (
                    <p className="hook-quote">"{clip.hook}"</p>
                  )}
                  {clip.reason && (
                    <span className="editorial-meta">{clip.reason}</span>
                  )}
                </div>
              </button>

              {clip.audience && <div className="audience-insights">
                <div className="audience-chips"><span>{clip.audience.label}</span><span>{clip.audience.opening}</span><span>{clip.audience.payoff}</span></div>
                <small>{clip.audience.evidence}</small>
                {clip.audience.moment?.anchor != null && <p className="audience-help">Reaction cue at {time(clip.audience.moment.anchor)} · {clip.audience.moment.setup?'spoken setup included':'check earlier context'} · visual humor still needs review</p>}
                {clip.audience.benchmarks?.examples?.length > 0 && <details className="benchmark-matches"><summary>Public examples behind this score · +{clip.audience.benchmarks.bonus}</summary>{clip.audience.benchmarks.examples.map(example=><p key={example.id}><a href={example.url} target="_blank" rel="noreferrer">{example.title} ↗</a><small>{example.views.toLocaleString()} views · Matched: {example.matched_terms.join(', ')} · Collected {new Date(example.collected_at).toLocaleDateString()}</small></p>)}<small>Topic similarity is supporting evidence, not a performance forecast.</small></details>}
                <details><summary>Why this score? <span>{clip.score}/100 · editorial estimate</span></summary>
                  <div className="score-breakdown-grid">{Object.entries(clip.score_breakdown || {}).filter(([,v]) => v !== 0).map(([name,value]) => <div key={name}><span>{name}</span><b className={value < 0 ? 'negative' : ''}>{value > 0 ? '+' : ''}{value}</b></div>)}</div>
                  {clip.cautions?.map(caution => <p className="audience-caution" key={caution}>{caution}</p>)}
                  {clip.edited && <p className="audience-help">Score reflects the original selection. Review your edited boundaries.</p>}
                </details>
              </div>}

              {clip.tags && clip.tags.length > 0 && (
                <div className="tag-row">
                  {clip.tags.slice(0, 5).map(tag => (
                    <span key={tag} className="mono-tag">#{tag}</span>
                  ))}
                </div>
              )}

              {/* Card Footer Bar */}
              <div className="clip-row-footer">
                <button
                  type="button"
                  className="btn-inspect"
                  onClick={() => onChoose(clip.id)}
                >
                  <span>{isActive ? 'Editing' : 'Inspect & Trim'}</span>
                  <ChevronRightIcon size={12} />
                </button>
                <button
                  type="button"
                  className="btn-quick-post-pill"
                  onClick={() => onChoose(clip.id, 'post')}
                  title="Open Ready-to-Post Hub for titles, captions & hashtags"
                >
                  <span>🚀 Post Copy</span>
                </button>

                <div className="row-render-tag">
                  {isExportReady ? (
                    <div className="ready-group">
                      <span className="render-status-pill done">{clip.resolution || 'READY'}</span>
                      <a
                        className="btn-table-download"
                        href={`${clipUrl(project.id, clip.file)}?download=true`}
                        download
                        title="Download MP4 video"
                      >
                        <DownloadIcon size={11} />
                        <span>MP4</span>
                      </a>
                      <a
                        className="btn-table-download srt-pill"
                        href={clipSrtUrl(project.id, clip.id)}
                        download
                        title="Download SRT subtitles"
                      >
                        <SubtitlesIcon size={11} />
                        <span>SRT</span>
                      </a>
                      <button
                        type="button"
                        className="btn-table-folder"
                        onClick={(e) => {
                          e.stopPropagation();
                          openFolder(project.id, clip.export_dir);
                        }}
                        title="Show in Windows Explorer"
                      >
                        <FolderIcon size={11} />
                      </button>
                    </div>
                  ) : clip.render_status === 'rendering' ? (
                    <span className="render-status-pill rendering">RENDERING...</span>
                  ) : clip.render_status === 'error' ? (
                    <span className="render-status-pill error">ERROR</span>
                  ) : (
                    <span className="render-status-pill pending">READY TO RENDER</span>
                  )}
                </div>
              </div>
            </article>
          );
        })}

        {!clips.length && (
          <div className="empty-clips-filter">
            <span>{filterText ? 'No moments match your search query.' : 'No clips in shortlist.'}</span>
          </div>
        )}
      </div>
    </section>
  );
}
