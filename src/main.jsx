import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {MODELS, MIN_DATE, MAX_DATE, clubsIn, windowFor, evidenceFor} from './analysis.mjs';
import {ClubRail, FormDetail, ModelAudit, MethodAndData} from './components.jsx';
import './style.css';

function App({archive}) {
  const [club,setClub]=useState('Arsenal FC'),[asOf,setAsOf]=useState(MAX_DATE),[model,setModel]=useState('baseline');
  const [status,setStatus]=useState('');
  const updateDate=e=>{setAsOf(e.currentTarget.value);setStatus('');};
  let window=null,error='';try{window=windowFor(archive,club,asOf,model);}catch(e){error=e.message;}
  const exportEvidence=()=>{if(!window)return;const payload=evidenceFor(archive,window);
    const blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'});const url=URL.createObjectURL(blob);
    const a=document.createElement('a');a.href=url;a.download=`fixturelens-${club.replaceAll(' ','-')}-${asOf}-${model}.json`;a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);setStatus('Evidence exported for the selected club, date and model.');};
  return <div className="app-shell"><header><a className="wordmark" href="#form-review">FixtureLens</a><nav aria-label="Sections"><a href="#form-review">Form review</a><a href="#model-audit">Model audit</a><a href="#method-data" onClick={()=>{document.querySelector('#method-data details').open=true;}}>Method &amp; data</a></nav><button className="export" onClick={exportEvidence} disabled={!window}>Export evidence</button></header>
    <main><section className="intro" id="form-review"><h1>Understand the last five.</h1><p>A historical form review with every assumption in view.</p>
      <div className="toolbar"><label htmlFor="as-of">As of</label><input id="as-of" type="date" value={asOf} min={MIN_DATE} max={MAX_DATE} onInput={updateDate} onChange={updateDate}/><label htmlFor="model">Model</label><select id="model" value={model} onChange={e=>{setModel(e.target.value);setStatus('');}}>{Object.entries(MODELS).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select><span>Only matches before this date</span></div></section>
      <div className="review-layout"><ClubRail clubs={clubsIn(archive)} selected={club} onSelect={setClub}/>{error?<section className="date-error" role="alert"><h2>Choose an archive date.</h2><p>{error}</p></section>:<FormDetail window={window} archive={archive}/>}</div>
      <ModelAudit summary={archive.summary}/><MethodAndData summary={archive.summary}/></main>
    <footer><span>Historical data: 2023–25. Not live forecasts.</span><span>Source: openfootball · CC0</span></footer><p className="sr-only" role="status">{status}</p></div>;
}
const root=createRoot(document.getElementById('root'));
root.render(<p role="status">Loading the historical archive…</p>);
import('./data/archive.json').then(({default:archive})=>root.render(<App archive={archive}/>))
  .catch(()=>root.render(<main className="app-shell"><h1>Archive unavailable.</h1><p role="alert">The local historical data could not be loaded. Reload the page from its HTTP server.</p></main>));
