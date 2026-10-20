import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {windowFor, clubsIn, validDate, evidenceFor} from './analysis.mjs';
const archive=JSON.parse(readFileSync(new URL('./data/archive.json',import.meta.url),'utf8'));
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-12,`${a} differs from ${b}`);

test('all 23 default windows agree with frozen Python output',()=>{
  assert.equal(clubsIn(archive).length,23);
  for(const expected of archive.baseline_windows){
    const w=windowFor(archive,expected.club,'2025-05-26');
    assert.equal(w.available,expected.available);close(w.mean,expected.mean_residual);
    w.range.forEach((v,i)=>close(v,expected.leave_one_out_range[i]));
    assert.equal(w.last,expected.last_match_date);assert.equal(w.age,expected.days_since_last_match);
    w.games.forEach((g,i)=>{assert.deepEqual(g.id,expected.matches[i].id);close(g.expected,expected.matches[i].expected);});
  }
});
test('same-day and future outcomes cannot enter selected window',()=>{
  for(const day of ['2023-08-11','2023-08-12','2024-08-16','2024-12-01','2025-05-25']){
    for(const club of clubsIn(archive))for(const model of ['baseline','candidate']){
      const w=windowFor(archive,club,day,model);assert.ok(w.games.length<=5);
      assert.ok(w.games.every(g=>g.date<day));
      for(const g of w.games)assert.ok(archive.match_ids.slice(0,g.training_prefix_count).every(id=>id[1]<g.date));
    }
  }
});
test('first archive date clears aggregate statistics instead of zero padding',()=>{
  const w=windowFor(archive,'Arsenal FC','2023-08-11');
  assert.equal(w.available,false);assert.equal(w.mean,null);assert.equal(w.range,null);assert.deepEqual(w.games,[]);
});
test('invalid calendar dates, out-of-range dates, clubs and models fail closed',()=>{
  for(const day of ['','2024-02-30','2023-8-11','2026-10-20','2023-08-10','2025-05-27']){
    assert.equal(validDate(day),false);assert.throws(()=>windowFor(archive,'Arsenal FC',day));
  }
  assert.throws(()=>windowFor(archive,'Invented FC','2025-05-26'));
  assert.throws(()=>windowFor(archive,'Arsenal FC','2025-05-26','winner'));
});
test('baseline stays the default even when Elo has lower evaluation loss',()=>{
  assert.ok(archive.summary.comparison.candidate<archive.summary.comparison.baseline);
  const w=windowFor(archive,'Arsenal FC','2025-05-26');assert.equal(w.model,'baseline');
  assert.notEqual(w.mean,windowFor(archive,'Arsenal FC','2025-05-26','candidate').mean);
});
test('old clubs retain last-observed date and conspicuous age evidence',()=>{
  const w=windowFor(archive,'Burnley FC','2025-05-26');
  assert.equal(w.last,'2024-05-19');assert.equal(w.age,372);assert.equal(w.games.length,5);
});
test('export binds exact model, date and all earlier contributing match IDs',()=>{
  for(const model of ['baseline','candidate']){
    const w=windowFor(archive,'Arsenal FC','2025-05-26',model),e=evidenceFor(archive,w);
    assert.equal(e.selected_model,model);assert.equal(e.as_of_date,'2025-05-26');assert.equal(e.confidence_interval,false);
    assert.equal(e.preanalysis_sha256,'2237d8781491300904a0272b5288c785580d097339d2d705c4561f68703abd59');
    for(const [i,g]of e.matches.entries()){
      assert.deepEqual(g.probabilities,w.games[i][model]);assert.equal(g.training_match_ids.length,w.games[i].training_prefix_count);
      assert.ok(g.training_match_ids.every(id=>id[1]<g.date));
    }
  }
});
