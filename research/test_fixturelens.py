import unittest

from fixturelens import Match, parse_season, walk_forward, compare_season, club_windows, brier


def row(day='2023-08-11', home='A', away='B', goals=None):
    return {'date': day, 'team1': home, 'team2': away,
            'score': {'ft': [2, 1] if goals is None else goals}}


def prediction_values(result):
    return {tuple(r['id']): (r['baseline'], r['candidate'], r['training_prefix_count'])
            for r in result['predictions']}


class ChronologyTests(unittest.TestCase):
    def test_initial_probabilities_match_declared_formula(self):
        r = walk_forward([Match('dev', '2023-01-01', 'A', 'B', 1, 0)])['predictions'][0]
        self.assertEqual(r['baseline'], (1/3, 1/3, 1/3))
        expected = 1/(1 + 10 ** (-65/400))
        self.assertAlmostEqual(r['candidate'][0], expected - 1/6)
        self.assertAlmostEqual(r['candidate'][1], 1/3)
        self.assertEqual(r['training_prefix_count'], 0)
        self.assertIsNone(r['latest_training_date'])

    def test_same_day_outcomes_never_affect_other_predictions(self):
        games = [Match('dev', '2023-01-01', 'A', 'B', 1, 0),
                 Match('dev', '2023-01-01', 'C', 'D', 2, 2),
                 Match('dev', '2023-01-02', 'A', 'C', 0, 1)]
        changed = list(games); changed[0] = Match('dev', '2023-01-01', 'A', 'B', 0, 9)
        a, b = walk_forward(games), walk_forward(changed)
        self.assertEqual(prediction_values(a)[games[1].id], prediction_values(b)[games[1].id])
        self.assertNotEqual(a['predictions'][2]['candidate'], b['predictions'][2]['candidate'])
        self.assertEqual(a['predictions'][2]['baseline'], (2/5, 2/5, 1/5))

    def test_future_label_changes_do_not_change_earlier_predictions(self):
        games = [Match('dev', '2023-01-01', 'A', 'B', 1, 0),
                 Match('eval', '2024-01-01', 'B', 'A', 2, 1),
                 Match('eval', '2024-01-02', 'A', 'B', 0, 0)]
        changed = games[:2] + [Match('eval', '2024-01-02', 'A', 'B', 8, 0)]
        self.assertEqual(prediction_values(walk_forward(games)), prediction_values(walk_forward(changed)))

    def test_input_order_does_not_change_predictions(self):
        games = [Match('dev', '2023-01-02', 'A', 'C', 0, 1),
                 Match('dev', '2023-01-01', 'C', 'D', 0, 0),
                 Match('dev', '2023-01-01', 'A', 'B', 1, 0)]
        self.assertEqual(walk_forward(games), walk_forward(list(reversed(games))))

    def test_training_prefix_contains_only_strictly_earlier_dates(self):
        games = [Match('dev', '2023-01-01', 'A', 'B', 1, 0),
                 Match('dev', '2023-01-01', 'C', 'D', 0, 0),
                 Match('eval', '2024-01-01', 'A', 'E', 0, 1)]
        r = walk_forward(games)
        for pred in r['predictions']:
            prefix = r['match_ids'][:pred['training_prefix_count']]
            self.assertTrue(all(i[1] < pred['date'] for i in prefix))
        self.assertEqual(r['predictions'][-1]['training_prefix_count'], 2)

    def test_duplicate_match_and_same_day_team_rejected(self):
        m = Match('dev', '2023-01-01', 'A', 'B', 1, 0)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            walk_forward([m, m])
        with self.assertRaisesRegex(ValueError, 'twice'):
            walk_forward([m, Match('dev', '2023-01-01', 'C', 'A', 0, 1)])


class InputAndEvaluationTests(unittest.TestCase):
    def test_malformed_final_scores_and_dates_fail_closed(self):
        for goals in ([True, 1], [-1, 0], [float('nan'), 0], [1.0, 0], [1], ['1', 0]):
            with self.subTest(goals=goals), self.assertRaises(ValueError):
                parse_season({'matches': [row(goals=goals)]}, 'dev')
        for day in ('2023-02-29', '2023-8-11', '20230811', None):
            with self.subTest(day=day), self.assertRaises(ValueError):
                parse_season({'matches': [row(day=day)]}, 'dev')

    def test_duplicate_pairs_and_same_team_rejected_by_parser(self):
        for rows in ([row(), row(day='2023-08-12')], [row(home='A', away='A')],
                     [row(), row(home='C', away='A')]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                parse_season({'matches': rows}, 'dev')

    def test_unscaled_three_class_brier_endpoints(self):
        self.assertEqual(brier((1, 0, 0), 0), 0)
        self.assertEqual(brier((1, 0, 0), 2), 2)
        self.assertAlmostEqual(brier((1/3, 1/3, 1/3), 1), 2/3)
        with self.assertRaises(ValueError): brier((float('nan'), 0, 1), 0)

    def test_evaluation_reports_both_without_changing_default(self):
        r = walk_forward([Match('eval', '2024-01-01', 'A', 'B', 0, 4)])
        report = compare_season(r, 'eval')
        self.assertEqual(report['n'], 1)
        self.assertEqual(report['default_model'], 'baseline')
        self.assertFalse(report['selection_on_evaluation'])
        self.assertAlmostEqual(report['candidate_minus_baseline'], report['candidate'] - report['baseline'])

    def test_five_game_windows_exclude_asof_day_and_use_loo_sensitivity(self):
        games = [Match('dev', f'2023-01-{i:02d}', 'A', f'B{i}', i % 3, 1)
                 for i in range(1, 7)]
        result = walk_forward(games)
        early = next(w for w in club_windows(result, '2023-01-05') if w['club'] == 'A')
        self.assertFalse(early['available']); self.assertEqual(early['observations'], 4)
        w = next(w for w in club_windows(result, '2023-01-06') if w['club'] == 'A')
        self.assertTrue(w['available']); self.assertFalse(w['confidence_interval'])
        self.assertEqual(w['last_match_date'], '2023-01-05')
        self.assertEqual(w['days_since_last_match'], 1)
        self.assertTrue(all(x['id'][1] < '2023-01-06' for x in w['matches']))
        residuals = [x['residual'] for x in w['matches']]
        independently_calculated = [sum(residuals[:i] + residuals[i+1:]) / 4 for i in range(5)]
        self.assertAlmostEqual(w['mean_residual'], sum(residuals)/5)
        self.assertEqual(w['leave_one_out_range'], [min(independently_calculated), max(independently_calculated)])

    def test_new_club_windows_are_unavailable_not_zero_padded(self):
        result = walk_forward([Match('dev', '2023-01-01', 'A', 'B', 0, 0)])
        windows = club_windows(result, '2023-01-01')
        self.assertEqual(len(windows), 2)
        self.assertTrue(all(not w['available'] and w['matches'] == [] for w in windows))


if __name__ == '__main__':
    unittest.main()
