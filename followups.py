"""Follow-through: what the price did after each flagged move, 1, 5 and 20 trading days later.

Every move flagged in a final report gets a follow-up. The prices come from Yahoo Finance
(free), so keeping follow-ups current costs nothing. They're filled in after each final
report is saved, and by "Refresh prices" on the Follow-through tab.

Each move is judged at each horizon by how much of it the price gave back:
- held:     gave back less than a quarter of the move (or kept going)
- faded:    gave back between a quarter and all of it
- reversed: gave back all of it or more (the price is back past where it started)

A move is a surprise if, a week (5 trading days) later, it had reversed, or kept going by as
much again. Surprises get an automatic news check (see stories.py).

From the terminal:
    python followups.py update        fill in follow-ups now
    python followups.py list          the latest moves and how they played out
    python followups.py patterns      how moves of each kind played out
"""

import argparse
import re
import statistics
from contextlib import closing
from datetime import date, datetime, timedelta, timezone

import market_tools
import prices
import reports_db
from events import transaction

HORIZONS = (1, 5, 20)            # trading days after the move
SURPRISE_HORIZON = 5             # when a move is judged a surprise (and its news re-checked)
HELD_UP_TO = 0.25                # giving back up to this much of the move still counts as held
MIN_FOR_PATTERN = 5              # fewer settled moves than this: "too few to tell"
PERIODS = ((28, "1mo"), (88, "3mo"), (178, "6mo"), (360, "1y"), (725, "2y"), (1820, "5y"))  # Yahoo history to ask for
EARNINGS_WORDS = re.compile(r"\b(earnings|quarterly|results|guidance|revenue|profit|eps)\b", re.I)
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")

KIND_LABELS = {"stock-specific": "Stock-specific", "sector-wide": "Sector-wide", "market-wide": "Market-wide",
               "mixed": "Mixed", "in line": "In line with its sector", None: "Not compared"}
REASON_LABELS = {"earnings": "Earnings", "news": "Other news", "none": "No clear reason"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS followups (
    session_date TEXT NOT NULL,         -- the day of the flagged move (from its final report)
    ticker       TEXT NOT NULL,
    move_pct     REAL NOT NULL,         -- that day's move
    move_read    TEXT,                  -- stock-specific, sector-wide, market-wide, mixed or in line
    reason       TEXT NOT NULL CHECK (reason IN ('earnings', 'news', 'none')),
    why          TEXT,                  -- the brief's "Likely why" line
    after_1d     REAL,                  -- % change from that day's close to the close N trading days later
    after_5d     REAL,
    after_20d    REAL,
    surprise     INTEGER NOT NULL DEFAULT 0,
    note         TEXT,                  -- why prices are missing, if they are
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (session_date, ticker)
);
CREATE TABLE IF NOT EXISTS followup_updates (
    id           INTEGER PRIMARY KEY,
    finished_at  TEXT NOT NULL,
    trigger      TEXT NOT NULL,
    status       TEXT NOT NULL,         -- ok or partial
    added        INTEGER NOT NULL,
    updated      INTEGER NOT NULL,
    new_surprises INTEGER NOT NULL,
    message      TEXT
);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect():
    """The reports database, with the follow-up tables added if they're missing."""
    conn = reports_db.connect()
    conn.executescript(SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Judging a move
# ---------------------------------------------------------------------------

def give_back(move_pct: float, after_pct: float) -> float:
    """How much of the move the price gave back: 0 = none, 1 = all of it, below 0 = it kept going.
    Rounded to 2 places, so a price exactly back where it started counts as all of it."""
    m, a = move_pct / 100, after_pct / 100
    return round(-a * (1 + m) / m, 2) if m else 0.0


def outcome(move_pct: float, after_pct: float | None) -> str | None:
    """held, faded or reversed (None until that horizon's price is known)."""
    if after_pct is None:
        return None
    g = give_back(move_pct, after_pct)
    return "reversed" if g >= 1 else "faded" if g > HELD_UP_TO else "held"


def follow(move_pct: float, after_pct: float | None) -> float | None:
    """The price change after the move, counted in the move's direction (+ means it kept going)."""
    return None if after_pct is None else round(after_pct if move_pct >= 0 else -after_pct, 2)


def is_surprise(move_pct: float, after_5d: float | None) -> bool:
    """Reversed within a week, or kept going by as much again."""
    if after_5d is None:
        return False
    g = give_back(move_pct, after_5d)
    return g >= 1 or g <= -1


def surprise_kind(move_pct: float, after_5d: float | None) -> str | None:
    if not is_surprise(move_pct, after_5d):
        return None
    return "reversed within a week" if give_back(move_pct, after_5d) >= 1 else "kept going: as much again within a week"


# ---------------------------------------------------------------------------
# Finding the flagged moves
# ---------------------------------------------------------------------------

def likely_why(body_md: str, ticker: str) -> str | None:
    """The brief's "Likely why" line for a ticker, as plain text."""
    section = re.search(rf"(?ms)^### {re.escape(ticker)}\b.*?(?=^#{{1,3}} |\Z)", body_md or "")
    if not section:
        return None
    line = re.search(r"(?m)^- \*\*Likely why:\*\*\s*(.+)$", section.group(0))
    return MARKDOWN_LINK.sub(r"\1", line.group(1)).strip() if line else None


def reason_for(why: str | None, earnings_day: bool) -> str:
    if why and "no clear catalyst" in why.lower():
        return "earnings" if earnings_day else "none"
    if earnings_day or (why and EARNINGS_WORDS.search(why)):
        return "earnings"
    return "news" if why else "none"


def _earnings_days(conn) -> set[tuple[str, str]]:
    """(ticker, day) for each earnings date on the events calendar."""
    try:
        return {(r[0], r[1]) for r in conn.execute("SELECT ticker, event_date FROM events WHERE kind = 'earnings'")}
    except Exception:  # no calendar yet
        return set()


def _add_new(conn) -> int:
    """A follow-up for each move flagged in a final report that doesn't have one yet."""
    rows = conn.execute(
        """SELECT t.session_date, t.ticker, t.return_1d_pct, t.move_read, r.body_md
           FROM report_tickers t JOIN reports r ON r.session_date = t.session_date
           LEFT JOIN followups f ON f.session_date = t.session_date AND f.ticker = t.ticker
           WHERE r.status = 'final' AND t.category = 'flagged' AND t.return_1d_pct IS NOT NULL
             AND f.ticker IS NULL""").fetchall()
    earnings = _earnings_days(conn)
    now = _utc_now()
    for r in rows:
        day = date.fromisoformat(r["session_date"])
        near = {(r["ticker"], (day - timedelta(days=d)).isoformat()) for d in range(0, 4)}  # reported before or on the day
        why = likely_why(r["body_md"], r["ticker"])
        conn.execute("""INSERT INTO followups (session_date, ticker, move_pct, move_read, reason, why, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (r["session_date"], r["ticker"], r["return_1d_pct"], r["move_read"],
                      reason_for(why, bool(near & earnings)), why, now))
    return len(rows)


# ---------------------------------------------------------------------------
# Filling in prices
# ---------------------------------------------------------------------------

def last_complete_session() -> date:
    """The latest trading day whose close is known. The test environment replaces this."""
    session = market_tools.market_session()
    if session["status"] == "complete":
        return date.fromisoformat(session["as_of"])
    return date.fromisoformat(session["as_of"][:10]) - timedelta(days=1)  # today's isn't finished


def fetch_closes(ticker: str, since: date, last: date) -> list[tuple[str, float]]:
    """(day, close) from Yahoo, oldest first, from at least `since` up to the latest close."""
    days = (last - since).days + 10
    period = next((p for limit, p in PERIODS if days <= limit), PERIODS[-1][1])
    return [(row["date"], row["close"]) for row in prices.fetch_prices(ticker, period)]


def update(trigger: str = "command line", emit=None) -> dict:
    """Add follow-ups for newly flagged moves and fill in prices that are now known. Free (Yahoo only).
    Returns a summary, including the moves that just became surprises."""
    emit = emit or (lambda event: None)
    last = last_complete_session()
    problems, updated, surprises = [], 0, []
    with closing(connect()) as conn:
        with transaction(conn):
            added = _add_new(conn)
        pending = conn.execute("SELECT * FROM followups WHERE after_20d IS NULL ORDER BY ticker, session_date").fetchall()
        by_ticker: dict[str, list] = {}
        for row in pending:
            by_ticker.setdefault(row["ticker"], []).append(row)
        for ticker, rows in by_ticker.items():
            emit({"type": "progress", "message": f"Following up on {ticker}'s flagged moves"})
            try:
                closes = [(d, c) for d, c in fetch_closes(ticker, date.fromisoformat(rows[0]["session_date"]), last)
                          if date.fromisoformat(d) <= last]
            except Exception as e:  # one ticker failing doesn't stop the rest
                problems.append(f"{ticker}: {e}")
                continue
            index = {d: i for i, (d, _) in enumerate(closes)}
            done, found = 0, []
            try:
                with transaction(conn):
                    for row in rows:
                        i = index.get(row["session_date"])
                        base = closes[i][1] if i is not None else None
                        if not base or base <= 0:  # missing, or a broken price (Yahoo sometimes has 0)
                            conn.execute("UPDATE followups SET note = ? WHERE session_date = ? AND ticker = ?",
                                         ("no Yahoo price for that day", row["session_date"], ticker))
                            continue
                        after = {n: round((closes[i + n][1] / base - 1) * 100, 2) if i + n < len(closes) else None
                                 for n in HORIZONS}
                        old = {n: row[f"after_{n}d"] for n in HORIZONS}
                        if after == old:
                            continue
                        surprise = is_surprise(row["move_pct"], after[SURPRISE_HORIZON])
                        if surprise and not row["surprise"]:
                            found.append({"session_date": row["session_date"], "ticker": ticker})
                        conn.execute(f"""UPDATE followups SET {', '.join(f'after_{n}d = ?' for n in HORIZONS)},
                                         surprise = ?, note = NULL, updated_at = ? WHERE session_date = ? AND ticker = ?""",
                                     (*after.values(), int(surprise), _utc_now(), row["session_date"], ticker))
                        done += 1
            except Exception as e:  # this stock's changes are rolled back; the rest carry on
                problems.append(f"{ticker}: {e}")
                continue
            updated += done
            surprises += found
        status = "partial" if problems else "ok"
        message = "; ".join(problems)[:1000] or None
        conn.execute("""INSERT INTO followup_updates (finished_at, trigger, status, added, updated, new_surprises, message)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""", (_utc_now(), trigger, status, added, updated, len(surprises), message))
        summary = last_update(conn)
    summary["surprises"] = surprises
    return summary


# ---------------------------------------------------------------------------
# Reading (the API, Ask and the agent's past_moves tool)
# ---------------------------------------------------------------------------

def last_update(conn) -> dict | None:
    try:
        row = conn.execute("SELECT * FROM followup_updates ORDER BY id DESC LIMIT 1").fetchone()
    except Exception:  # not set up yet
        return None
    return dict(row) if row else None


def _move(row, story=None) -> dict:
    m = dict(row)
    m["direction"] = "up" if m["move_pct"] >= 0 else "down"
    m["kind"] = KIND_LABELS.get(m["move_read"], m["move_read"])
    m["reason_label"] = REASON_LABELS[m["reason"]]
    m["outcomes"] = {str(n): outcome(m["move_pct"], m[f"after_{n}d"]) for n in HORIZONS}
    m["follow"] = {str(n): follow(m["move_pct"], m[f"after_{n}d"]) for n in HORIZONS}
    m["settled"] = m[f"after_{HORIZONS[-1]}d"] is not None
    m["surprise_kind"] = surprise_kind(m["move_pct"], m[f"after_{SURPRISE_HORIZON}d"])
    m["surprise"] = bool(m["surprise"])
    m["story"] = story
    return m


def moves(conn, ticker: str | None = None, since: str | None = None, limit: int = 500) -> list[dict]:
    """Flagged moves, newest first, with how they played out and their latest story update."""
    try:
        rows = conn.execute(
            f"""SELECT * FROM followups WHERE 1 = 1{' AND ticker = ?' if ticker else ''}{' AND session_date >= ?' if since else ''}
                ORDER BY session_date DESC, ticker LIMIT ?""",
            [p for p in (ticker and ticker.upper(), since) if p] + [limit]).fetchall()
    except Exception:  # not set up yet
        return []
    stories = _latest_stories(conn)
    return [_move(r, stories.get((r["session_date"], r["ticker"]))) for r in rows]


def _latest_stories(conn) -> dict:
    try:
        rows = conn.execute("""SELECT session_date, ticker, verdict, update_text, finished_at, status FROM story_checks
                               WHERE status IN ('ok', 'no_news') ORDER BY id""").fetchall()
    except Exception:  # no story checks yet
        return {}
    return {(r["session_date"], r["ticker"]): {"verdict": r["verdict"], "update": r["update_text"],
                                                 "checked_at": r["finished_at"], "status": r["status"]} for r in rows}


def _group(label: str, found: list[dict], horizon: int) -> dict:
    judged = [m for m in found if m["outcomes"][str(horizon)]]
    counts = {k: sum(m["outcomes"][str(horizon)] == k for m in judged) for k in ("held", "faded", "reversed")}
    follows = [m["follow"][str(horizon)] for m in judged]
    return {"label": label, "moves": len(found), "judged": len(judged), **counts,
            "median_follow_pct": round(statistics.median(follows), 2) if follows else None,
            "enough": len(judged) >= MIN_FOR_PATTERN}


def patterns(all_moves: list[dict], horizon: int) -> dict:
    """How flagged moves played out `horizon` trading days later, grouped three ways."""
    def by(key, labels):
        groups = {}
        for m in all_moves:
            groups.setdefault(m[key], []).append(m)
        order = list(labels)
        return [_group(labels.get(k, k), groups[k], horizon)
                for k in sorted(groups, key=lambda k: order.index(k) if k in order else len(order))]
    return {"horizon": horizon, "all": _group("All flagged moves", all_moves, horizon),
            "by_kind": by("move_read", KIND_LABELS), "by_reason": by("reason", REASON_LABELS),
            "by_direction": by("direction", {"up": "Up moves", "down": "Down moves"})}


def describe_group(g: dict, horizon: int) -> str:
    when = {1: "the next day", 5: "a week later", 20: "a month later"}.get(horizon, f"{horizon} trading days later")
    if not g["judged"]:
        return f"{g['label']}: no moves to judge yet"
    return (f"{g['label']}: {g['held']} of {g['judged']} held {when}, {g['faded']} faded, {g['reversed']} reversed"
            + ("" if g["enough"] else " (too few to tell)"))


def past_for(conn, ticker: str, move_read: str | None, horizon: int = SURPRISE_HORIZON) -> dict:
    """For the brief: how this stock's earlier flagged moves, and moves of the same kind, played out."""
    every = moves(conn)
    mine = [m for m in every if m["ticker"] == ticker.upper()]
    same = [m for m in every if m["move_read"] == move_read] if move_read else []
    mine_g = _group(f"{ticker.upper()}'s flagged moves", mine, horizon)
    same_g = _group(f"{KIND_LABELS.get(move_read, move_read)} moves across the watchlist", same, horizon)
    lines = [describe_group(g, horizon) for g in (mine_g, same_g) if g["judged"]]
    last = next((m for m in mine if m["outcomes"][str(horizon)]), None)
    result = {"ticker": ticker.upper(), "horizon_days": horizon, "this_stock": mine_g,
              "same_kind": same_g if move_read else None,
              "last_move": None if last is None else {
                  "date": last["session_date"], "move_pct": last["move_pct"],
                  f"after_{horizon}d_pct": last[f"after_{horizon}d"], "outcome": last["outcomes"][str(horizon)]},
              "latest_story": mine[0]["story"] if mine and mine[0]["story"] else None,
              "summary": "; ".join(lines) or None,
              "worth_mentioning": mine_g["enough"] or same_g["enough"]}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Follow-through: what happened after each flagged move.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("update", help="fill in follow-ups now (Yahoo only, free)")
    show = commands.add_parser("list", help="the latest moves and how they played out")
    show.add_argument("--ticker")
    pat = commands.add_parser("patterns", help="how moves of each kind played out")
    pat.add_argument("--days", type=int, default=SURPRISE_HORIZON, choices=HORIZONS)
    args = parser.parse_args()
    if args.command == "update":
        result = update(emit=lambda e: print(e["message"]))
        print(f"{result['status']}: {result['added']} new moves, {result['updated']} updated, "
              f"{result['new_surprises']} new surprises" + (f" ({result['message']})" if result["message"] else ""))
        return
    with closing(reports_db.connect(readonly=True)) as conn:
        found = moves(conn, args.ticker if args.command == "list" else None)
    if args.command == "list":
        for m in found[:40]:
            after = "  ".join(f"{n}d {m[f'after_{n}d']:+.2f}%" if m[f"after_{n}d"] is not None else f"{n}d   …   "
                              for n in HORIZONS)
            print(f"{m['session_date']}  {m['ticker']:<6} {m['move_pct']:+7.2f}%  {after}  "
                  f"{m['outcomes'][str(SURPRISE_HORIZON)] or 'pending':<9} {m['reason_label']}"
                  + ("  SURPRISE" if m["surprise"] else ""))
    else:
        result = patterns(found, args.days)
        for g in [result["all"], *result["by_kind"], *result["by_reason"], *result["by_direction"]]:
            print(describe_group(g, args.days))


if __name__ == "__main__":
    main()
