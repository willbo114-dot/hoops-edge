"""Pricing utilities for odds conversion and risk assessment."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from hoops_edge.config import KELLY_CAP, LINE_THRESHOLDS, PROBABILITY_THRESHOLDS


def american_to_probability(odds: int) -> float:
    if odds < 0:
        return -odds / (-odds + 100)
    return 100 / (odds + 100)


def probability_to_american(prob: float) -> int:
    prob = max(1e-6, min(0.999999, prob))
    if prob > 0.5:
        return int(round(-prob / (1 - prob) * 100))
    return int(round((1 - prob) / prob * 100))


def american_to_decimal(odds: int) -> float:
    if odds > 0:
        return 1 + odds / 100
    return 1 + 100 / -odds


def devig_two_way(price_a: int, price_b: int) -> Tuple[float, float]:
    p_a_raw = american_to_probability(price_a)
    p_b_raw = american_to_probability(price_b)
    total = p_a_raw + p_b_raw
    if total == 0:
        return 0.5, 0.5
    return p_a_raw / total, p_b_raw / total


def edge_percentage(model_prob: float, book_prob: float) -> float:
    return model_prob - book_prob


def classify_risk(diff: float, is_line: bool = False) -> str:
    thresholds = LINE_THRESHOLDS if is_line else PROBABILITY_THRESHOLDS
    return thresholds.classify_line(diff) if is_line else thresholds.classify_prob(diff)


def kelly_fraction(model_prob: float, odds: int) -> float:
    decimal = american_to_decimal(odds)
    b = decimal - 1
    q = 1 - model_prob
    if b == 0:
        return 0
    kelly = (model_prob * (decimal - 1) - q) / b
    return max(0.0, min(KELLY_CAP, kelly))


@dataclass
class MarketComparison:
    fair_value: float
    book_value: float
    diff: float
    edge: float
    kelly: float
    risk: str


def compare_probability_market(model_prob: float, price_a: int, price_b: int, side: str) -> MarketComparison:
    book_probs = devig_two_way(price_a, price_b)
    if side == "over" or side == "home" or side == "yes":
        book_prob = book_probs[0]
        odds = price_a
    else:
        book_prob = book_probs[1]
        odds = price_b
    diff = abs(model_prob - book_prob)
    risk = classify_risk(diff, is_line=False)
    edge = edge_percentage(model_prob, book_prob)
    kelly = kelly_fraction(model_prob, odds)
    return MarketComparison(
        fair_value=model_prob,
        book_value=book_prob,
        diff=diff,
        edge=edge,
        kelly=kelly,
        risk=risk,
    )


def compare_line_market(model_line: float, book_line: float, price_a: int, price_b: int, side: str) -> MarketComparison:
    diff = abs(model_line - book_line)
    risk = classify_risk(diff, is_line=True)
    if side == "home" or side == "over":
        odds = price_a
    else:
        odds = price_b
    # Edge is computed as advantage vs chosen side probability assuming half point value
    model_prob = 0.5 + (model_line - book_line) / 10
    model_prob = max(0.01, min(0.99, model_prob))
    book_prob = devig_two_way(price_a, price_b)[0]
    edge = edge_percentage(model_prob, book_prob)
    kelly = kelly_fraction(model_prob, odds)
    return MarketComparison(
        fair_value=model_line,
        book_value=book_line,
        diff=diff,
        edge=edge,
        kelly=kelly,
        risk=risk,
    )
