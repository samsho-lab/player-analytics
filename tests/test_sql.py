"""SQL tests on tiny hand-written event logs where the right answer is known."""
import itertools

from analytics import db

_ids = itertools.count()


def ev(player, event, ts, variant="", event_id=None):
    return {
        "event_id": event_id or f"e{next(_ids)}",
        "player_id": player,
        "event": event,
        "ts": ts,
        "variant": variant,
    }


def install(player, day, variant="A"):
    return [
        ev(player, "install", f"2026-06-{day:02d}T10:00:00", variant),
        ev(player, "session_start", f"2026-06-{day:02d}T10:00:05"),
    ]


def test_duplicates_bad_clocks_and_unknown_events_are_cleaned():
    rows = install("p1", 1) + [
        ev("p1", "tutorial_start", "2026-06-01T10:01:00", event_id="dup"),
        ev("p1", "tutorial_start", "2026-06-01T10:01:00", event_id="dup"),   # retry, same id
        ev("p1", "session_start", "2025-01-01T00:00:00"),                    # before install
        ev("p1", "debug_ping", "2026-06-01T10:02:00"),                       # unknown event
    ]
    conn = db.load(rows)
    q = db.data_quality(conn)
    assert q["raw_events"] == 6
    assert q["duplicates_removed"] == 1
    assert q["other_rows_removed"] == 2
    assert q["clean_events"] == 3


def test_funnel_requires_steps_in_order():
    rows = (
        install("p1", 1) + install("p2", 1) + install("p3", 1)
        + [
            # p1: full path
            ev("p1", "tutorial_start", "2026-06-01T10:01:00"),
            ev("p1", "tutorial_complete", "2026-06-01T10:05:00"),
            ev("p1", "first_match", "2026-06-01T10:07:00"),
            ev("p1", "first_purchase", "2026-06-01T11:00:00"),
            # p2: starts tutorial, never finishes, but somehow has a match
            ev("p2", "tutorial_start", "2026-06-01T10:01:00"),
            ev("p2", "first_match", "2026-06-01T10:03:00"),
            # p3: nothing after install
        ]
    )
    funnel = {r["name"]: r for r in db.query(db.load(rows), "funnel")}

    assert funnel["install"]["players"] == 3
    assert funnel["tutorial_start"]["players"] == 2
    assert funnel["tutorial_complete"]["players"] == 1
    assert funnel["first_match"]["players"] == 1  # p2's match doesn't count, they skipped the tutorial
    assert funnel["first_purchase"]["players"] == 1
    assert funnel["tutorial_start"]["pct_of_installs"] == 66.7
    assert funnel["tutorial_complete"]["pct_of_previous"] == 50.0


def test_retention_only_counts_eligible_players():
    rows = (
        install("early", 1) + install("late", 10)
        + [
            ev("early", "session_start", "2026-06-02T09:00:00"),   # day 1
            ev("early", "session_start", "2026-06-08T09:00:00"),   # day 7
            ev("late", "session_start", "2026-06-11T09:00:00"),    # day 1
            ev("late", "session_start", "2026-06-12T09:00:00"),    # last day in the data
        ]
    )
    ret = {r["day"]: r for r in db.query(db.load(rows), "retention")}

    assert ret[1] == {"day": 1, "eligible": 2, "retained": 2, "retention_pct": 100.0}
    # Data ends 2026-06-12. "late" installed 06-10, so their day 7 hasn't happened yet.
    assert ret[7]["eligible"] == 1
    assert ret[7]["retained"] == 1
    assert 14 not in ret  # nobody is 14 days old yet


def test_session_on_wrong_day_does_not_count_as_day_n():
    rows = install("p1", 1) + [
        ev("p1", "session_start", "2026-06-06T09:00:00"),  # day 5
        ev("p1", "session_start", "2026-06-20T09:00:00"),  # extends the data window
    ]
    ret = {r["day"]: r for r in db.query(db.load(rows), "retention")}
    assert ret[3]["retained"] == 0
    assert ret[7]["retained"] == 0


def test_experiment_splits_by_variant():
    rows = (
        install("a1", 1, "A") + install("a2", 1, "A") + install("b1", 1, "B")
        + [
            ev("a1", "tutorial_start", "2026-06-01T10:01:00"),
            ev("a1", "tutorial_complete", "2026-06-01T10:05:00"),
            ev("b1", "tutorial_start", "2026-06-01T10:01:00"),
            ev("b1", "tutorial_complete", "2026-06-01T10:05:00"),
            ev("b1", "session_start", "2026-06-08T12:00:00"),  # day 7
        ]
    )
    exp = {r["variant"]: r for r in db.query(db.load(rows), "experiment")}
    assert exp["A"] == {"variant": "A", "players": 2, "completed_tutorial": 1, "d7_eligible": 2, "d7_retained": 0}
    assert exp["B"] == {"variant": "B", "players": 1, "completed_tutorial": 1, "d7_eligible": 1, "d7_retained": 1}
