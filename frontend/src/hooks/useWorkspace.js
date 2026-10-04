import {useCallback, useEffect, useRef, useState} from 'react';
import {api, post, del, uploadVideo, working} from '../lib/api';

export default function useWorkspace() {
  const [project, setProject] = useState(null);
  const [projects, setProjects] = useState([]);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const selected = useRef(null);
  const revision = useRef(0);
  const pending = useRef(false);

  const refresh = useCallback(async () => {
    const list = await api('/projects');
    setProjects(list);
    return list;
  }, []);

  const openProject = useCallback(async id => {
    const token = ++revision.current;
    selected.current = id;
    setError(''); setNotice(''); setProject(null);
    try { id ? localStorage.setItem('localcut.project', id) : localStorage.removeItem('localcut.project'); } catch {}
    if (!id) { setLoading(false); return; }
    setLoading(true);
    try {
      const result = await api(`/projects/${id}`);
      if (token === revision.current) setProject(result);
    } catch (e) {
      if (token === revision.current) setError(e.message);
    } finally {
      if (token === revision.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api('/health'), refresh()]).then(([status, list]) => {
      if (cancelled) return;
      setHealth(status);
      let saved;
      try { saved = localStorage.getItem('localcut.project'); } catch {}
      if (saved && list.some(p => p.id === saved) && revision.current === 0) openProject(saved);
    }).catch(() => !cancelled && setError('The local server is unavailable. Open start.bat, then reload this page.'));
    return () => { cancelled = true; };
  }, [openProject, refresh]);

  useEffect(() => {
    if (!working(project)) return;
    const controller = new AbortController();
    let timer;
    const poll = async () => {
      const token = revision.current;
      try {
        if (!pending.current) {
          const updated = await api(`/projects/${project.id}`, {signal: controller.signal});
          if (!controller.signal.aborted && token === revision.current && selected.current === project.id) {
            setProject(updated);
            setError(previous => previous.startsWith('Connection interrupted.') ? '' : previous);
            if (!working(updated)) refresh().catch(() => {});
          }
        }
      } catch (e) {
        if (!controller.signal.aborted) setError('Connection interrupted. Progress will reconnect automatically while this page is open.');
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(poll, 1200);
      }
    };
    timer = setTimeout(poll, 600);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [project?.id, project?.status, refresh]);

  useEffect(() => {
    if (!projects.some(working)) return;
    const timer = setInterval(() => refresh().catch(() => {}), 5000);
    return () => clearInterval(timer);
  }, [projects, refresh]);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(''), 4000);
    return () => clearTimeout(timer);
  }, [notice]);

  const createProject = async ({url, file, settings}) => {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError('');
    const token = ++revision.current;
    try {
      const created = file ? await uploadVideo(file, settings, setUploadProgress)
        : await post('/projects/url', {url, settings});
      if (revision.current === token) {
        selected.current = created.id;
        setProject(created);
        try { localStorage.setItem('localcut.project', created.id); } catch {}
      }
      await refresh();
    } catch (e) { if (revision.current === token) setError(e.message); }
    finally { pending.current = false; setBusy(false); setUploadProgress(null); }
  };

  const mutate = async (path, body, message = '') => {
    if (!selected.current || pending.current) return null;
    const id = selected.current;
    const token = ++revision.current;
    pending.current = true; setBusy(true); setError('');
    try {
      const updated = await post(`/projects/${id}${path}`, body);
      if (revision.current === token && selected.current === id) {
        setProject(updated); setNotice(message);
      }
      refresh().catch(() => {});
      return updated;
    } catch (e) { if (revision.current === token) setError(e.message); return null; }
    finally { pending.current = false; setBusy(false); }
  };

  const deleteProject = async id => {
    if (pending.current) return;
    setError('');
    try {
      try {
        await del(`/projects/${id}`);
      } catch {
        await post(`/projects/${id}/delete`);
      }
      if (selected.current === id) {
        selected.current = null;
        setProject(null);
        try { localStorage.removeItem('localcut.project'); } catch {}
      }
      await refresh();
      setNotice('Project deleted');
    } catch (e) {
      setError(e.message);
    }
  };

  const renameProject = async (newTitle) => {
    if (!project?.id || !newTitle.trim()) return;
    return mutate('/rename', {title: newTitle.trim()}, 'Project renamed');
  };

  const addClip = async (start, end, title) => {
    if (!project?.id) return;
    return mutate('/clips', {start, end, title: title || 'Custom Clip'}, 'New clip added');
  };

  const deleteClip = async (clipId) => {
    if (!project?.id) return;
    return mutate(`/clips/${clipId}/delete`, {}, 'Clip removed');
  };

  return {project, projects, health, error, notice, busy, loading, uploadProgress,
    openProject, createProject, deleteProject, renameProject, addClip, deleteClip, mutate, setError};
}
