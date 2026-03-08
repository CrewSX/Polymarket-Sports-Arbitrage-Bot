#!/usr/bin/env python3
"""
Train XGBoost strategy model on directional arbitrage opportunities.

Without resolution data (outcome won/lost):
  - Use --target profit_margin to train a regression model that predicts edge (rank opportunities).
  - Use --target profit_margin_median to train a binary classifier (above/below median edge).

With resolution data (optional CSV with market_id, outcome_won 0/1):
  - Use --resolution-csv path and --target outcome_won for a classifier that predicts P(outcome wins).

Examples:
  python scripts/train_strategy_model.py --data data/directional_arbitrage.json --target profit_margin --out models/strategy.json
  python scripts/train_strategy_model.py --data data/directional_arbitrage.json --target profit_margin_median --out models/strategy_clf.json
"""
import argparse
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import numpy as np

from poly_sports.utils.file_utils import load_json, save_json
from poly_sports.utils.logger import logger
from poly_sports.ml.strategy_model import StrategyModel


def main():
    parser = argparse.ArgumentParser(description="Train XGBoost strategy model on arbitrage opportunities")
    parser.add_argument("--data", type=str, default="data/directional_arbitrage.json", help="Path to opportunities JSON")
    parser.add_argument("--out", type=str, default="models/strategy_model.json", help="Output model path")
    parser.add_argument(
        "--target",
        type=str,
        default="profit_margin",
        choices=["profit_margin", "profit_margin_median", "outcome_won"],
        help="Target: profit_margin (regress), profit_margin_median (classify), outcome_won (classify, needs --resolution-csv)",
    )
    parser.add_argument("--resolution-csv", type=str, default=None, help="Optional CSV with market_id,outcome_won for labels")
    parser.add_argument("--test-size", type=float, default=0.2, help="Fraction for test set")
    parser.add_argument("--max-depth", type=int, default=4, help="XGBoost max_depth")
    parser.add_argument("--n-estimators", type=int, default=200, help="XGBoost n_estimators")
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        logger.info(f"Error: {data_path} not found. Run arbitrage detection first to generate directional_arbitrage.json")
        sys.exit(1)

    opportunities = load_json(str(data_path))
    if not opportunities:
        logger.info("No opportunities in file. Run arbitrage detection with lower --min-profit to get more data.")
        sys.exit(1)

    logger.info(f"Loaded {len(opportunities)} opportunities from {data_path}")

    targets = None
    task = "regress" if args.target == "profit_margin" else "classify"
    if args.target == "outcome_won" and args.resolution_csv:
        res_path = Path(args.resolution_csv)
        if not res_path.exists():
            logger.info(f"Resolution CSV not found: {res_path}")
            logger.info("To train without resolution data, use: --target profit_margin (no --resolution-csv)")
            sys.exit(1)
        try:
            import pandas as pd
            df = pd.read_csv(args.resolution_csv)
            if "market_id" not in df.columns or "outcome_won" not in df.columns:
                logger.info("Resolution CSV must have columns: market_id, outcome_won")
                sys.exit(1)
            id_to_won = dict(zip(df["market_id"].astype(str), df["outcome_won"].astype(float)))
            targets = np.array([id_to_won.get(str(o.get("pm_market_id")), np.nan) for o in opportunities])
            valid = ~np.isnan(targets)
            opportunities = [o for o, v in zip(opportunities, valid) if v]
            targets = targets[valid]
            if len(opportunities) == 0:
                logger.info("No opportunities matched resolution CSV market_ids")
                sys.exit(1)
            logger.info(f"Using {len(opportunities)} opportunities with resolution labels")
        except Exception as e:
            logger.info(f"Failed to load resolution CSV: {e}")
            sys.exit(1)
    elif args.target == "outcome_won":
        logger.info("--target outcome_won requires --resolution-csv with a path to a CSV (market_id, outcome_won)")
        sys.exit(1)

    model = StrategyModel(task=task, max_depth=args.max_depth, n_estimators=args.n_estimators)

    if targets is not None:
        metrics = model.fit(opportunities, targets=targets, test_size=args.test_size)
    else:
        metrics = model.fit(
            opportunities,
            target_col=args.target,
            test_size=args.test_size,
        )

    logger.info(f"Metrics: {metrics}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(out_path))
    logger.info(f"Model saved to {out_path}")


if __name__ == "__main__":
    main()
