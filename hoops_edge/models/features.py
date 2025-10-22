"""Feature engineering helpers."""
from __future__ import annotations

from dataclasses import dataclass

from hoops_edge.ingest.stats_provider import PlayerStats, TeamStats


@dataclass
class GameFeatures:
    home: TeamStats
    away: TeamStats
    pace: float


@dataclass
class PlayerFeatures:
    stats: PlayerStats
    opponent_def_rating: float
    opponent_pace: float


def build_game_features(home: TeamStats, away: TeamStats) -> GameFeatures:
    pace = (home.pace + away.pace) / 2
    return GameFeatures(home=home, away=away, pace=pace)


def build_player_features(
    player: PlayerStats, opponent: TeamStats
) -> PlayerFeatures:
    return PlayerFeatures(
        stats=player,
        opponent_def_rating=opponent.defensive_rating,
        opponent_pace=opponent.pace,
    )


def project_player_mean(features: PlayerFeatures, market: str) -> float:
    base = features.stats
    if market == "points":
        return base.points * (features.opponent_pace / 100)
    if market == "rebounds":
        return base.rebounds * (100 / features.opponent_def_rating)
    if market == "assists":
        return base.assists * (features.opponent_pace / 98)
    if market == "threes":
        return base.threes * (features.opponent_pace / 100)
    if market == "pra":
        return project_player_mean(features, "points") + project_player_mean(
            features, "rebounds"
        ) + project_player_mean(features, "assists")
    return base.points
