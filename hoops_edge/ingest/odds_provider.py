"""Odds provider interfaces."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import json


@dataclass
class MarketOdds:
    line: Optional[float]
    prices: Dict[str, int]


@dataclass
class GameOdds:
    game_id: str
    date: datetime
    home: str
    away: str
    books: Dict[str, Dict[str, MarketOdds]]

    @property
    def matchup(self) -> str:
        return f"{self.away} @ {self.home}"


class OddsProvider:
    """Base class for odds providers."""

    def fetch(self, date: datetime, books: Iterable[str]) -> List[GameOdds]:
        raise NotImplementedError


class ReplayOddsProvider(OddsProvider):
    """Loads odds data from a JSON fixture."""

    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path

    def fetch(self, date: datetime, books: Iterable[str]) -> List[GameOdds]:
        with self.fixture_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        if isinstance(payload, dict):
            payload = [payload]

        results: List[GameOdds] = []
        for game in payload:
            game_books: Dict[str, Dict[str, MarketOdds]] = {}
            for book_name, markets in game.get("books", {}).items():
                if book_name not in books:
                    continue
                book_markets: Dict[str, MarketOdds] = {}
                for market_key, market_value in markets.items():
                    if isinstance(market_value, dict):
                        line = market_value.get("line")
                        prices = {
                            side: int(price)
                            for side, price in market_value.items()
                            if side != "line"
                        }
                    else:
                        line = None
                        prices = {}
                    book_markets[market_key] = MarketOdds(line=line, prices=prices)
                if book_markets:
                    game_books[book_name] = book_markets
            results.append(
                GameOdds(
                    game_id=game["game_id"],
                    date=datetime.fromisoformat(game["date"]),
                    home=game["home"],
                    away=game["away"],
                    books=game_books,
                )
            )
        return results


class LiveOddsProvider(OddsProvider):
    """Placeholder live provider.

    The implementation is intentionally lightweight for v1; it can be
    replaced by a real API-backed provider later.
    """

    def __init__(self) -> None:
        self._not_implemented_message = (
            "Live odds are not implemented in the offline build. "
            "Use --replay with a fixture to run deterministically."
        )

    def fetch(self, date: datetime, books: Iterable[str]) -> List[GameOdds]:
        raise RuntimeError(self._not_implemented_message)
