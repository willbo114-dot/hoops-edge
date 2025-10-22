"""DraftKings props provider."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import json


@dataclass
class PlayerProp:
    game_id: str
    player: str
    market: str
    line: float
    over: int
    under: int
    book: str


class PropsProvider:
    def fetch(self, game_ids: Iterable[str], book: str) -> List[PlayerProp]:
        raise NotImplementedError


class DraftKingsPropsProvider(PropsProvider):
    def __init__(self, fixture_dir: Path | None = None) -> None:
        self.fixture_dir = fixture_dir

    def fetch(self, game_ids: Iterable[str], book: str) -> List[PlayerProp]:
        if self.fixture_dir is None:
            return []

        props: List[PlayerProp] = []
        for game_id in game_ids:
            fixture = self.fixture_dir / f"{game_id}.json"
            if not fixture.exists():
                continue
            with fixture.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            for prop in payload.get("props", []):
                if prop.get("book", book) != book:
                    continue
                props.append(
                    PlayerProp(
                        game_id=game_id,
                        player=prop["player"],
                        market=prop["market"],
                        line=float(prop["line"]),
                        over=int(prop["over"]),
                        under=int(prop["under"]),
                        book=book,
                    )
                )
        return props
