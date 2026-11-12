"""Offline tests for company filings: reading the SEC (edgar.py) and first takes (filings.py).
The SEC, Claude and Discord are faked, so these are free and need no internet.

Run from the project folder:
    pytest -v tests/test_filings.py

Live check of the SEC's real data (free, needs internet and your SEC_CONTACT):
    LIVE_TESTS=1 pytest -v -s -k live_filings
"""

import asyncio
import io
import json
import os
import sys
import time
import urllib.error
import zlib
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import alerts  # noqa: E402
import api  # noqa: E402
import ask  # noqa: E402
import edgar  # noqa: E402
import events  # noqa: E402
import filings  # noqa: E402
import market_tools  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
from claude_agent_sdk import ResultMessage  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

LIVE_CONTACT = os.environ.get("SEC_CONTACT")  # kept for the live test: conftest.py removes it for every test
ET = market_tools.ET
CLOCK = {"now": datetime(2026, 10, 29, 9, 0, tzinfo=ET)}  # a Thursday morning in New York
SEC = {}      # address -> what the fake SEC answers: JSON (a dict), text, or an error to raise
FILED = {}    # company number -> its filings, as the SEC lists them
ASKED = []    # every address the code asked for
CLAUDE = []   # every (system prompt, prompt) the fake Claude was sent
SENT = []     # Discord messages "sent"
REPLY = {}    # what the fake Claude answers: {"value": a dict, text or an error}

NWND = 1111   # Northwind, the company most tests use
RESULTS, PREVIOUS = "0000001111-26-000090", "0000001111-26-000050"
REPORT = "0000001111-26-000095"


# ---------------------------------------------------------------------------
# A fake SEC
# ---------------------------------------------------------------------------

def fake_sec(url, max_bytes=None):
    ASKED.append(url)
    if url not in SEC:
        raise edgar.EdgarError("the SEC doesn't have that page", 404)
    if isinstance(SEC[url], Exception):
        raise SEC[url]
    return SEC[url] if max_bytes is None or not isinstance(SEC[url], str) else SEC[url][:max_bytes]


def companies(*listed):
    """The SEC's list of companies: (ticker, number, name)."""
    SEC[f"{edgar.WWW}/files/company_tickers.json"] = {
        str(i): {"cik_str": cik, "ticker": ticker, "title": name} for i, (ticker, cik, name) in enumerate(listed)}


def filing(cik, accession, form, filed, items="", report_date="", docs=(), index=True):
    """Add a filing to a company's list, with its index page and documents.
    filed is New York time ('2026-10-28 16:05'). docs are (file name, type, html)."""
    when = datetime.strptime(filed, "%Y-%m-%d %H:%M").replace(tzinfo=ET)
    FILED.setdefault(cik, []).append({
        "accessionNumber": accession, "filingDate": filed[:10], "reportDate": report_date,
        "acceptanceDateTime": when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"), "form": form,
        "items": items, "primaryDocument": docs[0][0] if docs else "", "primaryDocDescription": form})
    rows = sorted(FILED[cik], key=lambda r: r["acceptanceDateTime"], reverse=True)
    SEC[f"{edgar.DATA}/submissions/CIK{cik:010d}.json"] = {
        "cik": str(cik), "name": "A COMPANY INC", "filings": {"recent": {k: [r[k] for r in rows] for k in rows[0]}, "files": []}}
    base = edgar.folder(cik, accession)
    path = base.replace(edgar.WWW, "")
    table = "".join(
        f'<tr><td scope="row">{n}</td><td scope="row">{kind}</td><td scope="row">'
        + (f'<a href="/ix?doc={path}{name}">{name}</a> <span>iXBRL</span>' if n == 1 else f'<a href="{path}{name}">{name}</a>')
        + f'</td><td scope="row">{kind}</td><td scope="row">{len(html)}</td></tr>'
        for n, (name, kind, html) in enumerate(docs, 1))
    if index:
        SEC[edgar.index_url(cik, accession)] = (
            '<html><body><div class="formGrouping"><div class="infoHead">Filing Date</div></div>'
            '<table class="tableFile" summary="Document Format Files"><tr><th scope="col">Seq</th>'
            '<th scope="col">Description</th><th scope="col">Document</th><th scope="col">Type</th><th scope="col">Size</th></tr>'
            f'{table}<tr><td scope="row">&nbsp;</td><td scope="row">Complete submission text file</td><td scope="row">'
            f'<a href="{path}{accession}.txt">{accession}.txt</a></td><td scope="row">&nbsp;</td><td scope="row">99</td></tr></table>'
            '<table class="tableFile" summary="Data Files"><tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th>'
            f'<th>Size</th></tr><tr><td>9</td><td>XBRL</td><td><a href="{path}data.xml">data.xml</a></td><td>XML</td><td>5</td></tr>'
            '</table></body></html>')
    SEC[base + "index.json"] = {"directory": {"name": path, "parent-dir": path, "item": [
        {"last-modified": "2026-10-28 16:05:00", "name": name, "type": "text.gif", "size": str(len(html))} for name, _, html in docs]}}
    for name, _, html in docs:
        SEC[base + name] = html


def press_release(quarter="third", ended="September 30, 2026", revenue=12_400, gross=8_100, operating=4_000, net=3_200,
                  eps="2.67", year_ago=(10_000, 6_500, 3_000, 2_400, "2.00"), extra=""):
    return f"""<html><head><title>EX-99.1</title><style>p {{}}</style></head><body>
<ix:header><ix:hidden>0001111 false 2026-09-30</ix:hidden></ix:header>
<p>Northwind Reports {quarter.title()} Quarter Results</p>
<p>REDMOND, Wash. &#8212; Northwind Corp. today announced results for the quarter ended {ended}.</p>
<p>Revenue was ${revenue / 1000:.1f} billion and increased from a year earlier.</p>
<p>Cloud revenue grew 30% on demand for AI services.</p>
<p>&#8220;Customers are choosing Northwind for their most important workloads,&#8221; said the chief executive.</p>
<p>Business outlook: The company expects fourth-quarter revenue of $12.8 billion to $13.2 billion.</p>
{extra}
<table><tr><td>(In millions, except per share amounts)</td><td></td><td>Three Months Ended</td></tr>
<tr><td>Total revenue</td><td>$</td><td>{revenue:,}</td><td></td><td>$</td><td>{year_ago[0]:,}</td></tr>
<tr><td>Gross margin</td><td></td><td>{gross:,}</td><td></td><td></td><td>{year_ago[1]:,}</td></tr>
<tr><td>Operating income</td><td></td><td>{operating:,}</td><td></td><td></td><td>{year_ago[2]:,}</td></tr>
<tr><td>Other expense, net</td><td>(</td><td>120</td><td>)</td><td>(</td><td>90</td><td>)</td></tr>
<tr><td>Net income</td><td>$</td><td>{net:,}</td><td></td><td>$</td><td>{year_ago[3]:,}</td></tr>
<tr><td>Diluted earnings per share</td><td>$</td><td>{eps}</td><td></td><td>$</td><td>{year_ago[4]}</td></tr></table>
</body></html>"""


COVER = """<html><body><p>UNITED STATES SECURITIES AND EXCHANGE COMMISSION</p><p>FORM 8-K</p>
<p>Item 2.02 Results of Operations and Financial Condition.</p>
<p>On October 28, 2026, Northwind Corp. issued a press release announcing its results. A copy is attached as Exhibit 99.1.</p>
</body></html>"""


def fact(start, end, value, form="10-Q", filed=None):
    return {"start": start, "end": end, "val": value, "accn": "0000001111-26-000001", "fy": int(end[:4]), "fp": "Q",
            "form": form, "filed": filed or (date.fromisoformat(end) + timedelta(days=28)).isoformat()}


M = 1_000_000
# (revenue, gross profit, operating income, net income, earnings per share) for each quarter, in $ millions
HISTORY = {("2025-07-01", "2025-09-30"): (10_000, 6_500, 3_000, 2_400, 2.00),
           ("2026-04-01", "2026-06-30"): (11_800, 7_700, 3_700, 2_950, 2.46)}
THIRD_QUARTER = {("2026-07-01", "2026-09-30"): (12_400, 8_100, 4_000, 3_200, 2.67)}


def set_facts(cik, quarters, revenue_tag="Revenues", leave_out=()):
    """The company's structured figures, as the SEC publishes them."""
    tags = {revenue_tag: 0, "GrossProfit": 1, "OperatingIncomeLoss": 2, "NetIncomeLoss": 3}
    reported = {tag: {"label": tag, "units": {"USD": [fact(s, e, values[i] * M) for (s, e), values in quarters.items()]}}
                for tag, i in tags.items() if tag not in leave_out}
    if "EarningsPerShareDiluted" not in leave_out:
        reported["EarningsPerShareDiluted"] = {"units": {"USD/shares": [fact(s, e, v[4]) for (s, e), v in quarters.items()]}}
    SEC[f"{edgar.DATA}/api/xbrl/companyfacts/CIK{cik:010d}.json"] = {"cik": cik, "entityName": "x", "facts": {
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{"end": "2026-10-20", "val": 1}]}}},
        "us-gaap": reported}}


def results_reply(**changes):
    """What a careful Claude would say about press_release()."""
    reply = {
        "headline": "Northwind reported third-quarter revenue of $12.4 billion, up from a year earlier.",
        "period_end": "2026-09-30",
        "figures": [
            {"metric": "revenue", "as_written": "12,400", "scale": "millions", "quote": "Total revenue | $12,400 | $10,000"},
            {"metric": "gross_profit", "as_written": "8,100", "scale": "millions", "quote": "Gross margin | 8,100 | 6,500"},
            {"metric": "operating_income", "as_written": "4,000", "scale": "millions", "quote": "Operating income | 4,000 | 3,000"},
            {"metric": "net_income", "as_written": "3,200", "scale": "millions", "quote": "Net income | $3,200 | $2,400"},
            {"metric": "eps_diluted", "as_written": "2.67", "scale": "units", "quote": "Diluted earnings per share | $2.67 | $2.00"}],
        "points": [
            {"text": "Cloud revenue grew 30%, driven by AI services.", "quote": "Cloud revenue grew 30% on demand for AI services."},
            {"text": "Management says customers are moving key workloads to it.",
             "quote": "“Customers are choosing Northwind for their most important workloads,” said the chief executive."}],
        "guidance": [{"text": "It expects fourth-quarter revenue of $12.8 billion to $13.2 billion.", "direction": "raised",
                      "quote": "The company expects fourth-quarter revenue of $12.8 billion to $13.2 billion."}],
        "changes": []}
    reply.update(changes)
    return reply


def fake_claude(system_prompt, prompt):
    CLAUDE.append((system_prompt, prompt))
    reply = REPLY["value"]
    if isinstance(reply, Exception):
        raise reply
    return (reply if isinstance(reply, str) else json.dumps(reply)), 0.08


def northwind():
    """Northwind's last two results announcements, and its figures up to the quarter before."""
    companies(("NWND", NWND, "NORTHWIND CORP"))
    filing(NWND, PREVIOUS, "8-K", "2026-07-29 16:05", "2.02,9.01", "2026-07-29", docs=[
        ("nwnd-8k.htm", "8-K", COVER),
        ("nwnd-ex991.htm", "EX-99.1", press_release("second", "June 30, 2026", 11_800, 7_700, 3_700, 2_950, "2.46",
                                                    extra="<p>Supply constraints limited growth in the quarter.</p>"))])
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02,9.01", "2026-10-28", docs=[
        ("nwnd-8k.htm", "8-K", COVER), ("nwnd-ex991.htm", "EX-99.1", press_release())])
    set_facts(NWND, HISTORY)


@pytest.fixture
def sec(tmp_path, monkeypatch):
    """A temporary watchlist and database, a fixed clock, and a fake SEC, Claude and Discord.
    Returns the watchlist file."""
    for store in (SEC, FILED, ASKED, CLAUDE, SENT):
        store.clear()
    CLOCK["now"] = datetime(2026, 10, 29, 9, 0, tzinfo=ET)
    REPLY["value"] = results_reply()
    path = tmp_path / "watchlist.txt"
    path.write_text("NWND\n")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", path)
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.setattr(market_tools, "now_et", lambda: CLOCK["now"])
    monkeypatch.setattr(edgar, "get_json", fake_sec)
    monkeypatch.setattr(edgar, "get_text", fake_sec)
    monkeypatch.setattr(filings, "ask_claude", fake_claude)
    monkeypatch.setattr(events, "_names", {"NWND": "Northwind"})
    monkeypatch.setattr(alerts, "send", SENT.append)
    reports_db.connect().close()
    northwind()
    return path


def listed(ticker=None):
    with closing(reports_db.connect(readonly=True)) as conn:
        return filings.list_filings(conn, ticker)


def the(accession):
    with closing(reports_db.connect(readonly=True)) as conn:
        return filings.get_filing(conn, accession)


def figures_of(accession=RESULTS):
    return {r["metric"]: r for r in the(accession)["read"]["figures"]["rows"]}


# ---------------------------------------------------------------------------
# edgar.py: documents as text
# ---------------------------------------------------------------------------

def test_a_filing_becomes_plain_text_with_one_line_per_table_row():
    text = edgar.to_text(press_release())
    assert "Northwind Reports Third Quarter Results" in text.splitlines()[0]
    assert "Total revenue | $12,400 | $10,000" in text      # the $ joins its number, empty cells go
    assert "Other expense, net | (120) | (90)" in text      # ( and ) in cells of their own
    assert 'REDMOND, Wash. - Northwind' in text and '"Customers are choosing' in text  # dashes and quotes made plain
    assert "0001111 false" not in text and "p {}" not in text and "EX-99.1" not in text  # hidden parts left out


def test_text_copes_with_nested_tables_hidden_parts_and_cut_off_html():
    html = ('<div style="display: none">secret <div>nested</div> still secret</div><p>Shown</p>'
            '<table><tr><td><table><tr><td>inner</td><td>cell</td></tr></table></td><td>outer</td></tr>'
            '<tr><td>Revenue</td><td>1,234')  # the download stopped here
    assert edgar.to_text(html).splitlines() == ["Shown", "inner | cell | outer", "Revenue | 1,234"]
    assert edgar.to_text("Plain text, no tags — as some old filings are.") == "Plain text, no tags - as some old filings are."


def test_managements_discussion_is_found_past_the_contents_page():
    body = "We sell software. " * 200
    report = "\n".join(["Table of contents", "Item 1. Financial Statements 3",
                        "Item 2. Management's Discussion and Analysis of Financial Condition 20",
                        "Item 3. Quantitative and Qualitative Disclosures 40", "Item 1. Financial Statements", "numbers " * 50,
                        "Item 2. | Management’s Discussion and Analysis of Financial Condition and Results of Operations",
                        body, "Item 3. Quantitative and Qualitative Disclosures About Market Risk", "risk " * 50])
    found = edgar.discussion(edgar.tidy(report), annual=False)
    assert found.startswith("Item 2. | Management's Discussion") and found.rstrip().endswith("We sell software.")
    assert "risk risk" not in found and "Table of contents" not in found
    annual = report.replace("Item 2.", "Item 7.").replace("Item 3.", "Item 7A.")
    assert edgar.discussion(edgar.tidy(annual), annual=True).startswith("Item 7.")
    assert edgar.discussion("A report with no such heading. " * 200, annual=False) == ""


# ---------------------------------------------------------------------------
# edgar.py: filings and documents
# ---------------------------------------------------------------------------

def test_a_companys_filings_are_read_from_the_secs_lists(sec):
    filing(NWND, "0000001111-26-000091", "4", "2026-10-28 18:00")
    FILED[NWND].append({"accessionNumber": "not-a-number", "filingDate": "2026-10-28", "form": "8-K"})  # a row to skip
    rows = FILED[NWND]
    SEC[f"{edgar.DATA}/submissions/CIK{NWND:010d}.json"]["filings"]["recent"] = {
        "accessionNumber": [r["accessionNumber"] for r in rows], "filingDate": [r["filingDate"] for r in rows],
        "form": [r["form"] for r in rows], "items": [r.get("items", "") for r in rows][:3],  # a list that's too short
        "acceptanceDateTime": [r.get("acceptanceDateTime", "") for r in rows]}

    found = edgar.list_filings(NWND)["filings"]

    assert [f["accession"] for f in found] == ["0000001111-26-000091", RESULTS, PREVIOUS]  # newest first
    assert found[1]["items"] == ["2.02", "9.01"] and found[1]["filed_at"] == "2026-10-28T20:05:00Z"  # 4:05pm New York
    assert found[1]["filing_date"] == "2026-10-28" and found[0]["form"] == "4" and found[0]["primary_doc"] == ""


def test_a_filings_documents_come_from_its_index_page(sec):
    documents = edgar.filing_documents(NWND, RESULTS)
    assert [(d["name"], d["type"]) for d in documents] == [("nwnd-8k.htm", "8-K"), ("nwnd-ex991.htm", "EX-99.1")]
    assert documents[0]["url"] == f"{edgar.WWW}/Archives/edgar/data/1111/000000111126000090/nwnd-8k.htm"  # not the /ix?doc= viewer
    assert documents[1]["size"] == len(press_release())  # the .txt bundle and data files are left out


def test_without_an_index_page_documents_are_guessed_from_their_names(sec):
    filing(NWND, "0000001111-26-000092", "8-K", "2026-10-28 17:00", "5.02,9.01", index=False, docs=[
        ("d123d8k.htm", "8-K", COVER), ("d123dex991.htm", "EX-99.1", "<p>x</p>"), ("pic.jpg", "GRAPHIC", "")])
    documents = edgar.filing_documents(NWND, "0000001111-26-000092", "d123d8k.htm", "8-K")
    assert [(d["name"], d["type"]) for d in documents] == [("d123d8k.htm", "8-K"), ("d123dex991.htm", "EX-99.1")]


def test_requests_say_who_they_are_and_keep_their_distance(monkeypatch):
    sent, waits = [], []

    class Response:
        headers = {"Content-Encoding": "gzip"}

        def __init__(self):
            packer = zlib.compressobj(wbits=31)  # gzip, as the SEC sends it
            self.read = io.BytesIO(packer.compress(b'{"ok": true}' + b" " * 200_000) + packer.flush()).read

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(edgar.urllib.request, "urlopen", lambda request, timeout: sent.append(request) or Response())
    monkeypatch.setattr(edgar.time, "sleep", waits.append)
    monkeypatch.setattr(edgar, "_last_request", time.monotonic())

    with pytest.raises(edgar.ContactMissing, match="Set SEC_CONTACT"):
        edgar.fetch(f"{edgar.DATA}/submissions/CIK0000001111.json")       # nothing is sent without a contact
    monkeypatch.setenv("SEC_CONTACT", "Jane Doe jane@example.com")
    with pytest.raises(edgar.ContactMissing):
        edgar.fetch(f"{edgar.DATA}/x")                                     # the guide's placeholder doesn't count
    assert sent == []
    monkeypatch.setenv("SEC_CONTACT", "  Test Runner   test@tests.invalid ")

    assert edgar.get_json(f"{edgar.DATA}/submissions/CIK0000001111.json") == {"ok": True}  # unpacked
    assert sent[0].get_header("User-agent") == "Test Runner test@tests.invalid"
    assert waits and 0 < waits[0] <= edgar.MIN_GAP_SECONDS                  # it waited before asking again
    assert edgar.fetch(f"{edgar.WWW}/big", max_bytes=5) == b'{"ok"'         # never more than asked for
    with pytest.raises(edgar.EdgarError, match="only sec.gov"):
        edgar.fetch("https://example.org/Archives/x")


@pytest.mark.parametrize("code, message, status", [
    (403, "wait 10 minutes", 403), (429, "wait 10 minutes", 429), (404, "doesn't have that page", 404), (500, "an error \\(500\\)", 500)])
def test_the_secs_refusals_are_explained(monkeypatch, code, message, status):
    def refuse(request, timeout):
        raise urllib.error.HTTPError(request.full_url, code, "no", {}, io.BytesIO(b""))

    monkeypatch.setenv("SEC_CONTACT", "Test Runner test@tests.invalid")
    monkeypatch.setattr(edgar.urllib.request, "urlopen", refuse)
    monkeypatch.setattr(edgar.time, "sleep", lambda s: None)
    with pytest.raises(edgar.EdgarError, match=message) as refused:
        edgar.fetch(f"{edgar.DATA}/submissions/CIK0000001111.json")
    assert refused.value.status == status


# ---------------------------------------------------------------------------
# edgar.py: figures
# ---------------------------------------------------------------------------

# Microsoft's real revenue and earnings-per-share facts, as the SEC published them (November 2026)
MSFT_REVENUE = [
    ("2024-07-01", "2025-03-31", 205283, "10-Q", "2025-04-30"), ("2025-01-01", "2025-03-31", 70066, "10-Q", "2025-04-30"),
    ("2025-01-01", "2025-03-31", 70066, "10-Q", "2026-04-29"), ("2024-07-01", "2025-06-30", 281724, "10-K", "2025-07-30"),
    ("2025-07-01", "2025-09-30", 77673, "10-Q", "2025-10-29"), ("2025-07-01", "2025-09-30", 77673, "10-Q", "2026-10-28"),
    ("2025-07-01", "2025-12-31", 158946, "10-Q", "2026-01-28"), ("2025-10-01", "2025-12-31", 81273, "10-Q", "2026-01-28"),
    ("2025-07-01", "2026-03-31", 241832, "10-Q", "2026-04-29"), ("2026-01-01", "2026-03-31", 82886, "10-Q", "2026-04-29"),
    ("2025-07-01", "2026-06-30", 331839, "10-K", "2026-07-29"), ("2026-07-01", "2026-09-30", 92279, "10-Q", "2026-10-28")]
MSFT_EPS = [("2025-07-01", "2025-09-30", 3.72, "10-Q", "2025-10-29"), ("2025-07-01", "2025-12-31", 8.87, "10-Q", "2026-01-28"),
            ("2025-10-01", "2025-12-31", 5.16, "10-Q", "2026-01-28"), ("2025-07-01", "2026-03-31", 13.14, "10-Q", "2026-04-29"),
            ("2026-01-01", "2026-03-31", 4.27, "10-Q", "2026-04-29"), ("2025-07-01", "2026-06-30", 17.95, "10-K", "2026-07-29")]


def company_facts(**tags):
    return {"facts": {"us-gaap": {tag: {"units": {("USD/shares" if "PerShare" in tag else "USD"): [
        fact(s, e, v * (1 if "PerShare" in tag else M), form, filed) for s, e, v, form, filed in rows]}}
        for tag, rows in tags.items()}}}


def test_quarters_come_from_structured_data_and_the_fourth_is_worked_out():
    known = edgar.periods(company_facts(RevenueFromContractWithCustomerExcludingAssessedTax=MSFT_REVENUE,
                                        EarningsPerShareDiluted=MSFT_EPS))
    revenue, eps = known["revenue"], known["eps_diluted"]

    assert revenue["tag"] == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert {str(end): q["value"] / M for end, q in revenue["quarters"].items() if not q["derived"]} == {
        "2025-03-31": 70066, "2025-09-30": 77673, "2025-12-31": 81273, "2026-03-31": 82886, "2026-09-30": 92279}
    # The annual report gives only the year: April to June is the year minus the first nine months
    fourth = revenue["quarters"][date(2026, 6, 30)]
    assert fourth["derived"] and fourth["value"] / M == 331839 - 241832 and fourth["start"] == date(2026, 4, 1)
    assert revenue["quarters"][date(2025, 6, 30)]["value"] / M == 281724 - 205283
    assert {str(end): y["value"] / M for end, y in revenue["years"].items()} == {"2025-06-30": 281724, "2026-06-30": 331839}
    assert round(eps["quarters"][date(2026, 6, 30)]["value"], 2) == 4.81 and eps["quarters"][date(2026, 6, 30)]["derived"]
    assert set(known) == {"revenue", "eps_diluted"}  # nothing is invented for figures the company doesn't report


def test_a_fourth_quarter_can_also_be_the_year_minus_three_quarters():
    rows = [("2025-01-01", "2025-03-31", 100, "10-Q", "2025-04-30"), ("2025-04-01", "2025-06-30", 110, "10-Q", "2025-07-30"),
            ("2025-07-01", "2025-09-30", 120, "10-Q", "2025-10-30"), ("2025-01-01", "2025-12-31", 460, "10-K", "2026-02-10")]
    quarters = edgar.periods(company_facts(Revenues=rows))["revenue"]["quarters"]
    assert quarters[date(2025, 12, 31)]["value"] / M == 130 and quarters[date(2025, 12, 31)]["derived"]
    two = edgar.periods(company_facts(Revenues=[rows[0], rows[1], rows[3]]))["revenue"]["quarters"]
    assert date(2025, 12, 31) not in two  # with a quarter missing, nothing is guessed


def test_a_restated_figure_replaces_the_original():
    rows = [("2025-07-01", "2025-09-30", 100, "10-Q", "2025-10-30"), ("2025-07-01", "2025-09-30", 97, "10-Q", "2026-10-30")]
    assert edgar.periods(company_facts(Revenues=rows))["revenue"]["quarters"][date(2025, 9, 30)]["value"] / M == 97


def test_the_name_with_the_newest_figures_is_used_for_every_period():
    old = [("2019-01-01", "2019-03-31", 50, "10-Q", "2019-04-30")]
    new = [("2025-07-01", "2025-09-30", 100, "10-Q", "2025-10-30"), ("2026-07-01", "2026-09-30", 120, "10-Q", "2026-10-30")]
    known = edgar.periods(company_facts(SalesRevenueNet=old, RevenuesNetOfInterestExpense=new))
    assert known["revenue"]["tag"] == "RevenuesNetOfInterestExpense" and len(known["revenue"]["quarters"]) == 2


def test_quarters_that_end_a_few_days_apart_still_match():
    # A 52/53-week year: quarters end on the last Saturday of the month, not the same date each year
    rows = [("2025-06-29", "2025-09-27", 100, "10-Q", "2025-10-30"), ("2026-06-28", "2026-09-26", 120, "10-Q", "2026-10-30")]
    quarters = edgar.periods(company_facts(Revenues=rows))["revenue"]["quarters"]
    assert edgar.nearest(quarters, date(2026, 9, 26) - timedelta(days=365))["value"] / M == 100
    assert edgar.nearest(quarters, date(2026, 3, 28)) is None  # a different quarter is never used instead


@pytest.mark.parametrize("written, value", [
    ("94,930", 94930), ("$1.64", 1.64), ("(1,234)", -1234), ("-5.2", -5.2), ("$ 77,673", 77673), ("12.4", 12.4),
    ("1,23", None), ("about 5", None), ("", None), ("12,400 million", None)])
def test_numbers_are_read_as_written(written, value):
    assert edgar.parse_number(written) == value


# ---------------------------------------------------------------------------
# Naming filings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("form, items, kind, title, serious", [
    ("8-K", ["2.02", "9.01"], "results", "Results announcement", False),
    ("8-K", ["2.02", "5.02", "9.01"], "results", "Results announcement; Directors or senior officers leaving or appointed", True),
    ("8-K", ["5.02", "9.01"], "announcement", "Directors or senior officers leaving or appointed", True),
    ("8-K", ["7.01", "9.01"], "announcement", "Information shared with investors", False),
    ("8-K", ["4.02"], "announcement", "Earlier financial statements can no longer be relied on", True),
    ("8-K", ["6.66"], "announcement", "Item 6.66", False),
    ("8-K", [], "announcement", "Announcement", False),
    ("8-K/A", ["2.02", "9.01"], "results", "Amended: Results announcement", False),
    ("10-Q", [], "quarterly", "Quarterly report", False),
    ("10-K/A", [], "annual", "Amended: Annual report", False),
    ("NT 10-Q", [], "late", "Says its quarterly report will be late", True),
    ("NT 10-K", [], "late", "Says its annual report will be late", True),
    ("6-K", [], "foreign", "Report from a company based outside the US", False),
    ("20-F", [], "annual", "Annual report", False),
])
def test_filings_are_named_in_plain_words(form, items, kind, title, serious):
    about = filings.describe(form, items)
    assert (about["kind"], about["title"], about["serious"], about["amended"]) == (kind, title, serious, form.endswith("/A"))


@pytest.mark.parametrize("form", ["4", "SC 13G", "424B2", "S-8", "DEF 14A", "144"])
def test_forms_that_arent_followed_are_ignored(form):
    assert filings.describe(form, []) is None


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("quote, found", [
    ("Cloud revenue grew 30% on demand for AI services.", True),
    ("cloud revenue grew 30%  on demand", True),                                   # capitals and spacing don't matter
    ("Total revenue | $12,400 | $10,000", True),                                  # a table row
    ("Total revenue $12,400 $10,000", True),                                      # ...without the separators
    ("“Customers are choosing Northwind for their most important workloads,”", True),  # curly quotes
    ("Northwind Corp. today announced ... the quarter ended September 30, 2026", True),          # words skipped with ...
    ("the quarter ended September 30, 2026 ... Northwind Corp. today announced", False),         # ...but not out of order
    ("Cloud revenue grew 35% on demand for AI services.", False),                 # a changed number
    ("Revenue grew strongly across all segments.", False),                        # not in the filing
    ("Revenue was", False), ("", False), (None, False),                           # too short to prove anything
])
def test_a_quote_counts_only_if_its_in_the_filing(quote, found):
    assert filings.quoted(quote, filings._plain(edgar.to_text(press_release()))) is found


# ---------------------------------------------------------------------------
# Looking for filings
# ---------------------------------------------------------------------------

def test_a_check_lists_new_filings_once(sec):
    filing(NWND, "0000001111-26-000091", "4", "2026-10-28 18:00")                           # an insider trade: not followed
    filing(NWND, "0000001111-26-000010", "10-Q", "2026-04-29 16:10", report_date="2026-03-31")  # older than the lookback

    first = filings.check(read_new=False)
    second = filings.check(read_new=False)

    assert first["status"] == "ok" and first["new_filings"] == 2 and first["companies"] == 1 and first["reads"] == 0
    assert [f["accession"] for f in listed()] == [RESULTS, PREVIOUS]
    assert second["new_filings"] == 0 and second["new"] == []
    newest = listed()[0]
    assert (newest["kind"], newest["kind_label"], newest["title"]) == ("results", "Results", "Results announcement")
    assert newest["items"][0] == {"code": "2.02", "label": "Results announced"} and newest["read"] is None
    assert newest["url"].endswith("/000000111126000090/0000001111-26-000090-index.htm")
    assert ASKED.count(f"{edgar.WWW}/files/company_tickers.json") == 1 and CLAUDE == []  # the company list is asked for once


def test_an_empty_watchlist_or_a_filing_without_a_time_is_no_trouble(sec):
    FILED[NWND].append({"accessionNumber": "0000001111-26-000091", "filingDate": "2026-10-28", "reportDate": "", "form": "8-K",
                        "acceptanceDateTime": "", "items": "8.01", "primaryDocument": "x.htm", "primaryDocDescription": "8-K"})
    filing(NWND, "0000001111-26-000092", "8-K", "2026-10-28 18:00", "8.01", docs=[("y.htm", "8-K", COVER)])  # rebuilds the list
    assert filings.check(read_new=False)["new_filings"] == 3  # the one with no acceptance time is left out
    assert "0000001111-26-000091" not in [f["accession"] for f in listed()]
    sec.write_text("# nothing tracked yet\n")
    result = filings.check()
    assert (result["status"], result["companies"], result["new_filings"]) == ("ok", 0, 0)


def test_funds_and_unknown_tickers_are_skipped_quietly(sec):
    sec.write_text("NWND\nSPY\n")  # the SEC's company list has no SPY: funds don't file these forms

    result = filings.check(read_new=False)
    filings.check(read_new=False)

    with closing(reports_db.connect(readonly=True)) as conn:
        assert filings.not_covered(conn) == ["SPY"]
    assert result["status"] == "ok" and result["companies"] == 1
    assert ASKED.count(f"{edgar.WWW}/files/company_tickers.json") == 1  # not asked again the next time...
    with closing(filings.connect()) as conn:
        conn.execute("UPDATE filers SET checked_at = '2026-01-01T00:00:00Z' WHERE ticker = 'SPY'")
    companies(("NWND", NWND, "NORTHWIND CORP"), ("SPY", 884394, "SPDR S&P 500 ETF TRUST"))
    filings.check(read_new=False)
    assert ASKED.count(f"{edgar.WWW}/files/company_tickers.json") == 2  # ...but again after a month, in case it's listed now


def test_two_share_classes_are_one_company_asked_and_read_once(sec, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    sec.write_text("CNTA\nCNTB\n")
    companies(("CNTA", 3333, "CONTOSO INC"), ("CNTB", 3333, "CONTOSO INC"))
    filing(3333, "0000003333-26-000007", "8-K", "2026-10-28 16:05", "2.02,9.01", docs=[
        ("c-8k.htm", "8-K", COVER), ("c-ex991.htm", "EX-99.1", press_release())])
    set_facts(3333, HISTORY)

    result = filings.check()

    assert ASKED.count(f"{edgar.DATA}/submissions/CIK0000003333.json") == 1
    assert sorted(f["ticker"] for f in listed()) == ["CNTA", "CNTB"] and result["new_filings"] == 2
    assert result["reads"] == 1 and len(CLAUDE) == 1                    # one first take, shown under both tickers
    assert all(f["read"]["status"] == "ok" for f in listed())
    assert len(SENT) == 1                                               # and one Discord message


def test_one_company_failing_doesnt_stop_the_rest(sec):
    sec.write_text("NWND\nTSPN\n")
    companies(("NWND", NWND, "NORTHWIND CORP"), ("TSPN", 2222, "TAILSPIN INC"))
    filing(2222, "0000002222-26-000004", "8-K", "2026-10-27 08:00", "7.01,9.01", docs=[("t-8k.htm", "8-K", COVER)])
    SEC[f"{edgar.DATA}/submissions/CIK{NWND:010d}.json"] = edgar.EdgarError("couldn't reach the SEC (timed out)")

    result = filings.check(read_new=False)

    assert result["status"] == "partial" and "NWND: couldn't reach the SEC" in result["message"]
    assert [f["ticker"] for f in listed()] == ["TSPN"]


def test_being_limited_by_the_sec_stops_the_check(sec):
    sec.write_text("NWND\nTSPN\n")
    companies(("NWND", NWND, "NORTHWIND CORP"), ("TSPN", 2222, "TAILSPIN INC"))
    SEC[f"{edgar.DATA}/submissions/CIK{NWND:010d}.json"] = edgar.EdgarError("The SEC refused the request... wait 10 minutes", 403)

    result = filings.check(read_new=False)

    assert result["status"] == "partial" and "wait 10 minutes" in result["message"]
    assert f"{edgar.DATA}/submissions/CIK0000002222.json" not in ASKED  # asking for more would only make it worse


def test_an_unreachable_sec_is_given_up_on_quickly(sec):
    names = [f"CO{n}" for n in range(5)]
    sec.write_text("\n".join(names) + "\n")
    companies(*[(name, 4000 + n, f"COMPANY {n}") for n, name in enumerate(names)])
    filing(4000, "0000004000-26-000001", "8-K", "2026-10-28 16:00", "7.01", docs=[("c-8k.htm", "8-K", COVER)])
    for n in (1, 2, 3, 4):
        SEC[f"{edgar.DATA}/submissions/CIK{4000 + n:010d}.json"] = edgar.EdgarError("couldn't reach the SEC (timed out)")

    result = filings.check(read_new=False)

    asked = [url for url in ASKED if "/submissions/" in url]
    assert len(asked) == 3 and "stopped there: the SEC can't be reached right now" in result["message"]  # not all five
    assert result["status"] == "partial" and [f["ticker"] for f in listed()] == ["CO0"]  # what was found is kept


def test_without_a_contact_nothing_is_asked_and_a_run_carries_on(sec, monkeypatch):
    monkeypatch.undo()  # the real edgar.get_json again (conftest.py has removed SEC_CONTACT)
    monkeypatch.setattr(reports_db, "DB_PATH", sec.parent / "reports.db")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", sec)
    monkeypatch.delenv("SEC_CONTACT", raising=False)
    monkeypatch.setattr(edgar.urllib.request, "urlopen", lambda *a, **k: pytest.fail("a request was made"))

    with pytest.raises(edgar.ContactMissing, match="Set SEC_CONTACT to your name and email"):
        filings.check()
    seen = []
    assert filings.check_before_run(seen.append) is None  # a run isn't stopped by it
    assert seen[0]["type"] == "warning" and "Set SEC_CONTACT" in seen[0]["message"]


def test_only_fresh_results_are_read_automatically(sec):
    filing(NWND, "0000001111-26-000093", "8-K", "2026-10-28 17:00", "5.02,9.01", docs=[("n-8k.htm", "8-K", COVER)])
    filing(NWND, "0000001111-26-000094", "8-K/A", "2026-10-28 18:00", "2.02,9.01", docs=[
        ("n-8ka.htm", "8-K/A", COVER), ("n-ex991.htm", "EX-99.1", press_release())])

    result = filings.check()

    read = {f["accession"]: f["read"] and f["read"]["status"] for f in listed()}
    assert read == {RESULTS: "ok",                     # yesterday's results: read
                    PREVIOUS: None,                    # July's results: three months old, so listed only
                    "0000001111-26-000093": None,      # another announcement: a button, not automatic
                    "0000001111-26-000094": None}      # an amended announcement: a button too
    assert result["reads"] == 1 and result["cost_usd"] == 0.08 and len(CLAUDE) == 1
    assert the(RESULTS)["read"]["trigger"] == "automatic"
    assert filings.check()["reads"] == 0 and len(CLAUDE) == 1  # and never twice


def test_a_busy_day_reads_a_few_and_leaves_the_rest_for_the_next_check(sec, monkeypatch):
    monkeypatch.setattr(filings, "MAX_AUTOMATIC", 2)
    names = [f"CO{n}" for n in range(4)]
    sec.write_text("\n".join(names) + "\n")
    companies(*[(name, 4000 + n, f"COMPANY {n}") for n, name in enumerate(names)])
    for n in range(4):
        filing(4000 + n, f"000000400{n}-26-000001", "8-K", f"2026-10-28 16:0{n}", "2.02,9.01", docs=[
            ("c-8k.htm", "8-K", COVER), ("c-ex991.htm", "EX-99.1", press_release())])
        set_facts(4000 + n, HISTORY)

    assert filings.check()["reads"] == 2 and filings.check()["reads"] == 2 and filings.check()["reads"] == 0
    assert all(f["read"]["status"] == "ok" for f in listed())


# ---------------------------------------------------------------------------
# Reading a results announcement
# ---------------------------------------------------------------------------

def test_a_results_first_take(sec):
    REPLY["value"] = results_reply(changes=[{"text": "It no longer mentions supply constraints.",
                                             "quote": "Revenue was $12.4 billion and increased from a year earlier."}])
    filings.check(read_new=False)
    seen = []

    take = filings.read(RESULTS, emit=seen.append)

    assert take["status"] == "ok" and take["trigger"] == "manual" and take["cost_usd"] == 0.08
    assert take["document"] == "nwnd-ex991.htm" and take["document_url"].endswith("/000000111126000090/nwnd-ex991.htm")
    assert take["headline"].startswith("Northwind reported third-quarter revenue of $12.4 billion")
    assert [p["text"] for p in take["points"]] == ["Cloud revenue grew 30%, driven by AI services.",
                                                   "Management says customers are moving key workloads to it."]
    assert take["guidance"][0]["direction"] == "raised" and take["changes"][0]["text"].startswith("It no longer mentions")
    assert [e["message"] for e in seen] == ["Reading Northwind's results announcement",
                                           "First take on NWND: " + take["headline"]]

    system, prompt = CLAUDE[0]
    assert system == filings.RESULTS_PROMPT and "COMPANY: Northwind (NWND)" in prompt
    assert "FILING: Results announcement, filed 2026-10-28 (form 8-K, items 2.02,9.01)" in prompt
    assert "Total revenue | $12,400 | $10,000" in prompt and "UNITED STATES SECURITIES" not in prompt  # the press release, not the cover
    assert "PREVIOUS ANNOUNCEMENT (filed 2026-07-29)" in prompt and "Supply constraints limited growth" in prompt

    figures = take["figures"]
    rows = {r["metric"]: r for r in figures["rows"]}
    assert figures["period_end"] == "2026-09-30" and figures["basis"] == "quarter" and figures["source"] == "announcement"
    assert list(rows) == ["revenue", "gross_profit", "operating_income", "net_income", "eps_diluted"]
    revenue = rows["revenue"]
    assert revenue["value"] == 12_400 * M and revenue["as_written"] == "12,400" and revenue["quote"] == "Total revenue | $12,400 | $10,000"
    assert revenue["prior"] == {"end": "2026-06-30", "value": 11_800 * M, "derived": False}
    assert revenue["year_ago"] == {"end": "2025-09-30", "value": 10_000 * M, "derived": False}
    assert (revenue["change_prior_pct"], revenue["change_year_pct"]) == (5.1, 24.0)  # worked out in code: 12,400 vs 11,800 and 10,000
    assert rows["eps_diluted"]["value"] == 2.67 and rows["eps_diluted"]["change_year_pct"] == 33.5
    assert all(r["check"] == "pending" for r in figures["rows"])  # no quarterly report yet to check them against
    assert figures["margins"][1] == {"label": "Operating margin", "value": 32.3, "prior": 31.4, "year_ago": 30.0}
    assert take["notes"] == []


def test_points_claude_cant_quote_are_dropped(sec):
    reply = results_reply()
    reply["points"].append({"text": "Margins will keep expanding next year.", "quote": "We expect margins to keep expanding."})
    reply["guidance"].append({"text": "It will buy back $10 billion of shares.", "direction": "new", "quote": "a $10 billion buyback"})
    REPLY["value"] = reply
    filings.check()

    take = the(RESULTS)["read"]

    assert len(take["points"]) == 2 and len(take["guidance"]) == 1  # the two invented ones are gone
    assert take["notes"] == ["2 items from Claude were left out, because their quotes aren't in the filing."]


def test_a_take_with_nothing_quotable_fails_and_says_why(sec):
    REPLY["value"] = results_reply(points=[{"text": "A strong quarter.", "quote": "It was a strong quarter overall."}])
    filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "failed" and take["error"] == "Claude's reply quoted nothing that's in the filing"
    assert take["cost_usd"] == 0.08  # the cost is still recorded


def test_quotes_from_the_previous_announcement_dont_count(sec):
    REPLY["value"] = results_reply(changes=[{"text": "Supply is constrained.",
                                             "quote": "Supply constraints limited growth in the quarter."}])
    filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "ok" and take["changes"] == []  # that sentence is in July's announcement, not this one
    assert "1 item from Claude was left out" in take["notes"][0]


@pytest.mark.parametrize("figure, why", [
    ({"metric": "revenue", "as_written": "12,400", "scale": "thousands", "quote": "Total revenue | $12,400 | $10,000"}, "unit"),
    ({"metric": "revenue", "as_written": "12,900", "scale": "millions", "quote": "Total revenue | $12,400 | $10,000"}, "number"),
    ({"metric": "revenue", "as_written": "12,400", "scale": "millions", "quote": "Total revenue was 12,400 this quarter"}, "quote"),
    ({"metric": "revenue", "as_written": "twelve billion", "scale": "millions", "quote": "Total revenue | $12,400 | $10,000"}, "number"),
    ({"metric": "revenue", "as_written": "12,400", "scale": "lots", "quote": "Total revenue | $12,400 | $10,000"}, "scale"),
    ({"metric": "free_cash_flow", "as_written": "4,000", "scale": "millions", "quote": "Operating income | 4,000 | 3,000"}, "metric"),
])
def test_a_figure_that_doesnt_check_out_is_left_out(sec, figure, why):
    reply = results_reply()
    reply["figures"][0] = figure
    REPLY["value"] = reply
    filings.check()

    take = the(RESULTS)["read"]

    assert take["status"] == "ok" and "revenue" not in figures_of() and "net_income" in figures_of()
    if why == "unit":  # $12.4 million of revenue after $11.8 billion: the unit must be wrong
        assert take["notes"] == ["Revenue was left out: 12,400 thousands doesn't fit with $11.80B in the quarter to "
                                 "2026-06-30, so the unit is probably wrong."]
    elif why != "metric":
        assert "left out" in take["notes"][0]
    assert all(m["label"] != "Operating margin" for m in take["figures"]["margins"])  # no revenue, so no margins


def test_claude_never_sets_the_scale_of_earnings_per_share(sec):
    reply = results_reply()
    reply["figures"][4]["scale"] = "millions"
    REPLY["value"] = reply
    filings.check()
    assert figures_of()["eps_diluted"]["value"] == 2.67


@pytest.mark.parametrize("period_end", ["2026-12-31", "2025-09-30", "third quarter", None])
def test_an_unclear_quarter_means_no_comparisons(sec, period_end):
    REPLY["value"] = results_reply(period_end=period_end)
    filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "ok" and take["figures"]["period_end"] is None
    assert figures_of()["revenue"]["value"] == 12_400 * M and figures_of()["revenue"]["prior"] is None
    assert take["notes"] == ["The quarter's end date wasn't clear, so the figures aren't compared with earlier quarters."]


def test_a_loss_or_a_missing_quarter_gives_no_percentage(sec):
    history = dict(HISTORY)
    history[("2026-04-01", "2026-06-30")] = (11_800, 7_700, -300, -450, -0.38)  # a loss the quarter before
    del history[("2025-07-01", "2025-09-30")]                                    # and no figures from a year ago
    set_facts(NWND, history)
    filings.check()
    rows = figures_of()
    assert rows["net_income"]["prior"]["value"] == -450 * M and rows["net_income"]["change_prior_pct"] is None
    assert rows["revenue"]["change_prior_pct"] == 5.1 and rows["revenue"]["year_ago"] is None
    assert rows["revenue"]["change_year_pct"] is None


def test_a_bank_without_gross_profit_just_has_fewer_rows(sec):
    reply = results_reply()
    del reply["figures"][1:3]  # no gross profit or operating income in a bank's announcement
    REPLY["value"] = reply
    set_facts(NWND, HISTORY, revenue_tag="RevenuesNetOfInterestExpense", leave_out=("GrossProfit", "OperatingIncomeLoss"))
    filings.check()
    assert list(figures_of()) == ["revenue", "net_income", "eps_diluted"] and figures_of()["revenue"]["change_year_pct"] == 24.0
    assert [m["label"] for m in the(RESULTS)["read"]["figures"]["margins"]] == ["Net margin"]


def test_earlier_quarters_being_unavailable_still_gives_a_take(sec):
    SEC[f"{edgar.DATA}/api/xbrl/companyfacts/CIK{NWND:010d}.json"] = edgar.EdgarError("couldn't reach the SEC (timed out)")
    filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "ok" and figures_of()["revenue"]["value"] == 12_400 * M and figures_of()["revenue"]["prior"] is None
    assert take["notes"] == ["Earlier quarters couldn't be fetched for comparison (couldn't reach the SEC (timed out))."]


def test_a_first_results_announcement_has_nothing_to_compare_wording_with(sec):
    FILED[NWND].clear()
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02,9.01", docs=[
        ("nwnd-8k.htm", "8-K", COVER), ("nwnd-ex991.htm", "EX-99.1", press_release())])
    filings.check()
    assert "PREVIOUS ANNOUNCEMENT" not in CLAUDE[0][1]
    assert the(RESULTS)["read"]["notes"] == ["There's no earlier results announcement on file to compare the wording with."]


def test_a_long_document_is_cut_off_and_says_so(sec, monkeypatch):
    monkeypatch.setattr(filings, "MAX_CHARS", 3_000)
    monkeypatch.setattr(filings, "PREVIOUS_CHARS", 500)
    padding = "".join(f"<p>Segment note {n}: nothing unusual happened in this business line.</p>" for n in range(400))
    SEC[edgar.folder(NWND, RESULTS) + "nwnd-ex991.htm"] = press_release(extra=padding)
    reply = results_reply()
    reply["figures"] = []  # the figures table is past the cut
    REPLY["value"] = reply
    filings.check()

    take = the(RESULTS)["read"]
    prompt = CLAUDE[0][1]

    assert take["status"] == "ok" and take["cut_off"] == 1 and take["chars"] <= 3_000
    assert "Segment note 5:" in prompt and "Segment note 399:" not in prompt and "Total revenue | $12,400" not in prompt
    assert len(prompt) < 3_000 + 500 + 600 and take["notes"][0] == "The document is long: the first 3,000 characters were read."
    assert take["figures"]["rows"] == []


def test_with_several_exhibits_the_press_release_is_the_one_read(sec):
    FILED[NWND].clear()
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02,9.01", docs=[
        ("nwnd-8k.htm", "8-K", COVER), ("nwnd-ex992.htm", "EX-99.2", "<p>Slides for the earnings call.</p>" * 30),
        ("nwnd-ex991.htm", "EX-99.1", press_release()), ("nwnd-ex101.htm", "EX-10.1", "<p>A contract.</p>" * 30)])
    filings.check()
    assert the(RESULTS)["read"]["document"] == "nwnd-ex991.htm" and "Slides for the earnings call" not in CLAUDE[0][1]


def test_results_that_come_with_other_news_are_one_filing_and_one_message(sec, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    FILED[NWND].clear()
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02,5.02,9.01", docs=[
        ("nwnd-8k.htm", "8-K", COVER), ("nwnd-ex991.htm", "EX-99.1", press_release())])
    result = filings.check()
    found = the(RESULTS)
    assert (found["kind"], found["serious"]) == ("results", True) and found["read"]["status"] == "ok"  # read as results
    assert found["title"] == "Results announcement; Directors or senior officers leaving or appointed"
    assert result["alerts"] == ["NWND results"] and len(SENT) == 1  # not a second "filed" message


def test_results_without_a_press_release_read_the_filing_itself(sec):
    FILED[NWND].clear()
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02", docs=[("nwnd-8k.htm", "8-K", press_release())])
    filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "ok" and take["document"] == "nwnd-8k.htm"
    assert "This results filing has no press release attached, so the filing's own text was read." in take["notes"]


@pytest.mark.parametrize("reply, error", [
    ("I'm sorry, I can't summarise this.", "no JSON"),
    ("[1, 2]", "no JSON"),
    ({"points": [{"text": "x", "quote": "Cloud revenue grew 30% on demand for AI services."}]}, "no headline"),
    (RuntimeError("Claude couldn't read the filing: error_max_budget_usd"), "error_max_budget_usd"),
])
def test_a_bad_reply_is_saved_as_a_failed_read(sec, reply, error):
    REPLY["value"] = reply
    result = filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "failed" and error in take["error"] and take["finished_at"]
    assert result["read"][0]["status"] == "failed" and result["status"] == "ok"  # the check itself went fine
    REPLY["value"] = results_reply()
    assert filings.read(RESULTS)["status"] == "ok" and the(RESULTS)["read"]["status"] == "ok"  # trying again works


def test_a_later_failure_doesnt_hide_a_good_first_take(sec):
    filings.check()
    REPLY["value"] = "nonsense"
    assert filings.read(RESULTS)["status"] == "failed"
    assert the(RESULTS)["read"]["status"] == "ok"


def test_only_listed_filings_can_be_read_one_at_a_time(sec):
    with pytest.raises(filings.FilingError, match="No filing 0000009999-26-000001 is listed") as missing:
        filings.read("0000009999-26-000001")
    assert missing.value.status == 404
    filings.check(read_new=False)
    with closing(filings.connect()) as conn:
        conn.execute("INSERT INTO filing_reads (accession, ticker, trigger, status, started_at) VALUES (?, 'NWND', 'manual', 'running', ?)",
                     (RESULTS, filings._utc_now()))
    with pytest.raises(filings.FilingError, match="already being read") as busy:
        filings.read(RESULTS)
    assert busy.value.status == 409 and CLAUDE == []
    with closing(filings.connect()) as conn:  # a read that crashed long ago doesn't block a new one
        conn.execute("UPDATE filing_reads SET started_at = '2026-10-28T00:00:00Z'")
    assert the(RESULTS)["read"]["status"] == "failed" and "interrupted" in the(RESULTS)["read"]["error"]
    assert filings.read(RESULTS)["status"] == "ok"


# ---------------------------------------------------------------------------
# Reading other filings
# ---------------------------------------------------------------------------

DEPARTURE = """<html><body><p>FORM 8-K</p><p>Item 5.02 Departure of Directors or Certain Officers.</p>
<p>On October 27, 2026, Jordan Lee notified Northwind Corp. of the decision to resign as Chief Financial Officer, effective December 31, 2026.</p>
<p>The resignation was not the result of any disagreement with the company.</p></body></html>"""
ANNOUNCEMENT_REPLY = {"headline": "Northwind's chief financial officer is resigning at the end of the year.",
                      "points": [{"text": "Jordan Lee resigns as CFO, effective December 31, 2026.",
                                  "quote": "Jordan Lee notified Northwind Corp. of the decision to resign as Chief Financial Officer"},
                                 {"text": "A successor has been named.", "quote": "Avery Kim will become Chief Financial Officer"}]}


def test_an_announcement_is_read_with_its_press_release(sec):
    filing(NWND, "0000001111-26-000093", "8-K", "2026-10-28 17:00", "5.02,9.01", docs=[
        ("n-8k.htm", "8-K", DEPARTURE), ("n-ex991.htm", "EX-99.1", "<p>Northwind names Avery Kim. Avery Kim will become Chief "
                                                                  "Financial Officer on January 1, 2027.</p>" + "<p>About Northwind.</p>" * 20)])
    REPLY["value"] = ANNOUNCEMENT_REPLY
    filings.check(read_new=False)

    take = filings.read("0000001111-26-000093")

    system, prompt = CLAUDE[0]
    assert system == filings.ANNOUNCEMENT_PROMPT and "PREVIOUS ANNOUNCEMENT" not in prompt
    assert "decision to resign as Chief Financial Officer" in prompt and "--- Attached press release (EX-99.1) ---" in prompt
    assert take["status"] == "ok" and len(take["points"]) == 2 and take["figures"] is None and take["guidance"] == []
    assert the("0000001111-26-000093")["serious"] is True


def test_a_filing_with_nothing_readable_fails_clearly(sec):
    filing(NWND, "0000001111-26-000093", "8-K", "2026-10-28 17:00", "8.01", docs=[("scan.htm", "8-K", "<p>See attached.</p>")])
    filing(NWND, "0000001111-26-000096", "8-K", "2026-10-28 17:30", "8.01", docs=[("slides.pdf", "8-K", "%PDF")])
    filings.check(read_new=False)
    assert "no text that can be read (it may be a scan or a PDF)" in filings.read("0000001111-26-000093")["error"]
    assert "no document that can be read" in filings.read("0000001111-26-000096")["error"]
    assert CLAUDE == []  # nothing was sent to Claude, so nothing was spent


def test_a_report_is_read_through_managements_discussion(sec):
    body = "<p>Revenue increased 24% driven by cloud services. Operating expenses increased 12% as we hired engineers.</p>" * 40
    report = ("<html><body><p>Item 1. Financial Statements</p>" + "<p>Balance sheet line.</p>" * 30
              + "<p>Item 2. Management's Discussion and Analysis of Financial Condition and Results of Operations</p>" + body
              + "<p>Item 3. Quantitative and Qualitative Disclosures About Market Risk</p><p>Risk text.</p></body></html>")
    filing(NWND, REPORT, "10-Q", "2026-10-30 07:00", report_date="2026-09-30", docs=[("nwnd-10q.htm", "10-Q", report)])
    filing(NWND, "0000001111-26-000097", "10-Q", "2026-10-30 08:00", report_date="2026-09-30", docs=[
        ("odd-10q.htm", "10-Q", "<p>A report laid out in its own way, with no standard headings.</p>" * 20)])
    CLOCK["now"] = datetime(2026, 10, 30, 9, 0, tzinfo=ET)
    REPLY["value"] = {"headline": "Growth came from cloud services, while hiring pushed costs up.",
                      "points": [{"text": "Costs rose 12% on hiring.", "quote": "Operating expenses increased 12% as we hired engineers."}]}
    filings.check(read_new=False)

    take = filings.read(REPORT)
    odd = filings.read("0000001111-26-000097")

    system, prompt = CLAUDE[0]
    assert system == filings.REPORT_PROMPT and take["status"] == "ok" and take["figures"] is None
    assert "Operating expenses increased 12%" in prompt and "Balance sheet line." not in prompt and "Risk text." not in prompt
    assert odd["status"] == "failed"  # its text has no such sentence, so the quote check fails...
    assert "A report laid out in its own way" in CLAUDE[1][1]  # ...but the start of the report was what Claude was given


def test_companies_outside_the_us_are_listed_and_read_on_request(sec):
    sec.write_text("LTWR\n")
    companies(("LTWR", 5555, "LITWARE NV"))
    filing(5555, "0000005555-26-000003", "6-K", "2026-10-28 06:30", docs=[("ltwr-6k.htm", "6-K", DEPARTURE)])
    filing(5555, "0000005555-26-000001", "20-F", "2026-09-15 06:30", report_date="2026-06-30", docs=[("ltwr-20f.htm", "20-F", "x")])
    REPLY["value"] = ANNOUNCEMENT_REPLY | {"points": ANNOUNCEMENT_REPLY["points"][:1]}

    result = filings.check()

    assert [(f["form"], f["kind"], f["figures"]) for f in listed()] == [("6-K", "foreign", None), ("20-F", "annual", None)]
    assert result["reads"] == 0 and CLAUDE == []                      # a 6-K is never read automatically
    assert f"{edgar.DATA}/api/xbrl/companyfacts/CIK0000005555.json" not in ASKED  # and no US-style figures are looked for
    assert filings.read("0000005555-26-000003")["status"] == "ok" and CLAUDE[0][0] == filings.ANNOUNCEMENT_PROMPT


# ---------------------------------------------------------------------------
# The report confirms the announcement
# ---------------------------------------------------------------------------

def file_report(when="2026-10-30 07:00", quarters=None, **facts_options):
    filing(NWND, REPORT, "10-Q", when, report_date="2026-09-30", docs=[("nwnd-10q.htm", "10-Q", "<p>x</p>")])
    set_facts(NWND, {**HISTORY, **(quarters or THIRD_QUARTER)}, **facts_options)


def test_the_quarterly_report_confirms_the_announcements_figures(sec):
    filings.check()
    assert all(r["check"] == "pending" for r in figures_of().values())
    file_report()
    CLOCK["now"] = datetime(2026, 10, 30, 9, 0, tzinfo=ET)

    result = filings.check()

    assert result["new_filings"] == 1 and result["reads"] == 0 and len(CLAUDE) == 1  # confirming needs no Claude
    assert {m: r["check"] for m, r in figures_of().items()} == dict.fromkeys(
        ["revenue", "gross_profit", "operating_income", "net_income", "eps_diluted"], "confirmed")
    assert figures_of()["revenue"]["report_value"] == 12_400 * M
    own = the(REPORT)["figures"]  # the report's own figures are saved too, with the same comparisons
    assert own["source"] == "report" and own["period_end"] == "2026-09-30" and own["basis"] == "quarter"
    assert own["rows"][0]["value"] == 12_400 * M and own["rows"][0]["change_year_pct"] == 24.0
    assert own["margins"][1]["value"] == 32.3


def test_a_figure_the_report_gives_differently_is_flagged(sec):
    filings.check()
    file_report(quarters={("2026-07-01", "2026-09-30"): (12_400, 8_100, 4_000, 2_900, 2.42)})  # net income restated lower
    filings.check()
    rows = figures_of()
    assert rows["net_income"]["check"] == "differs" and rows["net_income"]["report_value"] == 2_900 * M
    assert rows["eps_diluted"]["check"] == "differs" and rows["eps_diluted"]["report_value"] == 2.42
    assert rows["revenue"]["check"] == "confirmed"


@pytest.mark.parametrize("announced, reported, same", [
    (12_400 * M, 12_400.4 * M, True),     # tables round to the million
    (12.4e9, 12.449e9, True),             # sentences round to a tenth of a billion
    (12.4e9, 12.6e9, False),
    (-450 * M, -450.3 * M, True), (450 * M, -450 * M, False),
    (3 * M, 3.5 * M, True),               # tiny figures: within the rounding of a table in millions
])
def test_rounding_is_allowed_but_real_differences_arent(announced, reported, same):
    assert filings.agrees("revenue", announced, reported) is same


def test_earnings_per_share_must_match_to_the_cent():
    assert filings.agrees("eps_diluted", 2.67, 2.674) and not filings.agrees("eps_diluted", 2.67, 2.70)


def test_a_report_filed_the_same_day_confirms_straight_away(sec):
    file_report(when="2026-10-28 16:01")  # some companies file the report minutes before the announcement
    result = filings.check()
    assert result["reads"] == 1 and all(r["check"] == "confirmed" for r in figures_of().values())
    assert figures_of()["revenue"]["prior"]["end"] == "2026-06-30"  # still compared with the quarter before, not with itself


def test_figures_the_report_doesnt_give_stop_waiting(sec):
    filings.check()
    file_report(leave_out=("GrossProfit",))
    address = f"{edgar.DATA}/api/xbrl/companyfacts/CIK{NWND:010d}.json"
    filings.check()
    asked = ASKED.count(address)
    assert figures_of()["gross_profit"]["check"] == "not_checked" and figures_of()["revenue"]["check"] == "confirmed"
    filings.check()
    assert ASKED.count(address) == asked  # nothing left to wait for, so the large file isn't downloaded again


def test_a_report_whose_figures_never_appear_isnt_fetched_forever(sec):
    filing(NWND, REPORT, "10-Q", "2026-10-30 07:00", report_date="2026-09-30", docs=[("nwnd-10q.htm", "10-Q", "<p>x</p>")])
    address = f"{edgar.DATA}/api/xbrl/companyfacts/CIK{NWND:010d}.json"
    CLOCK["now"] = datetime(2026, 10, 30, 9, 0, tzinfo=ET)
    filings.check(read_new=False)
    assert the(REPORT)["figures"] is None and ASKED.count(address) == 1  # not published yet: it will look again
    CLOCK["now"] = datetime(2026, 11, 5, 9, 0, tzinfo=ET)
    filings.check(read_new=False)
    assert the(REPORT)["figures"]["rows"] == [] and ASKED.count(address) == 2  # days later: settled as "none"
    filings.check(read_new=False)
    assert ASKED.count(address) == 2


def test_a_fourth_quarter_is_checked_against_the_annual_report(sec):
    """The annual report gives the year, not the quarter: revenue is checked against the year minus nine
    months, but earnings per share can't be worked out that way exactly, so it's marked as not checked."""
    FILED[NWND].clear()
    year, nine = ("2025-10-01", "2026-09-30"), ("2025-10-01", "2026-06-30")
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02,9.01", docs=[
        ("nwnd-8k.htm", "8-K", COVER), ("nwnd-ex991.htm", "EX-99.1", press_release("fourth"))])
    filing(NWND, REPORT, "10-K", "2026-10-28 16:30", report_date="2026-09-30", docs=[("nwnd-10k.htm", "10-K", "<p>x</p>")])
    set_facts(NWND, {**HISTORY, year: (46_000, 30_000, 14_500, 11_600, 9.70), nine: (33_600, 21_900, 10_500, 8_400, 7.02),
                     ("2024-10-01", "2025-09-30"): (38_000, 24_000, 11_000, 8_800, 7.30)})

    filings.check()

    rows = figures_of()
    assert rows["revenue"]["check"] == "confirmed" and rows["revenue"]["report_value"] == (46_000 - 33_600) * M
    assert rows["eps_diluted"]["check"] == "not_checked" and rows["eps_diluted"]["report_value"] is None
    own = the(REPORT)["figures"]  # the annual report's own figures are for the year, against the year before
    assert own["basis"] == "year" and own["rows"][0]["value"] == 46_000 * M and own["rows"][0]["prior"] is None
    assert own["rows"][0]["year_ago"]["value"] == 38_000 * M and own["rows"][0]["change_year_pct"] == 21.1


def test_an_amended_report_doesnt_replace_the_checks(sec):
    filings.check()
    file_report()
    filing(NWND, "0000001111-26-000099", "10-Q/A", "2026-10-31 07:00", report_date="2026-09-30", docs=[("a.htm", "10-Q/A", "x")])
    CLOCK["now"] = datetime(2026, 11, 2, 9, 0, tzinfo=ET)
    filings.check()
    assert the("0000001111-26-000099")["title"] == "Amended: Quarterly report" and the("0000001111-26-000099")["figures"] is None
    assert figures_of()["revenue"]["check"] == "confirmed"


def test_a_late_report_notice_is_flagged_without_claude(sec, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    filing(NWND, "0000001111-26-000098", "NT 10-Q", "2026-10-28 17:10", docs=[("nt.htm", "NT 10-Q", "<p>x</p>")])
    filings.check(read_new=False)
    late = the("0000001111-26-000098")
    assert (late["kind"], late["serious"], late["title"]) == ("late", True, "Says its quarterly report will be late")
    assert SENT[0]["content"] == "**NWND filed with the SEC**" and "will be late" in SENT[0]["embeds"][0]["title"]
    assert CLAUDE == []


# ---------------------------------------------------------------------------
# The calendar
# ---------------------------------------------------------------------------

def add_event(ticker, day, title="Earnings report", note=None, kind="earnings"):
    with closing(events.connect()) as conn:
        return conn.execute(
            """INSERT INTO events (event_date, ticker, company, kind, title, date_note, first_seen, last_seen)
               VALUES (?, ?, 'Northwind', ?, ?, ?, '2026-10-01', '2026-10-01')""", (day, ticker, kind, title, note)).lastrowid


def reported(start="2026-10-01", end="2026-11-15"):
    with closing(reports_db.connect(readonly=True)) as conn:
        found = events.events_between(conn, start, end)
        return filings.for_calendar(conn, found, start, end)


def test_the_calendar_shows_what_was_reported(sec):
    event = add_event("NWND", "2026-10-28")
    add_event("NWND", "2026-10-28", "Ex-dividend date", kind="dividend")
    with closing(reports_db.connect(readonly=True)) as conn:
        assert [e["ticker"] for e in filings.expected(conn, date(2026, 10, 29))] == ["NWND"]  # due yesterday, nothing filed yet
        assert filings.for_calendar(conn, events.events_between(conn, "2026-10-01", "2026-11-15"), "2026-10-01", "2026-11-15") == []

    filings.check()

    found = reported()
    assert len(found) == 1 and found[0]["event_id"] == event and found[0]["accession"] == RESULTS  # July's is out of range
    assert found[0]["headline"].startswith("Northwind reported third-quarter revenue") and found[0]["company"] == "Northwind"
    with closing(reports_db.connect(readonly=True)) as conn:
        assert filings.expected(conn, date(2026, 10, 29)) == []


@pytest.mark.parametrize("event_day, note, matched", [
    ("2026-10-26", None, True),                        # Yahoo had it two days early
    ("2026-10-30", None, True),                        # ...or two days late
    ("2026-10-22", None, False),                       # six days out: a different event
    ("2026-10-16", "Estimated: Yahoo Finance shows a window of Oct 16 to Oct 30.", True),   # an unconfirmed window
    ("2026-11-06", "Estimated: Yahoo Finance shows a window of Nov 6 to Nov 12.", False),   # a window that starts later
])
def test_a_calendar_date_thats_a_little_out_still_matches(sec, event_day, note, matched):
    event = add_event("NWND", event_day, note=note)
    filings.check(read_new=False)
    found = reported()
    assert found[0]["filing_date"] == "2026-10-28" and found[0]["event_id"] == (event if matched else None)
    assert found[0]["headline"] is None  # listed, not read


def test_results_the_calendar_never_expected_still_show_on_their_day(sec):
    filings.check(read_new=False)
    assert [(r["filing_date"], r["event_id"]) for r in reported("2026-10-01", "2026-10-31")] == [("2026-10-28", None)]
    assert reported("2026-11-01", "2026-11-30") == []
    assert [r["filing_date"] for r in reported("2026-07-01", "2026-07-31")] == ["2026-07-29"]


def test_another_companys_results_never_answer_an_event(sec):
    add_event("TSPN", "2026-10-28")
    filings.check(read_new=False)
    assert reported()[0]["event_id"] is None
    with closing(reports_db.connect(readonly=True)) as conn:
        assert filings.expected(conn, date(2026, 10, 29)) == []  # Tailspin isn't tracked, so it isn't waited for


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------

def test_discord_hears_about_results_and_serious_announcements_once(sec, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    filing(NWND, "0000001111-26-000093", "8-K", "2026-10-28 17:00", "5.02,9.01", docs=[("n-8k.htm", "8-K", DEPARTURE)])
    filing(NWND, "0000001111-26-000096", "8-K", "2026-10-28 17:30", "7.01,9.01", docs=[("n2-8k.htm", "8-K", COVER)])

    result = filings.check()

    assert result["alerts"] == ["NWND filing", "NWND results"] and len(SENT) == 2  # not the routine 7.01, not July's results
    results = next(m for m in SENT if m["content"] == "**NWND reported results**")["embeds"][0]
    assert results["title"] == "Northwind: results" and results["url"].endswith("0000001111-26-000090-index.htm")
    assert "Northwind reported third-quarter revenue of $12.4 billion" in results["description"]
    assert "• Revenue $12.40B (+24.0% vs a year ago)" in results["description"]
    assert "• Earnings per share (diluted) $2.67 (+33.5% vs a year ago)" in results["description"]
    assert "**Guidance (raised):** It expects fourth-quarter revenue" in results["description"]
    assert "research, not investment advice" in results["footer"]["text"]
    serious = next(m for m in SENT if m["content"] == "**NWND filed with the SEC**")["embeds"][0]
    assert serious["title"] == "Northwind: Directors or senior officers leaving or appointed"
    assert "Not read by Claude yet" in serious["description"]
    assert filings.check()["alerts"] == [] and len(SENT) == 2  # once each


def test_a_discord_message_that_fails_is_sent_by_the_next_check(sec, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    monkeypatch.setattr(alerts, "send", lambda payload: (_ for _ in ()).throw(alerts.SendError("couldn't reach Discord")))
    first = filings.check()
    assert first["status"] == "partial" and "Discord: NWND results (couldn't reach Discord)" in first["message"]
    monkeypatch.setattr(alerts, "send", SENT.append)
    assert filings.check()["alerts"] == ["NWND results"] and len(SENT) == 1


def test_no_discord_without_a_webhook_or_for_old_filings(sec, monkeypatch):
    assert filings.check()["alerts"] == [] and SENT == []  # no webhook set
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    CLOCK["now"] = datetime(2026, 11, 10, 9, 0, tzinfo=ET)
    assert filings.check()["alerts"] == [] and SENT == []  # set up two weeks later: old news isn't sent


# ---------------------------------------------------------------------------
# Briefs, runs and Ask
# ---------------------------------------------------------------------------

def test_the_agents_tool_gives_first_takes_for_flagged_tickers(sec):
    assert market_tools.recent_filings(["NWND"])["note"].startswith("Filings haven't been checked yet")
    add_event("TSPN", "2026-10-28")
    sec.write_text("NWND\nTSPN\n")
    companies(("NWND", NWND, "NORTHWIND CORP"), ("TSPN", 2222, "TAILSPIN INC"))
    filing(2222, "0000002222-26-000004", "8-K", "2026-10-27 08:00", "5.02,9.01", docs=[("t-8k.htm", "8-K", DEPARTURE)])
    filings.check()

    result = market_tools.recent_filings([" nwnd ", "TSPN", "AAPL"])

    assert set(result["filings"]) == {"NWND", "TSPN"} and "note" not in result and result["checked"]
    nwnd = result["filings"]["NWND"][0]  # July's announcement is too old to be listed here
    assert len(result["filings"]["NWND"]) == 1 and nwnd["kind"] == "Results" and nwnd["url"].endswith("-index.htm")
    take = nwnd["first_take"]
    assert take["headline"].startswith("Northwind reported") and take["guidance"] == [
        "Raised: It expects fourth-quarter revenue of $12.8 billion to $13.2 billion."]
    assert take["figures"][0] == "Revenue $12.40B (+24.0% vs a year ago), +5.1% vs the quarter before"
    tspn = result["filings"]["TSPN"][0]
    assert tspn["first_take"] is None and tspn["serious"] and tspn["title"].startswith("Directors or senior officers")
    assert [e["ticker"] for e in result["expected"]] == ["TSPN"]  # the calendar expected results that haven't come


def test_a_run_checks_filings_first_even_when_the_report_is_already_saved(sec, monkeypatch):
    order = []
    monkeypatch.setattr(run_brief, "send_alerts", lambda *a, **k: asyncio.sleep(0))
    monkeypatch.setattr(run_brief.search_index, "sync", lambda *a, **k: None)
    monkeypatch.setattr(run_brief.stories, "after_final_report", lambda emit=None: None)
    session = {"status": "complete", "as_of": "2026-10-28"}
    monkeypatch.setattr(run_brief, "market_session", lambda: session)
    monkeypatch.setattr(run_brief, "flag_events", lambda: {
        "session": session, "flagged": [], "quiet": [{"ticker": "NWND", "last_close": 1.0, "return_1d_pct": 0.1}], "errors": []})

    async def fake_query(*, prompt, options):
        order.append(("agent", the(RESULTS)["read"]["status"]))  # the first take is there before the agent starts
        assert "mcp__market__recent_filings" in options.allowed_tools
        yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=1,
                            session_id="s", total_cost_usd=0.01, result="# Brief\n\nNothing unusual.")

    monkeypatch.setattr(run_brief, "query", fake_query)
    seen = []

    asyncio.run(run_brief.run_once(seen.append))

    assert order == [("agent", "ok")]
    messages = [e.get("message") for e in seen]
    assert "Reading Northwind's results announcement" in messages
    assert "Filings: 2 new: NWND (results announcement), NWND (results announcement)" in messages
    assert [e["type"] for e in seen][-1] == "saved"

    filing(NWND, "0000001111-26-000093", "8-K", "2026-10-28 19:00", "5.02,9.01", docs=[("n-8k.htm", "8-K", DEPARTURE)])
    seen.clear()
    asyncio.run(run_brief.run_once(seen.append))  # the report is final already: the run is skipped, filings still checked
    assert [e["type"] for e in seen] == ["filings", "skipped"] and "NWND (directors or senior officers" in seen[0]["message"]


def test_a_problem_with_filings_never_stops_a_run(sec, monkeypatch):
    monkeypatch.setattr(filings, "check", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("database is locked")))
    seen = []
    assert filings.check_before_run(seen.append) is None
    assert seen == [{"type": "warning", "message": "Filings weren't checked (database is locked). The run carries on without them."}]


def test_ask_sees_filings_and_first_takes(sec):
    file_report(when="2026-10-28 16:30")
    filings.check()

    with closing(reports_db.connect(readonly=True)) as conn:
        named = ask.filings_section(conn, ["NWND"])
        general = ask.filings_section(conn, [])
        reports_db.save_report(reports_db.connect(), session_date="2026-10-28", status="final", title="Brief", body_md="# Brief",
                               as_of="2026-10-28", scan={"session": {"status": "complete", "as_of": "2026-10-28"}, "flagged": [],
                                                         "quiet": [{"ticker": "NWND", "last_close": 1.0, "return_1d_pct": 0.1}],
                                                         "errors": []}, sources=[])
        context, _ = ask.build_context(conn, "What did NWND say about its outlook?")

    assert named in context  # Claude is actually given it
    assert "## Company filings for NWND (cite as (filing, date filed))" in named
    assert "- 2026-10-28: Quarterly report (not read)" in named and "- 2026-07-29: Results announcement (not read)" in named
    assert "### NWND: Results announcement, filed 2026-10-28 (cite as (filing, 2026-10-28))" in named
    assert "- Revenue: $12.40B, +5.1% vs the quarter before, +24.0% vs a year earlier, confirmed by the quarterly report" in named
    assert "- Operating margin: 32.3%" in named and "- Cloud revenue grew 30%, driven by AI services." in named
    assert "- Guidance (raised): It expects fourth-quarter revenue of $12.8 billion to $13.2 billion." in named
    assert "## Company filings in the last 7 days" in general
    assert "- 2026-10-28 NWND: Results announcement. Northwind reported third-quarter revenue" in general
    assert "2026-07-29" not in general
    assert "(filing, then the date it was filed)" in ask.SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# The API
# ---------------------------------------------------------------------------

@pytest.fixture
def client(sec, monkeypatch):
    monkeypatch.setattr(api, "hub", api.EventHub())
    monkeypatch.setattr(api, "filing_checks", api.BackgroundJob(
        "filings_check", lambda: 60, "busy", "Filings were just checked. Try again in {}."))
    monkeypatch.setattr(api, "filing_reads", api.BackgroundJob(
        "filing_read", lambda: 60, "busy", "A filing was just read. Try again in {}."))
    with TestClient(api.app) as test_client:
        yield test_client


def wait_for(check, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := check():
            return value
        time.sleep(0.05)
    raise AssertionError("timed out waiting")


def test_api_check_then_the_filings_view(client, sec):
    sec.write_text("NWND\nSPY\n")
    add_event("NWND", "2026-10-29", "Earnings report")
    empty = client.get("/api/filings").json()
    assert client.get("/api/calendar?start=2026-10-01&end=2026-10-31").json()["reported"] == []  # before any check
    assert empty["filings"] == [] and empty["checked"] is None and empty["contact_set"] is False
    assert [e["ticker"] for e in empty["expected"]] == ["NWND"] and empty["max_cost_usd"] == 0.5

    started = client.post("/api/filings/check", json={})
    assert started.status_code == 202 and started.json()["check"]["state"] == "running"
    done = wait_for(lambda: (v := client.get("/api/filings").json())["check"]["state"] == "finished" and v)
    assert client.post("/api/filings/check", json={}).status_code == 429  # cooldown

    assert [f["accession"] for f in done["filings"]] == [RESULTS, PREVIOUS] and done["tickers"] == ["NWND"]
    assert done["filings"][0]["read"]["headline"].startswith("Northwind reported") and done["not_covered"] == ["SPY"]
    assert done["checked"]["trigger"] == "manual" and done["check"]["result"]["reads"] == 1
    assert done["expected"] == []  # the event was a day out, and still counts as answered
    assert client.get("/api/filings?ticker=tspn").json()["filings"] == []
    assert client.get("/api/filings?ticker=nwnd").json()["filings"][0]["ticker"] == "NWND"
    assert client.get("/api/filings?ticker=N W").status_code == 400
    calendar = client.get("/api/calendar?start=2026-10-01&end=2026-10-31").json()
    assert calendar["reported"][0]["accession"] == RESULTS and calendar["reported"][0]["event_id"] == calendar["events"][0]["id"]


def test_api_read_a_filing(client):
    filings.check(read_new=False)
    queue = api.hub.subscribe()

    started = client.post("/api/filings/read", json={"accession": RESULTS})
    assert started.status_code == 202 and started.json()["read"]["target"] == {"accession": RESULTS, "ticker": "NWND"}
    done = wait_for(lambda: (v := client.get("/api/filings").json())["read"]["state"] == "finished" and v)

    assert done["filings"][0]["read"]["status"] == "ok" and done["read"]["result"]["headline"].startswith("Northwind")
    progress = []
    while not queue.empty():
        event = queue.get_nowait()
        if event["type"] == "filing_read":
            progress.append(event["job"]["message"])
    assert "Reading Northwind's results announcement" in progress
    assert client.post("/api/filings/read", json={"accession": PREVIOUS}).status_code == 429


@pytest.mark.parametrize("body, status, message", [
    ({"accession": "0000009999-26-000001"}, 404, "No filing 0000009999-26-000001 is listed"),
    ({"accession": "123"}, 400, "send JSON like"),
    ({"ticker": "NWND"}, 400, "send JSON like"),
    ([RESULTS], 400, "send JSON like"),
])
def test_api_read_explains_what_went_wrong(client, body, status, message):
    filings.check(read_new=False)
    response = client.post("/api/filings/read", json=body)
    assert response.status_code == status and message in response.json()["error"] and CLAUDE == []


def test_other_websites_cannot_start_checks_or_reads(client):
    filings.check(read_new=False)
    for path, body in (("/api/filings/check", {}), ("/api/filings/read", {"accession": RESULTS})):
        assert client.post(path, json=body, headers={"Origin": "https://evil.example"}).status_code == 403
        assert client.post(path, content="x", headers={"Content-Type": "text/plain"}).status_code == 415
    assert CLAUDE == [] and the(RESULTS)["read"] is None


def test_filings_found_by_scheduled_runs_reach_open_pages(sec, monkeypatch):
    monkeypatch.setattr(api, "POLL_SECONDS", 0.05)
    monkeypatch.setattr(api, "hub", api.EventHub())

    async def scenario():
        queue = api.hub.subscribe()
        watcher = asyncio.create_task(api.watch_reports())
        await asyncio.sleep(0.3)
        await asyncio.to_thread(filings.check)  # what another program (a scheduled run) does
        seen = []
        deadline = time.monotonic() + 3
        while "filings_updated" not in seen and time.monotonic() < deadline:
            try:
                seen.append((await asyncio.wait_for(queue.get(), 0.5))["type"])
            except asyncio.TimeoutError:
                pass
        watcher.cancel()
        return seen

    assert "filings_updated" in asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Live
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not os.getenv("LIVE_TESTS"), reason="set LIVE_TESTS=1 (and SEC_CONTACT) to ask the SEC")
def test_live_filings(monkeypatch):
    if not LIVE_CONTACT:
        pytest.skip('set SEC_CONTACT to your name and email first, e.g. export SEC_CONTACT="Jane Doe jane@yourmail.com"')
    monkeypatch.setenv("SEC_CONTACT", LIVE_CONTACT)

    apple = edgar.company_numbers()["AAPL"]
    found = edgar.list_filings(apple["cik"])["filings"]
    followed = [(f, filings.describe(f["form"], f["items"])) for f in found]
    followed = [(f, about) for f, about in followed if about]
    print(f"\nApple is company {apple['cik']} ({apple['name']}). Its latest filings that are followed:")
    for f, about in followed[:8]:
        print(f"  {f['filing_date']}  {f['form']:<6} {f['accession']}  {about['title']}")
    results = next(f for f, about in followed if about["kind"] == "results")
    documents = edgar.filing_documents(apple["cik"], results["accession"], results["primary_doc"], results["form"])
    print(f"Documents in the results announcement of {results['filing_date']}:", [(d["name"], d["type"]) for d in documents])
    press = filings._press_release(documents)
    text = edgar.to_text(edgar.get_text(press["url"]))
    print(f"Its press release is {len(text):,} characters. It starts:\n  " + "\n  ".join(text.splitlines()[:4]))
    known = edgar.periods(edgar.company_facts(apple["cik"]))
    print("Quarterly revenue from the SEC's structured data:")
    for end in sorted(known["revenue"]["quarters"], reverse=True)[:5]:
        q = known["revenue"]["quarters"][end]
        print(f"  quarter to {end}: {filings.money(q['value'])}" + ("  (worked out from the annual report)" if q["derived"] else ""))

    assert apple["cik"] == 320193 and results["filed_at"].endswith("Z") and "2.02" in results["items"]
    assert press is not None and press["type"].startswith("EX-99") and len(text) > 2000
    assert {"revenue", "net_income", "eps_diluted"} <= set(known) and len(known["revenue"]["quarters"]) >= 8
    assert any(q["derived"] for q in known["revenue"]["quarters"].values())  # a fourth quarter, worked out
