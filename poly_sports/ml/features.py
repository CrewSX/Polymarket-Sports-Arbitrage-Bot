"""Feature extraction for XGBoost strategy model from arbitrage opportunities."""
import math
from typing import Dict, Any, List, Optional

import numpy as np

# Ordered feature names for consistent columns (must match keys in _extract)
FEATURE_NAMES = [
    "pm_price",
    "sb_implied_prob",
    "edge_raw",           # sb_implied_prob - pm_price
    "profit_margin",
    "delta_difference",
    "match_confidence",
    "outcome_match_confidence",
    "log_liquidity",
    "log_pm_liquidity",
    "pm_spread",
    "sportsbook_count",
    "market_type_2way",   # 1 = 2-way, 0 = 3-way
]


def _safe_float(x: Any, default: float = 0.0) -> float:
    if x is None:
        return default
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _safe_log(x: float, default: float = 0.0) -> float:
    if x is None or x <= 0:
        return default
    try:
        return math.log1p(float(x))
    except (TypeError, ValueError):
        return default


def _get_first_matched_outcome(opportunity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get first matched outcome from opportunity (one row per outcome in directional data)."""
    matched = opportunity.get("matched_outcomes") or []
    if not matched:
        return None
    return matched[0]


def opportunity_to_features(opportunity: Dict[str, Any]) -> np.ndarray:
    """
    Extract a fixed-size feature vector from one opportunity (directional arbitrage entry).

    Uses the first matched outcome for pm_price / sb_implied_prob. Handles missing
    fields with safe defaults so the model can run on partial data.

    Args:
        opportunity: One item from detect_arbitrage_opportunities() or directional_arbitrage.json

    Returns:
        1D numpy array of shape (len(FEATURE_NAMES),) in FEATURE_NAMES order.
    """
    mo = _get_first_matched_outcome(opportunity)
    pm_price = _safe_float(mo.get("pm_price") if mo else None)
    sb_implied_prob = _safe_float(mo.get("sb_implied_prob") if mo else None)
    outcome_match_conf = _safe_float(mo.get("match_confidence", 1.0) if mo else 1.0)

    profit_margin = _safe_float(opportunity.get("profit_margin"))
    delta_difference = _safe_float(opportunity.get("delta_difference"))
    match_confidence = _safe_float(opportunity.get("match_confidence"), 1.0)
    liquidity = _safe_float(opportunity.get("liquidity") or opportunity.get("pm_event_liquidity"), 1.0)
    pm_liquidity = _safe_float(opportunity.get("pm_liquidity") or opportunity.get("pm_market_liquidityNum"), 1.0)
    pm_spread = _safe_float(opportunity.get("pm_spread"), 0.01)
    sportsbook_count = _safe_float(opportunity.get("sportsbook_count"), 1.0)
    market_type = (opportunity.get("market_type") or "2-way").strip().lower()
    market_type_2way = 1.0 if market_type == "2-way" else 0.0

    edge_raw = sb_implied_prob - pm_price if (pm_price and sb_implied_prob) else 0.0

    return np.array([
        pm_price,
        sb_implied_prob,
        edge_raw,
        profit_margin,
        delta_difference,
        match_confidence,
        outcome_match_conf,
        _safe_log(liquidity),
        _safe_log(pm_liquidity),
        pm_spread,
        sportsbook_count,
        market_type_2way,
    ], dtype=np.float64)


def opportunities_to_matrix(opportunities: List[Dict[str, Any]]) -> np.ndarray:
    """
    Build feature matrix from a list of opportunities.

    Args:
        opportunities: List of opportunity dicts.

    Returns:
        2D array of shape (n_samples, n_features).
    """
    if not opportunities:
        return np.zeros((0, len(FEATURE_NAMES)), dtype=np.float64)
    rows = [opportunity_to_features(opp) for opp in opportunities]
    return np.vstack(rows)
