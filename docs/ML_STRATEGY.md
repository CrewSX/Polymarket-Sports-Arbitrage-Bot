# XGBoost Trading Strategy

The project includes an **XGBoost-based ML model** to build a data-driven trading strategy for Polymarket sports arbitrage (directional opportunities).

## What it does

- **Feature extraction**: Each opportunity is turned into a fixed vector of 12 features (e.g. `pm_price`, `sb_implied_prob`, `profit_margin`, `delta_difference`, `match_confidence`, liquidity, spread, sportsbook count, market type).
- **Training**: You can train in two ways:
  1. **Without resolution data**: Use `profit_margin` (regression) to learn a ranking model, or `profit_margin_median` (classification) to learn “above/below median edge.”
  2. **With resolution data**: If you have historical outcomes (e.g. CSV with `market_id`, `outcome_won` 0/1), train a classifier to predict P(outcome wins) and use that for expected value.
- **Inference**: The model adds a `strategy_score` to each opportunity so you can rank and filter (e.g. take only top‑k or score ≥ threshold).

## Quick start

1. **Generate opportunities** (if you don’t have them yet):
   ```bash
   python3 scripts/run_arbitrage_detection.py --min-profit 0.02 --min-liquidity 1000
   ```
   This writes `data/directional_arbitrage.json`.

2. **Train the model** (regression on profit margin to rank opportunities):
   ```bash
   pip install xgboost scikit-learn  # or use project venv with pyproject deps
   python3 scripts/train_strategy_model.py --data data/directional_arbitrage.json --target profit_margin --out models/strategy_model.json
   ```

3. **Run detection and score with the model**:
   ```bash
   python3 scripts/run_arbitrage_detection.py --model models/strategy_model.json --top 20
   ```
   Opportunities are scored and ordered by `strategy_score`; output is limited to the top 20.

## Training options

| Target                 | Task       | Use case |
|------------------------|------------|----------|
| `profit_margin`        | Regression | Rank by predicted edge; no labels needed. |
| `profit_margin_median` | Classification | Binary “strong vs weak” opportunity from current rules. |
| `outcome_won`          | Classification | Needs `--resolution-csv` with columns `market_id`, `outcome_won` (0/1). |

Example with resolution CSV (for when you have resolved markets):

```bash
python3 scripts/train_strategy_model.py \
  --data data/directional_arbitrage.json \
  --resolution-csv data/resolution_labels.csv \
  --target outcome_won \
  --out models/strategy_model.json
```

## Features used

- `pm_price`, `sb_implied_prob`, raw edge
- `profit_margin`, `delta_difference`
- `match_confidence`, outcome-level match confidence
- Log liquidity (event and market)
- `pm_spread`, `sportsbook_count`, `market_type_2way`

## Using the model in code

```python
from poly_sports.ml import StrategyModel, opportunity_to_features
from poly_sports.utils.file_utils import load_json

# Load model
model = StrategyModel()
model.load("models/strategy_model.json")

# Load opportunities (e.g. from detect_arbitrage_opportunities)
opportunities = load_json("data/directional_arbitrage.json")

# Score and filter
scored = model.score_opportunities(opportunities, min_score=0.02, top_k=50)
for opp in scored[:5]:
    print(opp["strategy_score"], opp["profit_margin"], opp.get("pm_market_id"))
```

This gives you an **AI-assisted strategy**: the model learns from your arbitrage data to score and rank opportunities so you can focus on the ones it predicts to be best.
