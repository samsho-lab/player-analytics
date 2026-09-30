import math

import pytest

from analytics.stats import two_proportion_ztest


def test_known_example():
    # 200/1000 vs 250/1000: pooled p = 0.225, z = 0.05 / sqrt(0.225 * 0.775 * 0.002) ≈ 2.677
    t = two_proportion_ztest(200, 1000, 250, 1000)
    assert t.rate_a == 0.2
    assert t.rate_b == 0.25
    assert t.lift == pytest.approx(0.25)
    assert t.z == pytest.approx(2.6774, abs=1e-3)
    assert t.p_value == pytest.approx(0.00742, abs=1e-4)
    assert t.ci_low < 0.05 < t.ci_high


def test_identical_groups_are_not_significant():
    t = two_proportion_ztest(300, 1000, 300, 1000)
    assert t.z == 0
    assert t.p_value == pytest.approx(1.0)


def test_symmetry():
    ab = two_proportion_ztest(120, 800, 150, 820)
    ba = two_proportion_ztest(150, 820, 120, 800)
    assert ab.z == pytest.approx(-ba.z)
    assert ab.p_value == pytest.approx(ba.p_value)


def test_all_or_nothing_does_not_divide_by_zero():
    t = two_proportion_ztest(0, 50, 0, 50)
    assert t.z == 0 and not math.isnan(t.p_value)


def test_empty_group_is_an_error():
    with pytest.raises(ValueError):
        two_proportion_ztest(0, 0, 5, 10)
