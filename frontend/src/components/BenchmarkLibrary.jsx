import React, {useEffect, useRef, useState} from 'react';
import {api, post} from '../lib/api';

const number = value => value == null ? 'Unavailable' : new Intl.NumberFormat(undefined, {notation:'compact', maximumFractionDigits:1}).format(value);
const date = value => value ? new Date(value).toLocaleDateString() : 'Unknown';

export default function BenchmarkLibrary({onClose}) {
  const dialog = useRef(null);
  const [data, setData] = useState({total:0, videos:[], job:{status:'idle'}});
  const [query, setQuery] = useState('');
  const [urls, setUrls] = useState('');
  const [profile, setProfile] = useState('auto');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const running = data.job.status === 'running';

  useEffect(() => {
    const element = dialog.current;
    element.showModal();
    return () => element.close();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let timer;
    const poll = async () => {
      try {
        const result = await api('/benchmarks', {signal:controller.signal});
        if (controller.signal.aborted) return;
        setData(result); setError(''); setLoading(false);
        if (result.job.status === 'running') timer = setTimeout(poll,1500);
      } catch (e) {
        if (!controller.signal.aborted) { setError(e.message); setLoading(false); timer = setTimeout(poll,5000); }
      }
    };
    poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [running]);

  const collect = async refresh => {
    setPending(true); setError('');
    try {
      const job = await post('/benchmarks/collect', {query, urls:urls.split(/\r?\n/).map(s=>s.trim()).filter(Boolean), profile, refresh});
      setData(prev=>({...prev,job}));
    } catch(e) { setError(e.message); }
    finally { setPending(false); }
  };
  const records = data.videos.filter(item=>(item.title+' '+item.channel+' '+item.query).toLowerCase().includes(filter.toLowerCase()));

  return <dialog ref={dialog} className="benchmark-dialog" onCancel={onClose} aria-labelledby="benchmark-title">
    <header className="benchmark-heading"><div><p className="benchmark-eyebrow">PUBLIC DATA · STORED ON YOUR PC</p><h2 id="benchmark-title">Shorts reference library</h2></div><button className="btn-neutral" onClick={onClose} aria-label="Close Shorts database">Close ×</button></header>
    <p className="audience-help">Collect examples in your niche. Relevant high-performing titles and topics can add up to 6 points to matching moments. Your footage and transcript stay local.</p>
    <form className="benchmark-form" onSubmit={e=>{e.preventDefault(); collect(false);}}>
      <label className="param-input-col"><span>Topic to research</span><input className="mono-input" value={query} maxLength={120} placeholder="e.g. Minecraft boat clutch" onChange={e=>setQuery(e.target.value)} /></label>
      <label className="param-input-col"><span>Content category</span><select className="mono-select" value={profile} onChange={e=>setProfile(e.target.value)}><option value="auto">Any category</option><option value="gaming">Gaming & reactions</option><option value="education">Education & how-to</option><option value="podcast">Podcast & opinion</option><option value="story">Stories & comedy</option></select></label>
      <button className="btn-execute" disabled={pending || running || (query.trim().length<3 && !urls.trim())}>{running ? 'Collecting…' : 'Collect public examples'}</button>
      <details className="benchmark-urls"><summary>Or add specific public Shorts links</summary><label className="param-input-col"><span>One YouTube video link per line · maximum 10</span><textarea className="mono-input" rows={3} value={urls} onChange={e=>setUrls(e.target.value)} placeholder="https://www.youtube.com/shorts/…" /></label><small>When links are provided, only those videos are collected.</small></details>
    </form>
    {error && <p role="alert" className="audience-caution">{error}</p>}
    <div className="benchmark-job" role="status"><span>{loading ? 'Loading local database…' : data.job.message || `${data.total} examples in your local database`}</span>{running && <progress max={Math.max(1,data.job.total)} value={data.job.processed} />}</div>
    {data.job.errors?.map((message,i)=><p key={i} className="audience-caution">{message}</p>)}
    <div className="benchmark-toolbar"><label className="param-input-col"><span>Filter collected examples</span><input className="mono-input" value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Title, channel or topic" /></label><button className="btn-neutral" disabled={loading || pending || running || !data.total} onClick={()=>collect(true)}>Refresh oldest 20</button><a className="btn-neutral" href="/api/benchmarks/export" download>Export database JSON</a></div>
    <div className="benchmark-table-wrap"><table className="benchmark-table"><caption>Best performing within your collected sample · up to 100 shown · not a global leaderboard</caption><thead><tr><th scope="col">Short-format video</th><th scope="col">Views</th><th scope="col">Likes</th><th scope="col">Comments</th><th scope="col">Avg views/day*</th><th scope="col">Observed growth/day</th><th scope="col">Collected</th></tr></thead><tbody>
      {records.map(item=><tr key={item.id}><td><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a><small>{item.channel} · {Math.round(item.duration)}s · {item.upload_date ? `Uploaded ${item.upload_date.slice(0,4)}-${item.upload_date.slice(4,6)}-${item.upload_date.slice(6)}` : 'Upload date unavailable'}</small></td><td>{number(item.views)}</td><td>{number(item.likes)}</td><td>{number(item.comments)}</td><td>{number(item.lifetime_views_per_day)}</td><td>{item.observed_views_per_day == null ? 'Needs later snapshot' : number(item.observed_views_per_day)}</td><td>{date(item.collected_at)}{item.stale && <small>Stale · excluded from ranking</small>}</td></tr>)}
    </tbody></table></div>
    {!loading && !records.length && <p className="benchmark-empty">No matching examples yet. Search for a specific subject or add Shorts you want to learn from.</p>}
    <footer className="benchmark-notes"><p>*Lifetime views divided by age, not recent momentum. Ranking uses this pace and a capped likes-per-view signal. Actual growth needs snapshots at least 24 hours apart. Missing counts remain unavailable.</p><p>Only verified vertical or square videos lasting 3–180 seconds are saved. Public counts do not reveal retention or which moment caused success. Examples older than 30 days are excluded until refreshed. Collection searches YouTube; analysis uses the saved database offline.</p><p>After collecting, use <strong>Refine Content, Duration & Ranking</strong> to apply examples to an existing project. Current edits are never replaced automatically.</p></footer>
  </dialog>;
}
