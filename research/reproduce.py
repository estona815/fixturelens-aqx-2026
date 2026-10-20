"""Read-only, offline reproduction of the frozen archive. Python stdlib only."""
from pathlib import Path
import json
import hashlib
import math
from fixturelens import parse_season, walk_forward, compare_season, club_windows

directory = Path(__file__).resolve().parent
plan_path = directory / 'preanalysis-plan.json'
plan = json.loads(plan_path.read_text())
assert hashlib.sha256(plan_path.read_bytes()).hexdigest() == '2237d8781491300904a0272b5288c785580d097339d2d705c4561f68703abd59'
freeze = json.loads((directory/'implementation-freeze-before-metrics.json').read_text())
for name, expected in freeze['source_files'].items():
    assert hashlib.sha256((directory/name).read_bytes()).hexdigest() == expected
games = []
for source in plan['input_seasons']:
    path = directory / 'data' / (source['season'] + '.json')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
    games.extend(parse_season(json.loads(path.read_text()), source['season']))
result = walk_forward(games)
archive = json.loads((directory.parent/'src/data/archive.json').read_text())
assert json.loads(json.dumps(result['match_ids'])) == archive['match_ids']
assert len(result['predictions']) == len(archive['predictions']) == 760
for actual, saved in zip(result['predictions'], archive['predictions']):
    for key in ('date','season','home','away','outcome','training_prefix_count','latest_training_date'):
        assert actual[key] == saved[key]
    for model in ('baseline','candidate'):
        assert all(math.isclose(a,b,abs_tol=1e-14) for a,b in zip(actual[model],saved[model]))
    assert all(identity[1] < actual['date'] for identity in result['match_ids'][:actual['training_prefix_count']])
comparison = compare_season(result, plan['evaluation_season'])
for model in ('baseline','candidate'):
    assert math.isclose(comparison[model],archive['summary']['comparison'][model],abs_tol=1e-14)
assert json.loads(json.dumps(club_windows(result,'2025-05-26'))) == archive['baseline_windows']
print(json.dumps({'status':'PASS_OFFLINE_REPRODUCTION','predictions':760,'club_windows':23,
                  'comparison':comparison,'files_written':0,'network_calls':0},indent=2))
