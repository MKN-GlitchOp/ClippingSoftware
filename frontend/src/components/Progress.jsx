import React from 'react';
import {CheckIcon} from './Icons';

const STAGES = [
  { id: 'downloading', label: 'Download', matches: ['downloading'] },
  { id: 'audio', label: 'Transcribe', matches: ['extracting audio', 'loading speech model', 'transcribing'] },
  { id: 'scenes', label: 'Scene Cuts', matches: ['detecting scenes and silence'] },
  { id: 'scoring', label: 'Moment Scoring', matches: ['analyzing moments', 'local LLM review'] },
  { id: 'rendering', label: 'Render', matches: ['rendering'] }
];

export default function Progress({project}) {
  const currentStatus = project?.status?.toLowerCase() || '';
  const progressPercent = Math.min(100, Math.max(0, project?.progress || 0));

  let activeIndex = 0;
  if (currentStatus === 'downloading') activeIndex = 0;
  else if (['extracting audio', 'loading speech model', 'transcribing'].includes(currentStatus)) activeIndex = 1;
  else if (currentStatus === 'detecting scenes and silence') activeIndex = 2;
  else if (['analyzing moments', 'local LLM review'].includes(currentStatus)) activeIndex = 3;
  else if (currentStatus === 'rendering') activeIndex = 4;
  else if (progressPercent >= 100) activeIndex = 5;

  return (
    <div className="pipeline-monitor-panel" aria-live="polite">
      <div className="monitor-header">
        <div className="monitor-title-group">
          <span className="live-tally-dot" />
          <span className="monitor-label">PIPELINE RUNNING:</span>
          <span className="monitor-status-text">{project.status}</span>
        </div>
        <div className="monitor-percentage mono-number">
          {progressPercent}%
        </div>
      </div>

      <div className="monitor-meter">
        <div className="meter-fill" style={{ width: `${progressPercent}%` }} />
      </div>

      <div className="pipeline-stages-bar">
        {STAGES.map((s, idx) => {
          const isDone = idx < activeIndex || progressPercent >= 100;
          const isCurrent = idx === activeIndex && progressPercent < 100;
          return (
            <div
              key={s.id}
              className={`stage-node ${isDone ? 'done' : ''} ${isCurrent ? 'active' : ''}`}
            >
              <span className="stage-index">{isDone ? '✓' : `0${idx + 1}`}</span>
              <span className="stage-title">{s.label}</span>
            </div>
          );
        })}
      </div>

      <div className="monitor-footer">
        <span className="detail-mono">{project.detail || 'Processing video streams locally...'}</span>
        <span className="host-badge">127.0.0.1 • CPU INT8</span>
      </div>
    </div>
  );
}
