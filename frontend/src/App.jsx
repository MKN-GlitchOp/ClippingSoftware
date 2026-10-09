import React, {useState, useEffect} from 'react';
import useWorkspace from './hooks/useWorkspace';
import NewProject from './components/NewProject';
import AudienceProfile from './components/AudienceProfile';
import BenchmarkLibrary from './components/BenchmarkLibrary';
import TrendsPage from './components/TrendsPage';
import Progress from './components/Progress';
import Candidates from './components/Candidates';
import ClipEditor, {editorKey} from './components/ClipEditor';
import BatchRenderModal from './components/BatchRenderModal';
import {time, working, fetchSystemDirs, openFolder} from './lib/api';
import {
  ScissorsIcon, TrashIcon, DownloadIcon,
  RefreshIcon, CheckIcon, CloseIcon, HardDriveIcon, CpuIcon,
  SlidersIcon, SubtitlesIcon, FolderIcon
} from './components/Icons';

function SelectionSettings({project, disabled, onApply}) {
  const [values, setValues] = useState(project.settings);
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="reanalyze-card">
      <button
        type="button"
        className="reanalyze-toggle-btn"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="reanalyze-title-group">
          <SlidersIcon size={14} />
          <span>Refine Content, Duration & Ranking</span>
        </div>
        <span className="reanalyze-arrow">{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <form
          className="reanalyze-form"
          onSubmit={e => {
            e.preventDefault();
            onApply({
              num_clips: +values.num_clips,
              min_length: +values.min_length,
              max_length: +values.max_length,
              content_profile: values.content_profile || 'auto',
              use_public_benchmarks: values.use_public_benchmarks ?? true
            });
          }}
        >
          <AudienceProfile value={values.content_profile} disabled={disabled} onChange={content_profile => setValues({...values, content_profile})} useBenchmarks={values.use_public_benchmarks ?? true} onBenchmarksChange={use_public_benchmarks => setValues({...values,use_public_benchmarks})} />
          <p className="audience-help">Reuses your transcript. Replaces the shortlist and clip edits; existing exported files stay on disk.</p>
          <div className="reanalyze-grid">
            <label className="param-input-col">
              <span>Target Clips</span>
              <input
                type="number"
                required
                min={1}
                max={20}
                className="mono-input"
                value={values.num_clips}
                disabled={disabled}
                onChange={e => setValues({...values, num_clips: e.target.value})}
              />
            </label>
            <label className="param-input-col">
              <span>Min Length (s)</span>
              <input
                type="number"
                required
                min={3}
                max={180}
                className="mono-input"
                value={values.min_length}
                disabled={disabled}
                onChange={e => setValues({...values, min_length: e.target.value})}
              />
            </label>
            <label className="param-input-col">
              <span>Max Length (s)</span>
              <input
                type="number"
                required
                min={3}
                max={180}
                className="mono-input"
                value={values.max_length}
                disabled={disabled}
                onChange={e => setValues({...values, max_length: e.target.value})}
              />
            </label>
          </div>
          <button
            type="submit"
            className="btn-neutral small"
            disabled={disabled || +values.min_length > +values.max_length}
          >
            <RefreshIcon size={13} />
            <span>Re-analyze Transcript</span>
          </button>
        </form>
      )}
    </div>
  );
}

export default function App() {
  const workspace = useWorkspace();
  const {
    project, projects, health, busy, loading, error, notice,
    uploadProgress, openProject, createProject, deleteProject,
    renameProject, addClip, deleteClip, mutate, setError
  } = workspace;

  const [activeId, setActiveId] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [search, setSearch] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const [renderModalOpen, setRenderModalOpen] = useState(false);
  const [systemDirs, setSystemDirs] = useState(null);
  const [benchmarksOpen, setBenchmarksOpen] = useState(false);
  const [page, setPage] = useState(()=>location.hash==='#trends'?'trends':'studio');
  useEffect(()=>{
    const change=()=>setPage(location.hash==='#trends'?'trends':'studio');
    window.addEventListener('hashchange',change);
    return()=>window.removeEventListener('hashchange',change);
  },[]);

  useEffect(() => {
    fetchSystemDirs().then(dirs => setSystemDirs(dirs)).catch(() => {});
  }, []);

  const running = working(project);
  const disabled = busy || running;
  const active = project?.candidates.find(clip => clip.id === activeId) || null;
  const selected = project?.candidates.filter(clip => clip.selected) || [];
  const exported = selected.filter(clip => clip.file && clip.render_status === 'ready');

  const navigate = id => {
    if (dirty) {
      setError('Save or discard changes before switching projects.');
      return;
    }
    setActiveId(null);
    location.hash='studio';
    setPage('studio');
    openProject(id);
  };

  const choose = id => {
    if (dirty && activeId !== id) {
      setError('Save or discard edits before selecting another clip.');
      return;
    }
    setError('');
    setActiveId(id);
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    e.preventDefault();
    if (confirmDeleteId === id) {
      await deleteProject(id);
      setConfirmDeleteId(null);
    } else {
      setConfirmDeleteId(id);
      setTimeout(() => setConfirmDeleteId(null), 4000);
    }
  };

  const handleTitleSubmit = async (e) => {
    e.preventDefault();
    if (titleDraft.trim() && titleDraft.trim() !== project.title) {
      await renameProject(titleDraft.trim());
    }
    setIsEditingTitle(false);
  };

  const handleAddCustomClip = async (start, end, title) => {
    const updated = await addClip(start, end, title);
    if (updated?.candidates?.length) {
      const newest = updated.candidates[updated.candidates.length - 1];
      setActiveId(newest.id);
    }
  };

  const handleDeleteClip = async (clipId) => {
    if (activeId === clipId) {
      setActiveId(null);
    }
    await deleteClip(clipId);
  };

  const filteredProjects = projects.filter(p =>
    (p.title || 'Untitled').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="studio-shell">
      {benchmarksOpen && <BenchmarkLibrary onClose={()=>setBenchmarksOpen(false)} />}
      {/* SIDEBAR */}
      <aside className="studio-sidebar">
        {/* Brand */}
        <div className="sidebar-brand-box">
          <button
            className="brand-link"
            onClick={() => navigate(null)}
          >
            <span className="brand-symbol">LOCALCUT</span>
            <span className="brand-dot">•</span>
            <span className="brand-tag">v0.2</span>
          </button>
        </div>

        {/* New Project CTA */}
        <nav className="studio-page-nav" aria-label="Workspace pages">
          <a href="#studio" aria-current={page==='studio'?'page':undefined}>◧ Clip studio</a>
          <a href="#trends" aria-current={page==='trends'?'page':undefined}>↗ Streamer moments</a>
        </nav>
        <button
          className="btn-new-cut"
          onClick={() => navigate(null)}
        >
          <span>+ New Project</span>
        </button>

        {/* Project Library */}
        <button className="btn-new-cut benchmark-open" onClick={()=>setBenchmarksOpen(true)}>Public Shorts database ↗</button>
        <div className="library-pane">
          <div className="library-bar">
            <span className="library-label">PROJECTS</span>
            <span className="library-badge">{projects.length}</span>
          </div>

          <div className="search-box">
            <input
              type="text"
              className="search-input mono-input"
              placeholder="Filter..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {search && (
              <button
                type="button"
                className="search-clear"
                onClick={() => setSearch('')}
              >
                <CloseIcon size={12} />
              </button>
            )}
          </div>

          <nav className="project-nav-scroll" aria-label="Projects">
            {filteredProjects.map(p => {
              const isSelected = project?.id === p.id;
              const isBusyProject = working(p);
              const isConfirming = confirmDeleteId === p.id;

              return (
                <div
                  key={p.id}
                  className={`nav-row ${isSelected ? 'active' : ''}`}
                  onClick={() => navigate(p.id)}
                >
                  <div className="nav-row-main">
                    <span className="nav-row-title" title={p.title}>
                      {p.title || 'Untitled Project'}
                    </span>
                    <span className="nav-row-meta">
                      {isBusyProject
                        ? 'PROCESSING...'
                        : p.status === 'ready'
                        ? `${p.clip_count || 0} CLIPS${p.duration ? ` • ${time(p.duration)}` : ''}`
                        : p.status.toUpperCase()}
                    </span>
                  </div>

                  <button
                    type="button"
                    className={`nav-row-trash ${isConfirming ? 'confirm-delete' : ''}`}
                    onClick={e => handleDelete(e, p.id)}
                    title={isConfirming ? 'Click again to confirm delete' : 'Delete project'}
                  >
                    {isConfirming ? (
                      <span className="confirm-label">CONFIRM?</span>
                    ) : (
                      <TrashIcon size={13} />
                    )}
                  </button>
                </div>
              );
            })}

            {!filteredProjects.length && (
              <div className="empty-library">
                <span>{search ? 'No matching projects.' : 'No projects yet.'}</span>
              </div>
            )}
          </nav>
        </div>

        {/* Hardware Status Footer */}
        <div className="sidebar-hardware-box">
          <div className="hardware-line">
            <HardDriveIcon size={12} />
            <span className="mono-text">{health ? `${health.free_gb} GB FREE` : 'DISK CHECK'}</span>
          </div>
          <div className="hardware-line">
            <CpuIcon size={12} />
            <span className="mono-text">INT8 CPU ENGINE</span>
          </div>
        </div>
      </aside>

      {/* WORKSPACE */}
      {page==='trends'&&<TrendsPage onOpenLibrary={()=>setBenchmarksOpen(true)} />}
      <main className="studio-workspace" style={{display:page==='trends'?'none':undefined}}>
        {/* Top Header */}
        <header className="workspace-topbar">
          <div className="topbar-left">
            <span className="app-breadcrumb">
              PROJECTS / {project ? (project.title || 'ACTIVE') : 'NEW PROJECT'}
            </span>
          </div>

          <div className="topbar-right">
            {project && (
              <button
                type="button"
                className={`topbar-delete-btn ${confirmDeleteId === project.id ? 'confirm' : ''}`}
                onClick={e => handleDelete(e, project.id)}
              >
                <TrashIcon size={13} />
                <span>{confirmDeleteId === project.id ? 'Click to Confirm Delete' : 'Delete Project'}</span>
              </button>
            )}
            <span className="engine-indicator">LOCAL HOST (127.0.0.1)</span>
          </div>
        </header>

        {/* Content Pane */}
        <div className="workspace-body">
          {/* Global Alert Notification */}
          {error && (
            <div role="alert" className="deck-error-banner dismissible">
              <span>{error}</span>
              <button
                type="button"
                className="dismiss-btn"
                onClick={() => setError('')}
              >
                <CloseIcon size={13} />
              </button>
            </div>
          )}

          {/* Toast Notification */}
          {notice && (
            <div className="studio-toast" role="status">
              <CheckIcon size={14} />
              <span>{notice}</span>
            </div>
          )}

          {health && (!health.ffmpeg || !health.ffprobe) && (
            <div className="deck-warning-banner">
              <span>FFmpeg or ffprobe missing from PATH. Check README.md for instructions.</span>
            </div>
          )}

          {loading ? (
            <div className="loading-deck">
              <span className="mono-spinner" />
              <p>LOADING PROJECT FROM DISK...</p>
            </div>
          ) : !project ? (
            <NewProject
              health={health}
              busy={busy}
              uploadProgress={uploadProgress}
              onCreate={createProject}
            />
          ) : (
            <div className="project-active-view">
              {/* Project Meta Bar with Inline Title Renaming */}
              {project.media && (
                <div className="project-stats-deck">
                  <div className="stats-deck-left">
                    {isEditingTitle ? (
                      <form className="rename-form" onSubmit={handleTitleSubmit}>
                        <input
                          type="text"
                          className="mono-input rename-input"
                          value={titleDraft}
                          onChange={e => setTitleDraft(e.target.value)}
                          autoFocus
                          onBlur={handleTitleSubmit}
                        />
                        <button type="submit" className="btn-execute small">Save</button>
                        <button type="button" className="btn-neutral small" onClick={() => setIsEditingTitle(false)}>Cancel</button>
                      </form>
                    ) : (
                      <h2
                        className="stats-deck-title editable"
                        onClick={() => {
                          setTitleDraft(project.title || '');
                          setIsEditingTitle(true);
                        }}
                        title="Click to rename project"
                      >
                        <span>{project.title}</span>
                        <span className="edit-pencil-icon">✎</span>
                      </h2>
                    )}
                    <div className="stats-row">
                      <span className="stat-pill">SOURCE: {time(project.media.duration)}</span>
                      <span className="stat-pill">FOUND: {project.candidates.length} CLIPS</span>
                      <span className="stat-pill">RENDERED: {project.candidates.filter(c => c.render_status === 'ready').length}</span>
                      <span className="stat-pill">{project.settings.ratio} • {project.media.width}x{project.media.height}</span>
                    </div>
                  </div>

                  <div className="stats-deck-right">
                    <a
                      className="btn-neutral small"
                      href={`/api/projects/${project.id}/transcript?format=srt`}
                      download
                    >
                      <SubtitlesIcon size={13} />
                      <span>Export SRT</span>
                    </a>
                  </div>
                </div>
              )}

              {/* Pipeline Progress */}
              {running && <Progress project={project} />}

              {/* Error Recovery */}
              {project.status === 'error' && (
                <div role="alert" className="deck-error-banner">
                  <div className="error-text">
                    <strong>PROCESSING STOPPED</strong>
                    <p>{project.error}</p>
                  </div>
                  <button
                    type="button"
                    className="btn-neutral small"
                    disabled={busy}
                    onClick={() => mutate('/retry')}
                  >
                    <RefreshIcon size={13} />
                    <span>Retry</span>
                  </button>
                </div>
              )}

              {project.warning && (
                <div className="deck-warning-banner">
                  <span>{project.warning}</span>
                </div>
              )}

              {/* Results & Editor Grid */}
              {!!project.candidates.length && (
                <div className="shortlist-section">
                  <div className="shortlist-actions-bar">
                    <div className="actions-bar-left">
                      <span className="table-caption">EXTRACTED MOMENTS ({project.candidates.length})</span>
                    </div>

                    <div className="actions-bar-right">
                      <button
                        type="button"
                        className="btn-neutral small"
                        disabled={disabled}
                        onClick={() =>
                          mutate('/selection', {
                            ids:
                              selected.length === project.candidates.length
                                ? []
                                : project.candidates.map(c => c.id)
                          })
                        }
                      >
                        {selected.length === project.candidates.length ? 'Deselect All' : 'Select All'}
                      </button>

                      <button
                        type="button"
                        className="btn-execute small"
                        disabled={disabled || dirty || !selected.length}
                        onClick={() => setRenderModalOpen(true)}
                      >
                        <span>Render Selected ({selected.length})</span>
                      </button>

                      {!!exported.length && (
                        <div className="zip-folder-group">
                          <button
                            type="button"
                            className="btn-neutral small"
                            onClick={() => openFolder(project.id, project.export_dir)}
                            title="Open exports folder in Windows File Explorer"
                          >
                            <FolderIcon size={13} />
                            <span>Show in Folder</span>
                          </button>
                          <a
                            className="btn-download-action small"
                            href={`/api/projects/${project.id}/bundle`}
                            download
                          >
                            <DownloadIcon size={13} />
                            <span>Download ZIP ({exported.length})</span>
                          </a>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="editor-two-col">
                    <Candidates
                      project={project}
                      activeId={activeId}
                      disabled={disabled}
                      onChoose={choose}
                      onSelect={(id, val) => mutate(`/clips/${id}`, {selected: val})}
                      onAddClip={handleAddCustomClip}
                      onDeleteClip={handleDeleteClip}
                    />

                    {active ? (
                      <ClipEditor
                        key={`${project.id}:${editorKey(active)}`}
                        project={project}
                        clip={active}
                        busy={disabled}
                        onDirtyChange={setDirty}
                        visible={page==='studio'}
                        onSave={values => mutate(`/clips/${active.id}`, values, 'Adjustments saved')}
                        onRender={options => mutate('/render', options || {ids: [active.id]})}
                        onDelete={handleDeleteClip}
                      />
                    ) : (
                      <div className="editor-empty-state">
                        <ScissorsIcon size={32} />
                        <h4>SELECT A MOMENT</h4>
                        <p>Click any clip on the left to inspect timestamps, framing, and render MP4.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Re-analyze settings */}
              {!running && (
                <SelectionSettings
                  key={project.id}
                  project={project}
                  disabled={busy || dirty}
                  onApply={async values => {
                    const res = await mutate('/analyze', values);
                    if (res) setActiveId(null);
                  }}
                />
              )}
            </div>
          )}

          {renderModalOpen && project && (
            <BatchRenderModal
              selectedCount={selected.length}
              defaultRatio={project?.settings?.ratio || '9:16'}
              defaultResolution={project?.settings?.resolution || '1080p'}
              defaultDir={project?.export_dir || ''}
              systemDirs={systemDirs}
              disabled={disabled}
              onClose={() => setRenderModalOpen(false)}
              onConfirm={async (options) => {
                setRenderModalOpen(false);
                await mutate('/render', {
                  ids: selected.map(c => c.id),
                  ...options
                });
              }}
            />
          )}
        </div>
      </main>
    </div>
  );
}
