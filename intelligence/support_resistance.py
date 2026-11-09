"""
SENTINEL AI - Support & Resistance Calculator
===============================================
Calculate support and resistance levels using standard floor-trader pivot
points and local-extrema detection.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SupportResistanceCalculator:
    """Calculate support and resistance levels from OHLC price data.

    Supports three methods:

    * **pivot** — Standard floor-trader pivot points derived from the most
      recent high, low, and close.
    * **local_extrema** — Local minima and maxima detected with a rolling
      window over the close series.
    * **combined** — Union of both pivot and local-extrema levels.
    """

    def calculate(
        self,
        df: pd.DataFrame,
        method: str = "pivot",
    ) -> dict[str, Any]:
        """Calculate support/resistance levels using the specified method.

        Args:
            df: DataFrame with at least ``'high'``, ``'low'``, ``'close'``
                columns.  Column names are case-insensitive.
            method: One of ``'pivot'``, ``'local_extrema'``, ``'combined'``.

        Returns:
            ``{'support': [...], 'resistance': [...], 'pivot': float}``
        """
        # Normalise column names to lowercase
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        required = {"high", "low", "close"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"DataFrame is missing required columns: {missing}"
            )

        if method == "pivot":
            return self._pivot_method(df)
        elif method == "local_extrema":
            return self._local_extrema_method(df)
        elif method == "combined":
            return self._combined_method(df)
        else:
            raise ValueError(
                f"Unknown method '{method}'. Choose from 'pivot', "
                f"'local_extrema', 'combined'."
            )

    # ------------------------------------------------------------------
    # Pivot points
    # ------------------------------------------------------------------

    def calculate_pivot_points(
        self,
        high: float,
        low: float,
        close: float,
    ) -> dict[str, float]:
        """Standard floor-trader pivot-point calculation.

        Formulas::

            P  = (H + L + C) / 3
            S1 = 2*P - H        R1 = 2*P - L
            S2 = P - (H - L)    R2 = P + (H - L)

        Args:
            high: Period high.
            low: Period low.
            close: Period close.

        Returns:
            ``{'pivot': P, 'S1': S1, 'S2': S2, 'R1': R1, 'R2': R2}``
        """
        pivot = (high + low + close) / 3.0
        s1 = 2.0 * pivot - high
        s2 = pivot - (high - low)
        r1 = 2.0 * pivot - low
        r2 = pivot + (high - low)

        result = {
            "pivot": round(pivot, 4),
            "S1": round(s1, 4),
            "S2": round(s2, 4),
            "R1": round(r1, 4),
            "R2": round(r2, 4),
        }

        logger.debug("Pivot points: %s", result)
        return result

    # ------------------------------------------------------------------
    # Local extrema
    # ------------------------------------------------------------------

    def find_local_extrema(
        self,
        prices: pd.Series,
        window: int = 20,
    ) -> dict[str, list[float]]:
        """Find local minima and maxima as support/resistance candidates.

        A point is a local minimum (support) if it is the minimum value
        within a rolling window centred on that point.  Analogously for
        maxima (resistance).

        Args:
            prices: Price series (typically close prices).
            window: Rolling window size.

        Returns:
            ``{'support': [float, ...], 'resistance': [float, ...]}``
        """
        prices = prices.dropna()
        if len(prices) < window:
            logger.warning(
                "Price series (%d rows) shorter than window (%d). "
                "Returning empty levels.",
                len(prices),
                window,
            )
            return {"support": [], "resistance": []}

        half_w = window // 2

        supports: list[float] = []
        resistances: list[float] = []

        values = prices.values.astype(np.float64)

        for i in range(half_w, len(values) - half_w):
            local_slice = values[i - half_w : i + half_w + 1]
            current = values[i]

            if current == np.min(local_slice):
                supports.append(round(float(current), 4))
            if current == np.max(local_slice):
                resistances.append(round(float(current), 4))

        # Deduplicate and sort
        supports = sorted(set(supports))
        resistances = sorted(set(resistances))

        logger.info(
            "Local extrema: %d support, %d resistance levels (window=%d).",
            len(supports),
            len(resistances),
            window,
        )
        return {"support": supports, "resistance": resistances}

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _pivot_method(self, df: pd.DataFrame) -> dict[str, Any]:
        """Calculate levels using the most recent bar's pivot points."""
        last = df.iloc[-1]
        pivots = self.calculate_pivot_points(
            high=float(last["high"]),
            low=float(last["low"]),
            close=float(last["close"]),
        )
        return {
            "support": [pivots["S1"], pivots["S2"]],
            "resistance": [pivots["R1"], pivots["R2"]],
            "pivot": pivots["pivot"],
        }

    def _local_extrema_method(
        self,
        df: pd.DataFrame,
        window: int = 20,
    ) -> dict[str, Any]:
        """Calculate levels using local extrema on the close series."""
        extrema = self.find_local_extrema(df["close"], window=window)
        # Use the last bar's pivot as a reference
        last = df.iloc[-1]
        pivot = round((float(last["high"]) + float(last["low"]) + float(last["close"])) / 3.0, 4)
        return {
            "support": extrema["support"],
            "resistance": extrema["resistance"],
            "pivot": pivot,
        }

    def _combined_method(self, df: pd.DataFrame) -> dict[str, Any]:
        """Merge pivot and local-extrema levels."""
        pivot_result = self._pivot_method(df)
        extrema_result = self._local_extrema_method(df)

        supports = sorted(
            set(pivot_result["support"] + extrema_result["support"])
        )
        resistances = sorted(
            set(pivot_result["resistance"] + extrema_result["resistance"])
        )

        return {
            "support": supports,
            "resistance": resistances,
            "pivot": pivot_result["pivot"],
        }
