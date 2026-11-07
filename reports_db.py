"""Reports database: every brief the agent writes, stored in SQLite.

Storage rules:
- One report per trading day (session_date).
- While the market is open, that day's report has status "intraday" and each
  new run replaces it with fresher information.
- Once the session is over, the final report is saved with status "final".
  Final reports are permanent: the database itself refuses to change or delete them.

Browse from the terminal:
    python reports_db.py list
    python reports_db.py show latest
    python reports_db.py show 2026-11-06
"""

import argparse
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("REPORTS_DB") or Path(__file__).parent / "reports.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    session_date   TEXT PRIMARY KEY,           -- trading day covered, YYYY-MM-DD
    status         TEXT NOT NULL CHECK (status IN ('intraday', 'final')),
    title          TEXT NOT NULL,
    body_md        TEXT NOT NULL,              -- the brief, in markdown
    as_of          TEXT NOT NULL,              -- '2026-11-06' (final) or '2026-11-06 12:30 ET' (intraday)
    revision       INTEGER NOT NULL DEFAULT 1, -- how many times this day's report has been written
    total_cost_usd REAL NOT NULL DEFAULT 0,    -- Claude cost of every run saved for this day
    created_at     TEXT NOT NULL,              -- UTC timestamps
    updated_at     TEXT NOT NULL,
    finalized_at   TEXT
);

CREATE TABLE IF NOT EXISTS report_tickers (
    session_date   TEXT NOT NULL REFERENCES reports(session_date),
    ticker         TEXT NOT NULL,
    category       TEXT NOT NULL CHECK (category IN ('flagged', 'quiet', 'error')),
    price          REAL,   -- last close (final) or last price (intraday)
    return_1d_pct  REAL,
    return_5d_pct  REAL,
    return_zscore  REAL,
    volume_vs_avg  REAL,
    compared_to    TEXT,
    error          TEXT,
    -- Sector and market context (flagged tickers; empty for reports saved before it existed)
    benchmark            TEXT,   -- sector ETF it was compared with, e.g. XLK (or SPY)
    benchmark_return_pct REAL,
    market_return_pct    REAL,   -- S&P 500 (SPY)
    vs_benchmark_pct     REAL,   -- ticker minus benchmark, in percentage points
    vs_benchmark_zscore  REAL,   -- how unusual that gap was
    move_read            TEXT,   -- stock-specific, sector-wide, market-wide, mixed or in line
    context_summary      TEXT,
    PRIMARY KEY (session_date, ticker)
);

CREATE TABLE IF NOT EXISTS report_sources (
    id             INTEGER PRIMARY KEY,
    session_date   TEXT NOT NULL REFERENCES reports(session_date),
    ticker         TEXT NOT NULL,
    title          TEXT,
    publisher      TEXT,
    url            TEXT,
    published      TEXT
);

CREATE INDEX IF NOT EXISTS idx_report_tickers_ticker ON report_tickers (ticker, session_date);
CREATE INDEX IF NOT EXISTS idx_report_sources_day ON report_sources (session_date, ticker);

CREATE TRIGGER IF NOT EXISTS final_reports_no_update BEFORE UPDATE ON reports
WHEN OLD.status = 'final' BEGIN SELECT RAISE(ABORT, 'final reports are permanent'); END;

CREATE TRIGGER IF NOT EXISTS final_reports_no_delete BEFORE DELETE ON reports
WHEN OLD.status = 'final' BEGIN SELECT RAISE(ABORT, 'final reports are permanent'); END;
"""

# The tickers and sources of a final report are locked too.
for _table in ("report_tickers", "report_sources"):
    for _op, _row in (("INSERT", "NEW"), ("UPDATE", "OLD"), ("DELETE", "OLD")):
        SCHEMA += f"""
CREATE TRIGGER IF NOT EXISTS {_table}_final_no_{_op.lower()} BEFORE {_op} ON {_table}
WHEN (SELECT status FROM reports WHERE session_date = {_row}.session_date) = 'final'
BEGIN SELECT RAISE(ABORT, 'final reports are permanent'); END;
"""

# Columns added after the first version. connect() adds them to older databases.
ADDED_TICKER_COLUMNS = {
    "benchmark": "TEXT", "benchmark_return_pct": "REAL", "market_return_pct": "REAL",
    "vs_benchmark_pct": "REAL", "vs_benchmark_zscore": "REAL", "move_read": "TEXT", "context_summary": "TEXT",
}

# save_report() outcomes
CREATED, UPDATED, FINALIZED = "created", "updated", "finalized"
SKIPPED_FINAL, SKIPPED_STALE = "skipped_final_exists", "skipped_older_update"


def connect(path: Path | None = None, readonly: bool = False) -> sqlite3.Connection:
    """Open the database, creating it and its tables on first use.

    readonly=True opens it so that no write is possible (used by the API).
    """
    path = Path(path or DB_PATH)
    if readonly:
        if not path.exists():
            connect(path).close()  # create an empty database first
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
    else:
        conn = sqlite3.connect(path, isolation_level=None, timeout=10)
        conn.execute("PRAGMA journal_mode = WAL")  # lets the API read while a run is writing
        conn.executescript(SCHEMA)
        _add_missing_columns(conn)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _add_missing_columns(conn) -> None:
    """Upgrade a database made by an earlier version. Existing rows (final ones included)
    are not changed: the new columns are simply empty for them."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(report_tickers)")}
    for name, kind in ADDED_TICKER_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE report_tickers ADD COLUMN {name} {kind}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_final(conn: sqlite3.Connection, session_date: str) -> bool:
    row = conn.execute("SELECT status FROM reports WHERE session_date = ?", (session_date,)).fetchone()
    return bool(row) and row["status"] == "final"


def save_report(conn, *, session_date, status, title, body_md, as_of,
                cost_usd=0.0, scan=None, sources=()) -> str:
    """Save one run's report, following the storage rules. Returns what happened.

    scan:    the flag_events result ({"flagged": [...], "quiet": [...], "errors": [...]})
    sources: news items the agent looked at, each with a "ticker" key
    """
    if status not in ("intraday", "final"):
        raise ValueError("status must be 'intraday' or 'final'")
    now = _utc_now()
    conn.execute("BEGIN IMMEDIATE")  # one writer at a time
    try:
        conn.execute("PRAGMA defer_foreign_keys = ON")  # tickers can be written before their report row
        old = conn.execute("SELECT status, as_of FROM reports WHERE session_date = ?", (session_date,)).fetchone()

        if old and old["status"] == "final":
            outcome = SKIPPED_FINAL
        elif old and status == "intraday" and as_of < old["as_of"]:
            outcome = SKIPPED_STALE
        else:
            if old:  # replace the day's intraday details
                conn.execute("DELETE FROM report_tickers WHERE session_date = ?", (session_date,))
                conn.execute("DELETE FROM report_sources WHERE session_date = ?", (session_date,))
            _insert_details(conn, session_date, scan or {}, sources)
            finalized_at = now if status == "final" else None
            if old:
                conn.execute(
                    """UPDATE reports SET status = ?, title = ?, body_md = ?, as_of = ?,
                       revision = revision + 1, total_cost_usd = total_cost_usd + ?,
                       updated_at = ?, finalized_at = ? WHERE session_date = ?""",
                    (status, title, body_md, as_of, cost_usd, now, finalized_at, session_date))
            else:
                conn.execute(
                    """INSERT INTO reports (session_date, status, title, body_md, as_of, total_cost_usd,
                       created_at, updated_at, finalized_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (session_date, status, title, body_md, as_of, cost_usd, now, now, finalized_at))
            outcome = FINALIZED if status == "final" else (UPDATED if old else CREATED)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return outcome


TICKER_COLUMNS = ("session_date", "ticker", "category", "price", "return_1d_pct", "return_5d_pct",
                  "return_zscore", "volume_vs_avg", "compared_to", "error", *ADDED_TICKER_COLUMNS)


def _insert_details(conn, session_date, scan, sources):
    rows = {}
    for category, key in (("flagged", "flagged"), ("quiet", "quiet"), ("error", "errors")):
        for m in scan.get(key) or []:
            context = m.get("context") or {}
            if "error" in context:  # comparison unavailable: keep the move, leave context empty
                context = {}
            rows[m["ticker"]] = (
                session_date, m["ticker"], category, m.get("last_close", m.get("last_price")),
                m.get("return_1d_pct"), m.get("return_5d_pct"), m.get("return_zscore"),
                m.get("volume_vs_avg"), m.get("compared_to"), m.get("error"),
                context.get("benchmark"), context.get("benchmark_return_pct"), context.get("market_return_pct"),
                context.get("vs_benchmark_pct"), context.get("vs_benchmark_zscore"), context.get("read"),
                context.get("summary"))
    conn.executemany(
        f"INSERT INTO report_tickers ({', '.join(TICKER_COLUMNS)}) VALUES ({', '.join('?' * len(TICKER_COLUMNS))})",
        rows.values())
    conn.executemany(
        """INSERT INTO report_sources (session_date, ticker, title, publisher, url, published)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [(session_date, s.get("ticker"), s.get("title"), s.get("publisher"), s.get("url"),
          None if s.get("published") is None else str(s.get("published"))) for s in sources])


# ---------------------------------------------------------------------------
# Reading (used by the API and the command line)
# ---------------------------------------------------------------------------

def list_reports(conn, limit: int = 30, before: str | None = None, status: str | None = None) -> list[dict]:
    """Report summaries, newest first. before: only days earlier than this date."""
    sql = """SELECT r.session_date, r.status, r.title, r.as_of, r.revision,
                    r.created_at, r.updated_at, r.finalized_at,
                    (SELECT COUNT(*) FROM report_tickers t
                     WHERE t.session_date = r.session_date AND t.category = 'flagged') AS flagged_count
             FROM reports r WHERE 1 = 1"""
    params = []
    if before:
        sql += " AND r.session_date < ?"
        params.append(before)
    if status:
        sql += " AND r.status = ?"
        params.append(status)
    sql += " ORDER BY r.session_date DESC LIMIT ?"
    params.append(limit)
    return [dict(row) for row in conn.execute(sql, params)]


def get_report(conn, session_date: str) -> dict | None:
    """One full report: the brief plus every ticker's figures and the news sources used."""
    row = conn.execute("SELECT * FROM reports WHERE session_date = ?", (session_date,)).fetchone()
    if row is None:
        return None
    report = dict(row)
    report["tickers"] = [_ticker_row(t) for t in conn.execute(
        """SELECT * FROM report_tickers WHERE session_date = ?
           ORDER BY CASE category WHEN 'flagged' THEN 0 WHEN 'quiet' THEN 1 ELSE 2 END, ticker""",
        (session_date,))]
    report["sources"] = [dict(s) for s in conn.execute(
        """SELECT ticker, title, publisher, url, published FROM report_sources
           WHERE session_date = ? ORDER BY ticker, id""", (session_date,))]
    return report


def _ticker_row(row) -> dict:
    """One ticker's figures. SELECT * so a database from an earlier version still reads
    (it just has no context columns yet)."""
    data = dict(row)
    data.pop("session_date", None)
    for name in ADDED_TICKER_COLUMNS:
        data.setdefault(name, None)
    return data


def latest_report(conn) -> dict | None:
    row = conn.execute("SELECT session_date FROM reports ORDER BY session_date DESC LIMIT 1").fetchone()
    return get_report(conn, row["session_date"]) if row else None


def ticker_history(conn, ticker: str, limit: int = 30) -> list[dict]:
    """One ticker's figures across days, newest first (for charts)."""
    rows = conn.execute(
        """SELECT t.*, r.status FROM report_tickers t JOIN reports r ON r.session_date = t.session_date
           WHERE t.ticker = ? ORDER BY t.session_date DESC LIMIT ?""",
        (ticker.upper(), limit))
    return [{"session_date": row["session_date"], **_ticker_row(row)} for row in rows]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Browse saved reports.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list the most recent reports")
    show = commands.add_parser("show", help="print one report")
    show.add_argument("date", nargs="?", default="latest", help="YYYY-MM-DD or 'latest'")
    args = parser.parse_args()

    conn = connect(readonly=True)
    if args.command == "list":
        for r in list_reports(conn, limit=50):
            print(f"{r['session_date']}  {r['status']:<8}  rev {r['revision']:<3} "
                  f"{r['flagged_count']} flagged  {r['title']}")
    else:
        report = latest_report(conn) if args.date == "latest" else get_report(conn, args.date)
        print(report["body_md"] if report else "No report found.")
