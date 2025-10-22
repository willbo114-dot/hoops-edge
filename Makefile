.PHONY: test run-replay build-docker

test:
pytest -q

run-replay:
python -m hoops_edge scan --replay odds=tests/fixtures/odds/2024-02-24_bos_at_nyk.json --conf east --date 2024-02-24

build-docker:
docker build -t hoops-edge .
