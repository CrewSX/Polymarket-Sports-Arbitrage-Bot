"""ML-based trading strategy for Polymarket sports arbitrage."""
from .features import opportunity_to_features, FEATURE_NAMES
from .strategy_model import StrategyModel

__all__ = [
    "StrategyModel",
    "opportunity_to_features",
    "FEATURE_NAMES",
]
