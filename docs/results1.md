# Test Results 1

Date: 2026-11-05 · Python 3.13.3 · pytest 9.2.0 · Windows 11

## Summary

| Layer | Result |
|---|---|
| Offline tests (`pytest tests -v`) | **8 passed**, 1 skipped (live test, gated by `LIVE_TESTS`) |
| Live data test (`LIVE_TESTS=1`) | **1 passed** |
| Manual live smoke checks | Passed |
| `run_brief.py` syntax check | Passed |
| Full agent run (`run_brief.py`) | **Passed**, 5 turns, $0.029 (see below) |
| MCP Inspector / schedule | **Not run** (need Node, scheduler) |

## Offline tests

| Test | Result |
|---|---|
| test_watchlist_skips_comments_blanks_and_uppercases | PASSED |
| test_zscore_matches_independent_calculation | PASSED |
| test_big_move_is_flagged_and_calm_ticker_is_quiet | PASSED |
| test_volume_spike_alone_is_flagged | PASSED |
| test_thresholds_control_flagging | PASSED |
| test_bad_tickers_are_reported_not_fatal | PASSED |
| test_news_handles_both_yfinance_formats_and_caps_limit | PASSED |
| test_tools_work_through_mcp | PASSED |
| test_live_data | SKIPPED (without `LIVE_TESTS=1`) |

## Live checks (real yfinance data)

- `test_live_data` with `LIVE_TESTS=1`: PASSED.
- `compute_moves("AAPL")`: `last_close` 344.17, 1d -1.53%, 5d -1.36%, z-score -1.24, volume 1.6x average, as of 2026-11-05.
- `flag_events()` on the 5-ticker watchlist: 3 flagged, 2 quiet, 0 errors.
- `compute_moves("ZZZZNOPE")` (invalid ticker): returns `{"error": "not enough price history"}` and doesn't crash. yfinance prints a 404 to stderr.
- `get_news("AAPL", 3)`: returned 3 items.

## Observations

- `main.py` is empty (0 lines). It is staged in git but has no code, so nothing to test there.
- `briefs/2026-11-03.md` exists from an earlier run. It reported "nothing flagged", which is consistent with the tools' output format.

## Agent run (`run_brief.py`)

Run after the API key was saved. Output: `briefs/2026-11-05.md`.

- Tool calls: `flag_events`, then `get_news` for MSFT, NVDA and JPM.
- Result: 5 turns, $0.029, well under the $1.00 cap.
- Flagged: NVDA -9.26% (z -4.09, volume 2.91x), MSFT -3.58% (z -2.31), JPM -4.19% (z -3.70).
- Quiet: AAPL -1.53%, AMZN -2.19%.
- The brief attributes all three moves to a market-wide sell-off and says no ticker-specific news was found, rather than inventing a catalyst. Sources are linked.

Items to review:
- MSFT is described as down 3.58% today but up 1.09% over five days. This is plausible but worth checking.
- The NVDA section says "Thursday's rout", and 2026-11-05 is a Thursday. Some articles may be older than the brief implies.
- The brief makes no claims beyond the news the tools returned.

## Verdict

The tool layer in `market_tools.py` works: the math, flagging logic, error handling, news parsing and the MCP round-trip all pass, and live data is flowing. The end-to-end agent run also works and produces a sourced brief. The remaining untested layers are the MCP Inspector and the schedule.
