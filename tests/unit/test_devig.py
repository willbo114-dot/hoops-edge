from hoops_edge.models.pricing import american_to_probability, devig_two_way


def test_american_to_probability_positive():
    assert round(american_to_probability(110), 4) == 0.4762


def test_devig_two_way_proportional():
    p_home, p_away = devig_two_way(-120, 100)
    total = round(p_home + p_away, 6)
    assert total == 1.0
    assert p_home > p_away
