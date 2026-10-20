export const MODELS = Object.freeze({baseline: 'League baseline', candidate: 'Fixed Elo'});
export const MIN_DATE = '2023-08-11';
export const MAX_DATE = '2025-05-26';
export function validDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const day = new Date(value + 'T00:00:00Z');
  return Number.isFinite(day.valueOf()) && day.toISOString().slice(0, 10) === value && value >= MIN_DATE && value <= MAX_DATE;
}
export function clubsIn(archive) {
  return [...new Set(archive.predictions.flatMap(r => [r.home, r.away]))].sort((a, b) => a.localeCompare(b, 'en'));
}
export function windowFor(archive, club, asOf, model = 'baseline') {
  if (!validDate(asOf)) throw new Error(`Choose a date from ${MIN_DATE} to ${MAX_DATE}.`);
  if (!Object.hasOwn(MODELS, model)) throw new Error('Choose a supported model.');
  if (!clubsIn(archive).includes(club)) throw new Error('Choose an observed club.');
  const rows = archive.predictions.filter(r => r.date < asOf && (r.home === club || r.away === club)).slice(-5);
  const games = rows.map(r => {
    const side = r.home === club ? 0 : 2;
    const actual = r.outcome === 1 ? 1 : r.outcome === side ? 3 : 0;
    const expected = 3 * r[model][side] + r[model][1];
    return {...r, opponent: side === 0 ? r.away : r.home, venue: side === 0 ? 'Home' : 'Away', actual, expected, residual: actual - expected};
  });
  const available = games.length === 5;
  const total = games.reduce((sum, g) => sum + g.residual, 0);
  const loo = available ? games.map(g => (total - g.residual) / 4) : [];
  const last = games.at(-1)?.date ?? null;
  return {club, asOf, model, games, available, actual: games.reduce((s,g) => s+g.actual,0),
    expected: games.reduce((s,g) => s+g.expected,0), mean: available ? total / 5 : null,
    range: available ? [Math.min(...loo), Math.max(...loo)] : null,
    last, age: last ? Math.round((Date.parse(asOf)-Date.parse(last))/86400000) : null};
}
export function shortClub(name) { return name.replace(/ FC$/, '').replace(/^AFC /, ''); }
export function displayDate(day) {
  return new Intl.DateTimeFormat('en-GB', {month:'short',day:'2-digit',timeZone:'UTC'}).format(new Date(day+'T00:00:00Z'));
}
export function signed(n) { return (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2); }
export function evidenceFor(archive, window) {
  return {schema:'fixturelens/selected-window-evidence/v1', historical_archive:true, club:window.club,
    as_of_date:window.asOf, selected_model:window.model, default_model:'baseline',
    window_available:window.available, observations:window.games.length,
    mean_residual:window.mean, leave_one_out_mean_range:window.range, confidence_interval:false,
    latest_match_date:window.last, days_since_last_match:window.age,
    preanalysis_sha256:archive.summary.preanalysis_sha256,
    implementation_freeze_sha256:archive.summary.implementation_freeze_sha256,
    input_seasons:archive.summary.input_seasons,
    matches:window.games.map(g=>({id:g.id,date:g.date,actual:g.actual,expected:g.expected,residual:g.residual,
      probabilities:g[window.model],latest_training_date:g.latest_training_date,
      training_match_ids:archive.match_ids.slice(0,g.training_prefix_count)})),
    limits:['One historical league archive; not live forecasts.','Source scores are not independently verified.',
      'Residuals are descriptive, not causal skill estimates.','Leave-one-out range is sensitivity, not a confidence interval.',
      window.model==='baseline' ? 'League baseline does not model opponent strength.' : 'Fixed heuristic Elo, without injuries, xG or player tracking.']};
}
