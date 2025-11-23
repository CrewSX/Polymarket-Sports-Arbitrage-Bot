# poly-sports

A Python package for fetching and analyzing sports market data from Polymarket, comparing it with traditional sportsbook odds to identify directional trading opportunities.

## Features

- **Polymarket Data Fetching**: Fetches all sports markets from Polymarket Gamma API
- **Sportsbook Integration**: Matches Polymarket events with The Odds API to compare prices
- **Event Matching**: Intelligent fuzzy matching of events across platforms using team names and metadata
- **Directional Opportunity Detection**: Identifies when Polymarket undervalues outcomes compared to sportsbooks
- **Delta Analysis**: Finds sportsbooks with maximum price differences for each event
- **PnL Monitoring**: Real-time profit and loss tracking for active positions
- **Data Persistence**: Stores events and odds data for efficient re-analysis
- **Multiple Export Formats**: Exports data to both JSON and CSV formats
- **Comprehensive Testing**: Test-driven development with full test coverage

## Setup

### Prerequisites

- Python 3.9 or higher
- pip or uv package manager

### Installation

1. Install dependencies:
```bash
pip install py-clob-client requests python-dotenv pandas pytest pytest-mock rapidfuzz python-dateutil
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

# The Odds API Configuration (Required for sportsbook comparison)
ODDS_API_KEY=your_odds_api_key_here

# CLOB API Configuration (Optional - for data enrichment)
CLOB_HOST=https://clob.polymarket.com
ENRICH_WITH_CLOB=false

# Output Configuration (Optional)
OUTPUT_DIR=data
```

**Required:**
- `GAMMA_API_URL` - Base URL for Polymarket Gamma API (default: `https://gamma-api.polymarket.com`)
- `ODDS_API_KEY` - The Odds API key (required for sportsbook comparison)

**Optional:**
- `CLOB_HOST` - CLOB API host URL (default: `https://clob.polymarket.com`)
- `ENRICH_WITH_CLOB` - Enable CLOB data enrichment (default: `false`)
- `EXCLUDE_ENDED_MARKETS` - Exclude markets that have already ended (default: `true`)
- `OUTPUT_DIR` - Directory to save output files (default: `data`)
- `ODDS_API_REGIONS` - Comma-separated list of regions for The Odds API (default: `us`)
- `ODDS_API_MARKETS` - Comma-separated list of markets to fetch (default: `h2h`)
- `ODDS_API_ODDS_FORMAT` - Odds format: `american` or `decimal` (default: `american`)
- `ODDS_API_MIN_CONFIDENCE` - Minimum confidence for event matching (default: `0.8`)
- `USE_STORED_EVENTS` - Use stored event files if available (default: `true`)
- `EVENTS_DIR` - Directory for stored event JSON files (default: `data/sportsbook_data/events`)
- `EXCLUDE_1H_MONEYLINE` - Exclude first half moneyline bets (default: `false`)
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

### 2. Fetch and Compare Odds (Production)

Fetch odds from The Odds API and create comparison dataset with Polymarket data:

```bash
python -m poly_sports.data_fetching.fetch_odds_comparison
```

**Prerequisites:**
- `ODDS_API_KEY` must be set in `.env` file
- `data/arbitrage_data_filtered.json` must exist (run step 1 first)

This script:
1. Loads Polymarket arbitrage data
2. Groups events by sport (auto-detected)
3. Fetches events from The Odds API (or loads from stored files if available)
4. Matches Polymarket events to The Odds API events using fuzzy matching
5. Fetches odds from multiple sportsbooks
6. Enriches odds with all formats (American, decimal, implied probability)
7. Consolidates sportsbook data into aggregate statistics
8. Saves comparison data and stores events/odds for future use

**Output:**
- `data/arbitrage_comparison.json` - Merged comparison data (JSON)
- `data/arbitrage_comparison.csv` - Merged comparison data (CSV)
- `data/sportsbook_data/events/*.json` - Stored event files by sport
- `data/sportsbook_data/odds/*.json` - Stored odds files by sport

**Note:** The script will automatically save fetched events and odds to disk. On subsequent runs with `USE_STORED_EVENTS=true`, it will use the stored files instead of making API calls, saving API quota.

### 3. Test Odds Pipeline (Development/Testing)

Test the odds matching pipeline using mock NCAAF data:

```bash
python scripts/test_odds_pipeline.py
```

**Prerequisites:**
- `data/arbitrage_data_filtered.json` must exist (run step 1 first)
- `data/mock_ncaaf_events.json` and `data/mock_ncaaf.json` must exist

**Output:**
- `data/arbitrage_comparison_test.json` - Merged comparison data (JSON)
- `data/arbitrage_comparison_test.csv` - Merged comparison data (CSV)

### 4. Run Arbitrage Detection

Detect directional trading opportunities from comparison data:

```bash
python scripts/run_arbitrage_detection.py [--sort-by profit_margin|delta_difference]
```

**Prerequisites:**
- `data/arbitrage_comparison.json` must exist (run step 2 first)

**Options:**
- `--sort-by`: Sort opportunities by `profit_margin` or `delta_difference` before saving

This script:
1. Loads comparison data from `data/arbitrage_comparison.json`
2. Detects directional opportunities with a minimum profit threshold (default: 10%)
3. Filters by minimum liquidity (default: $1000)
4. Displays detailed opportunity information including:
   - Profit margins and absolute profit
   - Market type (2-way or 3-way) and match confidence
   - Liquidity and spread information
   - Matched outcomes with buy prices and target prices
5. Saves results to `data/directional_arbitrage.json`

**Note:** This detects "directional opportunities" (not traditional arbitrage) because Polymarket prices always sum to 1.0. The system identifies when Polymarket undervalues outcomes compared to sportsbooks, allowing you to buy low and sell as prices move toward fair value.

### 5. Run Max Delta Analysis

Find the sportsbook with the largest delta difference for each event:

```bash
python scripts/run_max_delta_analysis.py [--odds-dir DIR] [--top-n N] [--output FILE]
```

**Prerequisites:**
- `data/arbitrage_comparison.json` must exist (run step 2 first)
- `data/sportsbook_data/odds/*.json` files must exist

**Options:**
- `--odds-dir`: Directory path to raw odds JSON files (default: `data/sportsbook_data/odds/`)
- `--top-n`: Number of top events to return (default: 50)
- `--output`: Output file path (default: `data/max_delta_by_sportsbook.json`)

This script:
1. Loads comparison data and raw odds files
2. For each event, compares Polymarket prices with individual sportsbook odds
3. Finds the sportsbook with maximum delta_difference (difference between sportsbook implied probability and Polymarket price)
4. Filters by minimum volume (default: $1000)
5. Returns top N events sorted by delta_difference

**Output:**
- `data/max_delta_by_sportsbook.json` - Top events with max delta information

### 6. Monitor PnL (Profit and Loss)

Monitor real-time Polymarket prices and calculate simulated PnL for positions:

```bash
python scripts/monitor_pnl.py
```

**Prerequisites:**
- `data/arbitrage_comparison_test.json` must exist (run step 3 first, or use comparison data from step 2)

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

Here's the typical workflow for analyzing directional trading opportunities:

1. **Fetch sports markets from Polymarket:**
   ```bash
   python -m poly_sports.data_fetching.fetch_sports_markets
   ```
   This creates `data/arbitrage_data_filtered.json` with match winner and draw markets.

2. **Fetch and compare with sportsbook odds:**
   ```bash
   python -m poly_sports.data_fetching.fetch_odds_comparison
   ```
   This matches Polymarket events with The Odds API and creates `data/arbitrage_comparison.json`.

3. **Detect directional opportunities:**
   ```bash
   python scripts/run_arbitrage_detection.py --sort-by profit_margin
   ```
   This identifies opportunities where Polymarket undervalues outcomes compared to sportsbooks.

4. **Analyze max delta by sportsbook (optional):**
   ```bash
   python scripts/run_max_delta_analysis.py --top-n 50
   ```
   This finds which sportsbook has the largest price difference for each event.

5. **Monitor PnL (optional, for active positions):**
   ```bash
   python scripts/monitor_pnl.py
   ```
   This monitors real-time prices and calculates PnL for positions.

### Output Files

All output files are saved to the `data/` directory by default:

**From fetch_sports_markets:**
- `data/sports_markets.json` - Full market data in JSON format (pretty-printed)
- `data/sports_markets.csv` - Flattened market data in CSV format
- `data/arbitrage_data.json` - Extracted arbitrage-relevant data in JSON format
- `data/arbitrage_data.csv` - Extracted arbitrage-relevant data in CSV format
- `data/arbitrage_data_filtered.json` - Filtered match winner and draw markets (JSON)
- `data/arbitrage_data_filtered.csv` - Filtered match winner and draw markets (CSV)

**From fetch_odds_comparison:**
- `data/arbitrage_comparison.json` - Merged Polymarket and Odds API comparison data (JSON)
- `data/arbitrage_comparison.csv` - Merged Polymarket and Odds API comparison data (CSV)
- `data/sportsbook_data/events/*.json` - Stored event files by sport (e.g., `americanfootball_nfl.json`)
- `data/sportsbook_data/odds/*.json` - Stored odds files by sport

**From test_odds_pipeline (testing only):**
- `data/arbitrage_comparison_test.json` - Merged Polymarket and Odds API comparison data (JSON)
- `data/arbitrage_comparison_test.csv` - Merged Polymarket and Odds API comparison data (CSV)

**From run_arbitrage_detection:**
- `data/directional_arbitrage.json` - Detected directional opportunities (JSON)

**From run_max_delta_analysis:**
- `data/max_delta_by_sportsbook.json` - Top events with maximum delta by sportsbook (JSON)

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

### Data Flow

1. **Polymarket Data Fetching**: 
   - Fetches sports markets from the Polymarket Gamma API `/events` endpoint
   - Filters for sports category markets
   - Extracts arbitrage-relevant data (match winner, draw markets)
   - Excludes ended markets by default

2. **Event Matching**:
   - Auto-detects sport type from Polymarket event data
   - Groups events by sport (NFL, NBA, etc.)
   - Fetches corresponding events from The Odds API
   - Uses fuzzy string matching to match events across platforms:
     - Normalizes team names (lowercase, strip whitespace)
     - Checks for exact matches, partial matches, and fuzzy similarity
     - Calculates confidence scores (0-1) for each match
     - Only includes matches above confidence threshold (default: 0.8)

3. **Odds Comparison**:
   - Fetches odds from multiple sportsbooks via The Odds API
   - Enriches odds with all formats:
     - American odds (e.g., +150, -200)
     - Decimal odds (e.g., 2.50, 1.50)
     - Implied probability (0-1)
   - Consolidates sportsbook data into aggregate statistics:
     - Average price and implied probability across all sportsbooks
     - Min/max price range
     - Count of sportsbooks offering each outcome

4. **Opportunity Detection**:
   - Compares Polymarket prices with sportsbook implied probabilities
   - Identifies directional opportunities where:
     - `pm_price < sb_implied_prob` (Polymarket undervalues outcome)
     - Expected price movement = `sb_implied_prob - pm_price`
     - Potential profit = `(sb_implied_prob - pm_price) / pm_price`
   - Filters by minimum profit threshold (default: 10%) and liquidity (default: $1000)

5. **Data Persistence**:
   - Stores fetched events and odds in `data/sportsbook_data/`
   - Enables efficient re-analysis without API calls when `USE_STORED_EVENTS=true`

### Why Directional Opportunities, Not Traditional Arbitrage?

Polymarket prices always sum to 1.0 because they represent probabilities in a prediction market. This means:
- All possible outcomes are covered
- No guaranteed arbitrage exists on Polymarket alone
- Traditional arbitrage (betting on all outcomes for guaranteed profit) is not possible

Instead, the system focuses on **directional opportunities** where:
- Polymarket undervalues an outcome compared to sportsbooks
- You can buy at the lower Polymarket price
- As the game progresses, the price may rise toward the sportsbook's implied probability
- You can sell at any time to lock in profits (unlike traditional betting)

See `docs/ARBITRAGE_CALCULATION.md` for detailed mathematical explanations.

## Error Handling

- API errors are caught and logged with tracebacks
- CLOB enrichment failures are handled gracefully (continues with unenriched data)
- Missing fields in market data are handled appropriately
- Network errors include retry logic where applicable
- Event matching failures are logged but don't stop processing
- Missing odds data for matched events are skipped with warnings
- Invalid JSON parsing is handled gracefully

## Project Structure

```
poly-sports/
├── poly_sports/
│   ├── data_fetching/      # Data fetching modules
│   │   ├── fetch_sports_markets.py    # Polymarket data fetching
│   │   ├── fetch_odds_api.py          # The Odds API client
│   │   ├── fetch_odds_data.py         # Main odds fetching and merging
│   │   └── fetch_odds_comparison.py   # Production comparison script
│   ├── processing/         # Data processing modules
│   │   ├── arbitrage_calculation.py   # Opportunity detection
│   │   ├── event_matching.py          # Event matching logic
│   │   ├── sport_detection.py         # Sport type detection
│   │   └── extractors/                 # Sport-specific extractors
│   └── utils/              # Utility modules
│       ├── file_utils.py              # File I/O helpers
│       └── odds_utils.py               # Odds conversion utilities
├── scripts/                # Executable scripts
│   ├── run_arbitrage_detection.py     # Detect opportunities
│   ├── run_max_delta_analysis.py      # Max delta analysis
│   ├── test_odds_pipeline.py           # Test pipeline
│   └── monitor_pnl.py                  # PnL monitoring
├── tests/                  # Test suite
├── data/                   # Output data directory
│   └── sportsbook_data/    # Stored events and odds
└── docs/                   # Documentation
    └── ARBITRAGE_CALCULATION.md        # Detailed calculation docs
```

## Future Enhancements

- Continuous sync mode (watch for new markets)
- Database storage option
- Additional category filters
- Scheduled execution
- Rate limiting and retry logic improvements
- Real-time price alerts
- Automated trading strategies

## License

[Add your license here]
