"""Reading the SEC's EDGAR service: which filings a company has made, the documents inside a
filing, and the figures companies report in structured form (XBRL).

It's free and needs no key or account. The SEC asks automated tools to say who they are and to
stay under 10 requests a second, so set SEC_CONTACT to your name and email:

    export SEC_CONTACT="Jane Doe jane@example.com"

Everything here is plain reading and arithmetic: no Claude. filings.py decides what to do with it.
Tests and the test environment replace get_json and get_text, so nothing else talks to the SEC.
"""

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
import zlib
from datetime import date, timedelta
from html.parser import HTMLParser

CONTACT_ENV = "SEC_CONTACT"
DATA = "https://data.sec.gov"
WWW = "https://www.sec.gov"
MIN_GAP_SECONDS = 0.2        # between requests: at most 5 a second (the SEC allows 10)
TIMEOUT_SECONDS = 20
MAX_BYTES = 12_000_000       # the most of one document that's downloaded
MAX_FACTS_BYTES = 80_000_000 # a company's structured figures come as one large file
READABLE = (".htm", ".html", ".txt")

SCALES = {"units": 1, "thousands": 1_000, "millions": 1_000_000, "billions": 1_000_000_000}

# The figures worked out for each company, and the XBRL names companies report them under.
# The first name a company has recent figures for is used for every period, so periods compare like with like.
METRICS = {
    "revenue": {"label": "Revenue", "unit": "USD", "tags": [
        "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax", "RevenuesNetOfInterestExpense"]},
    "gross_profit": {"label": "Gross profit", "unit": "USD", "tags": ["GrossProfit"]},
    "operating_income": {"label": "Operating income", "unit": "USD", "tags": ["OperatingIncomeLoss"]},
    "net_income": {"label": "Net income", "unit": "USD", "tags": [
        "NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"]},
    "eps_diluted": {"label": "Earnings per share (diluted)", "unit": "USD/shares", "tags": ["EarningsPerShareDiluted"]},
}
QUARTER_DAYS, NINE_MONTH_DAYS, YEAR_DAYS = (80, 100), (260, 290), (350, 380)


class EdgarError(Exception):
    """A problem reading from the SEC, with a message to show as it is."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class ContactMissing(EdgarError):
    """SEC_CONTACT isn't set, so nothing can be asked of the SEC."""


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_last_request = 0.0


def contact() -> str:
    """Who we tell the SEC we are. Raises EdgarError if SEC_CONTACT isn't a name and an email."""
    value = " ".join(os.environ.get(CONTACT_ENV, "").split())
    if "@" not in value or len(value) < 6 or "example.com" in value.lower():
        raise ContactMissing(f'Set {CONTACT_ENV} to your name and email first, for example: '
                         f'export {CONTACT_ENV}="Jane Doe jane@yourmail.com". '
                         "The SEC asks automated tools to say who they are.")
    return value


def contact_set() -> bool:
    try:
        contact()
        return True
    except EdgarError:
        return False


def fetch(url: str, max_bytes: int = MAX_BYTES) -> bytes:
    """One request to the SEC, politely: identified, spaced out, and never more than max_bytes."""
    global _last_request
    if not url.startswith((DATA + "/", WWW + "/")):
        raise EdgarError("only sec.gov addresses are read")
    request = urllib.request.Request(url, headers={"User-Agent": contact(), "Accept-Encoding": "gzip"})
    with _lock:  # one at a time, with a gap, whichever thread asks
        wait = MIN_GAP_SECONDS - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                unpack = zlib.decompressobj(47) if (response.headers.get("Content-Encoding") or "").lower() == "gzip" else None
                raw = bytearray()
                while len(raw) <= max_bytes:  # read (and unpack) only as much as is wanted
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    raw += unpack.decompress(chunk, max_bytes + 1 - len(raw)) if unpack else chunk
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise EdgarError("the SEC doesn't have that page", 404) from None
            if e.code in (403, 429):
                raise EdgarError("The SEC refused the request. Check SEC_CONTACT is your name and email. If it is, "
                                 "the SEC is limiting requests from this computer: wait 10 minutes and try again.",
                                 e.code) from None
            raise EdgarError(f"the SEC answered with an error ({e.code})", e.code) from None
        except zlib.error:
            raise EdgarError("the SEC's answer wasn't readable") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise EdgarError(f"couldn't reach the SEC ({getattr(e, 'reason', e)})") from None
        finally:
            _last_request = time.monotonic()
    return bytes(raw[:max_bytes])


def get_json(url: str, max_bytes: int = MAX_BYTES):
    try:
        return json.loads(fetch(url, max_bytes))
    except ValueError:
        raise EdgarError("the SEC's answer wasn't readable") from None


def get_text(url: str, max_bytes: int = MAX_BYTES) -> str:
    raw = fetch(url, max_bytes)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


# ---------------------------------------------------------------------------
# Companies and their filings
# ---------------------------------------------------------------------------

def company_numbers() -> dict[str, dict]:
    """Every company the SEC lists with a ticker: {"AAPL": {"cik": 320193, "name": "Apple Inc."}}."""
    listed = get_json(f"{WWW}/files/company_tickers.json")
    found = {}
    for entry in (listed.values() if isinstance(listed, dict) else listed):
        try:
            found.setdefault(str(entry["ticker"]).upper(), {"cik": int(entry["cik_str"]), "name": str(entry.get("title") or "")})
        except (KeyError, TypeError, ValueError):
            continue
    return found


def folder(cik: int, accession: str) -> str:
    return f"{WWW}/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"


def index_url(cik: int, accession: str) -> str:
    """The filing's own page on sec.gov, listing its documents."""
    return f"{folder(cik, accession)}{accession}-index.htm"


def _stamp(value: str) -> str:
    """'2026-11-09T23:04:33.000Z' -> '2026-11-09T23:04:33Z' (UTC)."""
    value = str(value or "")
    return value[:19] + "Z" if len(value) >= 19 and value[10] == "T" else ""


def list_filings(cik: int) -> dict:
    """A company's latest filings, newest first:
    {"name", "filings": [{accession, form, items, filing_date, report_date, filed_at, primary_doc, description}]}"""
    data = get_json(f"{DATA}/submissions/CIK{int(cik):010d}.json")
    recent = (data.get("filings") or {}).get("recent") or {}
    numbers = recent.get("accessionNumber") or []

    def column(name):
        values = recent.get(name) or []
        return [values[i] if i < len(values) else "" for i in range(len(numbers))]

    columns = {name: column(name) for name in ("form", "items", "filingDate", "reportDate", "acceptanceDateTime",
                                               "primaryDocument", "primaryDocDescription")}
    filings = []
    for i, accession in enumerate(numbers):
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", str(accession)):
            continue
        filings.append({
            "accession": accession, "form": str(columns["form"][i] or "").strip().upper(),
            "items": [code.strip() for code in str(columns["items"][i] or "").split(",") if code.strip()],
            "filing_date": str(columns["filingDate"][i] or "")[:10], "report_date": str(columns["reportDate"][i] or "")[:10],
            "filed_at": _stamp(columns["acceptanceDateTime"][i]),
            "primary_doc": str(columns["primaryDocument"][i] or ""),
            "description": str(columns["primaryDocDescription"][i] or "")})
    filings.sort(key=lambda f: (f["filed_at"] or f["filing_date"], f["accession"]), reverse=True)
    return {"name": str(data.get("name") or ""), "filings": filings}


class _Tables(HTMLParser):
    """Every table in a page as rows of cells: [{"text", "href"}]."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._row, self._cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = {"text": "", "href": None}
        elif tag == "a" and self._cell is not None and self._cell["href"] is None:
            self._cell["href"] = dict(attrs).get("href")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._cell["text"] = " ".join(self._cell["text"].split())
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self.tables and self._row:
                self.tables[-1].append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell["text"] += data


def _guess_type(name: str, primary_doc: str, form: str) -> str:
    if name == primary_doc:
        return form
    match = re.search(r"ex[-_]?(\d{2})[-_.]?(\d{1,2})?", name, re.I)
    return f"EX-{match.group(1)}" + (f".{match.group(2)}" if match.group(2) else "") if match else ""


def filing_documents(cik: int, accession: str, primary_doc: str = "", form: str = "") -> list[dict]:
    """The readable documents in a filing, in order: [{name, type, description, size, url}].
    type is the SEC's own label: the form itself ("8-K") or an exhibit ("EX-99.1", a press release)."""
    base = folder(cik, accession)
    documents = []
    try:
        parser = _Tables()
        parser.feed(get_text(index_url(cik, accession), 2_000_000))
        for table in parser.tables:
            if not table:
                continue
            head = [c["text"].lower() for c in table[0]]
            if "document" not in head or "type" not in head:
                continue
            at = {name: head.index(name) for name in ("document", "type", "description", "size") if name in head}
            for row in table[1:]:
                if len(row) <= max(at.values()):
                    continue
                cell = row[at["document"]]
                # The link may go through the SEC's viewer (/ix?doc=/Archives/...): the file name is its last part either way
                name = ((cell["href"] or "").rsplit("/", 1)[-1] or cell["text"].split(" ")[0]).strip()
                kind = row[at["type"]]["text"].strip().upper()
                if not name or not kind or not name.lower().endswith(READABLE):
                    continue
                size = row[at["size"]]["text"] if "size" in at else ""
                documents.append({"name": name, "type": kind, "url": base + name,
                                  "description": row[at["description"]]["text"] if "description" in at else "",
                                  "size": int(size) if size.isdigit() else None})
    except EdgarError as e:
        if e.status != 404:
            raise
    if documents:
        return documents
    # No readable index page: fall back to the folder listing, guessing each file's type from its name
    listing = get_json(base + "index.json")
    for item in ((listing.get("directory") or {}).get("item") or []):
        name = str(item.get("name") or "")
        kind = _guess_type(name, primary_doc, form)
        if kind and name.lower().endswith(READABLE) and "index" not in name.lower():
            size = str(item.get("size") or "")
            documents.append({"name": name, "type": kind, "url": base + name, "description": "",
                              "size": int(size) if size.isdigit() else None})
    documents.sort(key=lambda d: d["name"] != primary_doc)
    return documents


# ---------------------------------------------------------------------------
# Documents as plain text
# ---------------------------------------------------------------------------

_BLOCKS = {"p", "div", "br", "li", "ul", "ol", "table", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "section",
           "article", "center", "blockquote", "pre", "title"}
_SKIPPED = {"script", "style", "head", "noscript", "ix:header"}
_VOID = {"br", "hr", "img", "input", "meta", "link", "col", "area", "base", "wbr"}
_HIDDEN = re.compile(r"display\s*:\s*none", re.I)


def _join_row(cells: list[str]) -> str:
    """One table row as 'Label | 1,234 | (56)'. Filings often put $, ( and ) in cells of their own."""
    merged = []
    for cell in (" ".join(c.split()) for c in cells):
        if not cell:
            continue
        if merged and (cell in (")", "%", ")%") or merged[-1] in ("$", "(", "$(", "($")):
            merged[-1] += cell
        else:
            merged.append(cell)
    return " | ".join(merged)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self._line = [], []
        self._rows, self._cells = [], []     # stacks, because filings nest tables for layout
        self._skip_tag, self._skip_depth = None, 0

    def _write(self, text: str) -> None:
        (self._cells[-1] if self._cells else self._line).append(text)

    def _break(self) -> None:
        if self._cells:
            self._cells[-1].append(" ")
            return
        text = " ".join("".join(self._line).split())
        if text:
            self.lines.append(text)
        self._line = []

    def handle_starttag(self, tag, attrs):
        if self._skip_tag:
            self._skip_depth += tag == self._skip_tag
            return
        if tag in _SKIPPED or (tag not in _VOID and _HIDDEN.search(dict(attrs).get("style") or "")):
            self._skip_tag, self._skip_depth = tag, 1
            return
        if tag == "tr":
            self._break()
            self._rows.append([])
        elif tag in ("td", "th"):
            self._cells.append([])
        elif tag in _BLOCKS:
            self._break()

    def handle_endtag(self, tag):
        if self._skip_tag:
            if tag == self._skip_tag:
                self._skip_depth -= 1
                if self._skip_depth == 0:
                    self._skip_tag = None
            return
        if tag in ("td", "th") and self._cells:
            text = "".join(self._cells.pop())
            if self._rows:
                self._rows[-1].append(text)
            else:
                self._write(text)
        elif tag == "tr" and self._rows:
            row = _join_row(self._rows.pop())
            if self._cells:           # a table inside another table's cell
                self._cells[-1].append(" " + row + " ")
            elif row:
                self.lines.append(row)
        elif tag in _BLOCKS:
            self._break()

    def handle_data(self, data):
        if not self._skip_tag:
            self._write(data)

    def text(self) -> str:
        while self._cells:  # anything left open by cut-off or untidy HTML
            text = "".join(self._cells.pop())
            (self._rows[-1] if self._rows else self._line).append(text)
        while self._rows:
            row = _join_row(self._rows.pop())
            if row:
                self.lines.append(row)
        self._break()
        return "\n".join(self.lines)


def tidy(text: str) -> str:
    """Curly quotes, long dashes and odd spaces made plain, so quotes can be matched."""
    for old, new in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'), ("–", "-"),
                     ("—", "-"), ("−", "-"), (" ", " "), ("​", ""), ("­", "")):
        text = text.replace(old, new)
    return text


def to_text(html: str) -> str:
    """A filing's HTML as plain text: one line per paragraph or table row, cells separated by ' | '.
    Hidden parts (scripts, styles, inline-XBRL headers) are left out."""
    if "<" not in html:
        return tidy(html)
    parser = _Text()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # untidy or cut-off HTML: keep what was read
        pass
    return tidy(parser.text())


def discussion(text: str, annual: bool) -> str:
    """Management's discussion of the results from a quarterly (10-Q) or annual (10-K) report,
    or '' if it can't be found. The heading appears in the contents list too, so the longest match wins."""
    number, ends = ("7", r"7a|8") if annual else ("2", r"3|4")
    start = re.compile(rf"(?im)^\s*item\s*{number}\s*[.:\-]?\s*\|?\s*management'?s\s+discussion")
    end = re.compile(rf"(?im)^\s*item\s*(?:{ends})\s*[.:\-]?\s*\|?\s*[a-z]")
    best = ""
    for match in start.finditer(text):
        stop = end.search(text, match.end())
        body = text[match.start(): stop.start() if stop else len(text)]
        if len(body) > len(best):
            best = body
    return best.strip() if len(best) > 2000 else ""


# ---------------------------------------------------------------------------
# Figures (XBRL)
# ---------------------------------------------------------------------------

def company_facts(cik: int) -> dict:
    """Every figure a company has reported in structured form. Large: often several megabytes."""
    return get_json(f"{DATA}/api/xbrl/companyfacts/CIK{int(cik):010d}.json", MAX_FACTS_BYTES)


def _periods_of(facts: list) -> list[dict]:
    """Each period once, taking the most recently filed value (later reports restate earlier ones)."""
    best = {}
    for fact in facts or []:
        try:
            start, end, value = date.fromisoformat(fact["start"]), date.fromisoformat(fact["end"]), float(fact["val"])
        except (KeyError, TypeError, ValueError):
            continue  # a balance at a point in time, or something unreadable
        key = (start, end)
        if key not in best or str(fact.get("filed") or "") >= best[key]["filed"]:
            best[key] = {"start": start, "end": end, "value": value, "filed": str(fact.get("filed") or ""),
                         "accession": fact.get("accn"), "form": fact.get("form"), "derived": False}
    return list(best.values())


def _days(period: dict) -> int:
    return (period["end"] - period["start"]).days + 1


def _between(days: int, limits: tuple[int, int]) -> bool:
    return limits[0] <= days <= limits[1]


def _split(periods: list[dict]) -> tuple[dict, dict]:
    """(quarters, years) by end date. Annual reports don't give the fourth quarter on its own, so it's
    worked out: the year minus the first nine months (or minus the other three quarters)."""
    quarters = {p["end"]: p for p in periods if _between(_days(p), QUARTER_DAYS)}
    years = {p["end"]: p for p in periods if _between(_days(p), YEAR_DAYS)}
    for year in years.values():
        if any(abs((end - year["end"]).days) <= 5 for end in quarters):
            continue
        nine = [p for p in periods if _between(_days(p), NINE_MONTH_DAYS) and abs((p["start"] - year["start"]).days) <= 5
                and 75 <= (year["end"] - p["end"]).days <= 105]
        inside = [q for q in quarters.values()
                  if q["start"] >= year["start"] - timedelta(days=5) and q["end"] < year["end"] - timedelta(days=60)]
        if nine:
            first = max(nine, key=lambda p: p["end"])
            value, start = year["value"] - first["value"], first["end"] + timedelta(days=1)
        elif len(inside) == 3:
            value, start = year["value"] - sum(q["value"] for q in inside), max(q["end"] for q in inside) + timedelta(days=1)
        else:
            continue
        quarters[year["end"]] = {"start": start, "end": year["end"], "value": value, "filed": year["filed"],
                                 "accession": year["accession"], "form": year["form"], "derived": True}
    return quarters, years


def periods(facts: dict) -> dict:
    """Quarterly and yearly figures from a company's structured data:
    {metric: {"tag", "quarters": {end date: period}, "years": {end date: period}}}.
    A metric the company doesn't report (a bank has no gross profit) is left out."""
    reported = (facts.get("facts") or {}).get("us-gaap") or {}
    found = {}
    for metric, spec in METRICS.items():
        best = None
        for tag in spec["tags"]:
            quarters, years = _split(_periods_of(((reported.get(tag) or {}).get("units") or {}).get(spec["unit"])))
            if not quarters and not years:
                continue
            latest = max([*quarters, *years])
            if best is None or latest > best[0]:
                best = (latest, {"tag": tag, "quarters": quarters, "years": years})
        if best:
            found[metric] = best[1]
    return found


def nearest(by_end: dict, target: date, tolerance_days: int = 12) -> dict | None:
    """The period ending closest to a date (companies' quarters end a few days apart from year to year)."""
    close = [p for end, p in by_end.items() if abs((end - target).days) <= tolerance_days]
    return min(close, key=lambda p: abs((p["end"] - target).days)) if close else None


def parse_number(written: str) -> float | None:
    """A number as a filing writes it: '94,930', '$1.64', '(1,234)' (negative)."""
    text = written.replace("$", "").replace(" ", "").strip()
    negative = text.startswith("(") and text.endswith(")") or text.startswith("-")
    text = text.strip("()-")
    if not re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?|\d+(\.\d+)?", text):
        return None
    value = float(text.replace(",", ""))
    return -value if negative else value
