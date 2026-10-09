import React from 'react';

export default function AudienceProfile({value = 'auto', onChange, disabled = false, useBenchmarks = true, onBenchmarksChange}) {
  return <div className="audience-profile">
    <label className="param-input-col">
      <span>Content & audience</span>
      <select className="mono-select" value={value} disabled={disabled} onChange={e => onChange(e.target.value)}>
        <option value="auto">Auto · detect from the transcript</option>
        <option value="streamer">Funny streamer moments</option>
        <option value="gaming">Gaming & reactions</option>
        <option value="education">Education & how-to</option>
        <option value="podcast">Podcast & opinion</option>
        <option value="story">Stories & comedy</option>
      </select>
    </label>
    <p className="audience-help">{value==='streamer'?'Keep the setup, land the reaction, leave room for the laugh. Volume and slang alone do not make a good moment.':'Find the hook, keep the context, land the payoff. Ranking adapts to your content.'}</p>
    {onBenchmarksChange && <label className="benchmark-optin"><input type="checkbox" checked={useBenchmarks} disabled={disabled} onChange={e=>onBenchmarksChange(e.target.checked)} /><span>Use relevant examples from my public Shorts database</span></label>}
    <details className="audience-method"><summary>What informs the ranking?</summary>
      <p>Local analysis checks the opening, complete thoughts, useful takeaways, reactions and dead air. Public YouTube replay interest adds a small boost when available on new downloads.</p>
      <p>Editorial estimates, not predicted views or live trends. Replay data describes the original video’s audience.</p>
      <p>Open Public Shorts database in the sidebar to collect examples. Saved public counts can add a small, explainable topic-match bonus. Analysis never sends your transcript online.</p>
      <a href="https://support.google.com/youtube/answer/11914225" target="_blank" rel="noreferrer">YouTube discovery guidance ↗</a>
      <a href="https://support.tiktok.com/en/using-tiktok/exploring-videos/how-tiktok-recommends-content" target="_blank" rel="noreferrer">TikTok recommendation guidance ↗</a>
    </details>
  </div>;
}
