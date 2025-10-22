"""Simple simulators for games and props."""
from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt
from typing import Dict, Iterable, List

from hoops_edge.ingest.props_provider import PlayerProp
from hoops_edge.ingest.stats_provider import PlayerStats, TeamStats
from hoops_edge.models.features import (
    GameFeatures,
    PlayerFeatures,
    build_game_features,
    build_player_features,
    project_player_mean,
)
from hoops_edge.models.pricing import american_to_decimal, probability_to_american


@dataclass
class GameProjection:
    game_id: str
    home_score: float
    away_score: float
    fair_ml_home: float
    fair_ml_away: float
    fair_spread: float
    fair_total: float


@dataclass
class PropProjection:
    player: str
    market: str
    fair_mean: float
    fair_probability_over: float


def simulate_game(game_id: str, features: GameFeatures) -> GameProjection:
    offensive_edge = features.home.offensive_rating - features.away.defensive_rating
    defensive_edge = features.away.offensive_rating - features.home.defensive_rating
    pace_factor = features.pace / 100

    home_score = 100 + offensive_edge * pace_factor
    away_score = 100 + defensive_edge * pace_factor

    fair_total = home_score + away_score
    fair_spread = home_score - away_score

    # Convert spread to ML probability via logistic approximation
    home_prob = 0.5 + fair_spread / 20
    home_prob = max(0.05, min(0.95, home_prob))
    away_prob = 1 - home_prob

    return GameProjection(
        game_id=game_id,
        home_score=home_score,
        away_score=away_score,
        fair_ml_home=home_prob,
        fair_ml_away=away_prob,
        fair_spread=fair_spread,
        fair_total=fair_total,
    )


def normal_cdf(x: float, mean: float, std: float) -> float:
    z = (x - mean) / (std * sqrt(2))
    return 0.5 * (1 + erf(z))


def simulate_props(
    props: Iterable[PlayerProp],
    player_stats: Dict[str, PlayerStats],
    team_stats: Dict[str, TeamStats],
    matchup_lookup: Dict[str, str],
) -> List[PropProjection]:
    projections: List[PropProjection] = []
    for prop in props:
        player = player_stats.get(prop.player)
        opponent_team = team_stats.get(matchup_lookup.get(prop.game_id, ""))
        if not player or not opponent_team:
            continue
        features = build_player_features(player, opponent_team)
        mean = project_player_mean(features, prop.market)
        std = max(1.5, mean * 0.18)
        fair_prob = 1 - normal_cdf(prop.line, mean, std)
        projections.append(
            PropProjection(
                player=prop.player,
                market=prop.market,
                fair_mean=mean,
                fair_probability_over=fair_prob,
            )
        )
    return projections
