import argparse
import os

from . import db
from .generate import generate, write_csv
from .report import build_report


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m analytics")
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="write a synthetic event log to CSV")
    g.add_argument("--players", type=int, default=5000)
    g.add_argument("--seed", type=int, default=7)
    g.add_argument("--out", default="data/events.csv")

    r = sub.add_parser("report", help="clean an event CSV and write the report")
    r.add_argument("csv")
    r.add_argument("--out", default="reports")
    r.add_argument("--db", default=":memory:", help="optional SQLite file to keep the tables around")

    args = parser.parse_args()

    if args.cmd == "generate":
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        events = generate(args.players, args.seed)
        write_csv(events, args.out)
        print(f"wrote {len(events):,} events for {args.players:,} players to {args.out}")
    else:
        conn = db.load_csv(args.csv, args.db)
        path = build_report(conn, args.out)
        print(f"report written to {path}")


if __name__ == "__main__":
    main()
