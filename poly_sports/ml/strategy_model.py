"""XGBoost-based trading strategy model for scoring and ranking arbitrage opportunities."""
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal

import numpy as np

from .features import FEATURE_NAMES, opportunities_to_matrix, opportunity_to_features

try:
    import xgboost as xgb
except ImportError:
    xgb = None

try:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, roc_auc_score, accuracy_score
except ImportError:
    train_test_split = None
    mean_squared_error = None
    roc_auc_score = None
    accuracy_score = None


TaskType = Literal["regress", "classify"]


class StrategyModel:
    """
    XGBoost model to score arbitrage opportunities for trading strategy.

    - regress: Predicts a continuous score (e.g. profit_margin or custom edge).
      Use to rank opportunities; higher score = better trade.
    - classify: Predicts probability of "good" trade (e.g. outcome would win, or
      profit_margin above median). Use threshold on probability to filter.

    Without historical resolution data (outcome won/lost), train with task="regress"
    and target="profit_margin" to learn a ranking model from your rule-based edge.
    With resolution data, use task="classify" and labels 1=outcome won, 0=lost.
    """

    def __init__(
        self,
        task: TaskType = "regress",
        **xgb_params,
    ):
        if xgb is None:
            raise ImportError("xgboost is required. Install with: pip install xgboost")
        self.task = task
        self._params = {
            "max_depth": 4,
            "learning_rate": 0.05,
            "n_estimators": 200,
            "objective": "reg:squarederror" if task == "regress" else "binary:logistic",
            "eval_metric": "rmse" if task == "regress" else "auc",
            "random_state": 42,
            "n_jobs": -1,
            **xgb_params,
        }
        if task == "classify":
            self._params["objective"] = "binary:logistic"
            self._params["eval_metric"] = "auc"
        self._model: Optional[Any] = None
        self._feature_names = FEATURE_NAMES

    def fit(
        self,
        opportunities: List[Dict[str, Any]],
        targets: Optional[np.ndarray] = None,
        target_col: Optional[str] = "profit_margin",
        test_size: float = 0.2,
        val_size: float = 0.1,
    ) -> Dict[str, float]:
        """
        Train the model on a list of opportunities.

        Args:
            opportunities: List of opportunity dicts (e.g. from directional_arbitrage.json).
            targets: Optional 1D array of labels (length = len(opportunities)).
                     For classify: 0/1. For regress: continuous.
            target_col: If targets is None, build targets from this field.
                        "profit_margin" -> regression on profit_margin, or
                        "profit_margin_median" -> binary: 1 if above median, else 0.
            test_size: Fraction for holdout test (for metrics).
            val_size: Fraction of train for XGBoost early-stop validation.

        Returns:
            Dict with train/test metrics (e.g. rmse, auc, accuracy).
        """
        X = opportunities_to_matrix(opportunities)
        if X.shape[0] == 0:
            raise ValueError("No valid opportunities to train on")

        if targets is not None:
            y = np.asarray(targets, dtype=np.float64)
            task = self.task
        else:
            if target_col == "profit_margin_median":
                margins = np.array([float((o.get("profit_margin") or 0)) for o in opportunities])
                median = np.median(margins)
                y = (margins >= median).astype(np.float64)
                task = "classify"
            else:
                y = np.array([float((o.get(target_col) or 0)) for o in opportunities])
                task = self.task

        if len(y) != X.shape[0]:
            raise ValueError("targets length must match number of opportunities")

        if train_test_split is None:
            raise ImportError("scikit-learn is required for training. Install with: pip install scikit-learn")

        stratify = None
        if task == "classify" and len(np.unique(y)) >= 2:
            stratify = y
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=stratify
        )
        n_val = max(1, int(len(X_tr) * val_size))
        X_train, X_val = X_tr[:-n_val], X_tr[-n_val:]
        y_train, y_val = y_tr[:-n_val], y_tr[-n_val:]

        params = {**self._params}
        if task == "classify":
            params["objective"] = "binary:logistic"
            params["eval_metric"] = "auc"
            self._model = xgb.XGBClassifier(**params)
        else:
            params["objective"] = "reg:squarederror"
            params["eval_metric"] = "rmse"
            self._model = xgb.XGBRegressor(**params)
        self.task = task
        self._model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        metrics = {}
        if self.task == "regress":
            pred_te = self._model.predict(X_te)
            metrics["test_rmse"] = float(mean_squared_error(y_te, pred_te) ** 0.5)
        else:
            pred_proba = self._model.predict_proba(X_te)[:, 1]
            pred_label = (pred_proba >= 0.5).astype(int)
            metrics["test_auc"] = float(roc_auc_score(y_te, pred_proba)) if len(np.unique(y_te)) > 1 else 0.0
            metrics["test_accuracy"] = float(accuracy_score(y_te, pred_label))

        return metrics

    def predict(self, opportunities: List[Dict[str, Any]]) -> np.ndarray:
        """Predict continuous score (regress) or class 0/1 (classify)."""
        if self._model is None:
            raise RuntimeError("Model not trained or loaded")
        X = opportunities_to_matrix(opportunities)
        if self.task == "classify":
            return (self._model.predict_proba(X)[:, 1] >= 0.5).astype(int)
        return self._model.predict(X)

    def predict_proba(self, opportunities: List[Dict[str, Any]]) -> np.ndarray:
        """Predict probability of positive class (classify) or single score column (regress)."""
        if self._model is None:
            raise RuntimeError("Model not trained or loaded")
        X = opportunities_to_matrix(opportunities)
        if self.task == "classify":
            return self._model.predict_proba(X)[:, 1]
        return self._model.predict(X).reshape(-1, 1)

    def score_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        min_score: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Score each opportunity and optionally filter/rank.

        Adds "strategy_score" to each opportunity. For regress, higher = better.
        For classify, score is P(good trade).

        Args:
            opportunities: List of opportunity dicts.
            min_score: If set, keep only opportunities with score >= min_score.
            top_k: If set, return only top_k by score (descending).

        Returns:
            List of opportunities with "strategy_score" key, optionally filtered/sorted.
        """
        if not opportunities:
            return []
        scores = self.predict_proba(opportunities).ravel()
        out = []
        for i, opp in enumerate(opportunities):
            o = {**opp, "strategy_score": float(scores[i])}
            out.append(o)
        out.sort(key=lambda x: x["strategy_score"], reverse=True)
        if min_score is not None:
            out = [o for o in out if o["strategy_score"] >= min_score]
        if top_k is not None:
            out = out[:top_k]
        return out

    def save(self, path: str) -> None:
        """Save model to path (e.g. .json or .ubj)."""
        if self._model is None:
            raise RuntimeError("No model to save")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._model.save_model(str(path))

    def load(self, path: str) -> None:
        """Load model from path. Task is inferred from saved model."""
        if xgb is None:
            raise ImportError("xgboost is required")
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        # Try classifier first (binary); if wrong, regressor load may fail
        try:
            self._model = xgb.XGBClassifier()
            self._model.load_model(str(path))
            self.task = "classify"
        except Exception:
            self._model = xgb.XGBRegressor()
            self._model.load_model(str(path))
            self.task = "regress"
