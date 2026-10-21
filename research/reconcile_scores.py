"""Compare archived dates and full-time scores with separately downloaded CSVs.

Offline only. No model fitting, network calls, input changes or CSV publication.
Football-Data is a separate publisher, not an official league certification;
agreement does not establish that the two publishers have independent upstreams.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path


ALIASES = {
    'AFC Bournemouth': 'Bournemouth', 'Arsenal FC': 'Arsenal',
    'Aston Villa FC': 'Aston Villa', 'Brentford FC': 'Brentford',
    'Brighton & Hove Albion FC': 'Brighton', 'Burnley FC': 'Burnley',
    'Chelsea FC': 'Chelsea', 'Crystal Palace FC': 'Crystal Palace',
    'Everton FC': 'Everton', 'Fulham FC': 'Fulham', 'Ipswich Town FC': 'Ipswich',
    'Leicester City FC': 'Leicester', 'Liverpool FC': 'Liverpool',
    'Luton Town FC': 'Luton', 'Manchester City FC': 'Man City',
    'Manchester United FC': 'Man United', 'Newcastle United FC': 'Newcastle',
    'Nottingham Forest FC': "Nott'm Forest", 'Sheffield United FC': 'Sheffield United',
    'Southampton FC': 'Southampton', 'Tottenham Hotspur FC': 'Tottenham',
    'West Ham United FC': 'West Ham', 'Wolverhampton Wanderers FC': 'Wolves',
}
REFERENCE_URLS = {
    '2023-24': 'https://football-data.co.uk/mmz4281/2324/E0.csv',
    '2024-25': 'https://football-data.co.uk/mmz4281/2425/E0.csv',
}


def index_rows(rows, reference=False):
    """Key by ordered home/away pair so a changed date cannot hide a fixture."""
    indexed = {}
    for row in rows:
        if reference:
            home, away = row['HomeTeam'], row['AwayTeam']
            if home not in ALIASES.values() or away not in ALIASES.values():
                raise ValueError('Unknown reference club')
            day = datetime.strptime(row['Date'], '%d/%m/%Y').date().isoformat()
            raw_goals = (row['FTHG'], row['FTAG'])
            if any(not g.isascii() or not g.isdigit() for g in raw_goals):
                raise ValueError('Nonnegative integer full-time goals required')
            goals = tuple(map(int, raw_goals))
            outcome = 'H' if goals[0] > goals[1] else 'A' if goals[0] < goals[1] else 'D'
            if row['Div'] != 'E0' or row['FTR'] != outcome:
                raise ValueError('Reference division/result inconsistent')
        else:
            try:
                home, away = ALIASES[row['team1']], ALIASES[row['team2']]
            except KeyError as error:
                raise ValueError('Unknown archive club') from error
            day = row['date']
            if datetime.strptime(day, '%Y-%m-%d').date().isoformat() != day:
                raise ValueError('Exact ISO archive date required')
            goals = tuple(row['score']['ft'])
            if len(goals) != 2 or any(type(g) is not int or g < 0 for g in goals):
                raise ValueError('Nonnegative integer full-time goals required')
        key = (home, away)
        if home == away or key in indexed:
            raise ValueError('Same club or duplicate ordered fixture')
        indexed[key] = (day, *goals)
    return indexed


def reconcile(archive_rows, reference_rows):
    archive = index_rows(archive_rows)
    reference = index_rows(reference_rows, reference=True)
    common = sorted(archive.keys() & reference.keys())
    dates = [list(key) for key in common if archive[key][0] != reference[key][0]]
    scores = [list(key) for key in common if archive[key][1:] != reference[key][1:]]
    missing = [list(key) for key in sorted(archive.keys() - reference.keys())]
    extra = [list(key) for key in sorted(reference.keys() - archive.keys())]
    return {
        'archive_fixtures': len(archive), 'reference_fixtures': len(reference),
        'matched_ordered_fixtures': len(common),
        'date_mismatches': dates, 'score_mismatches': scores,
        'missing_from_reference': missing, 'extra_in_reference': extra,
        'all_agree': bool(common) and not (dates or scores or missing or extra),
    }


def audit_files(archive_dir, references):
    seasons = []
    for season, reference_path in references.items():
        archive_bytes = (archive_dir / (season + '.json')).read_bytes()
        reference_bytes = reference_path.read_bytes()
        archive_rows = json.loads(archive_bytes)['matches']
        reference_rows = list(csv.DictReader(io.StringIO(reference_bytes.decode('utf-8-sig'))))
        result = reconcile(archive_rows, reference_rows)
        if result['archive_fixtures'] != 380 or result['reference_fixtures'] != 380:
            raise ValueError('Each complete season must contain exactly 380 fixtures')
        seasons.append({
            'season': season, 'reference_url': REFERENCE_URLS[season],
            'archive_sha256': hashlib.sha256(archive_bytes).hexdigest(),
            'reference_sha256': hashlib.sha256(reference_bytes).hexdigest(), **result,
        })
    return {
        'schema': 'fixturelens/score-reconciliation/v1',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'compared_fields': ['home_club', 'away_club', 'calendar_date', 'full_time_home_goals', 'full_time_away_goals'],
        'aliases': ALIASES, 'seasons': seasons,
        'all_agree': all(s['all_agree'] for s in seasons),
        'limits': [
            'Separate publisher agreement, not official league certification.',
            'Upstream independence has not been established.',
            'No kickoff times, half-time scores, odds or match statistics checked.',
            'Does not establish predictive validity, significance or future accuracy.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-dir', type=Path, default=Path(__file__).parent / 'data')
    parser.add_argument('--reference-2023-24', type=Path, required=True)
    parser.add_argument('--reference-2024-25', type=Path, required=True)
    args = parser.parse_args()
    result = audit_files(args.archive_dir, {
        '2023-24': args.reference_2023_24, '2024-25': args.reference_2024_25,
    })
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['all_agree'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
