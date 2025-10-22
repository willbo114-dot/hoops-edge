# hoops-edge

Terminal tool for ranking NBA bets by profitability, disagreement risk, and Kelly staking guidance. The project is designed to run deterministically in replay mode while remaining pluggable for live odds feeds.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .[dev]
```

### Replay (no API keys required)

```
python -m hoops_edge scan --replay odds=tests/fixtures/odds/2024-02-24_bos_at_nyk.json --conf east --date 2024-02-24
```

The command writes `outputs/NBA_2024-02-24_East.xlsx` and prints a summary such as:

```
✅ Done: 1 games, 7 bets (Low: 3 | Med: 3 | High: 1)
```

### Live odds

Copy `.env.example` to `.env` and populate `ODDS_API_KEY`. Live mode is scaffolded but not implemented in the offline build—use replay fixtures for deterministic runs.

### CLI flags

```
python -m hoops_edge scan [--date YYYY-MM-DD] [--conf east|west|all] [--books DK,FD] [--replay odds=path.json]
```

When flags are omitted the CLI guides you through prompts for date, conference, books, and game selection. Non-interactive environments default to today, `all`, the default books (DK), and all listed games.

### Edge & risk definitions

* **De-vig** – American odds are converted to implied probabilities and normalised proportionally across a two-way market.
* **Edge %** – `model_prob - book_prob` for probability markets; line markets estimate the win probability advantage at the posted line.
* **Risk** – Classified by disagreement size:
  * Probability markets: Low ≤ 2%, Med 2–5%, High > 5%
  * Line markets: Low ≤ 0.5, Med 0.5–1.5, High > 1.5
* **Kelly %** – Fractional Kelly using model probability and market odds, capped at 1%.

### Excel output

* `Picks` – Ranked markets across ML, spreads, totals, and props.
* `Player Props` – Grouped by team with the same columns.
* `Game Summary` – Projected score, fair ML/spread/total, and team cards.
* `Audit` – Raw market data, implied probabilities, source metadata.

Headers are frozen, auto-filtered, and colour formatted according to risk. Files are written to `outputs/NBA_<date>_<Conference>.xlsx`.

### Docker

```
docker build -t hoops-edge .
docker run --rm -v "$PWD/outputs:/app/outputs" hoops-edge \
  python -m hoops_edge scan --replay odds=/app/tests/fixtures/odds/2024-02-24_bos_at_nyk.json --conf east --date 2024-02-24
```

### Makefile targets

* `make test`
* `make run-replay`
* `make build-docker`

## Tests

```
pytest -q
```

GitHub Actions runs the replay scenario and uploads the generated Excel workbook as an artifact on every push.
