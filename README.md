# FixtureLens

Understand the last five: a historical football form review with exact earlier
training evidence. Prepared locally for AQX Sports Analytics Data Bowl 4.0.
**Final project submission was confirmed on October 20, 2026 (KST), as
submission 1247423.** [View the Devpost project](https://devpost.com/software/fixturelens).
The platform showed SUBMITTED with all four steps complete after reload.
This is a historical submission receipt, not a judging result or award.
AI assisted the concept, code,
implementation, tests and documentation. The visual concept is AI generated;
the running interface is real HTML/CSS/React/SVG, with computed archived data.

## Use locally

Node.js compatible with Vite 8 and pnpm are required. Versions are pinned in
`package.json` and `pnpm-lock.yaml`. Dependencies are React/ReactDOM 19.3.1 and
Vite 8.3.4. The app makes no paid API calls and has no account or backend.

```sh
pnpm install --frozen-lockfile --ignore-scripts
pnpm dev
```

Open the displayed localhost address. To build static files, use `pnpm build`.
Serve `dist/` from an HTTP server; do not open ES modules with a `file:` URL.
No deployment is performed by these commands.

Select a historical date and club. Only matches strictly earlier than the
selected date enter the five-game window. The default is **League baseline**;
**Fixed Elo** is an explicit comparison choice. The default is never selected
from the observed evaluation winner. Search covers all 23 observed clubs,
including clubs absent from the later season. Last-match age exposes old data.
Fewer than five observations yields an unavailable state; no zero padding is used.
An empty or invalid date clears results and disables export.

The evidence table opens each match's complete earlier training list. **Export
evidence** downloads the selected club/date/model, probabilities, expected and
actual points, residuals, source hashes, and each contributing earlier match ID.
On narrow screens the evidence table scrolls horizontally.

## Reproduce and test

```sh
pnpm test
python3 -m unittest discover -s research -p 'test_fixturelens.py' -v
python3 research/reproduce.py
```

Seven frontend tests compare every default club window with the frozen Python
output, check date boundaries, stale observations and export provenance. Twelve
Python tests check same-day batching, future-label exclusion, ordering,
validation, proper scoring and sensitivity. The offline reproduction command
checks all 760 predictions, 23 club windows and the evaluation metric against
the browser data. It requires no installation beyond Python and writes no files.

## Data, methods and limitations

The exact 2023–24 and 2024–25 English league files come from
[openfootball/football.json](https://github.com/openfootball/football.json/tree/e6744429ee395bc86f247348c6184bb08d4eb361),
pinned at commit `e6744429ee395bc86f247348c6184bb08d4eb361`. The publisher's
CC0 1.0 license is preserved in `research/data/CC0-LICENSE.md`. Input hashes and
the unchanged plan are in `research/preanalysis-plan.json`. Source scores have
not been independently reconciled with official league records. There are no
injury, xG, odds, player-tracking or personal-data inputs.

The plan was fixed before metrics. Its SHA-256 is
`2237d8781491300904a0272b5288c785580d097339d2d705c4561f68703abd59`.
The implementation freeze records code hashes from before first real-data
metrics. Elo is a fixed heuristic: initial 1500, home advantage 65, K 20, scale
400, with the specified earlier-data draw bins. No held-out tuning was used.

Sequential 2024–25 evaluation covers 380 matches. Unscaled multiclass Brier loss
is **0.6563440697** for League baseline and **0.6074892205** for Fixed Elo;
lower is better, metric range 0–2. The small audit bars use that same 0–2 scale.
This is one retrospective season, not proof of significance or future results.
The model audit always covers the full archived evaluation season; changing the
form date does not redefine that separate audit population.

Actual-minus-expected points is descriptive. The league baseline has no
opponent-strength component. Switching models can reverse a window's sign:
Arsenal's final archived five matches produce +0.19 mean baseline residual,
versus −0.33 under Fixed Elo. This is a demonstration of assumption sensitivity,
not a causal claim about skill. Leave-one-out mean ranges are sensitivity
ranges, not confidence intervals. Historical data is not a live forecast or
betting recommendation.

## Submission preflight record — 2026-10-20

The initial rules-page preflight did not explicitly address AI assistance.
The actual finalization form subsequently stated: “We allow the usage of AI,
so long as your ideas and final execution are your own.” AI contributions are
disclosed above; this is not a claim of organizer eligibility approval.

Independent method/source and desktop-interface review is complete. A separate
check recomputed all 760 predictions and compared 10,580 club/date/model
combinations. The published 24-file source was read back and matched its reviewed
SHA-256 manifest; the fetched source passed 12 Python tests, 7 JavaScript tests
and offline reproduction. These checks do not independently validate the source
scores against official league records or establish future predictive accuracy.

At the initial preflight, individual event registration was complete and the
FixtureLens Devpost draft (submission 1247423) was saved at 3/4 steps, with three
actual app screenshots and a thumbnail. Finalization subsequently completed on
October 20, 2026 (KST): the platform displayed “Project submitted!” and the
reloaded management page retained SUBMITTED with 4/4 steps complete for that
same submission. The repository publication preceded this separate platform
receipt. Organizer eligibility approval, judging results and awards remain
unconfirmed.

## Full-time score cross-check — 2026-10-21

All 760 archived fixtures were compared with the separately published
[Football-Data English Premier League CSVs](https://football-data.co.uk/englandm.php)
([2023–24](https://football-data.co.uk/mmz4281/2324/E0.csv),
[2024–25](https://football-data.co.uk/mmz4281/2425/E0.csv)). After an explicit
23-club alias mapping, every ordered home/away fixture, calendar date and
full-time home/away score agreed: 380/380 in each season, with no missing,
extra, date-mismatched or score-mismatched fixtures.

The [recorded report](research/score-reconciliation.json) includes both input
SHA-256 values, the complete alias map and comparison limits. Football-Data is
a separate publisher, not an official league certification; upstream source
independence has not been established. Kickoff times, half-time results, odds
and other match statistics were not checked or added to the model. Agreement
does not establish predictive validity or future accuracy. The original data,
preanalysis plan, implementation freeze, model and evaluation metrics are unchanged.

To repeat the check, download those two CSVs separately and keep them outside
the repository. Only Python's standard library is needed; the checker itself
makes no network calls and writes no files:

```sh
python3 research/reconcile_scores.py \
  --reference-2023-24 /path/to/2324-E0.csv \
  --reference-2024-25 /path/to/2425-E0.csv
python3 -m unittest discover -s research -p 'test_reconcile_scores.py' -v
```

Exit status is 0 only for complete agreement and 1 for a comparison mismatch;
invalid inputs also fail. Compare downloaded file hashes with the recorded
report before claiming reproduction of this exact snapshot. Nine tests cover
score/date changes, missing/extra fixtures, duplicate identities, unknown
aliases, invalid reference values, reversed venues and empty input. Reference
CSVs are not redistributed in this repository.

