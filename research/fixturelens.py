"""Local research implementation of the frozen 2026-10-19 plan.

No network, model selection, publication, or event submission. Fixed heuristic
Elo probabilities are compared with an always-visible league-frequency baseline.
Dates are batch boundaries: no same-day result may enter any day's prediction.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from itertools import groupby
import math


@dataclass(frozen=True)
class Match:
    season: str
    date: str
    home: str
    away: str
    home_goals: int
    away_goals: int

    @property
    def id(self):
        return (self.season, self.date, self.home, self.away)

    @property
    def outcome(self):
        return 0 if self.home_goals > self.away_goals else 2 if self.home_goals < self.away_goals else 1


def parse_season(document, season):
    if not isinstance(document, dict) or not isinstance(document.get('matches'), list):
        raise ValueError('matches array required')
    if not isinstance(season, str) or not season.strip():
        raise ValueError('season required')
    matches, pairs, appearances = [], set(), set()
    for row in document['matches']:
        if not isinstance(row, dict):
            raise ValueError('match object required')
        day, home, away = row.get('date'), row.get('team1'), row.get('team2')
        try:
            valid_date = isinstance(day, str) and date.fromisoformat(day).isoformat() == day
        except ValueError:
            valid_date = False
        if not valid_date:
            raise ValueError('exact ISO calendar date required')
        if not all(isinstance(t, str) and t.strip() == t and t for t in (home, away)) or home == away:
            raise ValueError('two distinct named teams required')
        score = row.get('score')
        goals = score.get('ft') if isinstance(score, dict) else None
        if not isinstance(goals, list) or len(goals) != 2 or not all(type(n) is int and n >= 0 for n in goals):
            raise ValueError('two nonnegative integer final goals required')
        if (home, away) in pairs:
            raise ValueError('duplicate ordered pair within season')
        if (day, home) in appearances or (day, away) in appearances:
            raise ValueError('team appears twice on one date')
        pairs.add((home, away))
        appearances.update(((day, home), (day, away)))
        matches.append(Match(season, day, home, away, *goals))
    if not matches:
        raise ValueError('empty season')
    return matches


def rating_bin(adjusted_difference):
    return 0 if abs(adjusted_difference) < 100 else 1 if abs(adjusted_difference) < 200 else 2


def check_probability(p):
    if len(p) != 3 or any(not math.isfinite(x) or x < -1e-12 or x > 1 + 1e-12 for x in p):
        raise ValueError('invalid probability')
    if not math.isclose(sum(p), 1, abs_tol=1e-12):
        raise ValueError('probability must sum to one')
    return tuple(p)


def walk_forward(matches):
    """Return predictions plus a canonical ID index for training-prefix audit.

    Each prediction's training_prefix_count selects the exact contributing IDs
    from match_ids[:count]. This lossless representation avoids quadratic JSON
    duplication, and is not an assertion of independently verified score truth.
    """
    matches = sorted(matches, key=lambda m: (m.date, m.id))
    ids = [m.id for m in matches]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate match identity')
    # Validate combined-season appearances too, before any state updates.
    seen = set()
    for match in matches:
        for club in (match.home, match.away):
            if (match.date, club) in seen:
                raise ValueError('team appears twice on one date')
            seen.add((match.date, club))
    ratings, counts, draws, bin_matches = defaultdict(lambda: 1500.0), Counter(), Counter(), Counter()
    predictions, training_count, latest_training_date = [], 0, None
    for day, batch in groupby(matches, key=lambda m: m.date):
        batch = list(batch)
        pending = []
        baseline = check_probability(tuple((counts[c] + 1) / (training_count + 3) for c in range(3)))
        for match in batch:
            adjusted = ratings[match.home] - ratings[match.away] + 65
            expected = 1 / (1 + 10 ** (-adjusted / 400))
            band = rating_bin(adjusted)
            draw = min((draws[band] + 5) / (bin_matches[band] + 15), 2 * min(expected, 1 - expected))
            candidate = check_probability((expected - draw / 2, draw, 1 - expected - draw / 2))
            predictions.append({'id': match.id, 'date': day, 'season': match.season,
                'home': match.home, 'away': match.away, 'outcome': match.outcome,
                'baseline': baseline, 'candidate': candidate,
                'training_prefix_count': training_count, 'latest_training_date': latest_training_date})
            pending.append((match, expected, band))
        deltas = defaultdict(float)
        for match, expected, band in pending:
            observed = (1.0, 0.5, 0.0)[match.outcome]
            change = 20 * (observed - expected)
            deltas[match.home] += change
            deltas[match.away] -= change
            counts[match.outcome] += 1
            draws[band] += match.outcome == 1
            bin_matches[band] += 1
        for club, delta in deltas.items():
            ratings[club] += delta
        training_count += len(batch)
        latest_training_date = day
    return {'match_ids': ids, 'predictions': predictions, 'default_model': 'baseline'}


def brier(p, outcome):
    check_probability(p)
    if type(outcome) is not int or outcome not in (0, 1, 2):
        raise ValueError('three-class outcome required')
    return sum((prob - (i == outcome)) ** 2 for i, prob in enumerate(p))


def compare_season(result, season):
    rows = [r for r in result['predictions'] if r['season'] == season]
    if not rows:
        raise ValueError('evaluation season absent')
    loss = {name: sum(brier(r[name], r['outcome']) for r in rows) / len(rows)
            for name in ('baseline', 'candidate')}
    return {'season': season, 'n': len(rows), 'metric': 'unscaled multiclass Brier loss',
            'range': [0, 2], **loss, 'candidate_minus_baseline': loss['candidate'] - loss['baseline'],
            'default_model': 'baseline', 'selection_on_evaluation': False}


def club_windows(result, as_of_date):
    """All observed clubs, using strictly earlier completed league appearances.

    Leave-one-out range describes sensitivity; it is not a confidence interval.
    Residuals are descriptive and do not establish causal difficulty or skill.
    """
    if date.fromisoformat(as_of_date).isoformat() != as_of_date:
        raise ValueError('exact as-of date required')
    clubs = sorted({c for r in result['predictions'] for c in (r['home'], r['away'])})
    history = defaultdict(list)
    for row in result['predictions']:
        if row['date'] >= as_of_date:
            continue
        for club, side in ((row['home'], 0), (row['away'], 2)):
            actual = 1 if row['outcome'] == 1 else 3 if row['outcome'] == side else 0
            expected = 3 * row['baseline'][side] + row['baseline'][1]
            history[club].append({'id': row['id'], 'actual': actual, 'expected': expected,
                                  'residual': actual - expected})
    windows = []
    for club in clubs:
        games = history[club][-5:]
        entry = {'club': club, 'observations': len(games), 'as_of_date': as_of_date,
                 'available': len(games) == 5, 'model': 'baseline', 'matches': games,
                 'last_match_date': games[-1]['id'][1] if games else None,
                 'days_since_last_match': (date.fromisoformat(as_of_date) -
                     date.fromisoformat(games[-1]['id'][1])).days if games else None}
        if len(games) == 5:
            residuals = [g['residual'] for g in games]
            loo = [(sum(residuals) - x) / 4 for x in residuals]
            entry.update(mean_residual=sum(residuals) / 5,
                         leave_one_out_range=[min(loo), max(loo)], confidence_interval=False)
        windows.append(entry)
    return windows
