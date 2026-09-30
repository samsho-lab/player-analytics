# Player Analytics

![tests](https://github.com/samsho-lab/player-analytics/actions/workflows/ci.yml/badge.svg)

A small analytics pipeline for game telemetry: load a raw event log into SQLite, clean it, and answer the questions a game team actually asks.

- Where do new players drop off during onboarding?
- How many come back on day 1, 3, 7 and 14?
- Did the new tutorial work, and did it hurt anything else?

The metrics are written in plain SQL (`analytics/queries/`). Python handles loading, the stats test and the charts.

**[See the generated report →](reports/report.md)**

![retention](reports/retention.png)

## The data

`python -m analytics generate` builds a synthetic event log. The numbers are made up, but the problems in it are the ones real telemetry has:

- **Duplicate events.** About 2% of events are sent twice with the same `event_id`, the way a client does when it retries after a timeout.
- **Bad clocks.** Some events are stamped a year before the player installed.
- **An A/B test.** Players are split between the original tutorial (A) and a shorter one (B).

Events look like this:

| event_id | player_id | event | ts | variant |
|---|---|---|---|---|
| 5f1c… | p00042 | install | 2026-06-03T14:22:10 | B |
| 9a0e… | p00042 | tutorial_start | 2026-06-03T14:22:40 | |

## What the SQL does

**`clean.sql`**: removes duplicate deliveries with `ROW_NUMBER() OVER (PARTITION BY event_id)`, drops unknown event names, and drops events stamped before the player's install. It also builds a `players` table with install day and variant. The report shows how many rows each rule removed.

**`funnel.sql`**: an *ordered* funnel. A player only counts for "first match" if they started and finished the tutorial first, in that order. Uses `FIRST_VALUE` and `LAG` window functions for the step-over-step percentages.

**`retention.sql`**: Day-N retention, meaning the share of players who opened the game on exactly day N after install. Players whose day N hasn't happened yet are **left out of the denominator**. Counting them would drag retention down just because recent players haven't had time to come back.

**`experiment.sql`**: tutorial completion and D7 retention per variant.

## The experiment result

`stats.py` runs a two-proportion z-test by hand, with no scipy: it computes the pooled standard error for the test and the unpooled one for the confidence interval. On the sample data:

- **Tutorial completion (primary metric):** B wins clearly, p < 0.0001.
- **D7 retention (guardrail):** no significant difference.

So the shorter tutorial gets more people through onboarding without hurting week-one retention.

## Running it

```bash
pip install -r requirements-dev.txt

python -m analytics generate --players 5000 --out data/events.csv
python -m analytics report data/events.csv --out reports
```

To poke at the tables yourself, pass `--db analytics.db`, then open that file with `sqlite3`.

## Tests

```bash
pytest -v
```

The SQL tests build tiny event logs by hand, a few players each, where the right answer is obvious, and check the queries return exactly that. That includes the edge cases: a retry duplicate, an event before install, a player who skips a funnel step, and a player too new to count for D7. The stats tests check the z-test against a worked example.

## Layout

```
analytics/
  generate.py      synthetic event log
  db.py            load CSV → SQLite, run the cleaning step, run named queries
  queries/*.sql    all the metric definitions
  stats.py         two-proportion z-test
  report.py        markdown report + charts
tests/
reports/           sample output (report.md, funnel.png, retention.png)
```
