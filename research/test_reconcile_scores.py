import copy
import unittest
from reconcile_scores import reconcile


class ScoreReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.archive = [{'date': '2024-01-01', 'team1': 'Manchester City FC',
                         'team2': 'AFC Bournemouth', 'score': {'ft': [2, 1]}}]
        self.reference = [{'Date': '01/01/2024', 'HomeTeam': 'Man City',
                           'AwayTeam': 'Bournemouth', 'FTHG': '2', 'FTAG': '1',
                           'FTR': 'H', 'Div': 'E0'}]

    def test_alias_and_exact_score_agreement(self):
        self.assertTrue(reconcile(self.archive, self.reference)['all_agree'])

    def test_changed_score_detected_without_changing_outcome(self):
        self.reference[0]['FTHG'] = '3'
        result = reconcile(self.archive, self.reference)
        self.assertFalse(result['all_agree'])
        self.assertEqual(result['score_mismatches'], [['Man City', 'Bournemouth']])

    def test_changed_date_is_not_hidden_by_fixture_join(self):
        self.reference[0]['Date'] = '02/01/2024'
        result = reconcile(self.archive, self.reference)
        self.assertEqual(result['matched_ordered_fixtures'], 1)
        self.assertEqual(result['date_mismatches'], [['Man City', 'Bournemouth']])
        self.assertFalse(result['all_agree'])

    def test_missing_and_extra_fixtures_detected(self):
        self.assertFalse(reconcile(self.archive, [])['all_agree'])
        self.assertEqual(len(reconcile(self.archive, [])['missing_from_reference']), 1)
        self.assertEqual(len(reconcile([], self.reference)['extra_in_reference']), 1)

    def test_duplicate_in_either_input_rejected(self):
        for archive, reference in [(self.archive * 2, self.reference),
                                    (self.archive, self.reference * 2)]:
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                reconcile(archive, reference)

    def test_unknown_club_not_silently_fuzzy_matched(self):
        self.reference[0]['HomeTeam'] = 'Manchester'
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            reconcile(self.archive, self.reference)

    def test_invalid_reference_score_or_outcome_rejected(self):
        for field, value in [('FTHG', '-1'), ('FTAG', '1.0'), ('FTR', 'D'), ('Div', 'E1')]:
            rows = copy.deepcopy(self.reference)
            rows[0][field] = value
            with self.assertRaises(ValueError):
                reconcile(self.archive, rows)

    def test_reversed_venue_is_missing_and_extra_not_match(self):
        self.reference[0].update(HomeTeam='Bournemouth', AwayTeam='Man City')
        result = reconcile(self.archive, self.reference)
        self.assertEqual(result['matched_ordered_fixtures'], 0)
        self.assertFalse(result['all_agree'])

    def test_empty_inputs_do_not_pass(self):
        self.assertFalse(reconcile([], [])['all_agree'])


if __name__ == '__main__':
    unittest.main()
