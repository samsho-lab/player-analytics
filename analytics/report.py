import os
import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import db  # noqa: E402
from .stats import two_proportion_ztest  # noqa: E402


def _table(rows: list[dict]) -> str:
    if not rows:
        return "_no rows_\n"
    cols = list(rows[0])
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join("" if r[c] is None else str(r[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def _funnel_chart(funnel: list[dict], path: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    names = [r["name"] for r in funnel]
    ax.barh(names[::-1], [r["players"] for r in funnel][::-1], color="#4c78a8")
    for i, r in enumerate(funnel[::-1]):
        ax.text(r["players"], i, f"  {r['pct_of_installs']}%", va="center", fontsize=9)
    ax.set_xlim(0, max(r["players"] for r in funnel) * 1.15)
    ax.set_xlabel("players")
    ax.set_title("Onboarding funnel")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _retention_chart(curve: list[dict], path: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    for variant, color in (("A", "#4c78a8"), ("B", "#f58518")):
        pts = [r for r in curve if r["variant"] == variant]
        ax.plot([r["day"] for r in pts], [r["retention_pct"] for r in pts],
                marker="o", ms=3, color=color, label=f"variant {variant}")
    ax.set_xlabel("days since install")
    ax.set_ylabel("% of players active")
    ax.set_title("Day-N retention by onboarding variant")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def experiment_results(conn: sqlite3.Connection) -> dict:
    rows = {r["variant"]: r for r in db.query(conn, "experiment")}
    a, b = rows["A"], rows["B"]
    return {
        "rows": list(rows.values()),
        "tutorial": two_proportion_ztest(a["completed_tutorial"], a["players"],
                                         b["completed_tutorial"], b["players"]),
        "d7": two_proportion_ztest(a["d7_retained"], a["d7_eligible"],
                                   b["d7_retained"], b["d7_eligible"]),
    }


def _fmt_test(name: str, t) -> str:
    verdict = "significant at 5%" if t.p_value < 0.05 else "not significant at 5%"
    pval = "< 0.0001" if t.p_value < 0.0001 else f"= {t.p_value:.4f}"
    return (f"- **{name}:** A {t.rate_a:.1%} vs B {t.rate_b:.1%} "
            f"(lift {t.lift:+.1%}, 95% CI for the difference {t.ci_low:+.1%} to {t.ci_high:+.1%}, "
            f"z = {t.z:.2f}, p {pval}, {verdict})\n")


def build_report(conn: sqlite3.Connection, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    quality = db.data_quality(conn)
    funnel = db.query(conn, "funnel")
    retention = db.query(conn, "retention")
    curve = db.query(conn, "retention_curve")
    exp = experiment_results(conn)

    _funnel_chart(funnel, os.path.join(out_dir, "funnel.png"))
    _retention_chart(curve, os.path.join(out_dir, "retention.png"))

    md = ["# Player analytics report\n\n"]
    md.append("## Data quality\n\n")
    md.append(_table([quality]))
    md.append("\n## Onboarding funnel\n\n")
    md.append(_table(funnel))
    md.append("\n![funnel](funnel.png)\n")
    md.append("\n## Retention\n\n")
    md.append(_table(retention))
    md.append("\n![retention](retention.png)\n")
    md.append("\n## Onboarding experiment (A = original tutorial, B = shorter tutorial)\n\n")
    md.append(_table(exp["rows"]))
    md.append("\n")
    md.append(_fmt_test("Tutorial completion (primary)", exp["tutorial"]))
    md.append(_fmt_test("D7 retention (guardrail)", exp["d7"]))

    path = os.path.join(out_dir, "report.md")
    with open(path, "w") as f:
        f.write("".join(md))
    return path
