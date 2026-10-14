export async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map(item => item.msg.replace(/^Value error, /, '')).join(' ')
      : 'The request could not finish. Please try again.';
    throw new Error(message);
  }
  return data;
}

export function post(path, body) {
  return api(path, {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: body === undefined ? undefined : JSON.stringify(body)});
}

export function del(path) {
  return api(path, {method: 'DELETE'});
}

export function uploadVideo(file, settings, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append('file', file);
    form.append('settings', JSON.stringify(settings));
    xhr.open('POST', '/api/projects/upload');
    xhr.upload.onprogress = event => {
      if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100));
    };
    xhr.onload = () => {
      let result;
      try { result = JSON.parse(xhr.responseText); }
      catch { reject(new Error('The local server returned an unreadable response.')); return; }
      if (xhr.status >= 200 && xhr.status < 300) resolve(result);
      else reject(new Error(typeof result.detail === 'string' ? result.detail : 'Upload failed. Check the file and try again.'));
    };
    xhr.onerror = () => reject(new Error('The connection to the local server was lost. Reopen start.bat and retry.'));
    xhr.send(form);
  });
}

export const working = project => project && !['ready', 'error'].includes(project.status);
export function time(value, decimal = false) {
  const total = Math.max(0, Number(value) || 0);
  const hours = Math.floor(total / 3600);
  const minutes = String(Math.floor(total / 60) % 60).padStart(hours ? 2 : 1, '0');
  const seconds = (decimal ? (total % 60).toFixed(1).padStart(4, '0') : String(Math.floor(total % 60)).padStart(2, '0'));
  return `${hours ? `${hours}:` : ''}${minutes}:${seconds}`;
}
export const clipUrl = (pid, name) => `/api/projects/${pid}/files/${encodeURIComponent(name)}`;
export const clipSrtUrl = (pid, cid) => `/api/projects/${pid}/clips/${cid}/srt`;
export const openFolder = (pid, path) => post(`/projects/${pid}/open-folder`, { path });
export const fetchSystemDirs = () => api('/system-directories');
export const fetchWaveform = pid => api(`/projects/${pid}/waveform`);
export const fetchSocialPost = (pid, cid) => api(`/projects/${pid}/clips/${cid}/social`);
export const fetchSubtitlePresets = () => api('/subtitle-presets');
