"""Configuration values for hoops-edge."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List


@dataclass(frozen=True)
class RiskThresholds:
    low: float
    medium: float

    def classify_prob(self, diff: float) -> str:
        if diff <= self.low:
            return "Low"
        if diff <= self.medium:
            return "Med"
        return "High"

    def classify_line(self, diff: float) -> str:
        if diff <= self.low:
            return "Low"
        if diff <= self.medium:
            return "Med"
        return "High"


DEFAULT_BOOKS: List[str] = ["DK"]
SUPPORTED_BOOKS: List[str] = ["DK", "FD"]

PROBABILITY_THRESHOLDS = RiskThresholds(low=0.02, medium=0.05)
LINE_THRESHOLDS = RiskThresholds(low=0.5, medium=1.5)

KELLY_CAP: float = 0.01

PROPS_MARKETS: List[str] = [
    "points",
    "rebounds",
    "assists",
    "threes",
    "pra",
]

CACHE_TTLS: Dict[str, timedelta] = {
    "odds": timedelta(seconds=180),
    "stats": timedelta(seconds=86400),
}

OUTPUT_DIR = "outputs"
