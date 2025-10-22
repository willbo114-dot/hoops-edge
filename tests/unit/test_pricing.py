from hoops_edge.models.pricing import american_to_probability, probability_to_american


def test_round_trip_conversion():
    prob = american_to_probability(-150)
    odds = probability_to_american(prob)
    assert isinstance(odds, int)
    assert odds < 0
