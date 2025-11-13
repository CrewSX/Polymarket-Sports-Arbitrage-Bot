# poly-sports

A Python script to fetch all sports market data from Polymarket using the Gamma API and optionally enrich with CLOB data.

## Features

- Fetches all markets from Polymarket Gamma API
- Filters markets by category (Sports)
- Optionally enriches market data with CLOB data (prices, order books, spreads)
- Exports data to both JSON and CSV formats
- Test-driven development with comprehensive test coverage

## Setup

### Prerequisites

- Python 3.9 or higher
- pip or uv package manager

### Installation

1. Install dependencies:
```bash
pip install py-clob-client requests python-dotenv pandas pytest pytest-mock
```

Or if using uv:
```bash
uv pip install -e .
```

### Configuration

Create a `.env` file in the project root with the following settings:

```env
# Gamma API Configuration
GAMMA_API_URL=https://gamma-api.polymarket.com

# CLOB API Configuration (Optional - for data enrichment)
CLOB_HOST=https://clob.polymarket.com
ENRICH_WITH_CLOB=false

# Output Configuration (Optional)
OUTPUT_DIR=data
```

**Required:**
- `GAMMA_API_URL` - Base URL for Polymarket Gamma API (default: `https://gamma-api.polymarket.com`)

**Optional:**
- `CLOB_HOST` - CLOB API host URL (default: `https://clob.polymarket.com`)
- `ENRICH_WITH_CLOB` - Enable CLOB data enrichment (default: `false`)
- `EXCLUDE_ENDED_MARKETS` - Exclude markets that have already ended (default: `true`)
- `OUTPUT_DIR` - Directory to save output files (default: `data`)
- `PNL_TEST_FILE` - File path for PnL monitoring input (default: `data/arbitrage_comparison_test.json`)
- `PNL_POLL_INTERVAL` - Seconds between price updates for PnL monitoring (default: `30`)
- `PNL_OUTPUT_DIR` - Directory for PnL snapshot output files (default: `data`)

## Usage

### 1. Fetch Sports Markets

Fetch all sports markets from Polymarket:

```bash
python -m poly_sports.data_fetching.fetch_sports_markets
```

This will:
1. Fetch all markets from the Gamma API
2. Filter for markets with `category == "Sports"`
3. Extract arbitrage-relevant data
4. Save results to `data/sports_markets.json`, `data/sports_markets.csv`, `data/arbitrage_data.json`, and `data/arbitrage_data.csv`

#### With CLOB Enrichment

To enrich markets with CLOB data (prices, order books, spreads), set `ENRICH_WITH_CLOB=true` in your `.env` file:

```env
ENRICH_WITH_CLOB=true
```

Then run the same command. **Note:** CLOB enrichment requires the `py-clob-client` package to be installed.

#### Filter Arbitrage Data

Filter existing arbitrage data to only include match winner and draw markets:

```bash
python -m poly_sports.data_fetching.fetch_sports_markets filter [input_file] [output_dir]
```

Example:
```bash
python -m poly_sports.data_fetching.fetch_sports_markets filter data/arbitrage_data.json data
```

#### Extract from JSON File

Extract arbitrage data from an existing events JSON file:

```bash
python -m poly_sports.data_fetching.fetch_sports_markets [input_file] [output_dir]
```

Example:
```bash
python -m poly_sports.data_fetching.fetch_sports_markets data/events.json data
```

### 2. Test Odds Pipeline

Test the odds matching pipeline using mock NCAAF data. This script:
1. Loads Polymarket arbitrage data
2. Filters for NCAAF events
3. Matches events with Odds API data
4. Merges Polymarket and sportsbook odds
5. Saves comparison data

```bash
python scripts/test_odds_pipeline.py
```

**Prerequisites:**
- `data/arbitrage_data_filtered.json` must exist (run step 1 first)
- `data/mock_ncaaf_events.json` and `data/mock_ncaaf.json` must exist

**Output:**
- `data/arbitrage_comparison_test.json` - Merged comparison data (JSON)
- `data/arbitrage_comparison_test.csv` - Merged comparison data (CSV)

### 3. Run Arbitrage Detection

Detect arbitrage opportunities from comparison data:

```bash
python scripts/run_arbitrage_detection.py
```

**Prerequisites:**
- `data/arbitrage_comparison_test.json` must exist (run step 2 first)

This script:
1. Loads comparison data from `data/arbitrage_comparison_test.json`
2. Detects arbitrage opportunities with a minimum profit threshold (default: 10%)
3. Displays detailed opportunity information including:
   - Profit margins and absolute profit
   - Market type and match confidence
   - Liquidity and spread information
   - Matched outcomes and recommended sell points

### 4. Monitor PnL (Profit and Loss)

Monitor real-time Polymarket prices and calculate simulated PnL for positions:

```bash
python scripts/monitor_pnl.py
```

**Prerequisites:**
- `data/arbitrage_comparison_test.json` must exist (run step 2 first)

**Configuration (via `.env`):**
```env
# PnL Monitoring Configuration
PNL_TEST_FILE=data/arbitrage_comparison_test.json
PNL_POLL_INTERVAL=30  # seconds between price updates
PNL_OUTPUT_DIR=data   # directory for output files
CLOB_HOST=https://clob.polymarket.com
```

This script:
1. Loads events from the test file
2. Filters for active (non-ended) markets
3. Detects arbitrage opportunities and creates positions
4. Continuously monitors prices and calculates unrealized PnL
5. Saves snapshots to `data/pnl_snapshots.json` and `data/pnl_snapshots.csv`

**Output:**
- `data/pnl_snapshots.json` - PnL snapshots in JSON format
- `data/pnl_snapshots.csv` - PnL snapshots in CSV format

Press `Ctrl+C` to stop monitoring.

### Complete Workflow

Here's the typical workflow for analyzing arbitrage opportunities:

1. **Fetch sports markets:**
   ```bash
   python -m poly_sports.data_fetching.fetch_sports_markets
   ```

2. **Test odds pipeline (with mock data):**
   ```bash
   python scripts/test_odds_pipeline.py
   ```

3. **Detect arbitrage opportunities:**
   ```bash
   python scripts/run_arbitrage_detection.py
   ```

4. **Monitor PnL (optional, for active positions):**
   ```bash
   python scripts/monitor_pnl.py
   ```

### Output Files

All output files are saved to the `data/` directory by default:

**From fetch_sports_markets:**
- `data/sports_markets.json` - Full market data in JSON format (pretty-printed)
- `data/sports_markets.csv` - Flattened market data in CSV format
- `data/arbitrage_data.json` - Extracted arbitrage-relevant data in JSON format
- `data/arbitrage_data.csv` - Extracted arbitrage-relevant data in CSV format
- `data/arbitrage_data_filtered.json` - Filtered match winner and draw markets (JSON)
- `data/arbitrage_data_filtered.csv` - Filtered match winner and draw markets (CSV)

**From test_odds_pipeline:**
- `data/arbitrage_comparison_test.json` - Merged Polymarket and Odds API comparison data (JSON)
- `data/arbitrage_comparison_test.csv` - Merged Polymarket and Odds API comparison data (CSV)

**From monitor_pnl:**
- `data/pnl_snapshots.json` - Real-time PnL snapshots (JSON)
- `data/pnl_snapshots.csv` - Real-time PnL snapshots (CSV)

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

All tests should pass, confirming the code behaves as expected.

## How It Works

1. **Gamma API Integration**: Fetches sports markets from the Polymarket Gamma API `/events` endpoint using sports series IDs
2. **Series Filtering**: Uses predefined sports series IDs to fetch only sports-related events and markets
3. **End Date Filtering**: By default, excludes markets that have already ended (using `end_date_max` parameter with current UTC time)
4. **CLOB Enrichment** (optional): For each market, fetches:
   - Midpoint price
   - Buy/Sell prices
   - Spread
   - Order book (top 5 bids/asks)
5. **Data Export**: Saves all market data to both JSON and CSV formats, including event metadata (event_id, event_title, event_slug, event_tags)

## Error Handling

- API errors are caught and logged
- CLOB enrichment failures are handled gracefully (continues with unenriched data)
- Missing fields in market data are handled appropriately
- Network errors include retry logic where applicable

## Future Enhancements

- Continuous sync mode (watch for new markets)
- Database storage option
- Additional category filters
- Scheduled execution
- Rate limiting and retry logic improvements

## License

[Add your license here]
