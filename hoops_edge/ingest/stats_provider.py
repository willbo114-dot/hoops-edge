"""Stats provider using nba_api or fixtures."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass
class TeamStats:
    team: str
    pace: float
    offensive_rating: float
    defensive_rating: float
    effective_fg: float
    offensive_rebound_pct: float
    turnover_pct: float
    free_throw_rate: float
    recent_record: str


@dataclass
class PlayerStats:
    player: str
    minutes: float
    usage: float
    points: float
    rebounds: float
    assists: float
    threes: float


class StatsProvider:
    def fetch_team_stats(self, teams: Iterable[str]) -> Dict[str, TeamStats]:
        raise NotImplementedError

    def fetch_player_stats(self, players: Iterable[str]) -> Dict[str, PlayerStats]:
        raise NotImplementedError


class NBAStatsProvider(StatsProvider):
    """Simplified stats provider for offline use."""

    def fetch_team_stats(self, teams: Iterable[str]) -> Dict[str, TeamStats]:
        results: Dict[str, TeamStats] = {}
        for team in teams:
            base = sum(ord(c) for c in team) % 10
            results[team] = TeamStats(
                team=team,
                pace=95 + base,
                offensive_rating=108 + base * 0.7,
                defensive_rating=105 - base * 0.5,
                effective_fg=0.52 + base * 0.001,
                offensive_rebound_pct=0.26 + base * 0.002,
                turnover_pct=0.12 - base * 0.001,
                free_throw_rate=0.24 + base * 0.002,
                recent_record=f"{3+base%3}-{2+base%3}",
            )
        return results

    def fetch_player_stats(self, players: Iterable[str]) -> Dict[str, PlayerStats]:
        results: Dict[str, PlayerStats] = {}
        for player in players:
            base = sum(ord(c) for c in player) % 12
            results[player] = PlayerStats(
                player=player,
                minutes=28 + base,
                usage=0.22 + base * 0.003,
                points=15 + base * 0.8,
                rebounds=5 + base * 0.3,
                assists=4 + base * 0.25,
                threes=1.5 + base * 0.1,
            )
        return results
