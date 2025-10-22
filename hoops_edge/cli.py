"""Command line entrypoint for hoops-edge."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from hoops_edge.config import DEFAULT_BOOKS, OUTPUT_DIR, PROPS_MARKETS
from hoops_edge.config import SUPPORTED_BOOKS
from hoops_edge.ingest.mapping import conference_for_team
from hoops_edge.ingest.odds_provider import GameOdds, LiveOddsProvider, ReplayOddsProvider
from hoops_edge.ingest.props_provider import DraftKingsPropsProvider
from hoops_edge.ingest.stats_provider import NBAStatsProvider
from hoops_edge.models.features import build_game_features
from hoops_edge.models.pricing import (
    MarketComparison,
    compare_line_market,
    compare_probability_market,
)
from hoops_edge.models.simulator import simulate_game, simulate_props
from hoops_edge.output.excel import ExcelWriter
from hoops_edge.utils import log


@dataclass
class BetRecord:
    tip: str
    matchup: str
    market: str
    selection: str
    book: str
    line_price: str
    fair_value: str
    book_value: str
    diff: str
    edge: str
    kelly: str
    risk: str
    notes: str
    pulled_at: str


@dataclass
class AuditRecord:
    game_id: str
    market: str
    side: str
    book: str
    line: str
    price_a: str
    price_b: str
    implied_a: str
    implied_b: str
    devig_a: str
    devig_b: str
    timestamp: str
    source: str
    books: str
    conference: str


def _is_interactive() -> bool:
    try:
        return bool(__import__("sys").stdin.isatty())
    except Exception:
        return False


def _prompt(prompt: str, default: str | None = None) -> str:
    if not _is_interactive():
        return default or ""
    value = input(prompt)
    if not value:
        return default or ""
    return value


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="hoops-edge", description="NBA betting edge scanner")
    parser.add_argument("scan", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("--date", dest="date", help="Target date (YYYY-MM-DD)")
    parser.add_argument("--conf", choices=["east", "west", "all"], help="Conference filter")
    parser.add_argument("--books", help="Comma separated list of books", default=",")
    parser.add_argument("--replay", help="Replay fixture e.g. odds=path.json")
    return parser.parse_args(argv)


def _parse_date(value: str | None) -> datetime:
    if value:
        return datetime.fromisoformat(value)
    today = datetime.utcnow()
    return today


def _parse_books(value: str | None) -> List[str]:
    if not value or value == ",":
        return DEFAULT_BOOKS
    return [book.strip().upper() for book in value.split(",") if book.strip()]


def _select_games(games: List[GameOdds]) -> List[GameOdds]:
    if not games:
        return []
    if not _is_interactive():
        return games
    log.bullet_list("Available games:", [f"{g.matchup}" for g in games])
    selection = _prompt("Select one or multiple (e.g., 1,3) or 'all': ", "all")
    if not selection or selection.lower() == "all":
        return games
    indices = {int(idx.strip()) for idx in selection.split(",") if idx.strip().isdigit()}
    chosen: List[GameOdds] = []
    for idx, game in enumerate(games, start=1):
        if idx in indices:
            chosen.append(game)
    return chosen or games


def _parse_replay(value: str | None) -> Path | None:
    if not value:
        return None
    if "=" in value:
        key, path = value.split("=", 1)
        if key != "odds":
            raise ValueError("Unsupported replay argument; expected odds=<path>")
        return Path(path)
    return Path(value)


def _format_percentage(value: float) -> str:
    return f"{value * 100:.1f}%"


def _format_diff(value: float, market: str) -> str:
    if market in {"Spread", "Total"}:
        return f"{value:.2f}"
    return _format_percentage(value)


def _build_bet_record(
    matchup: str,
    tip: str,
    market: str,
    selection: str,
    book: str,
    line_price: str,
    comparison: MarketComparison,
    notes: str = "",
    pulled_at: str | None = None,
) -> BetRecord:
    return BetRecord(
        tip=tip,
        matchup=matchup,
        market=market,
        selection=selection,
        book=book,
        line_price=line_price,
        fair_value=f"{comparison.fair_value:.3f}" if market in {"Spread", "Total"} else _format_percentage(comparison.fair_value),
        book_value=f"{comparison.book_value:.3f}" if market in {"Spread", "Total"} else _format_percentage(comparison.book_value),
        diff=_format_diff(comparison.diff, market),
        edge=_format_percentage(comparison.edge),
        kelly=_format_percentage(comparison.kelly),
        risk=comparison.risk,
        notes=notes,
        pulled_at=pulled_at or datetime.utcnow().isoformat(timespec="seconds"),
    )


def _bet_record_to_row(record: BetRecord) -> List[str]:
    return [
        record.tip,
        record.matchup,
        record.market,
        record.selection,
        record.book,
        record.line_price,
        record.fair_value,
        record.book_value,
        record.diff,
        record.edge,
        record.kelly,
        record.risk,
        record.notes,
        record.pulled_at,
    ]


def _audit_record_to_row(record: AuditRecord) -> List[str]:
    return [
        record.game_id,
        record.market,
        record.side,
        record.book,
        record.line,
        record.price_a,
        record.price_b,
        record.implied_a,
        record.implied_b,
        record.devig_a,
        record.devig_b,
        record.timestamp,
        record.source,
        record.books,
        record.conference,
    ]


def scan(argv: Sequence[str] | None = None) -> None:
    ns = _parse_args(argv)
    target_date = _parse_date(ns.date)
    conference = ns.conf or (
        _prompt("Conference [1] East [2] West [3] All: ", "all")
        .replace("1", "east")
        .replace("2", "west")
        .replace("3", "all")
    )
    books = _parse_books(ns.books)
    if not set(books).issubset(set(SUPPORTED_BOOKS)):
        raise SystemExit("Unsupported book specified")

    replay_path = _parse_replay(ns.replay)
    if replay_path:
        provider = ReplayOddsProvider(replay_path)
        source = "replay"
    else:
        provider = LiveOddsProvider()
        source = "live"

    odds = provider.fetch(target_date, books)

    filtered_games = []
    for game in odds:
        home_conf = conference_for_team(game.home)
        away_conf = conference_for_team(game.away)
        if conference == "all" or home_conf == conference or away_conf == conference:
            filtered_games.append(game)

    selected_games = _select_games(filtered_games)
    if not selected_games:
        log.warning("No games found for the selected filters.")
        return

    stats_provider = NBAStatsProvider()
    team_names = {game.home for game in selected_games} | {game.away for game in selected_games}
    team_stats = stats_provider.fetch_team_stats(team_names)

    picks: List[BetRecord] = []
    props_rows: List[BetRecord] = []
    audit_rows: List[AuditRecord] = []
    summary_rows: List[List[str]] = []

    fixture_dirs = [Path("tests/fixtures/props"), Path("hoops_edge/data/fixtures/props")]
    for candidate in fixture_dirs:
        if candidate.exists():
            props_fixture_dir = candidate
            break
    else:
        props_fixture_dir = None
    props_provider = DraftKingsPropsProvider(props_fixture_dir)
    props_data = props_provider.fetch([game.game_id for game in selected_games], books[0])
    player_stats = stats_provider.fetch_player_stats({prop.player for prop in props_data})

    matchup_lookup: Dict[str, str] = {game.game_id: game.home for game in selected_games}

    for game in selected_games:
        tip = f"{target_date:%m-%d} 07:30 PM"
        matchup = game.matchup
        book_name = books[0]
        book_markets = game.books.get(book_name, {})
        home_stats = team_stats.get(game.home)
        away_stats = team_stats.get(game.away)
        if not home_stats or not away_stats:
            continue
        features = build_game_features(home_stats, away_stats)
        projection = simulate_game(game.game_id, features)

        summary_rows.append(
            [
                tip,
                matchup,
                conference,
                f"{projection.home_score:.1f}-{projection.away_score:.1f}",
                f"{projection.fair_ml_home:.2f}",
                f"{projection.fair_ml_away:.2f}",
                f"{projection.fair_spread:.2f}",
                f"{projection.fair_total:.2f}",
                f"Pace {home_stats.pace:.1f}, ORtg {home_stats.offensive_rating:.1f}",
                f"Pace {away_stats.pace:.1f}, ORtg {away_stats.offensive_rating:.1f}",
            ]
        )

        ml_market = book_markets.get("ml")
        if ml_market and ml_market.prices:
            home_comp = compare_probability_market(
                projection.fair_ml_home,
                ml_market.prices.get("home", -110),
                ml_market.prices.get("away", -110),
                "home",
            )
            picks.append(
                _build_bet_record(
                    matchup=matchup,
                    tip=tip,
                    market="ML",
                    selection="Home",
                    book=book_name,
                    line_price=f"Home / {ml_market.prices.get('home', -110)}",
                    comparison=home_comp,
                )
            )
            audit_rows.append(
                AuditRecord(
                    game_id=game.game_id,
                    market="ML",
                    side="home",
                    book=book_name,
                    line="N/A",
                    price_a=str(ml_market.prices.get("home", -110)),
                    price_b=str(ml_market.prices.get("away", -110)),
                    implied_a=f"{home_comp.fair_value:.3f}",
                    implied_b=f"{(1-home_comp.fair_value):.3f}",
                    devig_a=f"{home_comp.book_value:.3f}",
                    devig_b=f"{(1-home_comp.book_value):.3f}",
                    timestamp=datetime.utcnow().isoformat(timespec="seconds"),
                    source=source,
                    books=",".join(books),
                    conference=conference,
                )
            )

        spread_market = book_markets.get("spread")
        if spread_market and spread_market.prices:
            comparison = compare_line_market(
                projection.fair_spread,
                float(spread_market.line or 0),
                spread_market.prices.get("home", -110),
                spread_market.prices.get("away", -110),
                "home",
            )
            picks.append(
                _build_bet_record(
                    matchup=matchup,
                    tip=tip,
                    market="Spread",
                    selection="Home",
                    book=book_name,
                    line_price=f"{spread_market.line} / {spread_market.prices.get('home', -110)}",
                    comparison=comparison,
                )
            )
            audit_rows.append(
                AuditRecord(
                    game_id=game.game_id,
                    market="Spread",
                    side="home",
                    book=book_name,
                    line=str(spread_market.line),
                    price_a=str(spread_market.prices.get("home", -110)),
                    price_b=str(spread_market.prices.get("away", -110)),
                    implied_a=f"{comparison.fair_value:.3f}",
                    implied_b=f"{(-comparison.fair_value):.3f}",
                    devig_a=f"{comparison.book_value:.3f}",
                    devig_b=f"{comparison.book_value:.3f}",
                    timestamp=datetime.utcnow().isoformat(timespec="seconds"),
                    source=source,
                    books=",".join(books),
                    conference=conference,
                )
            )

        total_market = book_markets.get("total")
        if total_market and total_market.prices:
            comparison = compare_line_market(
                projection.fair_total,
                float(total_market.line or 0),
                total_market.prices.get("over", -110),
                total_market.prices.get("under", -110),
                "over",
            )
            picks.append(
                _build_bet_record(
                    matchup=matchup,
                    tip=tip,
                    market="Total",
                    selection="Over",
                    book=book_name,
                    line_price=f"Over {total_market.line} / {total_market.prices.get('over', -110)}",
                    comparison=comparison,
                )
            )
            audit_rows.append(
                AuditRecord(
                    game_id=game.game_id,
                    market="Total",
                    side="over",
                    book=book_name,
                    line=str(total_market.line),
                    price_a=str(total_market.prices.get("over", -110)),
                    price_b=str(total_market.prices.get("under", -110)),
                    implied_a=f"{comparison.fair_value:.3f}",
                    implied_b=f"{comparison.fair_value:.3f}",
                    devig_a=f"{comparison.book_value:.3f}",
                    devig_b=f"{comparison.book_value:.3f}",
                    timestamp=datetime.utcnow().isoformat(timespec="seconds"),
                    source=source,
                    books=",".join(books),
                    conference=conference,
                )
            )

    prop_projections = simulate_props(props_data, player_stats, team_stats, matchup_lookup)
    for prop, projection in zip(props_data, prop_projections):
        comparison = compare_probability_market(
            projection.fair_probability_over,
            prop.over,
            prop.under,
            "over",
        )
        record = _build_bet_record(
            matchup=next((g.matchup for g in selected_games if g.game_id == prop.game_id), prop.game_id),
            tip=f"{target_date:%m-%d} 07:30 PM",
            market=prop.market.capitalize(),
            selection=f"{prop.player} • Over",
            book=prop.book,
            line_price=f"Over {prop.line} / {prop.over}",
            comparison=comparison,
        )
        props_rows.append(record)
        audit_rows.append(
            AuditRecord(
                game_id=prop.game_id,
                market=f"Prop-{prop.market}",
                side="over",
                book=prop.book,
                line=str(prop.line),
                price_a=str(prop.over),
                price_b=str(prop.under),
                implied_a=f"{projection.fair_probability_over:.3f}",
                implied_b=f"{1-projection.fair_probability_over:.3f}",
                devig_a=f"{comparison.book_value:.3f}",
                devig_b=f"{(1-comparison.book_value):.3f}",
                timestamp=datetime.utcnow().isoformat(timespec="seconds"),
                source=source,
                books=",".join(books),
                conference=conference,
            )
        )

    excel_writer = ExcelWriter()
    output_path = excel_writer.write(
        target_date,
        conference,
        [_bet_record_to_row(bet) for bet in picks],
        [_bet_record_to_row(bet) for bet in props_rows],
        summary_rows,
        [_audit_record_to_row(audit) for audit in audit_rows],
    )

    total_bets = len(picks) + len(props_rows)
    risk_counts = {"Low": 0, "Med": 0, "High": 0}
    for bet in picks + props_rows:
        risk_counts[bet.risk] = risk_counts.get(bet.risk, 0) + 1

    log.success(
        f"Done: {len(selected_games)} games, {total_bets} bets "
        f"(Low: {risk_counts['Low']} | Med: {risk_counts['Med']} | High: {risk_counts['High']})"
    )
    log.success(f"Excel → {output_path}")


def main() -> None:
    scan()


if __name__ == "__main__":
    main()
