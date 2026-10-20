import React, {useState, useEffect} from 'react';
import {displayDate, shortClub, signed, MODELS} from './analysis.mjs';

export function ClubRail({clubs, selected, onSelect}) {
  const [search,setSearch] = useState('');
  const filtered = clubs.filter(c=>c.toLowerCase().includes(search.toLowerCase()));
  const ordered = filtered.includes(selected) ? [selected,...filtered.filter(c=>c!==selected)] : filtered;
  return <aside className="club-rail" aria-label="Observed clubs"><h2>{clubs.length} observed clubs</h2>
    <label className="sr-only" htmlFor="club-search">Find a club</label><input id="club-search" placeholder="Find a club" value={search} onChange={e=>setSearch(e.target.value)}/>
    <div className="club-list" aria-label="Club choices">{ordered.map(c=><button key={c} className={c===selected?'selected':''} aria-pressed={c===selected} onClick={()=>onSelect(c)}>{c}</button>)}
    {!ordered.length&&<p role="status">No club matches this search.</p>}</div></aside>;
}

export function ResidualChart({games}) {
  const [narrow,setNarrow]=useState(()=>window.matchMedia('(max-width:700px)').matches);
  useEffect(()=>{const media=window.matchMedia('(max-width:700px)');const sync=()=>setNarrow(media.matches);
    media.addEventListener('change',sync);return()=>media.removeEventListener('change',sync);},[]);
  const extent=games.some(g=>Math.abs(g.residual)>2)?3:2;
  const width=narrow?360:920, height=narrow?180:extent===3?196:168, x0=narrow?28:36, right=12;
  const zero=narrow?80:extent===3?85:73, scale=narrow?(extent===3?20:26):extent===3?25:28;
  const step=(width-x0-right)/5;
  return <svg className={`residual-chart${narrow?' narrow-chart':''}`} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Actual points minus pre-match expected points for the last five matches">
    <title>Five-match residuals, points per match</title>
    {[-extent,0,extent].map(v=><g key={v}><text x={narrow?21:20} y={zero-v*scale+5} textAnchor="end">{v>0?`+${v}`:v}</text>{v===0&&<line x1={x0} x2={width-right} y1={zero} y2={zero}/>}</g>)}
    {games.map((g,i)=>{const x=x0+i*step+step*.21, bw=step*.58, y=g.residual>=0?zero-g.residual*scale:zero;
      return <g key={g.id.join('|')}><rect x={x} y={y} width={bw} height={Math.max(Math.abs(g.residual)*scale,0.5)} className={g.residual>=0?'positive':'negative'}/>
        <text className="bar-value" x={x+bw/2} y={g.residual>=0?y-9:y+Math.abs(g.residual)*scale+17} textAnchor="middle">{signed(g.residual)}</text>
        <text x={x+bw/2} y={height-10} textAnchor="middle">{displayDate(g.date)}</text></g>;})}
  </svg>;
}

export function EvidenceTable({games,archive}) {
  const [inspected,setInspected]=useState(null);
  const current=games.find(g=>g.id.join('|')===inspected);
  return <><div className="table-scroll"><table><caption className="sr-only">Last five matches and earlier training evidence</caption><thead><tr><th>Date</th><th>Opponent</th><th>Venue</th><th>Actual</th><th>Expected</th><th>Evidence</th></tr></thead>
    <tbody>{games.map(g=><tr key={g.id.join('|')}><td>{displayDate(g.date)}</td><td>{shortClub(g.opponent)}</td><td>{g.venue}</td><td>{g.actual}</td><td>{g.expected.toFixed(2)}</td><td><button className="text-button" aria-expanded={inspected===g.id.join('|')} onClick={()=>setInspected(inspected===g.id.join('|')?null:g.id.join('|'))}>{g.training_prefix_count} earlier matches</button></td></tr>)}</tbody></table></div>
    {current&&<section className="training-inspector" aria-label="Training evidence"><h4>Before {current.date}</h4><p>{current.training_prefix_count} matches. Latest training date: {current.latest_training_date??'None — prior only'}. No same-date results.</p>
      <ol>{archive.match_ids.slice(0,current.training_prefix_count).map(id=><li key={id.join('|')}>{id[1]} · {id[2]} / {id[3]}</li>)}</ol>{current.training_prefix_count===0&&<p>No earlier matches. Only the fixed prior is used.</p>}</section>}</>;
}

export function FormDetail({window,archive}) {
  const {games,available}=window;
  return <section className="form-detail" aria-labelledby="club-title"><h2 id="club-title">{window.club}</h2>
    {!available?<div className="empty-history" role="status"><h3>Five observations needed.</h3><p>{games.length} completed matches before {window.asOf}. No padding or future results are used.</p></div>:<>
      <dl className="metrics"><div><dt>Actual points</dt><dd>{window.actual}</dd></div><div><dt>Expected points</dt><dd>{window.expected.toFixed(2)}</dd></div><div><dt>Mean residual</dt><dd>{signed(window.mean)}</dd></div></dl>
      <h3>Last five matches</h3><ResidualChart games={games}/><p className="sensitivity">Leave-one-out mean range {signed(window.range[0])} to {signed(window.range[1])} · sensitivity, not a confidence interval</p>
      <EvidenceTable games={games} archive={archive}/></>}
    <p className="archive-age">{window.last?`Last observed match: ${window.last} · ${window.age} ${window.age===1?'day':'days'} before the selected date.`:'No earlier match for this club in the archive.'}</p>
    {window.age>60&&<p className="stale-notice" role="status">No recent observation in this archive. This does not establish current league membership or current form.</p>}
  </section>;
}

export function ModelAudit({summary}) {
  return <section className="model-audit" id="model-audit" aria-labelledby="audit-title"><div><h2 id="audit-title">Model audit</h2><p>2024–25 · 380 matches · Brier loss, lower is better</p><p className="audit-limit">Full archived season, independent of the date selector. No significance claim.</p></div>
    <div className="audit-bars">{['baseline','candidate'].map(k=><div className="audit-row" key={k}><span>{MODELS[k]}</span><strong>{summary.comparison[k].toFixed(5)}</strong><span className="bar-track"><span style={{width:`${summary.comparison[k]/2*100}%`}}/></span></div>)}</div></section>;
}

export function MethodAndData({summary}) {
  return <section id="method-data" className="methods"><details><summary>Method &amp; data</summary><div className="method-content"><h2>Traceable, limited, historical.</h2>
    <p>Each day is predicted as a batch before any result from that date updates the model. The archive contains 380 matches from 2023–24 followed by 380 from 2024–25. Times within a day are ignored. Scores are not independently reconciled with league records.</p>
    <p>The default league baseline uses earlier home/draw/away counts with a pseudocount of one each. It does not model opponent strength. The optional fixed Elo model starts at 1500, with home advantage 65, K 20 and scale 400. Draw rates use earlier rating-difference bins and fixed priors. No parameter was tuned to the evaluation season, and the better observed loss did not change the default.</p>
    <p>Residuals and leave-one-out ranges describe a five-match window. They do not establish causal skill, injury risk or future performance. All 23 observed clubs are retained, including clubs absent from the later league season. Last-match dates expose old observations.</p>
    <p>Data: <a href="https://github.com/openfootball/football.json/tree/e6744429ee395bc86f247348c6184bb08d4eb361" target="_blank" rel="noreferrer">openfootball/football.json, pinned source</a> · CC0 1.0 Universal. No player tracking, odds, xG, injuries or personal information are included.</p>
    <p className="hash-line">Preanalysis SHA-256: <code>{summary.preanalysis_sha256}</code></p><p>AI assisted the implementation and tests. No organizer approval or entry receipt is implied by this local prototype.</p>
  </div></details></section>;
}
