import React, {useEffect, useState} from 'react';
import {api, post} from '../lib/api';

const compact = value => value == null ? '—' : new Intl.NumberFormat(undefined,{notation:'compact',maximumFractionDigits:1}).format(value);
const currentMonth = () => {
  const parts=new Intl.DateTimeFormat('en',{timeZone:'Africa/Johannesburg',year:'numeric',month:'2-digit'}).formatToParts(new Date());
  return parts.find(p=>p.type==='year').value+'-'+parts.find(p=>p.type==='month').value;
};
const TOPICS = [['all','All funny moments'],['reactions','Unexpected reactions'],['banter','Roasts & banter'],['fails','Fails & rage'],['scares','Scares & screams'],['irl','IRL moments'],['funny','Other funny moments']];

export default function TrendsPage({onOpenLibrary}) {
  const [month,setMonth] = useState(currentMonth);
  const format = 'streamer';
  const [period,setPeriod] = useState('all');
  const [minViews,setMinViews] = useState(1000);
  const [topic,setTopic] = useState('all');
  const [sort,setSort] = useState('views');
  const [data,setData] = useState(null);
  const [loading,setLoading] = useState(true);
  const [pending,setPending] = useState(false);
  const [error,setError] = useState('');
  const [refresh,setRefresh] = useState(0);
  const [search,setSearch] = useState('');
  const running=data?.job.status==='running';
  const showJob=running || (data?.job.scope==='trends' && data?.job.month===month && data?.job.period===period);

  useEffect(()=>{
    const controller=new AbortController(); let timer;
    setLoading(true);
    const read=async()=>{
      try {
        const params=new URLSearchParams({month,format,topic,sort,period,min_views:minViews});
        const result=await api('/trends?'+params,{signal:controller.signal});
        if(controller.signal.aborted) return;
        setData(result);setLoading(false);setError('');
        if(result.job.status==='running') timer=setTimeout(read,2000);
      } catch(e) {if(!controller.signal.aborted){setError(e.message);setLoading(false);}}
    };
    read();
    return()=>{controller.abort();clearTimeout(timer);};
  },[month,format,topic,sort,period,minViews,refresh]);

  const scan=async()=>{
    setPending(true);setError('');
    try{await post('/trends/scan',{month,topic,format,period});setRefresh(value=>value+1);}
    catch(e){setError(e.message);}
    finally{setPending(false);}
  };
  const label=month && /^\d{4}-\d{2}$/.test(month) ? new Date(month+'-01T12:00:00').toLocaleDateString(undefined,{month:'long',year:'numeric'}) : 'Choose a month';
  const metricLabel=sort==='pace'?'median views/day':sort==='likes'?'median likes':'median views';
  const videos=(data?.videos||[]).filter(v=>(v.title+' '+v.channel).toLowerCase().includes(search.toLowerCase()));

  return <main className="studio-workspace trends-page">
    <header className="workspace-topbar"><span className="app-breadcrumb">DISCOVER / STREAMER MOMENTS</span><span className="trends-local">Public signals. Local library.</span></header>
    <div className="trends-content">
      <section className="trends-hero"><div><p className="trends-kicker">FIND THE MOMENT THAT LANDS</p><h1>Big reactions.<br/><em>Better clips.</em></h1><p>Find the best-performing funny streamer Shorts in your public sample. Explore the fails, banter and unexpected reactions people are watching.</p></div><div className="trends-month-card"><span>STREAMER SPOTLIGHT</span><strong>{period==='all'?'All upload dates':label}</strong><span>Latest public counts · {minViews?`${compact(minViews)}+ views`:'all view counts'}</span></div></section>
      <section className="trends-controls streamer-controls" aria-label="Trend filters">
        <label><span>Published</span><select aria-label="Published" value={period} onChange={e=>setPeriod(e.target.value)}><option value="all">All upload dates</option><option value="month">Choose a month</option></select></label>
        {period==='month'&&<label><span>Month published</span><input aria-label="Month published" type="month" value={month} min="2020-01" max={currentMonth()} onChange={e=>{if(e.target.value)setMonth(e.target.value);}} /></label>}
        <label><span>Moment type</span><select aria-label="Moment type" value={topic} onChange={e=>setTopic(e.target.value)}>{TOPICS.map(([value,text])=><option key={value} value={value}>{text}</option>)}</select></label>
        <label><span>Rank videos by</span><select value={sort} onChange={e=>setSort(e.target.value)}><option value="views">Most views</option><option value="pace">Average views / day</option><option value="likes">Most likes</option></select></label>
        <label><span>Minimum views</span><select aria-label="Minimum views" value={minViews} onChange={e=>setMinViews(Number(e.target.value))}><option value={0}>Show everything</option><option value={1000}>1,000+</option><option value={10000}>10,000+</option><option value={100000}>100,000+</option><option value={1000000}>1 million+</option></select></label>
        <button className="trends-scan" disabled={pending||running||loading||!month} onClick={scan}>{running?'Finding streamer clips…':'↻ Find funny moments'}</button>
      </section>
      <div className="trends-format"><span className="audience-help">Streamer identity + humor cues · verified short format</span><button className="trends-library-link" onClick={onOpenLibrary}>Add or refresh examples ↗</button></div>
      {error&&<div role="alert" className="deck-error-banner">{error}<button className="btn-neutral" onClick={()=>setRefresh(v=>v+1)}>Retry</button></div>}
      {showJob&&data?.job.message&&<div className={`trends-scan-status ${running?'running':''}`} role="status"><span>{running?'◌':data.job.status==='error'?'!':'✓'}</span>{data.job.message}{running&&<small>Metadata only · no videos downloaded · safe to leave this page</small>}</div>}
      {showJob&&data?.job.errors?.map((message,index)=><p className="audience-caution" key={index}>{message}</p>)}
      {loading?<div className="trends-empty" role="status">Reading your monthly sample…</div>:data&&<>
        <div className="trends-stats"><div><span>Funny streamer Shorts</span><strong>{data.total}</strong></div><div><span>Combined public views</span><strong>{compact(data.total_views)}</strong></div><div><span>Leading moment type</span><strong>{data.topics[0]&&!data.topics[0].low_reach?data.topics[0].label:'No strong signal yet'}</strong></div></div>
        {data.below_threshold>0&&<p className="audience-help">{data.below_threshold} matching examples are below your view threshold or have unavailable counts.</p>}
        <div className="trends-section-heading"><div><h2>What’s getting a reaction?</h2><p>Ordered by {metricLabel}. Open the examples to judge the setup and payoff.</p></div>{topic!=='all'&&<button className="btn-neutral" onClick={()=>setTopic('all')}>Show all moments</button>}</div>
        {data.topics.length>0?<div className="trend-topic-grid">{data.topics.slice(0,6).map((item,index)=><article className="trend-topic-card" key={item.id}>
          <div className="trend-topic-top"><span>0{index+1}</span><small>{item.low_reach?'Low reach so far':item.evidence}</small></div><h3>{item.label}</h3><strong>{compact(item.metric_median)} <small>{metricLabel}</small></strong><p>{item.count} Shorts · {item.channels} channels · {compact(item.total_views)} total views</p><div className="topic-evidence">{item.examples.slice(0,2).map(video=><a key={video.id} href={video.url} target="_blank" rel="noreferrer">{video.title} ↗</a>)}</div><button onClick={()=>setTopic(item.id)}>Explore moments →</button>
        </article>)}</div>:<div className="trends-empty"><span>◎</span><h3>Find your next funny moment.</h3><p>No verified streamer Shorts match these filters{period==='month'?` for ${label}`:''}. Run a scan, lower the minimum views, or explore all upload dates.</p><button className="btn-neutral" disabled={running||pending} onClick={scan}>Find public examples</button></div>}
        <div className="trends-section-heading"><div><h2>Funny streamer leaderboard</h2><p>Best performing in your collected sample. Open any title to watch on YouTube.</p></div><input className="trends-search" aria-label="Filter Shorts" placeholder="Search streamers, titles or channels…" value={search} onChange={e=>setSearch(e.target.value)} /></div>
        {videos.length>0?<div className="trends-leaderboard"><table><thead><tr><th scope="col">#</th><th scope="col">Short</th><th scope="col">Views</th><th scope="col">Likes</th><th scope="col">Avg views/day</th><th scope="col">Published</th></tr></thead><tbody>{videos.map(video=><tr key={video.id}><td className="trend-rank">{String(data.videos.indexOf(video)+1).padStart(2,'0')}</td><td><a href={video.url} target="_blank" rel="noreferrer">{video.title} ↗</a><p>{video.channel} <span>· {Math.round(video.duration)}s · {TOPICS.find(([id])=>id===video.topic)?.[1]}</span></p></td><td>{compact(video.views)}</td><td>{compact(video.likes)}</td><td>{compact(video.views_per_day)}</td><td>{video.upload_date?`${video.upload_date.slice(0,4)}-${video.upload_date.slice(4,6)}-${video.upload_date.slice(6)}`:'Unknown'}<small>{video.stale?'Stale snapshot':'Checked '+new Date(video.collected_at).toLocaleDateString()}</small></td></tr>)}</tbody></table></div>:data.total>0&&<p className="audience-help">No titles match your search.</p>}
        <footer className="trends-method"><strong>From discovery to a better clip</strong><p>In Clip studio, choose <b>Funny streamer moments</b> under Content & audience. The selector looks for setup → reaction → payoff, keeps short timing pauses, and penalizes isolated shouting and long gaps. Relevant saved examples can contribute a small topic-match bonus; your transcript stays local.</p><p>This is a collected sample, not a global chart. Views and likes are cumulative counts at collection; average views/day is lifetime views divided by age, not recent growth. The optional month filters upload dates. Streamer identity uses known creator names or streaming terms; humor and moment types are inferred from public titles and can miss clips or misclassify them.</p><p>Scans check up to eight examples per moment type across six types. A small sample or one creator can skew results. Missing counts appear as —. “Low reach” means no example has 1,000 views.{data.stale_count>0?` ${data.stale_count} snapshots are older than 30 days; refresh them in the library.`:''}</p></footer>
      </>}
    </div>
  </main>;
}
