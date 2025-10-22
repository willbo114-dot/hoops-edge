"""Utilities for canonicalising team and player names."""
from __future__ import annotations

from typing import Dict


TEAM_ALIASES: Dict[str, str] = {
    "BOS": "Boston Celtics",
    "Boston": "Boston Celtics",
    "NYK": "New York Knicks",
    "New York": "New York Knicks",
    "Knicks": "New York Knicks",
    "Celtics": "Boston Celtics",
}

TEAM_CONFERENCES: Dict[str, str] = {
    "Atlanta Hawks": "east",
    "Boston Celtics": "east",
    "Brooklyn Nets": "east",
    "Charlotte Hornets": "east",
    "Chicago Bulls": "east",
    "Cleveland Cavaliers": "east",
    "Dallas Mavericks": "west",
    "Denver Nuggets": "west",
    "Detroit Pistons": "east",
    "Golden State Warriors": "west",
    "Houston Rockets": "west",
    "Indiana Pacers": "east",
    "Los Angeles Clippers": "west",
    "Los Angeles Lakers": "west",
    "Memphis Grizzlies": "west",
    "Miami Heat": "east",
    "Milwaukee Bucks": "east",
    "Minnesota Timberwolves": "west",
    "New Orleans Pelicans": "west",
    "New York Knicks": "east",
    "Oklahoma City Thunder": "west",
    "Orlando Magic": "east",
    "Philadelphia 76ers": "east",
    "Phoenix Suns": "west",
    "Portland Trail Blazers": "west",
    "Sacramento Kings": "west",
    "San Antonio Spurs": "west",
    "Toronto Raptors": "east",
    "Utah Jazz": "west",
    "Washington Wizards": "east",
}


def canonical_team(name: str) -> str:
    """Return the canonical team name for *name*."""
    name = name.strip()
    return TEAM_ALIASES.get(name, name)


def conference_for_team(team: str) -> str:
    return TEAM_CONFERENCES.get(team, "all")
