"""Generate a fake but realistic-looking event log.

The numbers are made up, but the shape matches what real game telemetry looks
like, including the messy parts:
  * about 2% of events are sent twice (client retries after a timeout)
  * a few events have timestamps before the player even installed (bad device clocks)
  * players are split 50/50 into an onboarding experiment: variant A has the
    original tutorial, variant B a shorter one that more people finish
"""
import csv
import random
import uuid
from datetime import datetime, timedelta

START = datetime(2026, 6, 1)
DAYS = 45

# Chance to finish the tutorial, by variant. B is the shorter tutorial.
TUTORIAL_COMPLETE = {"A": 0.62, "B": 0.70}


def _daily_return_chance(day: int, finished_tutorial: bool) -> float:
    # Retention decays roughly like a power curve. Finishing the tutorial
    # roughly doubles your odds of coming back.
    base = 0.45 if finished_tutorial else 0.22
    return base * (day ** -0.45)


def generate(players: int, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    events: list[dict] = []

    def emit(pid, name, ts, variant=""):
        events.append({
            "event_id": str(uuid.UUID(int=rng.getrandbits(128))),
            "player_id": pid,
            "event": name,
            "ts": ts.isoformat(timespec="seconds"),
            "variant": variant,
        })

    for i in range(players):
        pid = f"p{i:05d}"
        variant = rng.choice("AB")
        # Installs spread over the first 30 days so later cohorts still have room for D14.
        installed = START + timedelta(days=rng.randrange(30), seconds=rng.randrange(86_400))
        emit(pid, "install", installed, variant)
        emit(pid, "session_start", installed + timedelta(seconds=5))

        t = installed + timedelta(seconds=30)
        finished = False
        if rng.random() < 0.93:
            emit(pid, "tutorial_start", t)
            if rng.random() < TUTORIAL_COMPLETE[variant]:
                finished = True
                t += timedelta(minutes=rng.randint(3, 8))
                emit(pid, "tutorial_complete", t)
                if rng.random() < 0.80:
                    t += timedelta(minutes=rng.randint(1, 5))
                    emit(pid, "first_match", t)
                    if rng.random() < 0.06:
                        emit(pid, "first_purchase", t + timedelta(minutes=rng.randint(5, 90)))

        last_day = (START + timedelta(days=DAYS - 1) - installed).days
        for day in range(1, last_day + 1):
            if rng.random() < _daily_return_chance(day, finished):
                emit(pid, "session_start", installed + timedelta(days=day, seconds=rng.randrange(-3600, 3600)))

    # Messy data, on purpose.
    dupes = rng.sample(events, k=len(events) // 50)
    events.extend(dict(e) for e in dupes)
    for e in rng.sample(events, k=len(events) // 200):
        if e["event"] != "install":
            e["ts"] = (datetime.fromisoformat(e["ts"]) - timedelta(days=400)).isoformat(timespec="seconds")

    rng.shuffle(events)
    return events


def write_csv(events: list[dict], path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["event_id", "player_id", "event", "ts", "variant"])
        w.writeheader()
        w.writerows(events)
