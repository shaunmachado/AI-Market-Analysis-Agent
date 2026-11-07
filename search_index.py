"""Search over saved reports: the "R" in RAG.

Each report is split into passages (one per flagged ticker, plus an overview). Two
kinds of search run over them and their rankings are blended:
- keywords: SQLite's built-in full-text search (finds "downgrade" for "downgraded")
- meaning:  Voyage AI embeddings (finds "analyst cut its rating" for "downgrade")

Ask uses this to pull relevant passages from any day in your history, and the app's
search box uses it directly. Without VOYAGE_API_KEY it still works, by keywords only.

The index is its own file, search.db, built from reports.db. Your reports are only
read; the index can be deleted and rebuilt at any time.

    python search_index.py sync                  index new or changed reports
    python search_index.py rebuild               delete the index and build it again
    python search_index.py status                what's indexed
    python search_index.py search "analyst downgrade"
"""

import argparse
import json
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

import reports_db
load_dotenv()  # so VOYAGE_API_KEY in .env is found when this file runs on its own

EMBED_MODEL = os.environ.get("VOYAGE_MODEL", "voyage-4")  # or voyage-finance-2, voyage-4-large...
EMBED_BATCH = 128       # passages per Voyage request (their limit is 1,000)
RRF_K = 60              # how keyword and meaning rankings are blended (reciprocal rank fusion)
MIN_SIMILARITY = 0.25   # meaning matches weaker than this are always left out
MEANING_CUTOFF = 0.85   # ...and so are those below 85% of the best match's similarity. Briefs share a
                        # template, so loosely related ones score fairly high; lower this to see more of them
MAX_QUERY_WORDS = 20

SCHEMA = """
CREATE TABLE IF NOT EXISTS indexed_reports (
    session_date TEXT PRIMARY KEY,
    revision     INTEGER NOT NULL        -- the report revision the passages were built from
);
CREATE TABLE IF NOT EXISTS chunks (
    id           INTEGER PRIMARY KEY,
    session_date TEXT NOT NULL,
    status       TEXT NOT NULL,
    ticker       TEXT,                   -- the ticker for its section; empty for the overview
    heading      TEXT NOT NULL,
    text         TEXT NOT NULL,
    embedding    BLOB,                   -- float32 vector; empty until embedded
    model        TEXT                    -- the embedding model that made it
);
CREATE INDEX IF NOT EXISTS idx_chunks_day ON chunks (session_date);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    heading, text, content='chunks', content_rowid='id', tokenize='porter unicode61');
CREATE TRIGGER IF NOT EXISTS chunks_added AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts (rowid, heading, text) VALUES (new.id, new.heading, new.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_removed AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts (chunks_fts, rowid, heading, text) VALUES ('delete', old.id, old.heading, old.text);
END;
"""

TICKER_HEADING = re.compile(r"^### ([A-Z0-9.\-^=]{1,15})\b")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-']*")


def index_path() -> Path:
    """search.db next to reports.db, unless SEARCH_DB says otherwise."""
    return Path(os.environ.get("SEARCH_DB") or Path(reports_db.DB_PATH).with_name("search.db"))


def connect(path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or index_path(), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Embeddings (Voyage AI)
# ---------------------------------------------------------------------------

def vector_search_available() -> bool:
    return bool(os.environ.get("VOYAGE_API_KEY"))


def embed(texts: list[str], input_type: str) -> list[list[float]]:
    """Vectors from Voyage AI. input_type: "document" for passages, "query" for searches."""
    import voyageai  # pip install voyageai (only needed for meaning-based search)

    return voyageai.Client().embed(texts, model=EMBED_MODEL, input_type=input_type).embeddings


# ---------------------------------------------------------------------------
# Building the index
# ---------------------------------------------------------------------------

SKIPPED_SECTIONS = ("Coming up",)  # forward-looking calendar lines: they'd make a search for "earnings"
                                   # find the days *before* each earnings date (Ask gets the calendar itself)


def chunk_report(report: dict) -> list[dict]:
    """Split a brief into passages: one per ticker section, plus an overview of the rest.
    Each passage starts with the report's title, so it carries its date wherever it goes."""
    news = {}
    for s in report.get("sources") or []:
        news.setdefault(s.get("ticker"), []).append(f"News: {s.get('title')} ({s.get('publisher')})")
    prefix = f"{report['title']} ({report['status']})"
    body = MARKDOWN_LINK.sub(r"\1", report["body_md"])  # index what readers see: link text, not URLs
    passages, overview = [], []
    for section in re.split(r"(?m)^(?=#{1,3} )", body):
        if not section.strip():
            continue
        first_line = section.strip().splitlines()[0]
        if first_line.lstrip("#").strip() in SKIPPED_SECTIONS:
            continue
        match = TICKER_HEADING.match(first_line)
        if match:
            ticker = match.group(1)
            text = "\n".join([section.strip(), *news.get(ticker, [])])
            passages.append({"ticker": ticker, "heading": first_line.lstrip("#").strip(), "text": f"{prefix}\n{text}"})
        else:
            overview.append(section.strip())
    if overview:
        passages.insert(0, {"ticker": None, "heading": "Overview", "text": f"{prefix}\n" + "\n\n".join(overview)})
    return passages


def embed_pending(conn) -> int:
    """Embed every passage that has no vector from the current model. Returns how many."""
    if not vector_search_available():
        return 0
    rows = conn.execute("SELECT id, text FROM chunks WHERE embedding IS NULL OR model IS NOT ?",
                        (EMBED_MODEL,)).fetchall()
    for start in range(0, len(rows), EMBED_BATCH):
        batch = rows[start:start + EMBED_BATCH]
        vectors = embed([r["text"] for r in batch], "document")
        conn.executemany("UPDATE chunks SET embedding = ?, model = ? WHERE id = ?",
                         [(np.asarray(v, dtype=np.float32).tobytes(), EMBED_MODEL, r["id"])
                          for r, v in zip(batch, vectors)])
    return len(rows)


def sync(embed_now: bool = True) -> dict:
    """Bring the index up to date with reports.db: index new reports, re-index changed
    ones (a newer intraday revision, or a day that was finalized), and drop removed ones.
    Passages are searchable by keyword straight away; embedding needs VOYAGE_API_KEY."""
    with closing(reports_db.connect(readonly=True)) as reports, closing(connect()) as conn:
        current = {r["session_date"]: r["revision"] for r in reports.execute("SELECT session_date, revision FROM reports")}
        conn.execute("BEGIN IMMEDIATE")  # one update at a time; a second one waits, then finds nothing to redo
        try:
            indexed = {r["session_date"]: r["revision"] for r in conn.execute("SELECT * FROM indexed_reports")}
            changed = [day for day, revision in current.items() if indexed.get(day) != revision]
            removed = [day for day in indexed if day not in current]
            for day in changed + removed:
                conn.execute("DELETE FROM chunks WHERE session_date = ?", (day,))
                conn.execute("DELETE FROM indexed_reports WHERE session_date = ?", (day,))
            for day in changed:
                report = reports_db.get_report(reports, day)
                conn.executemany(
                    "INSERT INTO chunks (session_date, status, ticker, heading, text) VALUES (?, ?, ?, ?, ?)",
                    [(day, report["status"], c["ticker"], c["heading"], c["text"]) for c in chunk_report(report)])
                conn.execute("INSERT INTO indexed_reports VALUES (?, ?)", (day, report["revision"]))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        embedded = embed_pending(conn) if embed_now else 0  # outside the transaction: searches carry on meanwhile
    return {"reports_indexed": len(changed), "reports_removed": len(removed), "passages_embedded": embedded}


def rebuild() -> dict:
    for suffix in ("", "-wal", "-shm"):
        Path(str(index_path()) + suffix).unlink(missing_ok=True)
    return sync()


def status() -> dict:
    with closing(reports_db.connect(readonly=True)) as reports, closing(connect()) as conn:
        total = reports.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        row = conn.execute("""SELECT (SELECT COUNT(*) FROM indexed_reports) AS reports,
                                     COUNT(*) AS passages, SUM(model IS ? AND embedding IS NOT NULL) AS embedded
                              FROM chunks""", (EMBED_MODEL,)).fetchone()
    return {"reports_total": total, "reports_indexed": row["reports"], "passages": row["passages"],
            "passages_embedded": row["embedded"] or 0, "model": EMBED_MODEL,
            "meaning_search": vector_search_available(), "index": str(index_path())}


# ---------------------------------------------------------------------------
# Searching
# ---------------------------------------------------------------------------

def search(query: str, limit: int = 10, ticker: str | None = None,
           since: str | None = None, until: str | None = None) -> dict:
    """Passages matching the query, best first. Each result says whether it matched by
    keywords, by meaning, or both. mode is "hybrid" or "keyword"."""
    words = WORD.findall(query)[:MAX_QUERY_WORDS]
    result = {"query": query, "mode": "keyword", "note": None, "terms": words, "results": []}
    if not words:
        return result
    filters, params = "", []
    for clause, value in (("c.ticker = ?", ticker and ticker.upper()), ("c.session_date >= ?", since),
                          ("c.session_date <= ?", until)):
        if value:
            filters += f" AND {clause}"
            params.append(value)

    with closing(connect()) as conn:
        # Keywords: every word is optional (OR); quoting stops punctuation being read as search syntax
        fts_query = " OR ".join('"' + w.replace('"', "") + '"' for w in words)
        keyword = [r[0] for r in conn.execute(
            f"""SELECT c.id FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid
                WHERE chunks_fts MATCH ?{filters} ORDER BY bm25(chunks_fts) LIMIT ?""",
            (fts_query, *params, limit * 3))]

        meaning = []
        if vector_search_available():
            rows = conn.execute(f"SELECT c.id, c.embedding FROM chunks c WHERE c.model = ? AND c.embedding IS NOT NULL{filters}",
                                (EMBED_MODEL, *params)).fetchall()
            if rows:
                try:
                    q = np.asarray(embed([query], "query")[0], dtype=np.float32)
                    matrix = np.vstack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
                    scores = matrix @ q / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(q) + 1e-9)
                    floor = max(MIN_SIMILARITY, float(scores.max()) * MEANING_CUTOFF)
                    meaning = [rows[i]["id"] for i in np.argsort(-scores)[:limit * 3] if scores[i] >= floor]
                    result["mode"] = "hybrid"
                except Exception as e:  # Voyage unreachable: keyword results still come back
                    result["note"] = f"Meaning-based search is unavailable right now ({e}); showing keyword matches."
            else:
                result["note"] = "The search index is still being embedded; showing keyword matches for now."

        fused = {}
        for ranking, label in ((keyword, "keywords"), (meaning, "meaning")):
            for rank, chunk_id in enumerate(ranking):
                entry = fused.setdefault(chunk_id, {"score": 0.0, "matched_by": []})
                entry["score"] += 1 / (RRF_K + rank + 1)
                entry["matched_by"].append(label)
        best = sorted(fused.items(), key=lambda item: -item[1]["score"])[:limit]
        if best:
            ids = [chunk_id for chunk_id, _ in best]
            rows = {r["id"]: r for r in conn.execute(
                f"SELECT * FROM chunks WHERE id IN ({','.join('?' * len(ids))})", ids)}
            result["results"] = [{
                "session_date": rows[i]["session_date"], "status": rows[i]["status"], "ticker": rows[i]["ticker"],
                "heading": rows[i]["heading"], "text": rows[i]["text"].split("\n", 1)[-1],  # without the title prefix
                "score": round(entry["score"], 5), "matched_by": entry["matched_by"],
            } for i, entry in best]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search index for saved reports.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync", help="index new or changed reports")
    commands.add_parser("rebuild", help="delete the index and build it again")
    commands.add_parser("status", help="what's indexed")
    find = commands.add_parser("search", help="search from the terminal")
    find.add_argument("query")
    args = parser.parse_args()
    if args.command == "search":
        for r in search(args.query)["results"]:
            print(f"{r['session_date']}  {r['heading']:<45} matched by {' + '.join(r['matched_by'])}")
    else:
        print(json.dumps({"sync": sync, "rebuild": rebuild, "status": status}[args.command](), indent=2))
