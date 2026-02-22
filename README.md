# Polymarket Sports Arbitrage Bot

**Find directional sports betting opportunities by comparing Polymarket prediction markets with traditional sportsbook odds.**

The **Polymarket-Sports-Arbitrage-Bot** is a Python toolkit for **Polymarket sports betting** analysis. It fetches sports markets from the Polymarket Gamma API, matches them with odds from The Odds API, and surfaces opportunities where Polymarket prices diverge from sportsbook-implied probabilities—so you can identify undervalued outcomes and track potential edge.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Workflow](#workflow)
- [Example output](#example-output)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Documentation](#documentation)
- [License](#license)

---

## Overview

**Polymarket** is a decentralized prediction market platform. This bot focuses on **Polymarket sports markets**: it pulls live sports event data from Polymarket, pairs it with odds from major sportsbooks (via [The Odds API](https://the-odds-api.com)), and detects **directional opportunities**—cases where Polymarket undervalues an outcome relative to sportsbook-implied probability. Use it for research, backtesting, or as part of a manual or automated **Polymarket sports betting** workflow.

**Keywords:** Polymarket, Polymarket sports betting, Polymarket prediction markets, sports arbitrage, odds comparison, prediction markets, Gamma API, CLOB.

---

## Features

| Feature | Description |
|--------|-------------|
| **Polymarket data** | Fetches sports markets from the Polymarket Gamma API; filters by category and market type. |
| **Sportsbook odds** | Integrates with The Odds API for multi-sportsbook odds (US and international). |
| **Event matching** | Fuzzy matching of Polymarket events to sportsbook events (team names, dates, metadata). |
| **Directional detection** | Flags outcomes where Polymarket price &lt; sportsbook-implied probability. |
| **Delta analysis** | Identifies the sportsbook with the largest price gap per event. |
| **PnL monitoring** | Tracks unrealized P&amp;L for positions using live Polymarket CLOB prices. |
| **Export** | Outputs JSON and CSV for use in spreadsheets, dashboards, or other tools. |

---

## Installation

### Prerequisites

- **Python 3.9+**
- pip or [uv](https://github.com/astral-sh/uv)

### Install dependencies

```bash
pip install py-clob-client requests python-dotenv pandas pytest pytest-mock rapidfuzz python-dateutil
```

Or with uv (from project root):

```bash
uv pip install -e .
```

---

## Configuration

Create a `.env` file in the project root:

```env
# Polymarket
GAMMA_API_URL=https://gamma-api.polymarket.com
CLOB_HOST=https://clob.polymarket.com
ENRICH_WITH_CLOB=false

# The Odds API (required for sportsbook comparison)
ODDS_API_KEY=your_odds_api_key_here

# Output
OUTPUT_DIR=data
```

| Variable | Required | Description |
|---------|----------|-------------|
| `ODDS_API_KEY` | Yes | API key from [The Odds API](https://the-odds-api.com). |
| `GAMMA_API_URL` | No | Polymarket Gamma API base URL (default: `https://gamma-api.polymarket.com`). |
| `CLOB_HOST` | No | Polymarket CLOB host (default: `https://clob.polymarket.com`). |
| `ENRICH_WITH_CLOB` | No | Set `true` to enrich with CLOB prices (default: `false`). |
| `OUTPUT_DIR` | No | Output directory (default: `data`). |

Additional options: `ODDS_API_REGIONS`, `ODDS_API_MARKETS`, `ODDS_API_ODDS_FORMAT`, `ODDS_API_MIN_CONFIDENCE`, `USE_STORED_EVENTS`, `EVENTS_DIR`, `PNL_TEST_FILE`, `PNL_POLL_INTERVAL`, `PNL_OUTPUT_DIR`. See inline comments or code for defaults.

---

## Usage

All commands assume you are in the project root. Use `python3` if `python` is not available.

### 1. Fetch Polymarket sports markets

```bash
python3 -m poly_sports.data_fetching.fetch_sports_markets
```

Writes: `data/sports_markets.json`, `data/sports_markets.csv`, `data/arbitrage_data.json`, `data/arbitrage_data.csv`.

**Filter** to match-winner and draw markets only:

```bash
python3 -m poly_sports.data_fetching.fetch_sports_markets filter data/arbitrage_data.json data
```

Produces: `data/arbitrage_data_filtered.json`, `data/arbitrage_data_filtered.csv`.

### 2. Fetch and compare with sportsbook odds

Requires `ODDS_API_KEY` and `data/arbitrage_data_filtered.json` (from step 1).

```bash
python3 -m poly_sports.data_fetching.fetch_odds_comparison
```

Writes: `data/arbitrage_comparison.json`, `data/arbitrage_comparison.csv`, and `data/sportsbook_data/events/*.json`, `data/sportsbook_data/odds/*.json`.

### 3. Run arbitrage (directional) detection

Requires `data/arbitrage_comparison.json` (from step 2).

```bash
python3 scripts/run_arbitrage_detection.py
```

Optional: sort by profit margin or delta difference:

```bash
python3 scripts/run_arbitrage_detection.py --sort-by profit_margin
python3 scripts/run_arbitrage_detection.py --sort-by delta_difference
```

Writes: `data/directional_arbitrage.json`.

### 4. Max delta by sportsbook (optional)

```bash
python3 scripts/run_max_delta_analysis.py --top-n 50
```

Writes: `data/max_delta_by_sportsbook.json`.

### 5. Test odds pipeline (development)

Uses mock or filtered data; requires `data/arbitrage_data_filtered.json`.

```bash
python3 scripts/test_odds_pipeline.py
```

### 6. Monitor PnL (optional)

Uses `data/arbitrage_comparison_test.json` (or similar). Polls CLOB for live prices and writes PnL snapshots.

```bash
python3 scripts/monitor_pnl.py
```

Stop with `Ctrl+C`. Output: `data/pnl_snapshots.json`, `data/pnl_snapshots.csv`.

---

## Workflow

Typical end-to-end flow for **Polymarket sports arbitrage** analysis:

```bash
# 1. Fetch Polymarket sports markets
python3 -m poly_sports.data_fetching.fetch_sports_markets

# 2. Filter to match winner / draw
python3 -m poly_sports.data_fetching.fetch_sports_markets filter data/arbitrage_data.json data

# 3. Compare with sportsbook odds
python3 -m poly_sports.data_fetching.fetch_odds_comparison

# 4. Detect directional opportunities
python3 scripts/run_arbitrage_detection.py --sort-by profit_margin
```

Optional: run `run_max_delta_analysis.py` and `monitor_pnl.py` as needed.

---

## Example output

Sample output from running arbitrage detection on comparison data (49 matched events, 2 directional opportunities):

```
Loading comparison data from data/arbitrage_comparison.json...
Loaded 49 comparison entries

================================================================================
Running Arbitrage Detection
================================================================================

Found 2 opportunities

Sorting opportunities by profit_margin (descending)...
Sorted 2 opportunities

Directional Opportunities: 2

================================================================================
## DIRECTIONAL OPPORTUNITIES
================================================================================

1. Event ID: 211708 | Market ID: 1385463
   Potential Profit: 13.45% ($13.45 on $100 stake)
   Market Type: 2-way
   Match Confidence: 1.000
   Liquidity: $65,550.27
   Spread: 0.010
   Matched Outcomes:
     - Wizards: Buy at 0.165, Target: 0.187
       Expected movement: 2.2 percentage points

2. Event ID: 211719 | Market ID: 1385472
   Potential Profit: 10.96% ($10.96 on $100 stake)
   Market Type: 2-way
   Match Confidence: 1.000
   Liquidity: $38,741.28
   Spread: 0.010
   Matched Outcomes:
     - Bulls: Buy at 0.185, Target: 0.205
       Expected movement: 2.0 percentage points

================================================================================
## SUMMARY STATISTICS
================================================================================

Directional Opportunities:
  Average Potential Profit: 12.20%
  Maximum Potential Profit: 13.45%
  Total Opportunities: 2

================================================================================
Analysis complete!
================================================================================
```

Results are also written to `data/directional_arbitrage.json`.

---

## How It Works

1. **Polymarket**  
   Fetches sports events and markets from the Polymarket Gamma API; keeps only sports category and arbitrage-relevant fields.

2. **Event matching**  
   Infers sport from Polymarket metadata, loads corresponding events from The Odds API, and matches events using normalized team names and fuzzy similarity. Matches are scored (e.g. 0–1 confidence); low-confidence matches are dropped.

3. **Odds comparison**  
   Fetches odds from multiple sportsbooks, normalizes to American/decimal/implied probability, and aggregates (e.g. average, min, max) per outcome.

4. **Directional opportunities**  
   Compares Polymarket price to sportsbook-implied probability. When Polymarket price is lower, the outcome is treated as potentially undervalued (directional edge). Results are filtered by minimum profit threshold and liquidity.

5. **Why “directional” and not classic arbitrage?**  
   Polymarket prices sum to 1.0 (prediction market). There is no risk-free arbitrage on Polymarket alone. This bot finds **directional** edges: buy on Polymarket when it undervalues an outcome vs. sportsbooks; manage or exit as the market reprices.

Details: [docs/ARBITRAGE_CALCULATION.md](docs/ARBITRAGE_CALCULATION.md).

---

## Project Structure

```
polymarket-sports-arbitrage/
├── poly_sports/
│   ├── data_fetching/       # Polymarket Gamma API, Odds API, CLOB
│   ├── processing/          # Event matching, arbitrage detection, sport detection
│   └── utils/                # File I/O, odds conversion
├── scripts/                  # run_arbitrage_detection, run_max_delta_analysis, monitor_pnl, test_odds_pipeline
├── tests/
├── data/                     # Outputs (JSON/CSV, sportsbook_data)
└── docs/
    └── ARBITRAGE_CALCULATION.md
```

---

## Testing

```bash
pytest tests/ -v
```

---

## Documentation

- [ARBITRAGE_CALCULATION.md](docs/ARBITRAGE_CALCULATION.md) — Formulas and logic for opportunity detection and PnL.

---

## Contact

If you have any question or build AI Agent for Sports arbitrage bot on Polymarket, contact here: [Telegram](https://t.me/@microgift88)

## License

[Specify your license, e.g. MIT.]

---

**Polymarket-Sports-Arbitrage-Bot** — Polymarket sports betting analysis and directional opportunity detection.
