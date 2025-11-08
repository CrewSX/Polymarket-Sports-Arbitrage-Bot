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

## Usage

### Basic Usage

Run the script to fetch all sports markets:

```bash
python fetch_sports_markets.py
```

This will:
1. Fetch all markets from the Gamma API
2. Filter for markets with `category == "Sports"`
3. Save results to `data/sports_markets.json` and `data/sports_markets.csv`

### With CLOB Enrichment

To enrich markets with CLOB data (prices, order books, spreads), set `ENRICH_WITH_CLOB=true` in your `.env` file:

```env
ENRICH_WITH_CLOB=true
```

Then run:
```bash
python fetch_sports_markets.py
```

**Note:** CLOB enrichment requires the `py-clob-client` package to be installed.

### Output Files

All output files are saved to the `data/` directory by default:

- `data/sports_markets.json` - Full market data in JSON format (pretty-printed)
- `data/sports_markets.csv` - Flattened market data in CSV format
- `data/arbitrage_data.json` - Extracted arbitrage-relevant data in JSON format
- `data/arbitrage_data.csv` - Extracted arbitrage-relevant data in CSV format
- `data/arbitrage_data_filtered.json` - Filtered match winner and draw markets (JSON)
- `data/arbitrage_data_filtered.csv` - Filtered match winner and draw markets (CSV)

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
