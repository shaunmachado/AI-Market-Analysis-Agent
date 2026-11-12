"""Company filings: what your tracked companies file with the SEC, and a first take on each.

check() asks the SEC (free, see edgar.py) for each tracked company's new filings: results
announcements, other announcements (8-K), quarterly and annual reports, and notices that a
report will be late. Listing them costs nothing.

read() gives one filing to Claude and saves a first take: a headline, the key points, and for
results the reported figures, guidance, and what changed since the last announcement. Every
point carries a quote, and the quote is checked against the filing in code: anything Claude
can't quote exactly is dropped. Figures are never worked out by Claude. It copies each number
as written; the comparisons with earlier quarters use the SEC's structured data, in code.

- Automatic: a results announcement is read when it's found (if filed in the last 3 days).
- On request: any other filing, from the Filings tab ("Read this filing") or the terminal.
- When the quarterly or annual report arrives, its structured figures are compared with the
  announcement's, and each one is marked confirmed or different. That part is free.

    python filings.py check                          look for new filings now
    python filings.py list [--ticker MSFT]           the latest filings
    python filings.py read 0000789019-26-000123      read one filing now (costs a few cents)
    python filings.py show 0000789019-26-000123      a filing's first take
    python filings.py figures MSFT                   quarterly figures from the SEC's structured data
"""

import argparse
import asyncio
import json
import re
import sys
from contextlib import closing
from datetime import date, datetime, timedelta, timezone

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

import alerts
import edgar
import events
import market_tools
import reports_db
from events import transaction

LOOKBACK_DAYS = 120           # how far back filings are listed (far enough for last quarter's results)
AUTOMATIC_WITHIN_DAYS = 3     # only results this recent are read automatically, and only filings this recent go to Discord
MAX_AUTOMATIC = 5             # most automatic reads in one check
READ_BUDGET_USD = 0.50        # hard stop on Claude's cost per read
MAX_CHARS = 60_000            # the most of a filing Claude is given (about 15,000 tokens)
PREVIOUS_CHARS = 20_000       # ...and of the previous results announcement, for comparison
COVER_CHARS = 12_000          # ...and of an announcement's cover document, before its press release
MAX_POINTS = 6
MIN_QUOTE = 12                # a quote shorter than this proves nothing
FIGURES_WITHIN_DAYS = 45      # how long a report's structured figures are looked for after it's filed
FILER_RECHECK_DAYS = 30       # how often to ask again about a ticker the SEC didn't know
STUCK_AFTER = timedelta(minutes=10)  # a "running" read older than this is treated as crashed
UNREACHABLE_LIMIT = 2         # companies in a row that can't be reached before a check gives up

FORMS = {"8-K": "announcement", "10-Q": "quarterly", "10-K": "annual", "NT 10-Q": "late", "NT 10-K": "late",
         "6-K": "foreign", "20-F": "annual", "40-F": "annual"}
KIND_LABELS = {"results": "Results", "announcement": "Announcement", "quarterly": "Quarterly report",
               "annual": "Annual report", "late": "Late-report notice", "foreign": "Report from outside the US"}
# What each part ("item") of an announcement means, in plain words
ITEMS = {
    "1.01": "A major agreement signed", "1.02": "A major agreement ended", "1.03": "Bankruptcy or receivership",
    "1.05": "A serious cybersecurity incident", "2.01": "An acquisition or sale completed", "2.02": "Results announced",
    "2.03": "New debt or a similar obligation", "2.04": "An event that brings a debt due early",
    "2.05": "Restructuring or closures, with their costs", "2.06": "A large write-down of assets",
    "3.01": "A warning about staying listed on its exchange", "3.02": "Shares sold privately",
    "3.03": "Shareholders' rights changed", "4.01": "A change of auditor",
    "4.02": "Earlier financial statements can no longer be relied on", "5.01": "A change in who controls the company",
    "5.02": "Directors or senior officers leaving or appointed", "5.03": "Changes to its bylaws or financial year",
    "5.07": "Results of a shareholder vote", "7.01": "Information shared with investors", "8.01": "Other events",
    "9.01": "Financial statements and exhibits",
}
# Announcements worth a second look, highlighted in the list and sent to Discord (without Claude)
SERIOUS_ITEMS = {"1.03", "1.05", "2.01", "2.04", "2.05", "2.06", "3.01", "4.01", "4.02", "5.01", "5.02"}
DIRECTIONS = {"raised": "Raised", "lowered": "Lowered", "maintained": "Kept", "new": "New", "withdrawn": "Withdrawn"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS filers (
    ticker     TEXT PRIMARY KEY,
    cik        INTEGER,              -- the SEC's number for the company; NULL if it lists none (a fund, say)
    name       TEXT,
    checked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS filings (
    ticker      TEXT NOT NULL,
    accession   TEXT NOT NULL,       -- the SEC's number for the filing, e.g. 0000789019-26-000123
    cik         INTEGER NOT NULL,
    form        TEXT NOT NULL,       -- 8-K, 10-Q, 10-K, NT 10-Q, 6-K... (with /A if amended)
    items       TEXT NOT NULL DEFAULT '',   -- an announcement's parts, e.g. "2.02,9.01"
    kind        TEXT NOT NULL CHECK (kind IN ('results', 'announcement', 'quarterly', 'annual', 'late', 'foreign')),
    title       TEXT NOT NULL,
    serious     INTEGER NOT NULL DEFAULT 0,
    amended     INTEGER NOT NULL DEFAULT 0,
    filed_at    TEXT NOT NULL,       -- when the SEC accepted it (UTC)
    filing_date TEXT NOT NULL,       -- the SEC's filing date (New York)
    report_date TEXT,                -- reports: the last day of the period they cover
    primary_doc TEXT,
    figures     TEXT,                -- reports: figures from the SEC's structured data (JSON)
    first_seen  TEXT NOT NULL,
    PRIMARY KEY (ticker, accession)
);
CREATE INDEX IF NOT EXISTS idx_filings_filed ON filings (filed_at);
CREATE TABLE IF NOT EXISTS filing_reads (
    id           INTEGER PRIMARY KEY,
    accession    TEXT NOT NULL,
    ticker       TEXT NOT NULL,
    trigger      TEXT NOT NULL CHECK (trigger IN ('automatic', 'manual')),
    status       TEXT NOT NULL CHECK (status IN ('running', 'ok', 'failed')),
    headline     TEXT,
    points       TEXT,               -- JSON: [{text, quote}]
    guidance     TEXT,               -- JSON: [{text, direction, quote}]
    changes      TEXT,               -- JSON: [{text, quote}]: what's new since the previous announcement
    figures      TEXT,               -- JSON: the reported figures, compared and checked in code
    notes        TEXT,               -- JSON: plain sentences about anything left out or cut short
    document     TEXT,               -- the document that was read
    document_url TEXT,
    chars        INTEGER NOT NULL DEFAULT 0,
    cut_off      INTEGER NOT NULL DEFAULT 0,
    cost_usd     REAL NOT NULL DEFAULT 0,
    error        TEXT,
    started_at   TEXT NOT NULL,
    finished_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_filing_reads ON filing_reads (accession);
CREATE TABLE IF NOT EXISTS filing_checks (
    id          INTEGER PRIMARY KEY,
    finished_at TEXT NOT NULL,
    trigger     TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('ok', 'partial', 'failed')),
    companies   INTEGER NOT NULL DEFAULT 0,
    new_filings INTEGER NOT NULL DEFAULT 0,
    reads       INTEGER NOT NULL DEFAULT 0,
    cost_usd    REAL NOT NULL DEFAULT 0,
    message     TEXT
);
CREATE TABLE IF NOT EXISTS filing_alerts (
    accession  TEXT PRIMARY KEY,
    what       TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('pending', 'sent', 'failed')),
    error      TEXT,
    created_at TEXT NOT NULL,
    sent_at    TEXT
);
"""

RULES = """
Rules:
- Reply with JSON only, in the shape shown.
- Every "quote" must be copied exactly from the FILING TEXT (one sentence, or one table row), so it can be
  checked. Anything you can't quote exactly, leave out.
- Use only the filing. Never add outside knowledge, explain the share price, predict anything or give advice.
- Write plainly, in short sentences."""

RESULTS_PROMPT = """You read a company's results announcement and write a first take for an analyst.

Reply in this shape:
{"headline": "One sentence: what the company reported.",
 "period_end": "2026-09-30",
 "figures": [{"metric": "revenue", "as_written": "77,673", "scale": "millions", "quote": "Total revenue | $77,673 | $65,585"}],
 "points": [{"text": "A key point.", "quote": "The exact words it's based on."}],
 "guidance": [{"text": "What the company said about the period ahead.", "direction": "raised", "quote": "..."}],
 "changes": [{"text": "Something new, or dropped, compared with the previous announcement.", "quote": "..."}]}

- period_end: the last day of the quarter reported.
- figures: only these metrics, when the filing gives them: revenue, gross_profit, operating_income, net_income,
  eps_diluted. Use the standard (GAAP) figure for the quarter alone: three months, not the year to date, and
  not an "adjusted" or "non-GAAP" figure. "as_written" is the number exactly as it appears in your quote.
  "scale" is units, thousands, millions or billions (tables usually say, e.g. "in millions"). eps_diluted is always units.
  Never work anything out: no growth rates, margins or totals of your own.
- points: 3 to 6, most important first.
- guidance: one entry per outlook the company gives. direction is raised, lowered, maintained, new or withdrawn,
  compared with what it said before. Use [] if it gives none.
- changes: only if a PREVIOUS ANNOUNCEMENT is given. Quote from the new filing, never from the previous one. Use [] otherwise.""" + RULES

ANNOUNCEMENT_PROMPT = """You read a company's announcement filed with the SEC and write a first take for an analyst.

Reply in this shape:
{"headline": "One sentence: what the company announced.",
 "points": [{"text": "A key point.", "quote": "The exact words it's based on."}]}

- points: 1 to 5, most important first: what happened, who and when, and any amounts the filing gives.""" + RULES

REPORT_PROMPT = """You read management's discussion from a company's quarterly or annual report and write a first take
for an analyst who has already seen the headline figures.

Reply in this shape:
{"headline": "One sentence: the most important thing the report adds.",
 "points": [{"text": "A key point.", "quote": "The exact words it's based on."}]}

- points: 3 to 6, most important first: what drove the results, costs, cash, risks, and anything management
  says has changed.""" + RULES


def _options(system_prompt: str) -> ClaudeAgentOptions:
    from run_brief import AGENT_ENV  # same auth as the report runs: the project's API key, if set (imported here:
                                     # run_brief imports this module)
    return ClaudeAgentOptions(system_prompt=system_prompt, mcp_servers={}, strict_mcp_config=True, tools=[],
                              max_turns=1, max_budget_usd=READ_BUDGET_USD, env=AGENT_ENV)


class FilingError(ValueError):
    """Something that can't be done, with a message to show as it is. status is the HTTP status."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def now_utc() -> datetime:
    """Now, by the same clock as the rest of the program. The test environment replaces this with the sample's."""
    return market_tools.now_et().astimezone(timezone.utc)


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now() -> str:
    return _stamp(now_utc())


def _days_ago(days: int) -> str:
    return _stamp(now_utc() - timedelta(days=days))


def connect():
    """The reports database, with the filings tables added if they're missing."""
    conn = events.connect()
    conn.executescript(SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Naming a filing
# ---------------------------------------------------------------------------

def describe(form: str, items: list[str]) -> dict | None:
    """What kind of filing this is, in plain words. None for forms that aren't followed."""
    form = " ".join(str(form).upper().split())
    amended = form.endswith("/A")
    base = form[:-2] if amended else form
    kind = FORMS.get(base)
    if kind is None:
        return None
    others = [ITEMS.get(i, f"Item {i}") for i in items if i not in ("2.02", "9.01")]
    if kind == "announcement" and "2.02" in items:
        kind, title = "results", "; ".join(["Results announcement", *others])
    elif kind == "announcement":
        title = "; ".join(others) or "Announcement"
    elif kind == "late":
        title = f"Says its {'annual' if base.endswith('10-K') else 'quarterly'} report will be late"
    else:
        title = {"quarterly": "Quarterly report", "annual": "Annual report",
                 "foreign": "Report from a company based outside the US"}[kind]
    return {"kind": kind, "amended": amended, "title": ("Amended: " if amended else "") + title,
            "serious": kind == "late" or bool(SERIOUS_ITEMS & set(items))}


def money(value: float | None, unit: str = "USD") -> str:
    """$77.67B, $420.5M, $3.72 a share."""
    if value is None:
        return "—"
    sign, size = ("-" if value < 0 else ""), abs(value)
    if unit != "USD":
        return f"{sign}${size:.2f}"
    if size >= 1e9 or f"{size / 1e6:.1f}" == "1000.0":  # $999.96M rounds to a billion: not "$1000.0M"
        return f"{sign}${size / 1e9:.2f}B"
    if size >= 1e6 or f"{size:.0f}" == "1000000":
        return f"{sign}${size / 1e6:.1f}M"
    return f"{sign}${size:,.0f}"


def _company(conn, ticker: str) -> str:
    """A short company name without asking Yahoo: the calendar's, else the SEC's."""
    if ticker in events._names:
        return events._names[ticker]
    try:
        row = conn.execute("SELECT company FROM events WHERE ticker = ? ORDER BY id DESC LIMIT 1", (ticker,)).fetchone()
        if row:
            return row[0]
    except Exception:
        pass
    try:
        row = conn.execute("SELECT name FROM filers WHERE ticker = ?", (ticker,)).fetchone()
    except Exception:
        row = None
    return events.short_name((row["name"] or "").title()) if row and row["name"] else ticker


# ---------------------------------------------------------------------------
# Figures: comparing and checking, all in code
# ---------------------------------------------------------------------------

def _change(now: float | None, then: float | None) -> float | None:
    """Percentage change, or None when it would mislead (from zero or from a loss)."""
    if now is None or then is None or then <= 0:
        return None
    return round((now - then) / then * 100, 1)


def _earlier(by_end: dict, period_end: date, days: int) -> dict | None:
    found = edgar.nearest(by_end, period_end - timedelta(days=days))
    return None if found is None else {"end": found["end"].isoformat(), "value": found["value"], "derived": found["derived"]}


def agrees(metric: str, announced: float, reported: float) -> bool:
    """Do an announcement's figure and the report's match? Announcements round (to the million, or to a
    tenth of a billion in a sentence), so a small gap is allowed."""
    if edgar.METRICS[metric]["unit"] != "USD":
        return abs(announced - reported) <= 0.011
    return abs(announced - reported) <= max(abs(reported) * 0.006, 600_000)


def _margins(rows: list[dict]) -> list[dict]:
    """Each profit line as a share of revenue, for this period and the ones it's compared with."""
    by_metric = {r["metric"]: r for r in rows}
    revenue = by_metric.get("revenue")
    margins = []
    for metric, label in (("gross_profit", "Gross margin"), ("operating_income", "Operating margin"), ("net_income", "Net margin")):
        row = by_metric.get(metric)
        if not revenue or not row:
            continue

        def share(part, whole):
            return round(part / whole * 100, 1) if part is not None and whole else None
        margins.append({"label": label, "value": share(row["value"], revenue["value"]),
                        "prior": share((row["prior"] or {}).get("value"), (revenue["prior"] or {}).get("value")),
                        "year_ago": share((row["year_ago"] or {}).get("value"), (revenue["year_ago"] or {}).get("value"))})
    return [m for m in margins if m["value"] is not None]


def compare(reported: list[dict], period_end: date | None, known: dict, notes: list[str]) -> dict:
    """An announcement's figures next to earlier quarters from the SEC's structured data, and checked
    against the quarterly report's own figure if that's already filed."""
    rows = []
    for r in reported:
        metric, spec = r["metric"], edgar.METRICS[r["metric"]]
        quarters = (known.get(metric) or {}).get("quarters") or {}
        row = {"metric": metric, "label": spec["label"], "unit": spec["unit"], "value": r["value"],
               "as_written": r["as_written"], "scale": r["scale"], "quote": r["quote"],
               "prior": None, "year_ago": None, "change_prior_pct": None, "change_year_pct": None,
               "check": "pending", "report_value": None}
        if period_end:
            row["prior"], row["year_ago"] = _earlier(quarters, period_end, 91), _earlier(quarters, period_end, 365)
            nearby = row["prior"] or row["year_ago"]
            if spec["unit"] == "USD" and nearby and nearby["value"] > 0 and r["value"] > 0 \
                    and not 0.05 <= r["value"] / nearby["value"] <= 20:
                notes.append(f"{spec['label']} was left out: {r['as_written']} {r['scale']} doesn't fit with "
                             f"{money(nearby['value'])} in the quarter to {nearby['end']}, so the unit is probably wrong.")
                continue
            row["change_prior_pct"] = _change(r["value"], (row["prior"] or {}).get("value"))
            row["change_year_pct"] = _change(r["value"], (row["year_ago"] or {}).get("value"))
        rows.append(row)
    result = {"basis": "quarter", "source": "announcement", "period_end": period_end.isoformat() if period_end else None,
              "rows": rows, "margins": _margins(rows)}
    if period_end:
        confirm(result, known)
    return result


def confirm(figures: dict, known: dict) -> bool:
    """Mark each announced figure confirmed or different, once the report's own figure is known.
    Returns True if anything changed."""
    if not figures or figures.get("source") != "announcement" or not figures.get("period_end"):
        return False
    period_end, changed = date.fromisoformat(figures["period_end"]), False
    for row in figures["rows"]:
        if row["check"] != "pending":
            continue
        filed = edgar.nearest((known.get(row["metric"]) or {}).get("quarters") or {}, period_end, 7)
        if filed is None:
            continue
        if filed["derived"] and row["unit"] != "USD":
            row["check"] = "not_checked"  # a fourth quarter's earnings per share can't be worked out exactly
        else:
            row["check"] = "confirmed" if agrees(row["metric"], row["value"], filed["value"]) else "differs"
            row["report_value"] = filed["value"]
        changed = True
    return changed


def report_figures(known: dict, period_end: date, annual: bool) -> dict | None:
    """A quarterly or annual report's own figures, with the periods before. None if they aren't published yet."""
    rows = []
    for metric, spec in edgar.METRICS.items():
        by_end = (known.get(metric) or {}).get("years" if annual else "quarters") or {}
        now = edgar.nearest(by_end, period_end, 7)
        if now is None or (now["derived"] and not annual):
            continue
        prior = None if annual else _earlier(by_end, period_end, 91)
        year_ago = _earlier(by_end, period_end, 365)
        rows.append({"metric": metric, "label": spec["label"], "unit": spec["unit"], "value": now["value"],
                     "prior": prior, "year_ago": year_ago, "change_prior_pct": _change(now["value"], (prior or {}).get("value")),
                     "change_year_pct": _change(now["value"], (year_ago or {}).get("value")), "check": "report"})
    if not rows:
        return None
    return {"basis": "year" if annual else "quarter", "source": "report", "period_end": period_end.isoformat(),
            "rows": rows, "margins": _margins(rows)}


# ---------------------------------------------------------------------------
# Checking Claude's reply against the filing
# ---------------------------------------------------------------------------

def _plain(text: str) -> str:
    return " ".join(edgar.tidy(str(text)).replace("|", " ").lower().split())


def quoted(quote, document: str) -> bool:
    """Is this quote really in the document? `document` is already _plain(). A quote may skip words
    with "...", as long as each piece is there, in order."""
    pieces = [p.strip(" .") for p in re.split(r"\.\.\.|…", _plain(quote or ""))]
    pieces = [p for p in pieces if p]
    if not pieces or sum(len(p) for p in pieces) < MIN_QUOTE:
        return False
    at = 0
    for piece in pieces:
        at = document.find(piece, at)
        if at < 0:
            return False
        at += len(piece)
    return True


def _number_in(written: str, quote: str) -> bool:
    """Is the number, exactly as written, in the quote as a whole number? Not a part of a longer one
    ("2,281" in "$92,281", "4.9" in "$4.92"), and not without the brackets that make it a loss there."""
    number, row = written.replace(" ", ""), quote.replace(" ", "")
    return re.search(rf"(?<![\d.,(])(?<!\(\$){re.escape(number)}(?!\d|[.,]\d)", row) is not None


def _json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Claude's reply had no JSON in it")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("Claude's reply wasn't in the shape asked for")
    return data


def _entries(data: dict, key: str, document: str, dropped: list[str], extra=None) -> list[dict]:
    """A list of {text, quote} from Claude's reply, keeping only those whose quote is in the filing."""
    kept = []
    for entry in data.get(key) if isinstance(data.get(key), list) else []:
        if not isinstance(entry, dict):
            continue
        text, quote = " ".join(str(entry.get("text") or "").split()), " ".join(str(entry.get("quote") or "").split())
        if not text:
            continue
        if not quoted(quote, document):
            dropped.append(key)
            continue
        item = {"text": text[:500], "quote": quote[:600]}
        if extra:
            item.update(extra(entry))
        kept.append(item)
    return kept[:MAX_POINTS]


def check_reply(text: str, document: str, kind: str, filing_date: date) -> dict:
    """Claude's reply, checked: {headline, period_end, reported, points, guidance, changes, notes}.
    Raises ValueError if nothing in it can be trusted."""
    data, plain, dropped, notes = _json(text), _plain(document), [], []
    headline = " ".join(str(data.get("headline") or "").split())[:300]
    if not headline:
        raise ValueError("Claude's reply had no headline")
    points = _entries(data, "points", plain, dropped)
    if not points:
        raise ValueError("Claude's reply quoted nothing that's in the filing")
    result = {"headline": headline, "period_end": None, "reported": [], "points": points, "guidance": [],
              "changes": [], "notes": notes}
    if kind == "results":
        result["guidance"] = _entries(data, "guidance", plain, dropped, lambda e: {
            "direction": str(e.get("direction") or "").lower() if str(e.get("direction") or "").lower() in DIRECTIONS else "new"})
        result["changes"] = _entries(data, "changes", plain, dropped)
        try:
            period_end = date.fromisoformat(str(data.get("period_end"))[:10])
            if not filing_date - timedelta(days=200) <= period_end <= filing_date:
                raise ValueError
            result["period_end"] = period_end
        except ValueError:
            notes.append("The quarter's end date wasn't clear, so the figures aren't compared with earlier quarters.")
        seen = set()
        for entry in data.get("figures") if isinstance(data.get("figures"), list) else []:
            if not isinstance(entry, dict) or entry.get("metric") not in edgar.METRICS or entry.get("metric") in seen:
                continue
            metric, written = entry["metric"], str(entry.get("as_written") or "").strip()
            scale = "units" if edgar.METRICS[metric]["unit"] != "USD" else str(entry.get("scale") or "").lower()
            quote, number = " ".join(str(entry.get("quote") or "").split()), edgar.parse_number(written)
            if number is None or scale not in edgar.SCALES or not quoted(quote, plain) \
                    or not _number_in(written, quote):
                dropped.append("figures")
                continue
            seen.add(metric)
            result["reported"].append({"metric": metric, "value": number * edgar.SCALES[scale], "as_written": written,
                                       "scale": scale, "quote": quote[:600]})
    if dropped:
        n = len(dropped)
        notes.append(f"{n} item{'s' if n != 1 else ''} from Claude {'were' if n != 1 else 'was'} left out, "
                     f"because {'their quotes aren' if n != 1 else 'its quote isn'}'t in the filing.")
    return result


# ---------------------------------------------------------------------------
# Finding filings
# ---------------------------------------------------------------------------

def _tracked() -> list[str]:
    try:
        return market_tools.load_watchlist()
    except OSError:
        return []


def _filers(conn, tickers: list[str]) -> dict[str, int | None]:
    """Each tracked ticker's SEC company number, asking the SEC only about tickers it hasn't seen
    (or didn't know a month ago)."""
    known = {r["ticker"]: r for r in conn.execute("SELECT * FROM filers")}
    again = _days_ago(FILER_RECHECK_DAYS)
    missing = [t for t in tickers if t not in known or (known[t]["cik"] is None and known[t]["checked_at"] < again)]
    if missing:
        listed = edgar.company_numbers()
        with transaction(conn):
            for t in missing:
                entry = listed.get(t.upper()) or listed.get(t.upper().replace(".", "-")) or {}
                conn.execute("INSERT OR REPLACE INTO filers (ticker, cik, name, checked_at) VALUES (?, ?, ?, ?)",
                             (t, entry.get("cik"), entry.get("name"), _utc_now()))
        known = {r["ticker"]: r for r in conn.execute("SELECT * FROM filers")}
    return {t: known[t]["cik"] for t in tickers if t in known}


def check(trigger: str = "command line", emit=None, read_new: bool = True) -> dict:
    """Look for new filings from every tracked company (free), read new results announcements
    (a few cents each), compare reports' figures with what was announced (free), and send any
    Discord messages. Returns the saved check. Raises EdgarError if the SEC can't be asked at all."""
    emit = emit or (lambda event: None)
    today = events.today_et()
    since = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    problems, new, facts = [], [], {}
    with closing(connect()) as conn:
        try:
            numbers = _filers(conn, _tracked())
        except edgar.ContactMissing:
            raise
        except edgar.EdgarError as e:
            numbers = {r["ticker"]: r["cik"] for r in conn.execute("SELECT ticker, cik FROM filers")}
            problems.append(f"the SEC's company list: {e}")
        companies, unreachable = {}, 0
        for ticker, cik in numbers.items():
            if cik is not None:
                companies.setdefault(cik, []).append(ticker)  # two share classes are one company: asked once
        for cik, tickers in companies.items():
            emit({"type": "progress", "message": f"Checking {' and '.join(tickers)}'s filings"})
            try:
                listed = edgar.list_filings(cik)["filings"]
            except edgar.ContactMissing:
                raise
            except edgar.EdgarError as e:
                problems.append(f"{tickers[0]}: {e}")
                if e.status in (403, 429):  # being limited: asking for the rest would only make it worse
                    break
                unreachable = unreachable + 1 if e.status is None else 0
                if unreachable >= UNREACHABLE_LIMIT:  # the SEC is down or the network is: don't hold a run up for every company
                    problems.append("stopped there: the SEC can't be reached right now")
                    break
                continue
            unreachable = 0
            with transaction(conn):
                for f in listed:
                    about = describe(f["form"], f["items"])
                    if about is None or f["filing_date"] < since or not f["filed_at"]:
                        continue
                    for ticker in tickers:
                        added = conn.execute(
                            """INSERT OR IGNORE INTO filings (ticker, accession, cik, form, items, kind, title, serious,
                               amended, filed_at, filing_date, report_date, primary_doc, first_seen)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (ticker, f["accession"], cik, f["form"], ",".join(f["items"]), about["kind"], about["title"],
                             int(about["serious"]), int(about["amended"]), f["filed_at"], f["filing_date"],
                             f["report_date"] or None, f["primary_doc"], _utc_now())).rowcount
                        if added:
                            new.append({"ticker": ticker, "accession": f["accession"], "title": about["title"]})
        recent = _days_ago(AUTOMATIC_WITHIN_DAYS)
        due = [] if not read_new else [r["accession"] for r in conn.execute(
            """SELECT accession, MAX(filed_at) AS filed FROM filings f
               WHERE kind = 'results' AND amended = 0 AND filed_at >= ?
                 AND NOT EXISTS (SELECT 1 FROM filing_reads r WHERE r.accession = f.accession)
               GROUP BY accession ORDER BY filed DESC LIMIT ?""", (recent, MAX_AUTOMATIC))]
    reads = []
    for accession in due:
        try:
            reads.append(read(accession, "automatic", emit, facts))
        except Exception as e:  # one filing failing doesn't stop the rest
            problems.append(f"{accession}: {e}")
    with closing(connect()) as conn:
        problems += _fill_figures(conn, today, facts, emit)
    try:
        sent = notify(recent)
    except Exception as e:
        sent = {"sent": [], "failed": [f"Discord ({e})"]}
    problems += [f"Discord: {label}" for label in sent["failed"]]
    cost = round(sum(r["cost_usd"] for r in reads), 4)
    with closing(connect()) as conn:
        with transaction(conn):
            conn.execute("""INSERT INTO filing_checks (finished_at, trigger, status, companies, new_filings, reads, cost_usd, message)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                         (_utc_now(), trigger, "partial" if problems else "ok", len(companies), len(new), len(reads), cost,
                          "; ".join(problems)[:1000] or None))
        summary = last_check(conn)
    summary.update(new=new, read=[{"ticker": r["ticker"], "accession": r["accession"], "status": r["status"],
                                   "headline": r["headline"], "error": r["error"]} for r in reads], alerts=sent["sent"])
    return summary


def _facts(cik: int, cache: dict) -> dict:
    """A company's quarterly and yearly figures, downloaded once per check."""
    if cik not in cache:
        cache[cik] = edgar.periods(edgar.company_facts(cik))
    return cache[cik]


def _fill_figures(conn, today: date, cache: dict, emit) -> list[str]:
    """For each recent quarterly or annual report: save its own figures, and use them to confirm
    (or contradict) the figures in that quarter's results announcement. No Claude."""
    problems = []
    since = (today - timedelta(days=FIGURES_WITHIN_DAYS)).isoformat()
    reports = conn.execute(
        """SELECT * FROM filings WHERE kind IN ('quarterly', 'annual') AND amended = 0 AND report_date IS NOT NULL
           AND filing_date >= ? ORDER BY filed_at""", (since,)).fetchall()
    for report in reports:
        period_end = date.fromisoformat(report["report_date"])
        waiting = [r for r in conn.execute(
            "SELECT id, figures FROM filing_reads WHERE ticker = ? AND status = 'ok' AND figures IS NOT NULL",
            (report["ticker"],)) if _pending(r["figures"], period_end)]
        if report["figures"] is not None and not waiting:
            continue
        if not report["form"].startswith("10-"):
            continue  # companies outside the US don't file figures in this form
        try:
            emit({"type": "progress", "message": f"Fetching the figures from {report['ticker']}'s report"})
            known = _facts(report["cik"], cache)
        except edgar.EdgarError as e:
            problems.append(f"{report['ticker']}'s figures: {e}")
            continue
        own = report_figures(known, period_end, annual=report["kind"] == "annual")
        settled = own is not None or report["filing_date"] < (today - timedelta(days=3)).isoformat()
        if own is None and settled:  # the SEC publishes figures within minutes: after days, there are none to wait for
            own = {"basis": "year" if report["kind"] == "annual" else "quarter", "source": "report",
                   "period_end": report["report_date"], "rows": [], "margins": []}
        with transaction(conn):
            if own is not None and report["figures"] is None:
                conn.execute("UPDATE filings SET figures = ? WHERE ticker = ? AND accession = ?",
                             (json.dumps(own), report["ticker"], report["accession"]))
            for row in waiting:
                figures = json.loads(row["figures"])
                changed = confirm(figures, known)
                if settled:  # the report is in, so a figure it doesn't give can't be checked
                    for r in figures["rows"]:
                        if r["check"] == "pending":
                            r["check"], changed = "not_checked", True
                if changed:
                    conn.execute("UPDATE filing_reads SET figures = ? WHERE id = ?", (json.dumps(figures), row["id"]))
    return problems


def _pending(figures_json: str, period_end: date) -> bool:
    try:
        figures = json.loads(figures_json)
        return bool(figures.get("period_end")) and abs((date.fromisoformat(figures["period_end"]) - period_end).days) <= 7 \
            and any(r["check"] == "pending" for r in figures["rows"])
    except (ValueError, KeyError, TypeError):
        return False


def check_before_run(emit=None) -> dict | None:
    """What a run does first, so the brief can use today's filings. Never raises: a problem here
    is shown as a warning, and the run carries on."""
    emit = emit or (lambda event: None)
    try:
        result = check("before a run", lambda event: emit(event) if event.get("type") != "progress"
                       or event["message"].startswith(("Reading", "First take")) else None)
    except Exception as e:
        emit({"type": "warning", "message": f"Filings weren't checked ({e}). The run carries on without them."})
        return None
    if result["new"]:
        names = ", ".join(f"{f['ticker']} ({f['title'].split(';')[0].lower()})" for f in result["new"][:4])
        more = f" and {len(result['new']) - 4} more" if len(result["new"]) > 4 else ""
        emit({"type": "filings", "message": f"Filings: {len(result['new'])} new: {names}{more}"})
    for label in result["alerts"]:
        emit({"type": "alert", "message": f"Discord: sent {label}"})
    if result["message"]:
        emit({"type": "warning", "message": f"Filings: {result['message']}"})
    return result


# ---------------------------------------------------------------------------
# Reading one filing
# ---------------------------------------------------------------------------

async def _ask_claude_async(system_prompt: str, prompt: str) -> tuple[str, float]:
    result = None
    async for message in query(prompt=prompt, options=_options(system_prompt)):
        if isinstance(message, ResultMessage):
            result = message
    if result is None or result.is_error or not result.result:
        raise RuntimeError(f"Claude couldn't read the filing: {result.subtype if result else 'no result'}")
    return result.result, result.total_cost_usd or 0.0


def ask_claude(system_prompt: str, prompt: str) -> tuple[str, float]:
    """Claude's reply (JSON text) and its cost. Tests and the test environment replace this."""
    return asyncio.run(_ask_claude_async(system_prompt, prompt))


def _cut(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit].rsplit("\n", 1)[0], True


def _press_release(documents: list[dict]) -> dict | None:
    exhibits = sorted((d for d in documents if d["type"].startswith("EX-99")), key=lambda d: d["type"])
    return exhibits[0] if exhibits else None


def _main(documents: list[dict], filing: dict) -> dict | None:
    return next((d for d in documents if d["name"] == filing["primary_doc"]), None) or (documents[0] if documents else None)


def gather(filing: dict) -> dict:
    """The text to read from a filing: {text, name, url, cut_off, notes}.
    - Results: the press release (the first EX-99 exhibit).
    - Other announcements: the filing's own text, then its press release if it has one.
    - Quarterly and annual reports: management's discussion of the results."""
    documents = edgar.filing_documents(filing["cik"], filing["accession"], filing["primary_doc"] or "", filing["form"])
    notes, press, main = [], _press_release(documents), _main(documents, filing)
    if filing["kind"] == "results" and press:
        chosen, text = press, edgar.to_text(edgar.get_text(press["url"]))
    elif filing["kind"] in ("quarterly", "annual"):
        if main is None:
            raise FilingError("This filing has no document that can be read.", 422)
        annual = filing["kind"] == "annual"
        chosen, whole = main, edgar.to_text(edgar.get_text(main["url"]))
        text = edgar.discussion(whole, annual=annual)
        attached = next((d for d in documents if d["type"].startswith("EX-13")), None)
        if not text and attached:  # the discussion is in the annual report attached to the filing (Wells Fargo's is)
            chosen, whole = attached, edgar.to_text(edgar.get_text(attached["url"]))
            text = edgar.discussion(whole, annual=annual)
            if not text:
                text = whole
                notes.append("Management's discussion is in the annual report attached to this filing, so that was read.")
        elif not text:
            text = whole
            notes.append("Management's discussion couldn't be found in the report, so the start of the report was read instead.")
    else:
        if main is None and press is None:
            raise FilingError("This filing has no document that can be read.", 422)
        chosen = main or press
        text = edgar.to_text(edgar.get_text(chosen["url"]))
        if main and press:
            text, _ = _cut(text, COVER_CHARS)
            text += f"\n\n--- Attached press release ({press['type']}) ---\n" + edgar.to_text(edgar.get_text(press["url"]))
        if filing["kind"] == "results":
            notes.append("This results filing has no press release attached, so the filing's own text was read.")
    if len(text.strip()) < 200:
        raise FilingError("This filing's document has no text that can be read (it may be a scan or a PDF).", 422)
    text, cut_off = _cut(text, MAX_CHARS)
    if cut_off:
        notes.append(f"The document is long: the first {MAX_CHARS:,} characters were read.")
    return {"text": text, "name": chosen["name"], "url": chosen["url"], "cut_off": cut_off, "notes": notes}


def _previous_announcement(conn, filing: dict) -> tuple[str, str] | None:
    """(filing date, text) of the results announcement before this one, for 'what changed'."""
    row = conn.execute(
        """SELECT * FROM filings WHERE ticker = ? AND kind = 'results' AND amended = 0 AND filed_at < ?
           ORDER BY filed_at DESC LIMIT 1""", (filing["ticker"], filing["filed_at"])).fetchone()
    if row is None:
        return None
    try:
        press = _press_release(edgar.filing_documents(row["cik"], row["accession"], row["primary_doc"] or "", row["form"]))
        if press is None:
            return None
        return row["filing_date"], _cut(edgar.to_text(edgar.get_text(press["url"])), PREVIOUS_CHARS)[0]
    except edgar.EdgarError:
        return None  # the comparison is a bonus: the read goes ahead without it


def build_prompt(filing: dict, company: str, text: str, previous: tuple[str, str] | None = None) -> str:
    lines = [f"COMPANY: {company} ({filing['ticker']})",
             f"FILING: {filing['title']}, filed {filing['filing_date']} (form {filing['form']}"
             + (f", items {filing['items']}" if filing["items"] else "") + ")"]
    if previous:
        lines += ["", f"PREVIOUS ANNOUNCEMENT (filed {previous[0]}), for comparison only. Never quote from it:",
                  "<<<", previous[1], ">>>"]
    lines += ["", 'FILING TEXT (in tables, cells are separated by " | "):', "<<<", text, ">>>"]
    return "\n".join(lines)


def _the_filing(conn, accession: str) -> dict:
    row = conn.execute("SELECT * FROM filings WHERE accession = ? ORDER BY ticker LIMIT 1", (accession,)).fetchone()
    if row is None:
        raise FilingError(f"No filing {accession} is listed. Check for new filings first.", 404)
    return dict(row)


def read(accession: str, trigger: str = "manual", emit=None, facts: dict | None = None) -> dict:
    """Read one filing with Claude now and save the first take. Returns the saved read."""
    emit = emit or (lambda event: None)
    facts = {} if facts is None else facts
    with closing(connect()) as conn:
        filing = _the_filing(conn, accession)
        company = _company(conn, filing["ticker"])
        stuck = _stamp(now_utc() - STUCK_AFTER)
        with transaction(conn):
            if conn.execute("SELECT 1 FROM filing_reads WHERE accession = ? AND status = 'running' AND started_at >= ?",
                            (accession, stuck)).fetchone():
                raise FilingError("This filing is already being read.", 409)
            read_id = conn.execute(
                "INSERT INTO filing_reads (accession, ticker, trigger, status, started_at) VALUES (?, ?, ?, 'running', ?)",
                (accession, filing["ticker"], trigger, _utc_now())).lastrowid
        previous = _previous_announcement(conn, filing) if filing["kind"] == "results" else None
    fields = {"status": "failed", "headline": None, "points": "[]", "guidance": "[]", "changes": "[]", "figures": None,
              "notes": "[]", "document": None, "document_url": None, "chars": 0, "cut_off": 0, "cost_usd": 0.0, "error": None}
    try:
        emit({"type": "progress", "message": f"Reading {company}'s {filing['title'].split(';')[0].lower()}"})
        source = gather(filing)
        fields.update(document=source["name"], document_url=source["url"], chars=len(source["text"]),
                      cut_off=int(source["cut_off"]))
        system = {"results": RESULTS_PROMPT, "quarterly": REPORT_PROMPT, "annual": REPORT_PROMPT}.get(
            filing["kind"], ANNOUNCEMENT_PROMPT)
        reply, cost = ask_claude(system, build_prompt(filing, company, source["text"], previous))
        fields["cost_usd"] = round(cost, 4)
        take = check_reply(reply, source["text"], filing["kind"], date.fromisoformat(filing["filing_date"]))
        notes = source["notes"] + take["notes"]
        if filing["kind"] == "results":
            try:
                known = _facts(filing["cik"], facts) if take["reported"] else {}
            except edgar.EdgarError as e:
                known = {}
                notes.append(f"Earlier quarters couldn't be fetched for comparison ({e}).")
            fields["figures"] = json.dumps(compare(take["reported"], take["period_end"], known, notes))
            if previous is None:
                notes.append("There's no earlier results announcement on file to compare the wording with.")
        fields.update(status="ok", headline=take["headline"], points=json.dumps(take["points"]),
                      guidance=json.dumps(take["guidance"]), changes=json.dumps(take["changes"]), notes=json.dumps(notes))
        emit({"type": "progress", "message": f"First take on {filing['ticker']}: {take['headline']}"})
    except Exception as e:  # saved as a failed read, so the reason is visible
        fields["error"] = str(e)[:500] or type(e).__name__
    with closing(connect()) as conn:
        with transaction(conn):
            conn.execute(f"""UPDATE filing_reads SET {', '.join(f'{k} = ?' for k in fields)}, finished_at = ?
                             WHERE id = ?""", (*fields.values(), _utc_now(), read_id))
        return get_read(conn, read_id)


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------

def _figure_line(row: dict) -> str:
    change = row.get("change_year_pct")
    return f"{row['label']} {money(row['value'], row['unit'])}" + (f" ({change:+.1f}% vs a year ago)" if change is not None else "")


def alert_payload(filing: dict, take: dict | None, company: str) -> dict:
    """One Discord message for a filing: a results first take, or a serious announcement."""
    link = alerts._app_link(f"#/filings/{filing['accession']}") or {"url": filing["url"]}
    footer = {"text": "From the company's SEC filing · research, not investment advice"}
    if filing["kind"] == "results" and take and take["status"] == "ok":
        lines = [take["headline"], ""]
        lines += [f"• {_figure_line(r)}" for r in (take["figures"] or {}).get("rows", [])]
        lines += [f"**Guidance ({DIRECTIONS[g['direction']].lower()}):** {g['text']}" for g in take["guidance"][:2]]
        lines += ["", f"[The filing on sec.gov]({filing['url']})"]
        return {"content": f"**{filing['ticker']} reported results**",
                "embeds": alerts._fit([{"title": alerts._shorten(f"{company}: results", alerts.MAX_TITLE),
                                        "description": alerts._shorten("\n".join(lines), alerts.MAX_DESCRIPTION),
                                        "color": alerts.COLORS["neutral"], "footer": footer, **link}])}
    lines = [filing["title"] + ".", "Not read by Claude yet: open the Filings tab to read it.",
             "", f"[The filing on sec.gov]({filing['url']})"]
    return {"content": f"**{filing['ticker']} filed with the SEC**",
            "embeds": [{"title": alerts._shorten(f"{company}: {filing['title']}", alerts.MAX_TITLE),
                        "description": alerts._shorten("\n".join(lines), alerts.MAX_DESCRIPTION),
                        "color": alerts.COLORS["neutral"], "footer": footer, **link}]}


def notify(since: str) -> dict:
    """Send a Discord message for each recent filing that calls for one and hasn't had one: a results
    announcement (with its first take, once it's read) or a serious announcement. One that fails is
    tried again by the next check. Returns {"sent": [...], "failed": [...]}."""
    outcome = {"sent": [], "failed": []}
    if not alerts.enabled():
        return outcome
    with closing(connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")  # decide and claim in one step, so two checks can't both send
        try:
            pending = alerts._stamp(alerts._utc_now() - timedelta(seconds=alerts.PENDING_SECONDS))
            todo = []
            for filing in list_filings(conn, since=since):
                if filing["kind"] != "results" and not filing["serious"]:
                    continue
                take = filing["read"]
                if filing["kind"] == "results" and not filing["amended"] and (take is None or take["status"] == "running"):
                    continue  # wait for its first take
                done = conn.execute("SELECT status, created_at FROM filing_alerts WHERE accession = ?",
                                    (filing["accession"],)).fetchone()
                if done and (done["status"] == "sent" or (done["status"] == "pending" and done["created_at"] >= pending)):
                    continue
                if any(t[0]["accession"] == filing["accession"] for t in todo):
                    continue  # the same filing under a second ticker
                what = "first take" if filing["kind"] == "results" and take and take["status"] == "ok" else "filed"
                conn.execute("""INSERT OR REPLACE INTO filing_alerts (accession, what, status, created_at)
                                VALUES (?, ?, 'pending', ?)""", (filing["accession"], what, _utc_now()))
                todo.append((filing, take, _company(conn, filing["ticker"])))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        for filing, take, company in todo:
            label = f"{filing['ticker']} {'results' if filing['kind'] == 'results' else 'filing'}"
            try:
                alerts.send(alert_payload(filing, take, company))
                conn.execute("UPDATE filing_alerts SET status = 'sent', error = NULL, sent_at = ? WHERE accession = ?",
                             (_utc_now(), filing["accession"]))
                outcome["sent"].append(label)
            except Exception as e:
                conn.execute("UPDATE filing_alerts SET status = 'failed', error = ? WHERE accession = ?",
                             (str(e) or type(e).__name__, filing["accession"]))
                outcome["failed"].append(f"{label} ({e})")
    return outcome


# ---------------------------------------------------------------------------
# Reading (the API, the agent's tool, Ask and the command line)
# ---------------------------------------------------------------------------

def _read_row(row) -> dict:
    r = dict(row)
    for key in ("points", "guidance", "changes", "notes"):
        r[key] = json.loads(r[key] or "[]")
    r["figures"] = json.loads(r["figures"]) if r["figures"] else None
    return r


def get_read(conn, read_id: int) -> dict:
    return _read_row(conn.execute("SELECT * FROM filing_reads WHERE id = ?", (read_id,)).fetchone())


def _filing_row(row, reads: dict) -> dict:
    f = dict(row)
    f["items"] = [{"code": code, "label": ITEMS.get(code, f"Item {code}")} for code in f["items"].split(",") if code]
    f["serious"], f["amended"] = bool(f["serious"]), bool(f["amended"])
    f["kind_label"] = KIND_LABELS[f["kind"]]
    f["figures"] = json.loads(f["figures"]) if f["figures"] else None
    f["url"] = edgar.index_url(f["cik"], f["accession"])
    f["read"] = reads.get(f["accession"])
    return f


def list_filings(conn, ticker: str | None = None, since: str | None = None, limit: int = 300,
                 accession: str | None = None) -> list[dict]:
    """Filings, newest first, each with its latest read. Works on a read-only connection,
    even before the first check."""
    limit = min(limit, 900)
    stuck = _stamp(now_utc() - STUCK_AFTER)
    try:
        rows = conn.execute(
            """SELECT * FROM filings WHERE (? IS NULL OR ticker = ?) AND (? IS NULL OR filed_at >= ?)
               AND (? IS NULL OR accession = ?) ORDER BY filed_at DESC, accession DESC, ticker LIMIT ?""",
            (ticker, ticker and ticker.upper(), since, since, accession, accession, limit)).fetchall()
        wanted = sorted({r["accession"] for r in rows})
        reads = {}
        for r in conn.execute(f"SELECT * FROM filing_reads WHERE accession IN ({','.join('?' * len(wanted))}) ORDER BY id",
                              wanted):
            taken = _read_row(r)
            if taken["status"] == "running" and taken["started_at"] < stuck:
                taken.update(status="failed", error="This read was interrupted. Try again.")
            if taken["status"] == "failed" and reads.get(r["accession"], {}).get("status") == "ok":
                continue  # the latest read wins, unless it failed and an earlier one worked
            reads[r["accession"]] = taken
    except Exception:  # no filings tables yet
        return []
    return [_filing_row(r, reads) for r in rows]


def get_filing(conn, accession: str) -> dict | None:
    found = list_filings(conn, accession=accession)
    return found[0] if found else None


def last_check(conn) -> dict | None:
    try:
        row = conn.execute("SELECT * FROM filing_checks ORDER BY id DESC LIMIT 1").fetchone()
    except Exception:
        return None
    return dict(row) if row else None


def not_covered(conn) -> list[str]:
    """Tracked tickers the SEC lists no company for (funds, and some companies listed elsewhere)."""
    try:
        missing = {r[0] for r in conn.execute("SELECT ticker FROM filers WHERE cik IS NULL")}
    except Exception:
        return []
    return [t for t in _tracked() if t in missing]


def _matches(filing: dict, event: dict) -> bool:
    """Is this results filing the earnings report this calendar event expected? Yahoo's dates can be a
    day or two out, and an unconfirmed date is the start of a window."""
    gap = (date.fromisoformat(filing["filing_date"]) - date.fromisoformat(event["event_date"])).days
    return filing["ticker"] == event["ticker"] and (-3 <= gap <= 3 if events.confirmed(event) else -3 <= gap <= 14)


def for_calendar(conn, calendar_events: list[dict], start: str, end: str) -> list[dict]:
    """Results announcements for the Calendar tab: each with the earnings event it answers (event_id),
    if the calendar had one. Covers `start` to `end`, plus whatever the given events matched."""
    earnings = [e for e in calendar_events if e["kind"] == "earnings"]
    since = (date.fromisoformat(start) - timedelta(days=15)).isoformat()
    until = (date.fromisoformat(end) + timedelta(days=15)).isoformat()
    found, seen = [], set()
    for f in list_filings(conn, since=since + "T00:00:00Z"):
        if f["kind"] != "results" or f["amended"] or f["filing_date"] > until or (f["ticker"], f["accession"]) in seen:
            continue
        seen.add((f["ticker"], f["accession"]))
        match = min((e for e in earnings if _matches(f, e)), default=None,
                    key=lambda e: abs((date.fromisoformat(f["filing_date"]) - date.fromisoformat(e["event_date"])).days))
        if match is None and not start <= f["filing_date"] <= end:
            continue
        take = f["read"] if f["read"] and f["read"]["status"] == "ok" else None
        found.append({"ticker": f["ticker"], "company": _company(conn, f["ticker"]), "accession": f["accession"],
                      "filing_date": f["filing_date"], "filed_at": f["filed_at"], "url": f["url"],
                      "headline": take["headline"] if take else None, "event_id": match["id"] if match else None})
    return found


def expected(conn, today: date) -> list[dict]:
    """Earnings the calendar expected in the last few days (or today) with no results announcement yet."""
    start = today - timedelta(days=3)
    due = [e for e in events.upcoming(conn, start, 3, _tracked() or None) if e["kind"] == "earnings"]
    reported = for_calendar(conn, due, start.isoformat(), today.isoformat())
    answered = {r["event_id"] for r in reported}
    return [{"ticker": e["ticker"], "company": e["company"], "event_date": e["event_date"],
             "confirmed": events.confirmed(e)} for e in due if e["id"] not in answered]


def recent_for(conn, ticker: str, since: str) -> list[dict]:
    """A ticker's recent filings, compact, for the brief's recent_filings tool."""
    found = []
    for f in list_filings(conn, ticker, since):
        take = f["read"] if f["read"] and f["read"]["status"] == "ok" else None
        entry = {"filed": f["filing_date"], "kind": f["kind_label"], "title": f["title"], "serious": f["serious"],
                 "url": f["url"], "first_take": None}
        if take:
            figures = take["figures"] or {}
            entry["first_take"] = {
                "headline": take["headline"], "points": [p["text"] for p in take["points"]],
                "guidance": [f"{DIRECTIONS[g['direction']]}: {g['text']}" for g in take["guidance"]],
                "figures": [_figure_line(r) + (f", {r['change_prior_pct']:+.1f}% vs the quarter before"
                                                if r.get("change_prior_pct") is not None else "")
                            for r in figures.get("rows", [])]}
        found.append(entry)
    return found


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def _print_take(filing: dict) -> None:
    take = filing["read"]
    print(f"{filing['ticker']}  {filing['title']}  (filed {filing['filing_date']}, {filing['form']})\n{filing['url']}")
    for label, figures in (("Figures from the report", filing["figures"]), ("Figures as announced", take and take["figures"])):
        if figures and figures["rows"]:
            print(f"\n{label} ({figures['basis']} to {figures['period_end']}):")
            for r in figures["rows"]:
                checked = {"confirmed": "  ✓ confirmed by the report", "differs": f"  ✗ the report says {money(r.get('report_value'), r['unit'])}"}
                print(f"  {_figure_line(r)}{checked.get(r['check'], '')}")
    if take is None:
        print("\nNot read yet: python filings.py read", filing["accession"])
        return
    if take["status"] != "ok":
        print(f"\nRead {take['status']}: {take['error'] or ''}")
        return
    print(f"\n{take['headline']}  (${take['cost_usd']:.3f})")
    for title, entries in (("Key points", take["points"]), ("Guidance", take["guidance"]), ("What changed", take["changes"])):
        if entries:
            print(f"\n{title}:")
            for e in entries:
                print(f"  - {e['text']}\n      \"{e['quote']}\"")
    for note in take["notes"]:
        print(f"\nNote: {note}")


def _utf8_output() -> None:
    """Print ✓, ✗ and a filing's own wording even when output goes to a file or a pipe (a scheduled
    check's log, say). On Windows that output is in cp1252 by default, which can't print "✓" and
    would stop the program. A real console is left as it is."""
    for stream in (sys.stdout, sys.stderr):
        if (getattr(stream, "encoding", "") or "").lower().replace("-", "") != "utf8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    _utf8_output()
    parser = argparse.ArgumentParser(description="Company filings from the SEC, and first takes on them.")
    commands = parser.add_subparsers(dest="command", required=True)
    look = commands.add_parser("check", help="look for new filings now (free; reads new results announcements)")
    look.add_argument("--no-read", action="store_true", help="only list them: nothing is sent to Claude")
    show_list = commands.add_parser("list", help="the latest filings")
    show_list.add_argument("--ticker")
    for name, text in (("read", "read one filing with Claude now (costs a few cents)"), ("show", "a filing's first take")):
        commands.add_parser(name, help=text).add_argument("accession")
    commands.add_parser("figures", help="a company's quarterly figures from the SEC's structured data").add_argument("ticker")
    args = parser.parse_args()
    try:
        if args.command == "check":
            result = check(emit=lambda e: print(e["message"]), read_new=not args.no_read)
            print(f"{result['status']}: {result['new_filings']} new filing{'s' if result['new_filings'] != 1 else ''} from "
                  f"{result['companies']} companies, {result['reads']} read, ${result['cost_usd']:.3f}"
                  + (f" ({result['message']})" if result["message"] else ""))
        elif args.command == "list":
            with closing(reports_db.connect(readonly=True)) as conn:
                for f in list_filings(conn, args.ticker, limit=40):
                    state = "" if f["read"] is None else f"  [{'first take' if f['read']['status'] == 'ok' else f['read']['status']}]"
                    print(f"{f['filing_date']}  {f['ticker']:<6} {f['form']:<8} {f['accession']}  "
                          f"{'! ' if f['serious'] else ''}{f['title']}{state}")
        elif args.command == "read":
            taken = read(args.accession, emit=lambda e: print(e["message"]))
            if taken["status"] == "failed":
                raise SystemExit(f"failed: {taken['error']}")
            with closing(reports_db.connect(readonly=True)) as conn:
                _print_take(get_filing(conn, args.accession))
        elif args.command == "show":
            with closing(reports_db.connect(readonly=True)) as conn:
                filing = get_filing(conn, args.accession)
            if filing is None:
                raise SystemExit(f"No filing {args.accession} is listed.")
            _print_take(filing)
        else:
            ticker = args.ticker.upper()
            cik = (edgar.company_numbers().get(ticker) or {}).get("cik")
            if cik is None:
                raise SystemExit(f"The SEC lists no company under {ticker}.")
            for metric, found in edgar.periods(edgar.company_facts(cik)).items():
                print(f"\n{edgar.METRICS[metric]['label']} ({found['tag']})")
                for end in sorted(found["quarters"], reverse=True)[:8]:
                    q = found["quarters"][end]
                    print(f"  quarter to {end}  {money(q['value'], edgar.METRICS[metric]['unit']):>12}"
                          + ("  (worked out: the year minus the first nine months)" if q["derived"] else ""))
    except (FilingError, edgar.EdgarError) as e:
        raise SystemExit(str(e))


if __name__ == "__main__":
    main()
