from hoops_edge.ingest.mapping import TEAM_CONFERENCES, canonical_team, conference_for_team


def test_canonical_team_alias():
    assert canonical_team("BOS") == "Boston Celtics"


def test_conference_lookup():
    assert conference_for_team("Boston Celtics") == "east"
    assert conference_for_team("Non Team") == "all"
